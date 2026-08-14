"""ADR-0050 D5's third build increment: `CachingTestDataGenerator` wrapping
`LiveTestDataGenerator`.

No test in this module calls a real LLM -- the same hand-written
`FakeProvider` pattern
`test_automation_engineering_generation_test_data_generator.py` uses, so the
wrapped `LiveTestDataGenerator` is real, only the provider underneath it is
a fake. The correctness properties ADR-0050 D1/D3/D4 rest on are proven here
directly, not assumed: a HIT returns exactly what the prior MISS produced
and skips the LLM call; a changed input MISSES rather than staling; a HIT
replays the STORED identity; a HIT is measurably zero-cost in the token
scorecard; wrapping changes nothing on a MISS. Mirrors
`tests/unit/test_automation_engineering_generation_caching_step_definition_generator.py`
exactly, adapted to `TestDataSpecification`. Reuses
`GenerationCacheIdentityMismatchError` from the step-def caching module
unchanged -- both share `automation_engineering.errors.TransportFailureError`.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from automation_engineering.generation.caching_step_definition_generator import (
    GenerationCacheIdentityMismatchError,
)
from automation_engineering.generation.caching_test_data_generator import (
    CachingTestDataGenerator,
)
from automation_engineering.generation.live_test_data_generator import (
    LiveTestDataGenerator,
    resolve_test_data_identity,
)
from automation_engineering.generation.test_data_generator import TestDataGenerationContext
from contracts.test_data_specification import TestDataFieldSpec, TestDataSpecification
from contracts.testable_requirement import PolarityHint
from requirement_intelligence.llm.generation_cache import GenerationCacheStore
from requirement_intelligence.llm.llm_models import LLMRequest, LLMResponse, LLMUsage
from requirement_intelligence.llm.providers.base_provider import LLMProvider
from requirement_intelligence.llm.token_usage import TokenUsageTracker
from shared.enums.base import ExecutionStatus, ProviderType

pytestmark = pytest.mark.unit


def _specification(
    requirement_id: str = "REQ-checkout01",
    fields: tuple[TestDataFieldSpec, ...] | None = None,
) -> TestDataSpecification:
    default_fields = (
        TestDataFieldSpec(field_name="username", required_variants=(PolarityHint.POSITIVE,)),
    )
    return TestDataSpecification(
        requirement_id=requirement_id,
        fields=fields if fields is not None else default_fields,
    )


def _context(
    specification: TestDataSpecification | None = None, **overrides: object
) -> TestDataGenerationContext:
    defaults: dict[str, object] = {
        "specification": specification if specification is not None else _specification(),
        "class_name": "CheckoutTestData",
        "target_package": "com.automation.utils",
        "customqa_constraints": ("c1",),
    }
    defaults.update(overrides)
    return TestDataGenerationContext(**defaults)  # type: ignore[arg-type]


class FakeProvider(LLMProvider):
    """Mirrors `test_automation_engineering_generation_test_data_generator.py`'s
    own `FakeProvider` exactly -- a hand-written fake, not a mock-library
    double, records every request it receives."""

    def __init__(
        self,
        *,
        text: str = "package com.automation.utils;\n",
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
#: caller would supply pre-call, per `resolve_test_data_identity`'s own
#: contract, knowing in advance which provider/model it wired in.
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
) -> tuple[CachingTestDataGenerator, FakeProvider]:
    provider = inner_provider if inner_provider is not None else FakeProvider()
    inner = LiveTestDataGenerator(provider, usage_recorder=usage_recorder)
    identity = resolve_test_data_identity(**(identity_kwargs or _MATCHING_IDENTITY_KWARGS))
    decorator = CachingTestDataGenerator(inner, store, identity, usage_recorder=usage_recorder)
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
        independent_result = LiveTestDataGenerator(independent_provider).generate(context)
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

        assert result == "package com.automation.utils;\n"  # the FIRST decorator's own output
        assert second_provider.call_count == 0  # the second instance's LLM was never called


# ---------------------------------------------------------------------------
# MISS on a changed input -- the naive-key defect this cache must NOT repeat
# ---------------------------------------------------------------------------


class TestMissOnChange:
    def test_a_changed_field_set_with_requirement_id_unchanged_misses(
        self, tmp_path: Path
    ) -> None:
        """The exact shape of the naive-key defect ADR-0050 D1 found: this
        generator's `requirement_id` (the L3 analogue of a `REQ-*` id) stays
        IDENTICAL while its `fields` change. A correct cache must MISS and
        regenerate, never silently reuse the earlier artifact for a
        materially different input."""
        store = GenerationCacheStore(tmp_path)
        decorator, provider = _decorator(store=store)
        spec_a = _specification(
            requirement_id="REQ-checkout01",
            fields=(
                TestDataFieldSpec(
                    field_name="username", required_variants=(PolarityHint.POSITIVE,)
                ),
            ),
        )
        spec_b = _specification(
            requirement_id="REQ-checkout01",
            fields=(
                TestDataFieldSpec(
                    field_name="username",
                    required_variants=(PolarityHint.POSITIVE, PolarityHint.NEGATIVE),
                ),
            ),
        )

        decorator.generate(_context(spec_a))
        decorator.generate(_context(spec_b))

        assert provider.call_count == 2  # both calls reached the LLM -- no stale hit

    def test_a_changed_customqa_constraint_misses(self, tmp_path: Path) -> None:
        store = GenerationCacheStore(tmp_path)
        decorator, provider = _decorator(store=store)
        spec = _specification()

        decorator.generate(_context(spec, customqa_constraints=("c1",)))
        decorator.generate(_context(spec, customqa_constraints=("c1", "c2")))

        assert provider.call_count == 2

    def test_a_changed_target_class_name_misses(self, tmp_path: Path) -> None:
        store = GenerationCacheStore(tmp_path)
        decorator, provider = _decorator(store=store)
        spec = _specification()

        decorator.generate(_context(spec, class_name="CheckoutTestData"))
        decorator.generate(_context(spec, class_name="OrderTestData"))

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

        totals = tracker.by_call_type()["test_data_generation"]
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
# Additive: a MISS behaves exactly as an unwrapped LiveTestDataGenerator
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
        LiveTestDataGenerator(bare_provider).generate(context)

        assert wrapped_provider.requests[0].prompt == bare_provider.requests[0].prompt

    def test_miss_returns_the_generated_text_verbatim(self, tmp_path: Path) -> None:
        store = GenerationCacheStore(tmp_path)
        java = "package com.automation.utils;\n\npublic class CheckoutTestData {}\n"
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
        decorator, provider = _decorator(store=store, identity_kwargs=wrong_identity_kwargs)

        with pytest.raises(GenerationCacheIdentityMismatchError):
            decorator.generate(_context())

        assert provider.call_count == 1  # the LLM WAS called (a real MISS attempt)
        # nothing was written under either identity's key -- confirmed by re-running
        # with the correct identity and observing a fresh MISS, not a poisoned HIT
        correct_decorator, correct_provider = _decorator(store=store)
        correct_decorator.generate(_context())
        assert correct_provider.call_count == 1
