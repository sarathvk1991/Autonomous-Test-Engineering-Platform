"""ADR-0051 D5's third-generator entry point: run `TEST_DATA_EVAL_SET`
through any `TestDataGenerator` and score the result.

Deterministic by construction, mirroring `runner.py`/`feature_content_
runner.py`'s own scope decision: ``run_test_data_eval`` takes any
`TestDataGenerator` -- in this package's own tests, always
`StubTestDataGenerator` seeded with captured/fixture Java text, never a
live LLM call.

Reuses `eval_harness.scoring.score_eval_set` verbatim, exactly as the
feature-content increment did -- the third proof that `models.py`/
`scoring.py`/`baseline_store.py` are genuinely generator-agnostic, not
merely designed to look that way.
"""

from __future__ import annotations

from collections.abc import Sequence

from automation_engineering.generation.live_test_data_generator import CALL_TYPE
from automation_engineering.generation.test_data_generator import TestDataGenerator
from eval_harness.models import CaseResult, EvalScore
from eval_harness.scoring import score_eval_set
from eval_harness.test_data_eval_set import (
    TEST_DATA_EVAL_SET,
    TEST_DATA_EVAL_SET_VERSION,
    EvalCase,
)
from eval_harness.test_data_properties import run_property_checks
from requirement_intelligence.llm.generation_identity import GenerationIdentity


def run_test_data_eval(
    generator: TestDataGenerator,
    *,
    identity: GenerationIdentity,
    eval_set: Sequence[EvalCase] = TEST_DATA_EVAL_SET,
    eval_set_version: str = TEST_DATA_EVAL_SET_VERSION,
    generator_id: str = CALL_TYPE,
) -> EvalScore:
    """Run every case in ``eval_set`` through ``generator``, score each with
    the deterministic property checks (:mod:`.test_data_properties`), and
    aggregate into one :class:`~eval_harness.models.EvalScore` keyed by
    ``(generator_id, identity)``.

    ``identity`` is supplied by the caller, not read off ``generator`` --
    the same pre-call-identity discipline `resolve_test_data_identity`
    already establishes for the artifact-generation cache (ADR-0050 D3 Gap
    1), mirroring the other two runners' own discipline exactly.
    """
    case_results: list[CaseResult] = []
    for case in eval_set:
        generated_text = generator.generate(case.context)
        case_results.append(
            CaseResult(
                case_id=case.case_id,
                check_results=run_property_checks(generated_text, case.context),
            )
        )

    return score_eval_set(
        case_results,
        generator_id=generator_id,
        eval_set_version=eval_set_version,
        identity=identity,
    )


__all__ = ["run_test_data_eval"]
