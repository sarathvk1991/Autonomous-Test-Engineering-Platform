"""ADR-0051 D5's second-generator entry point: run
`FEATURE_CONTENT_EVAL_SET` through any `FeatureContentGenerator` and score
the result.

Deterministic by construction, mirroring `runner.py`'s own scope decision:
``run_feature_content_eval`` takes any `FeatureContentGenerator` -- in this
package's own tests, always `StubFeatureContentGenerator` seeded with
captured/fixture Gherkin text, never a live LLM call. A future CI-wiring
milestone decides whether the generator it constructs is live or replays the
artifact-generation cache (ADR-0050); this function is agnostic to which --
it only requires the seam's own Protocol.

Reuses `eval_harness.scoring.score_eval_set` verbatim (already
generator-agnostic -- it never references a step-def-specific type); does
NOT reuse `eval_harness.scoring.score_case`, which is typed to `StepDefinition
GenerationContext` -- this module builds its own `CaseResult` directly from
`feature_content_properties.run_property_checks`, the same one-line
composition `score_case` itself performs, just against a different check
set and context type.
"""

from __future__ import annotations

from collections.abc import Sequence

from eval_harness.feature_content_eval_set import (
    FEATURE_CONTENT_EVAL_SET,
    FEATURE_CONTENT_EVAL_SET_VERSION,
    EvalCase,
)
from eval_harness.feature_content_properties import run_property_checks
from eval_harness.models import CaseResult, EvalScore
from eval_harness.scoring import score_eval_set
from feature_engineering.generation.content_generator import FeatureContentGenerator
from feature_engineering.generation.live_content_generator import CALL_TYPE
from requirement_intelligence.llm.generation_identity import GenerationIdentity


def run_feature_content_eval(
    generator: FeatureContentGenerator,
    *,
    identity: GenerationIdentity,
    eval_set: Sequence[EvalCase] = FEATURE_CONTENT_EVAL_SET,
    eval_set_version: str = FEATURE_CONTENT_EVAL_SET_VERSION,
    generator_id: str = CALL_TYPE,
) -> EvalScore:
    """Run every case in ``eval_set`` through ``generator``, score each with
    the deterministic property checks (:mod:`.feature_content_properties`),
    and aggregate into one :class:`~eval_harness.models.EvalScore` keyed by
    ``(generator_id, identity)``.

    ``identity`` is supplied by the caller, not read off ``generator`` --
    the same pre-call-identity discipline `resolve_feature_content_identity`
    already establishes for the artifact-generation cache (ADR-0050 D3 Gap
    1), mirroring `run_step_definition_eval`'s own discipline exactly.
    """
    case_results: list[CaseResult] = []
    for case in eval_set:
        generated_text = generator.generate(case.requirement)
        case_results.append(
            CaseResult(
                case_id=case.case_id,
                check_results=run_property_checks(generated_text, case.requirement),
            )
        )

    return score_eval_set(
        case_results,
        generator_id=generator_id,
        eval_set_version=eval_set_version,
        identity=identity,
    )


__all__ = ["run_feature_content_eval"]
