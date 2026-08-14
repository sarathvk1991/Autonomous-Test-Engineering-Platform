"""Unit tests for token-usage-by-call-type instrumentation.

Deterministic and provider-free throughout: every usage value is stubbed
directly as an :class:`LLMUsage`, per the module's own "no new live run
required to build/test it" scope -- capture from a real LLM is exercised by
the existing live paths (``test_gemini_provider.py``), not here.
"""

from __future__ import annotations

from typing import Any

from requirement_intelligence.llm.llm_models import LLMUsage
from requirement_intelligence.llm.token_usage import TokenUsageTotals, TokenUsageTracker


class TestTokenUsageTracker:
    def test_starts_empty(self) -> None:
        tracker = TokenUsageTracker()
        assert tracker.by_call_type() == {}
        assert tracker.grand_total() == TokenUsageTotals()
        assert tracker.distribution() == {}

    def test_single_call_recorded_under_its_call_type(self) -> None:
        tracker = TokenUsageTracker()
        tracker.record(
            "step_definition_generation",
            LLMUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150),
        )
        totals = tracker.by_call_type()["step_definition_generation"]
        assert totals.call_count == 1
        assert totals.unmeasured_call_count == 0
        assert totals.prompt_tokens == 100
        assert totals.completion_tokens == 50
        assert totals.total_tokens == 150

    def test_multiple_calls_same_call_type_accumulate(self) -> None:
        tracker = TokenUsageTracker()
        tracker.record(
            "page_object_generation",
            LLMUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150),
        )
        tracker.record(
            "page_object_generation",
            LLMUsage(prompt_tokens=200, completion_tokens=75, total_tokens=275),
        )
        totals = tracker.by_call_type()["page_object_generation"]
        assert totals.call_count == 2
        assert totals.prompt_tokens == 300
        assert totals.completion_tokens == 125
        assert totals.total_tokens == 425

    def test_per_call_type_attribution_is_isolated(self) -> None:
        """Nitin's own example: attribution must separate call types, not
        blend them -- his '60%/15%' scenario is meaningless if two call
        types share one bucket."""
        tracker = TokenUsageTracker()
        tracker.record(
            "page_object_generation",
            LLMUsage(prompt_tokens=200, completion_tokens=100, total_tokens=300),
        )
        tracker.record(
            "page_object_generation",
            LLMUsage(prompt_tokens=0, completion_tokens=0, total_tokens=0),
        )
        tracker.record(
            "step_definition_generation",
            LLMUsage(prompt_tokens=50, completion_tokens=50, total_tokens=100),
        )
        by_type = tracker.by_call_type()
        assert by_type["page_object_generation"].total_tokens == 300
        assert by_type["page_object_generation"].call_count == 2
        assert by_type["step_definition_generation"].total_tokens == 100
        assert by_type["step_definition_generation"].call_count == 1

    def test_unmeasured_usage_is_counted_not_dropped(self) -> None:
        tracker = TokenUsageTracker()
        tracker.record("feature_content_generation", None)
        totals = tracker.by_call_type()["feature_content_generation"]
        assert totals.call_count == 1
        assert totals.unmeasured_call_count == 1
        assert totals.total_tokens == 0

    def test_grand_total_sums_every_call_type(self) -> None:
        tracker = TokenUsageTracker()
        tracker.record(
            "page_object_generation",
            LLMUsage(prompt_tokens=200, completion_tokens=100, total_tokens=300),
        )
        tracker.record(
            "step_definition_generation",
            LLMUsage(prompt_tokens=50, completion_tokens=25, total_tokens=75),
        )
        grand = tracker.grand_total()
        assert grand.call_count == 2
        assert grand.total_tokens == 375
        assert grand.prompt_tokens == 250
        assert grand.completion_tokens == 125

    def test_distribution_matches_nitins_own_worked_example(self) -> None:
        """Stage A = 300 tokens, stage B = 100 tokens -- A=75%, B=25%,
        total=400, exactly the worked example from the build's own
        verification plan."""
        tracker = TokenUsageTracker()
        tracker.record(
            "stage_a",
            LLMUsage(prompt_tokens=200, completion_tokens=100, total_tokens=300),
        )
        tracker.record(
            "stage_b",
            LLMUsage(prompt_tokens=80, completion_tokens=20, total_tokens=100),
        )
        assert tracker.grand_total().total_tokens == 400
        distribution = tracker.distribution()
        assert distribution == {"stage_a": 75.0, "stage_b": 25.0}

    def test_distribution_is_zero_for_every_call_type_when_grand_total_is_zero(self) -> None:
        tracker = TokenUsageTracker()
        tracker.record("feature_content_generation", None)
        tracker.record("feature_remediation", None)
        assert tracker.distribution() == {
            "feature_content_generation": 0.0,
            "feature_remediation": 0.0,
        }

    def test_as_dict_is_a_complete_json_serializable_snapshot(self) -> None:
        tracker = TokenUsageTracker()
        tracker.record(
            "step_definition_generation",
            LLMUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150),
        )
        snapshot: dict[str, Any] = tracker.as_dict()
        by_call_type: dict[str, Any] = snapshot["by_call_type"]
        grand_total: dict[str, Any] = snapshot["grand_total"]
        distribution_pct: dict[str, Any] = snapshot["distribution_pct"]
        assert by_call_type["step_definition_generation"]["total_tokens"] == 150
        assert grand_total["total_tokens"] == 150
        assert distribution_pct["step_definition_generation"] == 100.0

    def test_by_call_type_returns_a_copy_not_live_internal_state(self) -> None:
        tracker = TokenUsageTracker()
        tracker.record("stage_a", LLMUsage(total_tokens=10))
        snapshot = tracker.by_call_type()
        snapshot["stage_a"] = TokenUsageTotals(total_tokens=999)
        assert tracker.by_call_type()["stage_a"].total_tokens == 10

    def test_insertion_order_is_preserved(self) -> None:
        tracker = TokenUsageTracker()
        tracker.record("third", LLMUsage(total_tokens=1))
        tracker.record("first", LLMUsage(total_tokens=1))
        tracker.record("second", LLMUsage(total_tokens=1))
        assert list(tracker.by_call_type().keys()) == ["third", "first", "second"]


