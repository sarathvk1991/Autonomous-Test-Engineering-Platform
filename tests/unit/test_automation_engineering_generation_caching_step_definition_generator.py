"""ADR-0050 D5's first build increment: `CachingStepDefinitionGenerator`
wrapping `LiveStepDefinitionGenerator`.

No test in this module calls a real LLM -- the same hand-written
`FakeProvider` pattern
`test_automation_engineering_generation_step_definition_generator.py` uses,
so the wrapped `LiveStepDefinitionGenerator` is real, only the provider
underneath it is a fake. The correctness properties ADR-0050 D1/D3/D4 rest
on are proven here directly, not assumed: a HIT returns exactly what the
prior MISS produced and skips the LLM call; a changed input MISSES rather
than staling; a HIT replays the STORED identity; a HIT is measurably
zero-cost in the token scorecard; wrapping changes nothing on a MISS.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from automation_engineering.catalog.models import StepCapture
from automation_engineering.generation.caching_step_definition_generator import (
    CachingStepDefinitionGenerator,
    GenerationCacheIdentityMismatchError,
)
from automation_engineering.generation.live_step_definition_generator import (
    LiveStepDefinitionGenerator,
    resolve_step_definition_identity,
)
from automation_engineering.generation.step_definition_generator import (
    StepDefinitionGenerationContext,
)
from automation_engineering.reuse.models import GherkinStepNeed
from requirement_intelligence.llm.generation_cache import GenerationCacheStore
from requirement_intelligence.llm.llm_models import LLMRequest, LLMResponse, LLMUsage
from requirement_intelligence.llm.providers.base_provider import LLMProvider
from requirement_intelligence.llm.token_usage import TokenUsageTracker
from shared.enums.base import ExecutionStatus, ProviderType

pytestmark = pytest.mark.unit


def _need(text: str = "I log in as {string}") -> GherkinStepNeed:
    return GherkinStepNeed(
        text=text,
        step_type="When",
        captures=(StepCapture(index=0, style="cucumber_expression", expression_type="string"),),
    )


def _context(
    need: GherkinStepNeed | None = None, **overrides: object
) -> StepDefinitionGenerationContext:
    defaults: dict[str, object] = {
        "need": need if need is not None else _need(),
        "target_package": "com.automation.steps",
        "customqa_constraints": ("c1", "c2"),
    }
    defaults.update(overrides)
    return StepDefinitionGenerationContext(**defaults)  # type: ignore[arg-type]


class FakeProvider(LLMProvider):
    """Mirrors `test_automation_engineering_generation_step_definition_
    generator.py`'s own `FakeProvider` exactly -- a hand-written fake, not a
    mock-library double, records every request it receives."""

    def __init__(
        self,
        *,
        text: str = "package com.automation.steps;\n",
        execution_status: ExecutionStatus = ExecutionStatus.COMPLETED,
    ) -> None:
        self._text = text
        self._execution_status = execution_status
        self.requests: list[LLMRequest] = []

    @property
    def provider_name(self) -> str:
        return "fake"

    def validate_connection(self) -> bool:
        return True

    def generate(self, request: LLMRequest) -> LLMResponse:
        self.requests.append(request)
        return LLMResponse(
            provider=ProviderType.GEMINI,
            model="fake-model",
            generated_text=self._text,
            execution_status=self._execution_status,
            usage=LLMUsage(prompt_tokens=10, completion_tokens=20, total_tokens=30),
        )

    @property
    def call_count(self) -> int:
        return len(self.requests)


#: Matches exactly what `FakeProvider.generate` echoes back
#: (`provider=ProviderType.GEMINI`, `model="fake-model"`) -- the identity a
#: caller would supply pre-call, per `resolve_step_definition_identity`'s
#: own contract, knowing in advance which provider/model it wired in.
_MATCHING_IDENTITY_KWARGS: dict[str, str] = {
    "provider": str(ProviderType.GEMINI),
    "model": "fake-model",
}


def _decorator(
    *,
    inner_provider: FakeProvider | None = None,
    store: GenerationCacheStore,
    usage_recorder: TokenUsageTracker | None = None,
    identity_kwargs: dict[str, str] | None = None,
) -> tuple[CachingStepDefinitionGenerator, FakeProvider]:
    provider = inner_provider if inner_provider is not None else FakeProvider()
    inner = LiveStepDefinitionGenerator(provider, usage_recorder=usage_recorder)
    identity = resolve_step_definition_identity(**(identity_kwargs or _MATCHING_IDENTITY_KWARGS))
    decorator = CachingStepDefinitionGenerator(
        inner, store, identity, usage_recorder=usage_recorder
    )
    return decorator, provider


# ---------------------------------------------------------------------------
# HIT correctness -- the make-or-break proof
# ---------------------------------------------------------------------------


class TestHitCorrectness:
    def test_second_call_with_the_same_context_hits_and_skips_the_llm(
        self, tmp_path: Path
    ) -> None:
        store = GenerationCacheStore(tmp_path)
        decorator, provider = _decorator(store=store)
        context = _context()

        first_result = decorator.generate(context)
        second_result = decorator.generate(context)

        assert second_result == first_result
        assert provider.call_count == 1  # the LLM was called exactly once, not twice

    def test_hit_returns_the_identical_text_a_fresh_generation_would_have(
        self, tmp_path: Path
    ) -> None:
        """A HIT must return what a FRESH generation for the SAME input
        would produce -- proven by comparing against an entirely
        independent, never-cached generator call for the identical
        context."""
        store = GenerationCacheStore(tmp_path)
        context = _context()
        decorator, _ = _decorator(store=store)
        decorator.generate(context)  # MISS, populates the cache

        hit_result = decorator.generate(context)  # HIT

        independent_provider = FakeProvider()  # same canned text as the original
        independent_result = LiveStepDefinitionGenerator(independent_provider).generate(context)
        assert hit_result == independent_result

    def test_two_independent_decorator_instances_sharing_a_store_hit_across_instances(
        self, tmp_path: Path
    ) -> None:
        """Proves cross-run reuse, not merely intra-instance memoization --
        the entire point of an on-disk store (ADR-0050 D2)."""
        store = GenerationCacheStore(tmp_path)
        context = _context()
        first_decorator, _first_provider = _decorator(store=store)
        first_decorator.generate(context)

        second_provider = FakeProvider(text="should never be reached")
        second_decorator, _ = _decorator(store=store, inner_provider=second_provider)
        result = second_decorator.generate(context)

        assert result == "package com.automation.steps;\n"  # the FIRST decorator's own output
        assert second_provider.call_count == 0  # the second instance's LLM was never called


# ---------------------------------------------------------------------------
# MISS on a changed input -- the naive-key defect this cache must NOT repeat
# ---------------------------------------------------------------------------


class TestMissOnChange:
    def test_a_changed_page_object_interface_with_step_text_unchanged_misses(
        self, tmp_path: Path
    ) -> None:
        """The exact shape of the naive-key defect ADR-0050 D1 found (an
        edited narrative with an unchanged title, silently missed by a
        `REQ-*`-only key): here, `need.text` (the L3 analogue of a `REQ-*`
        id) stays IDENTICAL while `page_object_interface` changes. A correct
        cache must MISS and regenerate, never silently reuse the earlier
        artifact for a materially different input."""
        store = GenerationCacheStore(tmp_path)
        decorator, provider = _decorator(store=store)
        need = _need("I log in as {string}")

        decorator.generate(_context(need, page_object_interface=None))
        decorator.generate(_context(need, page_object_interface="com.automation.pages.LoginPage"))

        assert provider.call_count == 2  # both calls reached the LLM -- no stale hit

    def test_a_changed_customqa_constraint_misses(self, tmp_path: Path) -> None:
        store = GenerationCacheStore(tmp_path)
        decorator, provider = _decorator(store=store)
        need = _need()

        decorator.generate(_context(need, customqa_constraints=("c1",)))
        decorator.generate(_context(need, customqa_constraints=("c1", "c2")))

        assert provider.call_count == 2

    def test_a_changed_step_text_misses(self, tmp_path: Path) -> None:
        store = GenerationCacheStore(tmp_path)
        decorator, provider = _decorator(store=store)

        decorator.generate(_context(_need("I log in as {string}")))
        decorator.generate(_context(_need("I log out")))

        assert provider.call_count == 2


# ---------------------------------------------------------------------------
# Identity replay on a HIT
# ---------------------------------------------------------------------------


class TestIdentityReplay:
    def test_hit_replays_the_stored_identity_not_a_fresh_one(self, tmp_path: Path) -> None:
        store = GenerationCacheStore(tmp_path)
        context = _context()
        first_decorator, _ = _decorator(store=store)
        first_decorator.generate(context)
        original_identity = first_decorator.last_identity
        assert original_identity is not None

        second_decorator, _ = _decorator(store=store, inner_provider=FakeProvider())
        second_decorator.generate(context)

        assert second_decorator.last_identity == original_identity

    def test_no_identity_before_any_call(self, tmp_path: Path) -> None:
        decorator, _ = _decorator(store=GenerationCacheStore(tmp_path))
        assert decorator.last_identity is None


# ---------------------------------------------------------------------------
# Token scorecard -- ADR-0050 D3 Gap 2
# ---------------------------------------------------------------------------


class TestScorecard:
    def test_a_hit_records_a_cache_hit_not_a_measured_or_unmeasured_call(
        self, tmp_path: Path
    ) -> None:
        store = GenerationCacheStore(tmp_path)
        tracker = TokenUsageTracker()
        context = _context()
        decorator, _ = _decorator(store=store, usage_recorder=tracker)

        decorator.generate(context)  # MISS -- inner records a real, measured call
        decorator.generate(context)  # HIT -- the decorator records a cache hit

        totals = tracker.by_call_type()["step_definition_generation"]
        assert totals.call_count == 1  # exactly the one real LLM call
        assert totals.total_tokens == 30  # the MISS's own real usage, unchanged
        assert totals.cache_hit_count == 1  # the HIT, verified zero-cost
        assert totals.unmeasured_call_count == 0  # never conflated with "unmeasured"

    def test_no_recorder_is_a_no_op(self, tmp_path: Path) -> None:
        store = GenerationCacheStore(tmp_path)
        decorator, _ = _decorator(store=store)  # no usage_recorder
        context = _context()

        decorator.generate(context)
        result = decorator.generate(context)  # HIT, still no recorder

        assert result  # unaffected by the omission


# ---------------------------------------------------------------------------
# Additive: a MISS behaves exactly as an unwrapped LiveStepDefinitionGenerator
# ---------------------------------------------------------------------------


class TestAdditiveOnMiss:
    def test_miss_sends_the_identical_prompt_a_bare_live_generator_would(
        self, tmp_path: Path
    ) -> None:
        store = GenerationCacheStore(tmp_path)
        context = _context()

        wrapped_provider = FakeProvider()
        decorator, _ = _decorator(store=store, inner_provider=wrapped_provider)
        decorator.generate(context)

        bare_provider = FakeProvider()
        LiveStepDefinitionGenerator(bare_provider).generate(context)

        assert wrapped_provider.requests[0].prompt == bare_provider.requests[0].prompt

    def test_miss_returns_the_generated_text_verbatim(self, tmp_path: Path) -> None:
        store = GenerationCacheStore(tmp_path)
        java = "package com.automation.steps;\n\npublic class LoginSteps {}\n"
        decorator, _ = _decorator(store=store, inner_provider=FakeProvider(text=java))

        result = decorator.generate(_context())

        assert result == java


# ---------------------------------------------------------------------------
# Identity-mismatch safety
# ---------------------------------------------------------------------------


class TestIdentityMismatchSafety:
    def test_a_mismatched_static_identity_raises_on_miss_and_stores_nothing(
        self, tmp_path: Path
    ) -> None:
        store = GenerationCacheStore(tmp_path)
        wrong_identity_kwargs = {"provider": str(ProviderType.GEMINI), "model": "wrong-model"}
        decorator, provider = _decorator(
            store=store, identity_kwargs=wrong_identity_kwargs
        )

        with pytest.raises(GenerationCacheIdentityMismatchError):
            decorator.generate(_context())

        assert provider.call_count == 1  # the LLM WAS called (a real MISS attempt)
        # nothing was written under either identity's key -- confirmed by re-running
        # with the correct identity and observing a fresh MISS, not a poisoned HIT
        correct_decorator, correct_provider = _decorator(store=store)
        correct_decorator.generate(_context())
        assert correct_provider.call_count == 1
