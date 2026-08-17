"""Proves `check_step_covered` CONSUMES CAP-088's `BindingCompletenessReport`
read-only (ADR-0051 D3/D4) -- a lookup against an already-computed report,
never a re-derivation of binding completeness itself.
"""

from __future__ import annotations

from eval_harness.coverage import check_step_covered
from eval_harness.models import PropertyCheckOutcome
from requirement_intelligence.traceability_graph.models import (
    BindingCompletenessReport,
    UnboundStep,
)

_UNBOUND = UnboundStep(
    step_id="STEP-1",
    step_text="the user attempts to login with {string} credentials",
    reason="escalated",
)

_REPORT = BindingCompletenessReport(
    graph_id="graph-1",
    total_steps=2,
    bound_step_count=1,
    unbound_step_count=1,
    coverage_percentage=50.0,
    unbound_steps=(_UNBOUND,),
)


class TestCheckStepCovered:
    def test_a_bound_step_passes(self) -> None:
        result = check_step_covered("a different, bound step", _REPORT)
        assert result.outcome == PropertyCheckOutcome.PASSED

    def test_an_unbound_step_fails_with_the_reports_own_reason(self) -> None:
        result = check_step_covered(_UNBOUND.step_text, _REPORT)
        assert result.outcome == PropertyCheckOutcome.FAILED
        assert "escalated" in result.reason

    def test_never_recomputes_the_report_itself(self) -> None:
        """A step text absent from `unbound_steps` is trusted as bound
        without inspecting `total_steps`/`bound_step_count`/anything else on
        the report -- this check performs one lookup, nothing more."""
        empty_report = BindingCompletenessReport(
            graph_id="graph-2",
            total_steps=0,
            bound_step_count=0,
            unbound_step_count=0,
            coverage_percentage=0.0,
            unbound_steps=(),
        )
        result = check_step_covered("any step text at all", empty_report)
        assert result.outcome == PropertyCheckOutcome.PASSED
