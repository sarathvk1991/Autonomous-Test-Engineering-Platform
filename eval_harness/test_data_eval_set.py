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

**Every real `TestDataSpecification` this platform had ever emitted, as of
this file's original build, carried `fields=()`** -- confirmed directly
against `output/latest/test_data_specifications.json` (all 20
requirements) and stated explicitly in the contract's own docstring
(`contracts.test_data_specification.TestDataSpecification`). This was the
honest, current shape of the real corpus at the time, carried into this
eval set's original three cases below, unchanged.

**Amendment (additive, 2026-08-28, #3 Option B, ADR-0043 D10) -- a fourth
case, populated.** `feature_engineering.stage.test_data_enrichment` now
derives real, non-empty fields from a criterion's own finalized statement
text for several real corpus requirements when Layer 1 itself still emits
none. `_POPULATED_CASE` below is seeded with the SAME real, verbatim
statement text as `REQ-c64bb0f7` (`"...login with invalid credentials"`),
run through that same real derivation function -- not invented values --
under a DISTINCT requirement id: `StubTestDataGenerator` (this eval
harness's own generator stand-in) keys its canned Java text by
`requirement_id`, and the original `REQ-c64bb0f7` case above already claims
that id with the honest-empty shape; reusing it here would silently
overwrite one case's own canned answer with the other's in every test that
builds a `java_source_by_requirement_id` mapping. The id suffix is a
technical necessity of this eval harness's own lookup mechanism, not a
second, different requirement -- the derived fields themselves are real.
"""

from __future__ import annotations

from dataclasses import dataclass

from automation_engineering.generation.test_data_generator import TestDataGenerationContext
from automation_engineering.generation.test_data_orchestrator import (
    DEFAULT_CUSTOMQA_TEST_DATA_CONSTRAINTS,
    DEFAULT_TEST_DATA_TARGET_PACKAGE,
    derive_test_data_class_name,
)
from contracts.test_data_specification import TestDataFieldSpec, TestDataSpecification
from feature_engineering.stage.test_data_enrichment import derive_data_hints_from_statement

#: Independent from `GenerationIdentity`/the prompt version (ADR-0051 D2) --
#: this is the CURATED SET's own version, advanced when cases are added,
#: removed, or re-labeled, never when the generator or prompt changes.
#: Advanced to 1.1.0 for the populated-case amendment above.
TEST_DATA_EVAL_SET_VERSION = "1.1.0"


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


#: The distinct id `_populated_context` uses -- module docstring's own
#: amendment explains why this cannot reuse `REQ-c64bb0f7` verbatim.
_POPULATED_CASE_REQUIREMENT_ID = "REQ-c64bb0f7-optionb"

#: Verbatim `REQ-c64bb0f7` acceptance-criterion statement text
#: (`output/latest/testable_requirement_set.json`) -- the real, live text
#: `derive_data_hints_from_statement` derives this case's own fields from,
#: not an invented string.
_POPULATED_CASE_STATEMENT = (
    "The system shall display an error message when a user attempts to "
    "login with invalid credentials."
)


def _populated_context() -> TestDataGenerationContext:
    """A POPULATED `TestDataSpecification` -- module docstring's own
    amendment: real fields/variants, derived from `REQ-c64bb0f7`'s own real
    statement text via the SAME #3 Option B function
    (`feature_engineering.stage.test_data_spec.build_test_data_specification`
    would produce this identical field set for that real requirement), not
    hand-invented here."""
    hints = derive_data_hints_from_statement(_POPULATED_CASE_STATEMENT)
    fields = tuple(
        TestDataFieldSpec(field_name=field_name, required_variants=hints.polarity_hints)
        for field_name in hints.data_fields
    )
    return TestDataGenerationContext(
        specification=TestDataSpecification(
            requirement_id=_POPULATED_CASE_REQUIREMENT_ID, fields=fields
        ),
        class_name=derive_test_data_class_name(_POPULATED_CASE_REQUIREMENT_ID),
        target_package=DEFAULT_TEST_DATA_TARGET_PACKAGE,
        customqa_constraints=DEFAULT_CUSTOMQA_TEST_DATA_CONSTRAINTS,
    )


#: Seeded from three real, currently-tracked requirements -- the same three
#: `feature_content_eval_set.py` uses, each with the real, currently-tracked
#: empty `TestDataSpecification` every requirement in this corpus actually
#: has (`output/latest/test_data_specifications.json`) -- plus a fourth,
#: POPULATED case (module docstring's own amendment, #3 Option B).
TEST_DATA_EVAL_SET: tuple[EvalCase, ...] = (
    EvalCase(case_id="login_invalid_credentials_error", context=_context("REQ-c64bb0f7")),
    EvalCase(case_id="inventory_display_after_authentication", context=_context("REQ-f90f23fa")),
    EvalCase(case_id="session_timeout_invalidation", context=_context("REQ-92502735")),
    EvalCase(
        case_id="login_invalid_credentials_error_populated", context=_populated_context()
    ),
)


__all__ = ["TEST_DATA_EVAL_SET", "TEST_DATA_EVAL_SET_VERSION", "EvalCase"]