class TestCacheHitRecording:
    """ADR-0050 D3's "Gap 2" closure: a cache hit is *zero-cost-verified*,
    a distinct fact from both a measured and an unmeasured LLM call."""

    def test_cache_hit_increments_cache_hit_count_only(self) -> None:
        tracker = TokenUsageTracker()
        tracker.record_cache_hit("step_definition_generation")

        totals = tracker.by_call_type()["step_definition_generation"]
        assert totals.cache_hit_count == 1
        assert totals.call_count == 0
        assert totals.unmeasured_call_count == 0
        assert totals.total_tokens == 0

    def test_cache_hit_is_distinct_from_unmeasured(self) -> None:
        """The exact scorecard confusion ADR-0050 D3 named: recording a hit
        via `record(call_type, None)` would inflate `unmeasured_call_count`
        -- an incompleteness signal -- rather than showing a verified
        saving. This proves the two buckets never conflate."""
        tracker = TokenUsageTracker()
        tracker.record("step_definition_generation", None)
        tracker.record_cache_hit("step_definition_generation")

        totals = tracker.by_call_type()["step_definition_generation"]
        assert totals.unmeasured_call_count == 1
        assert totals.cache_hit_count == 1

    def test_multiple_hits_accumulate(self) -> None:
        tracker = TokenUsageTracker()
        tracker.record_cache_hit("step_definition_generation")
        tracker.record_cache_hit("step_definition_generation")
        tracker.record_cache_hit("step_definition_generation")

        assert tracker.by_call_type()["step_definition_generation"].cache_hit_count == 3

    def test_hits_and_measured_calls_coexist_in_the_same_call_type(self) -> None:
        """The measured saving a re-run should show: a first run's real
        call, then a second run's hit for the same call type."""
        tracker = TokenUsageTracker()
        tracker.record(
            "step_definition_generation",
            LLMUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150),
        )
        tracker.record_cache_hit("step_definition_generation")

        totals = tracker.by_call_type()["step_definition_generation"]
        assert totals.call_count == 1
        assert totals.total_tokens == 150
        assert totals.cache_hit_count == 1


class TestTokenUsageTotals:
    def test_plus_sums_every_field(self) -> None:
        a = TokenUsageTotals(
            call_count=1,
            unmeasured_call_count=0,
            cache_hit_count=1,
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15,
        )
        b = TokenUsageTotals(
            call_count=2,
            unmeasured_call_count=1,
            cache_hit_count=2,
            prompt_tokens=20,
            completion_tokens=10,
            total_tokens=30,
        )
        summed = a.plus(b)
        assert summed.call_count == 3
        assert summed.unmeasured_call_count == 1
        assert summed.cache_hit_count == 3
        assert summed.prompt_tokens == 30
        assert summed.completion_tokens == 15
        assert summed.total_tokens == 45

    def test_default_is_all_zero(self) -> None:
        totals = TokenUsageTotals()
        assert totals.call_count == 0
        assert totals.unmeasured_call_count == 0
        assert totals.cache_hit_count == 0
        assert totals.prompt_tokens == 0
        assert totals.completion_tokens == 0
        assert totals.total_tokens == 0
