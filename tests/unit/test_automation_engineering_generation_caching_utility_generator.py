"""ADR-0050's artifact-generation cache, extended to utilities:
`CachingUtilityGenerator` wrapping `LiveUtilityGenerator` -- the FIFTH and
FINAL generator covered (after step-def, feature-content, test-data,
page-object), closing the "one remaining generator" gap every prior
increment's own Consequences section named as the next trigger.

No test in this module calls a real LLM -- the same hand-written
`FakeProvider` pattern
`test_automation_engineering_generation_utility_generator.py` uses, so the
wrapped `LiveUtilityGenerator` is real, only the provider underneath it is a
fake. Mirrors
`test_automation_engineering_generation_caching_page_object_generator.py`'s
own test structure exactly, plus the same BIND/CACHE COMPOSITION proof
section (utility generation has the identical reuse-decide-then-generate
shape page objects do -- confirmed, not assumed, by the immediately
preceding identity task): a utility need the reuse engine BINDS to an
existing tracked asset never reaches this decorator's own `generate` at
all.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from automation_engineering.catalog.models import AssetCatalog, JavaMethod, UtilityAsset
from automation_engineering.generation.caching_utility_generator import (
    CachingUtilityGenerator,
    GenerationCacheIdentityMismatchError,
)
from automation_engineering.generation.live_utility_generator import (
    LiveUtilityGenerator,
    resolve_utility_identity,
)
from automation_engineering.generation.models import BoundUtilityMethod, UtilityMethodNeed
from automation_engineering.generation.utility_generator import UtilityGenerationContext
from automation_engineering.generation.utility_orchestrator import orchestrate_utility_method
from automation_engineering.reuse.matcher import StubSemanticMatcher
from automation_engineering.reuse.models import GherkinStepNeed, MatchCandidate
from requirement_intelligence.llm.generation_cache import GenerationCacheStore
from requirement_intelligence.llm.llm_models import LLMRequest, LLMResponse, LLMUsage
from requirement_intelligence.llm.providers.base_provider import LLMProvider
from requirement_intelligence.llm.token_usage import TokenUsageTracker
from shared.enums.base import ExecutionStatus, ProviderType

pytestmark = pytest.mark.unit

_DEFAULT_METHOD_NAME = "data"


def _need(text: str = "read a test-data value by key") -> GherkinStepNeed:
    return GherkinStepNeed(text=text, step_type="UtilityAction", captures=())


def _context(
    need: GherkinStepNeed | None = None, **overrides: object
) -> UtilityGenerationContext:
    defaults: dict[str, object] = {
        "need": need if need is not None else _need(),
        "class_name": "TestDataReader",
        "target_package": "com.automation.utils",
        "customqa_constraints": ("c1", "c2"),
    }
    defaults.update(overrides)
    return UtilityGenerationContext(**defaults)  # type: ignore[arg-type]


def _java(class_name: str = "TestDataReader") -> str:
    return (
        "package com.automation.utils;\n\n"
        f"public final class {class_name} {{\n"
        f"    private {class_name}() {{\n"
        "    }\n"
        "}\n"
    )


class FakeProvider(LLMProvider):
    """Mirrors `test_automation_engineering_generation_utility_generator.py`'s
    own `FakeProvider` exactly."""

    def __init__(
        self,
        *,
        text: str | None = None,
        execution_status: ExecutionStatus = ExecutionStatus.COMPLETED,
    ) -> None:
        self._text = text if text is not None else _java()
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


#: Matches exactly what `FakeProvider.generate` echoes back.
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
) -> tuple[CachingUtilityGenerator, FakeProvider]:
    provider = inner_provider if inner_provider is not None else FakeProvider()
    inner = LiveUtilityGenerator(provider, usage_recorder=usage_recorder)
    identity = resolve_utility_identity(
        **(identity_kwargs or _MATCHING_IDENTITY_KWARGS)  # type: ignore[arg-type]
    )
    decorator = CachingUtilityGenerator(inner, store, identity, usage_recorder=usage_recorder)
    return decorator, provider


# ---------------------------------------------------------------------------
# HIT correctness -- the make-or-break proof
# ---------------------------------------------------------------------------


class TestHitCorrectness:
    def test_second_call_with_the_same_context_hits_and_skips_the_llm(self, tmp_path: Path) -> None:
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
        store = GenerationCacheStore(tmp_path)
        context = _context()
        decorator, _ = _decorator(store=store)
        decorator.generate(context)  # MISS, populates the cache

        hit_result = decorator.generate(context)  # HIT

        independent_provider = FakeProvider()  # same canned text as the original
        independent_result = LiveUtilityGenerator(independent_provider).generate(context)
        assert hit_result == independent_result

    def test_two_independent_decorator_instances_sharing_a_store_hit_across_instances(
        self, tmp_path: Path
    ) -> None:
        """Proves cross-run reuse, not merely intra-instance memoization."""
        store = GenerationCacheStore(tmp_path)
        context = _context()
        first_decorator, _first_provider = _decorator(store=store)
        first_decorator.generate(context)

        second_provider = FakeProvider(text="package com.automation.utils;\n// never reached\n")
        second_decorator, _ = _decorator(store=store, inner_provider=second_provider)
        result = second_decorator.generate(context)

        assert result == _java()  # the FIRST decorator's own output
        assert second_provider.call_count == 0  # the second instance's LLM was never called


# ---------------------------------------------------------------------------
# MISS on a changed input -- action text + captures + class name + target
# package + customqa constraints, the real utility generation payload
# ---------------------------------------------------------------------------


class TestMissOnChange:
    def test_a_changed_action_text_misses(self, tmp_path: Path) -> None:
        store = GenerationCacheStore(tmp_path)
        decorator, provider = _decorator(store=store)

        decorator.generate(_context(_need("read a test-data value by key")))
        decorator.generate(_context(_need("format a date")))

        assert provider.call_count == 2  # both reached the LLM -- no stale hit

    def test_a_changed_class_name_with_action_text_unchanged_misses(self, tmp_path: Path) -> None:
        """The exact shape of the naive-key defect ADR-0050 D1 found: the
        need text (the closest L3 analogue of a `REQ-*` id) stays IDENTICAL
        while `class_name` changes. A correct cache must MISS."""
        store = GenerationCacheStore(tmp_path)
        decorator, provider = _decorator(store=store)

        decorator.generate(_context(class_name="TestDataReader"))
        decorator.generate(_context(class_name="DateFormatter"))

        assert provider.call_count == 2

    def test_a_changed_customqa_constraint_misses(self, tmp_path: Path) -> None:
        store = GenerationCacheStore(tmp_path)
        decorator, provider = _decorator(store=store)

        decorator.generate(_context(customqa_constraints=("c1",)))
        decorator.generate(_context(customqa_constraints=("c1", "c2")))

        assert provider.call_count == 2

    def test_a_changed_target_package_misses(self, tmp_path: Path) -> None:
        store = GenerationCacheStore(tmp_path)
        decorator, provider = _decorator(store=store)

        decorator.generate(_context(target_package="com.automation.utils"))
        decorator.generate(_context(target_package="com.automation.other"))

        assert provider.call_count == 2

    def test_a_changed_capture_shape_misses(self, tmp_path: Path) -> None:
        """A capture-shape change (the closest utility analogue of
        page-object's signature-shape MISS) with class/action text
        unchanged -- part of the real payload's own `captures` field."""
        from automation_engineering.catalog.models import StepCapture

        store = GenerationCacheStore(tmp_path)
        decorator, provider = _decorator(store=store)
        need_no_captures = _need()
        need_with_capture = GherkinStepNeed(
            text=need_no_captures.text,
            step_type=need_no_captures.step_type,
            captures=(StepCapture(index=0, style="cucumber_expression", expression_type="string"),),
        )

        decorator.generate(_context(need_no_captures))
        decorator.generate(_context(need_with_capture))

        assert provider.call_count == 2

    def test_two_calls_with_identical_payloads_hit_regardless_of_object_identity(
        self, tmp_path: Path
    ) -> None:
        """The positive control for the MISS proofs above: two SEPARATELY
        constructed contexts with the SAME action text + class + constraints
        hit -- proving the key is a real content hash, not an accidental
        object-identity/id-based shortcut."""
        store = GenerationCacheStore(tmp_path)
        decorator, provider = _decorator(store=store)

        decorator.generate(_context())
        decorator.generate(_context())  # a fresh, separately-built, identical context

        assert provider.call_count == 1


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

        totals = tracker.by_call_type()["utility_generation"]
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
# Additive: a MISS behaves exactly as an unwrapped LiveUtilityGenerator
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
        LiveUtilityGenerator(bare_provider).generate(context)

        assert wrapped_provider.requests[0].prompt == bare_provider.requests[0].prompt

    def test_miss_returns_the_generated_text_verbatim(self, tmp_path: Path) -> None:
        store = GenerationCacheStore(tmp_path)
        java = _java()
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
        # Nothing was written under either identity's key -- confirmed by
        # re-running with the correct identity and observing a fresh MISS,
        # not a poisoned HIT.
        correct_decorator, correct_provider = _decorator(store=store)
        correct_decorator.generate(_context())
        assert correct_provider.call_count == 1


# ---------------------------------------------------------------------------
# The before -> after measure: a two-pass, multi-artifact proof, the SAME
# deterministic shape the step-def/feature-content/test-data/page-object
# increments measured (page-object deterministically only, no live traffic
# yet) -- here proven deterministically (stub-shaped, no live LLM in
# `make test`); the live number is the same shape, available once utility
# generation is wired and runs live.
# ---------------------------------------------------------------------------


class TestTwoPassMeasure:
    def test_pass_two_with_identical_inputs_makes_zero_generation_calls(
        self, tmp_path: Path
    ) -> None:
        store = GenerationCacheStore(tmp_path)
        class_names = ("TestDataReader", "DateFormatter", "EnvReader")
        contexts = [
            _context(_need(f"do the {name} action"), class_name=name) for name in class_names
        ]

        # Pass 1 -- three DIFFERENT fresh generations, one real LLM call each.
        pass_one_provider = FakeProvider(text=_java())
        pass_one_decorator, _ = _decorator(store=store, inner_provider=pass_one_provider)
        pass_one_results = [pass_one_decorator.generate(context) for context in contexts]
        assert pass_one_provider.call_count == 3

        # Pass 2 -- the IDENTICAL three inputs, a fresh decorator/provider
        # instance sharing the same on-disk store: every one HITS.
        pass_two_provider = FakeProvider(text="should never be reached")
        pass_two_decorator, _ = _decorator(store=store, inner_provider=pass_two_provider)
        pass_two_results = [pass_two_decorator.generate(context) for context in contexts]

        assert pass_two_provider.call_count == 0  # zero fresh generation calls
        assert pass_two_results == pass_one_results  # byte-identical output


# ---------------------------------------------------------------------------
# THE BIND/CACHE COMPOSITION -- utility generation's own extra reuse
# mechanism, confirmed (not assumed) to mirror page-object's, not the
# simpler always-generate shape the first three generators had. Bind (an
# existing tracked UtilityAsset already satisfies this need) and cache (we
# already generated this exact thing before) are orthogonal: bind never
# reaches this decorator's own generate() at all.
# ---------------------------------------------------------------------------


class TestBindNeverReachesTheCachingGenerator:
    def test_a_trusted_reuse_bind_never_calls_generate_or_touches_the_cache(
        self, tmp_path: Path
    ) -> None:
        asset = UtilityAsset(
            asset_id="UTIL-configfixture01",
            class_name="com.automation.utils.ConfigReader",
            fields=(),
            methods=(JavaMethod(name=_DEFAULT_METHOD_NAME, parameters=(), return_type="String"),),
            source_file="com/automation/utils/ConfigReader.java",
            content_hash="current-hash",
        )
        catalog = AssetCatalog(baseline_root="test-suite-baseline", utilities=(asset,))
        method_need = UtilityMethodNeed(need=_need(), method_name=_DEFAULT_METHOD_NAME)
        matcher = StubSemanticMatcher(
            {
                method_need.need.text: (
                    MatchCandidate(
                        asset_id=asset.asset_id, confidence=0.99, content_hash=asset.content_hash
                    ),
                )
            }
        )
        store = GenerationCacheStore(tmp_path)
        decorator, provider = _decorator(store=store)

        outcome = orchestrate_utility_method(method_need, catalog, matcher, decorator)

        assert isinstance(outcome, BoundUtilityMethod)
        assert provider.call_count == 0  # no LLM call
        assert decorator.last_identity is None  # generate() was never called at all
        # The store is genuinely untouched -- a later NoMatch generation for
        # the SAME context still MISSES, proving nothing was ever written
        # for the bound need.
        decorator.generate(_context())
        assert provider.call_count == 1

    def test_a_no_match_need_still_reaches_the_cache_normally(self, tmp_path: Path) -> None:
        """The contrast case: an empty catalog (guaranteed NoMatch) DOES
        reach the caching generator, and caches normally -- proving the
        bind test above is about bind specifically, not a broken wrapper."""
        catalog = AssetCatalog(baseline_root="test-suite-baseline")
        method_need = UtilityMethodNeed(need=_need(), method_name=_DEFAULT_METHOD_NAME)
        matcher = StubSemanticMatcher({method_need.need.text: ()})
        store = GenerationCacheStore(tmp_path)
        decorator, provider = _decorator(store=store)

        first = orchestrate_utility_method(method_need, catalog, matcher, decorator)
        second = orchestrate_utility_method(method_need, catalog, matcher, decorator)

        assert first.java_source == second.java_source  # type: ignore[union-attr]
        assert provider.call_count == 1  # the second call HIT the cache
