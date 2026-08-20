"""ADR-0051 D3's coverage-shaped property check for feature-content --
consumes the traceability graph's `CompletenessReport` (CAP-088, ADR-0048)
read-only. No new coverage-computation logic lives here: this module
performs a single lookup against a report the traceability graph already
computed; it never re-derives requirement completeness itself.

Mirrors `coverage.py`'s own `check_step_covered` exactly, one level up the
same graph: that check asks "is this STEP bound to a step definition,"
keyed against `BindingCompletenessReport.unbound_steps`; this one asks "does
this REQUIREMENT reach a full requirement -> scenario -> step chain," keyed
against `CompletenessReport.untested_requirements` -- the same graph,
`requirement_intelligence.traceability_graph.completeness.
evaluate_completeness` already computes, at a different node level.

**Optional, not part of the default `FEATURE_CONTENT_PROPERTY_CHECKS`
set**, for the identical reason `check_step_covered` is optional: `FEATURE_
CONTENT_EVAL_SET`'s curated cases are isolated generation contexts, scored
independently of any real corpus run -- there is no real `CompletenessReport`
to consult for them by default. This check is for a caller scoring a
generator's output against a REAL run's own traceability graph, folding
`check_requirement_covered` into that run's own per-requirement check
results, alongside (not instead of) the structural checks in
:mod:`.feature_content_properties`.
"""

from __future__ import annotations

from eval_harness.models import PropertyCheckOutcome, PropertyCheckResult
from requirement_intelligence.traceability_graph.models import CompletenessReport


def check_requirement_covered(
    requirement_id: str, completeness_report: CompletenessReport
) -> PropertyCheckResult:
    """Does ``requirement_id`` reach a full requirement -> scenario -> step
    chain in ``completeness_report``?

    A pure lookup against `CompletenessReport.untested_requirements` -- the
    coverage-shaped defect this check catches (ADR-0051 D3, row 2: "an
    acceptance criterion with no corresponding generated scenario/step")
    manifests here as the requirement's own id appearing in that
    already-computed untested set, keyed exactly the way
    `requirement_intelligence.traceability_graph.completeness.
    evaluate_completeness` already keys it -- no re-derivation.
    """
    reasons = {
        untested.requirement_id: untested.reason
        for untested in completeness_report.untested_requirements
    }
    if requirement_id in reasons:
        reason = reasons[requirement_id]
        return PropertyCheckResult(
            check_name="requirement_covered",
            outcome=PropertyCheckOutcome.FAILED,
            reason=f"untested in the traceability graph's completeness report ({reason})",
        )
    return PropertyCheckResult(
        check_name="requirement_covered", outcome=PropertyCheckOutcome.PASSED
    )


__all__ = ["check_requirement_covered"]
