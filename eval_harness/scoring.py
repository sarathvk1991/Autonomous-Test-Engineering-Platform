"""ADR-0051 D2's scoring: turn one generator's per-case property-check
results into one :class:`~eval_harness.models.EvalScore`, keyed by
:class:`~requirement_intelligence.llm.generation_identity.GenerationIdentity`
-- the per-component identity Nitin's ask needs a score to be comparable
across model/prompt versions (`GenerationIdentity` was built for the
artifact cache, ADR-0050; this is its second consumer, per ADR-0051's own
Consequences).

``NOT_APPLICABLE`` results are excluded from the pass-rate denominator --
a case with no applicable checks contributes nothing to the score, never a
silent pass or a silent fail.
"""

from __future__ import annotations

from collections.abc import Sequence

from automation_engineering.generation.step_definition_generator import (
    StepDefinitionGenerationContext,
)
from eval_harness.models import CaseResult, EvalScore, PropertyCheckOutcome
from eval_harness.step_definition_properties import (
    STEP_DEFINITION_PROPERTY_CHECKS,
    PropertyCheck,
    run_property_checks,
)
from requirement_intelligence.llm.generation_identity import GenerationIdentity


def score_case(
    case_id: str,
    generated_text: str,
    context: StepDefinitionGenerationContext,
    checks: tuple[PropertyCheck, ...] = STEP_DEFINITION_PROPERTY_CHECKS,
) -> CaseResult:
    """Run ``checks`` against one generated artifact and return the case's
    aggregate result."""
    return CaseResult(
        case_id=case_id,
        check_results=run_property_checks(generated_text, context, checks),
    )


def score_eval_set(
    case_results: Sequence[CaseResult],
    *,
    generator_id: str,
    eval_set_version: str,
    identity: GenerationIdentity,
) -> EvalScore:
    """Aggregate a sequence of per-case results into one
    :class:`EvalScore`, keyed by ``(generator_id, identity)``.

    ``pass_rate`` is ``total_checks_passed / total_checks_applicable``,
    excluding every ``NOT_APPLICABLE`` result -- a generator is never
    rewarded or penalized for a check that had nothing to evaluate. A case
    set with zero applicable checks anywhere (no case exercised any
    checkable property) scores ``1.0`` -- no evidence of a defect, not
    evidence of a passing one; callers relying on this score should ensure
    the curated set actually exercises each check (proven for
    `STEP_DEFINITION_EVAL_SET` by this package's own tests).
    """
    applicable = [
        result
        for case in case_results
        for result in case.check_results
        if result.outcome != PropertyCheckOutcome.NOT_APPLICABLE
    ]
    passed = [result for result in applicable if result.outcome == PropertyCheckOutcome.PASSED]
    pass_rate = (len(passed) / len(applicable)) if applicable else 1.0

    return EvalScore(
        generator_id=generator_id,
        eval_set_version=eval_set_version,
        identity=identity,
        case_results=tuple(case_results),
        total_checks_applicable=len(applicable),
        total_checks_passed=len(passed),
        pass_rate=pass_rate,
    )


__all__ = ["score_case", "score_eval_set"]
