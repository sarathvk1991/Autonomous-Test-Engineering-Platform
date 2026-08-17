"""ADR-0051 D5's first-build entry point: run
`STEP_DEFINITION_EVAL_SET` through any `StepDefinitionGenerator` and score
the result.

Deterministic by construction, matching this build's own scope decision
(ADR-0051 D2's "live-vs-cached" open question, left unresolved for CI, but
resolved here for the eval LOGIC itself): ``run_step_definition_eval``
takes any `StepDefinitionGenerator` -- in this package's own tests, always
`StubStepDefinitionGenerator` seeded with captured/fixture Java text, never
a live LLM call. A future CI-wiring milestone decides whether the generator
it constructs is live or replays the artifact-generation cache (ADR-0050);
this function is agnostic to which -- it only requires the seam's own
Protocol.
"""

from __future__ import annotations

from collections.abc import Sequence

from automation_engineering.generation.live_step_definition_generator import CALL_TYPE
from automation_engineering.generation.step_definition_generator import StepDefinitionGenerator
from eval_harness.models import CaseResult, EvalScore
from eval_harness.scoring import score_case, score_eval_set
from eval_harness.step_definition_eval_set import (
    STEP_DEFINITION_EVAL_SET,
    STEP_DEFINITION_EVAL_SET_VERSION,
    EvalCase,
)
from requirement_intelligence.llm.generation_identity import GenerationIdentity


def run_step_definition_eval(
    generator: StepDefinitionGenerator,
    *,
    identity: GenerationIdentity,
    eval_set: Sequence[EvalCase] = STEP_DEFINITION_EVAL_SET,
    eval_set_version: str = STEP_DEFINITION_EVAL_SET_VERSION,
    generator_id: str = CALL_TYPE,
) -> EvalScore:
    """Run every case in ``eval_set`` through ``generator``, score each with
    the deterministic property checks (:mod:`.step_definition_properties`),
    and aggregate into one :class:`~eval_harness.models.EvalScore` keyed by
    ``(generator_id, identity)``.

    ``identity`` is supplied by the caller, not read off ``generator`` --
    the same pre-call-identity discipline
    `resolve_step_definition_identity` already establishes for the
    artifact-generation cache (ADR-0050 D3 Gap 1): a caching decorator, a
    stub, and a live generator all satisfy the same
    `StepDefinitionGenerator` Protocol, none of which is required to expose
    its own identity.
    """
    case_results: list[CaseResult] = []
    for case in eval_set:
        generated_text = generator.generate(case.context)
        case_results.append(score_case(case.case_id, generated_text, case.context))

    return score_eval_set(
        case_results,
        generator_id=generator_id,
        eval_set_version=eval_set_version,
        identity=identity,
    )


__all__ = ["run_step_definition_eval"]
