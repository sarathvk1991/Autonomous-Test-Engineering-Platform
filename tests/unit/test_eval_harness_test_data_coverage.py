"""Proves `check_requirement_covered` (built for feature-content,
`eval_harness.feature_content_coverage`) is genuinely generic -- reusable
VERBATIM for test-data's own coverage-shaped question ("does this
requirement reach a full traceability chain") without a third,
test-data-specific coverage module. No new coverage-computation logic is
introduced by this file; it is a reuse proof, not a new check.

CAP-088's `CompletenessReport` answers a REQUIREMENT-level question --
"did requirement X reach a scenario/step at all" -- which is exactly as
relevant to test-data (spec-driven from the same `TestableRequirement`,
ADR-0044 D7) as it is to feature-content. Optional, not part of the default
`TEST_DATA_PROPERTY_CHECKS` set, for the identical reason it is optional for
the other two generators: the curated, isolated eval-set cases have no real
`CompletenessReport` to consult by default.
"""

from __future__ import annotations

from eval_harness.feature_content_coverage import check_requirement_covered
from eval_harness.models import PropertyCheckOutcome
from eval_harness.test_data_eval_set import TEST_DATA_EVAL_SET
from requirement_intelligence.traceability_graph.models import (
    CompletenessReport,
    UncoveredRequirement,
)

_CASE = next(
    case for case in TEST_DATA_EVAL_SET if case.case_id == "login_invalid_credentials_error"
)
_REQUIREMENT_ID = _CASE.context.specification.requirement_id

_UNCOVERED = UncoveredRequirement(requirement_id=_REQUIREMENT_ID, reason="no_scenario")

_REPORT = CompletenessReport(
    graph_id="graph-1",
    total_requirements=2,
    tested_requirement_count=1,
    untested_requirement_count=1,
    coverage_percentage=50.0,
    untested_requirements=(_UNCOVERED,),
)


class TestSameCoverageCheckReusedForTestData:
    def test_a_covered_test_data_requirement_passes(self) -> None:
        result = check_requirement_covered("REQ-not-in-this-report", _REPORT)
        assert result.outcome == PropertyCheckOutcome.PASSED

    def test_an_uncovered_test_data_requirement_fails(self) -> None:
        result = check_requirement_covered(_REQUIREMENT_ID, _REPORT)
        assert result.outcome == PropertyCheckOutcome.FAILED
        assert "no_scenario" in result.reason
