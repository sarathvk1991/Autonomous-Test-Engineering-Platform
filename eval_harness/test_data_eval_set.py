"""ADR-0051 D5's third-generator eval set: `LiveTestDataGenerator`.

Same discipline as `step_definition_eval_set.py`/`feature_content_eval_set.py`,
applied to a third artifact type -- seeded from real generation contexts, not
invented, versioned independently of `GenerationIdentity`/the prompt.

Each case's `TestDataGenerationContext` is built from a real, currently-
tracked `TestDataSpecification` in `output/latest/test_data_specifications.json`
(the same 20-requirement corpus feature-content's own eval set was seeded
from), using the SAME requirement ids feature-content's curated set uses
(`REQ-c64bb0f7`/`REQ-f90f23fa`/`REQ-92502735`), for continuity across the
harness's three built increments. `class_name`/`target_package`/
`customqa_constraints` are derived via the real orchestrator's own functions
(`derive_test_data_class_name`, `DEFAULT_TEST_DATA_TARGET_PACKAGE`,
`DEFAULT_CUSTOMQA_TEST_DATA_CONSTRAINTS`, `automation_engineering.generation.
test_data_orchestrator`) -- never reinvented here.

**Every real `TestDataSpecification` this platform has ever emitted carries
`fields=()`** -- confirmed directly against `output/latest/
test_data_specifications.json` (all 20 requirements) and stated explicitly
in the contract's own docstring (`contracts.test_data_specification.
TestDataSpecification`: "a requirement whose acceptance criteria carry no
`data_fields` (true of every requirement this platform has emitted so
far)"). This is not a simplification made here -- it is the honest, current
shape of the real corpus, carried into this eval set's own three cases.
"""

from __future__ import annotations

from dataclasses import dataclass

from automation_engineering.generation.test_data_generator import TestDataGenerationContext
from automation_engineering.generation.test_data_orchestrator import (
    DEFAULT_CUSTOMQA_TEST_DATA_CONSTRAINTS,
    DEFAULT_TEST_DATA_TARGET_PACKAGE,
    derive_test_data_class_name,
)
from contracts.test_data_specification import TestDataSpecification

#: Independent from `GenerationIdentity`/the prompt version (ADR-0051 D2) --
#: this is the CURATED SET's own version, advanced when cases are added,
#: removed, or re-labeled, never when the generator or prompt changes.
TEST_DATA_EVAL_SET_VERSION = "1.0.0"


@dataclass(frozen=True, slots=True)
class EvalCase:
    """One curated eval case: an id (for diagnosis) plus the real
    `TestDataGenerationContext` a `TestDataGenerator` would be called
    with."""

    case_id: str
    context: TestDataGenerationContext


def _context(requirement_id: str) -> TestDataGenerationContext:
    """Builds one real `TestDataGenerationContext` the exact way
    `test_data_orchestrator.generate_test_data_class` itself does --
    reusing its own naming/package/constraint functions verbatim, never a
    second, divergent derivation."""
    return TestDataGenerationContext(
        specification=TestDataSpecification(requirement_id=requirement_id, fields=()),
        class_name=derive_test_data_class_name(requirement_id),
        target_package=DEFAULT_TEST_DATA_TARGET_PACKAGE,
        customqa_constraints=DEFAULT_CUSTOMQA_TEST_DATA_CONSTRAINTS,
    )


#: Seeded from three real, currently-tracked requirements -- the same three
#: `feature_content_eval_set.py` uses, each with the real, currently-tracked
#: empty `TestDataSpecification` every requirement in this corpus actually
#: has (`output/latest/test_data_specifications.json`).
TEST_DATA_EVAL_SET: tuple[EvalCase, ...] = (
    EvalCase(case_id="login_invalid_credentials_error", context=_context("REQ-c64bb0f7")),
    EvalCase(case_id="inventory_display_after_authentication", context=_context("REQ-f90f23fa")),
    EvalCase(case_id="session_timeout_invalidation", context=_context("REQ-92502735")),
)


__all__ = ["TEST_DATA_EVAL_SET", "TEST_DATA_EVAL_SET_VERSION", "EvalCase"]
