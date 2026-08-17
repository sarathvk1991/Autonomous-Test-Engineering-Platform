"""ADR-0051 D3's coverage-shaped property check -- consumes the
traceability graph's `BindingCompletenessReport` (CAP-088, ADR-0048)
read-only. No new coverage-computation logic lives here: this module
performs a single dictionary lookup against a report the traceability graph
already computed; it never re-derives binding completeness itself.

**Optional, not part of the default `STEP_DEFINITION_PROPERTY_CHECKS`
set.** `STEP_DEFINITION_EVAL_SET`'s curated cases are isolated generation
contexts, scored independently of any real corpus run -- there is no real
`BindingCompletenessReport` to consult for them by default. This check is
for the composition point ADR-0051 D3 names: a caller scoring a
generator's output against a REAL run's own traceability graph can fold
`check_step_covered` into that run's own per-step check results, alongside
(not instead of) the structural checks in
:mod:`.step_definition_properties`.
"""

from __future__ import annotations

from eval_harness.models import PropertyCheckOutcome, PropertyCheckResult
from requirement_intelligence.traceability_graph.models import BindingCompletenessReport


def check_step_covered(
    step_text: str, binding_report: BindingCompletenessReport
) -> PropertyCheckResult:
    """Is ``step_text`` bound (not unbound/escalated) in ``binding_report``?

    A pure lookup against `BindingCompletenessReport.unbound_steps` -- the
    coverage-shaped defect this check catches (ADR-0051 D3, row 2: "an
    acceptance criterion with no corresponding generated scenario/step")
    manifests here as the step's own text appearing in that already-computed
    unbound set, keyed exactly the way
    `requirement_intelligence.traceability_graph.completeness.
    evaluate_binding_completeness` already keys it (first-seen step text,
    no re-derivation).
    """
    unbound_reasons = {step.step_text: step.reason for step in binding_report.unbound_steps}
    if step_text in unbound_reasons:
        reason = unbound_reasons[step_text]
        return PropertyCheckResult(
            check_name="step_covered",
            outcome=PropertyCheckOutcome.FAILED,
            reason=f"unbound in the traceability graph's binding report ({reason})",
        )
    return PropertyCheckResult(check_name="step_covered", outcome=PropertyCheckOutcome.PASSED)


__all__ = ["check_step_covered"]
