"""Proves `check_requirement_covered` CONSUMES CAP-088's `CompletenessReport`
read-only (ADR-0051 D3/D4) -- a lookup against an already-computed report,
never a re-derivation of requirement completeness itself. Mirrors
`test_eval_harness_coverage.py`'s own proof shape one graph level up.
"""

from __future__ import annotations

from eval_harness.feature_content_coverage import check_requirement_covered
from eval_harness.models import PropertyCheckOutcome
from requirement_intelligence.traceability_graph.models import (
    CompletenessReport,
    UncoveredRequirement,
)

_UNCOVERED = UncoveredRequirement(requirement_id="REQ-c64bb0f7", reason="no_scenario")

_REPORT = CompletenessReport(
    graph_id="graph-1",
    total_requirements=2,
    tested_requirement_count=1,
    untested_requirement_count=1,
    coverage_percentage=50.0,
    untested_requirements=(_UNCOVERED,),
)


class TestCheckRequirementCovered:
    def test_a_covered_requirement_passes(self) -> None:
        result = check_requirement_covered("REQ-f90f23fa", _REPORT)
        assert result.outcome == PropertyCheckOutcome.PASSED

    def test_an_uncovered_requirement_fails_with_the_reports_own_reason(self) -> None:
        result = check_requirement_covered(_UNCOVERED.requirement_id, _REPORT)
        assert result.outcome == PropertyCheckOutcome.FAILED
        assert "no_scenario" in result.reason

    def test_never_recomputes_the_report_itself(self) -> None:
        """A requirement id absent from `untested_requirements` is trusted
        as covered without inspecting `total_requirements`/
        `tested_requirement_count`/anything else on the report -- this
        check performs one lookup, nothing more."""
        empty_report = CompletenessReport(
            graph_id="graph-2",
            total_requirements=0,
            tested_requirement_count=0,
            untested_requirement_count=0,
            coverage_percentage=0.0,
            untested_requirements=(),
        )
        result = check_requirement_covered("REQ-anything", empty_report)
        assert result.outcome == PropertyCheckOutcome.PASSED
