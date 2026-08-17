"""ADR-0051 D2's curated eval set for `LiveStepDefinitionGenerator` --
seeded from real generation contexts, not invented, mirroring the
`GOLDEN_DATASET_VERSION`-style independent versioning
`tests/productization/fixtures/golden_dataset.py` already establishes for
structural regression.

Each case's ``need.text``/``target_package``/``page_object_interface``
mirrors the real, currently-tracked, currently-compiling step-definition
corpus (`test-suite-baseline/src/test/java/com/automation/steps/
LoginSteps.java`) -- the same corpus `[[cap-compile-gap-closed]]`'s real
`gemini-2.5-flash` measurement regenerated and found 76% defective. This
module curates the INPUT contexts only; it carries no expected Java text
(ADR-0051 D2's own "rejected as the primary mechanism" finding for
expected-output matching) and no canned generator output -- a caller pairs
each case with whatever a real or stub generator actually produces for it.
"""

from __future__ import annotations

from dataclasses import dataclass

from automation_engineering.generation.step_definition_generator import (
    StepDefinitionGenerationContext,
)
from automation_engineering.reuse.models import GherkinStepNeed

#: Independent from `GenerationIdentity`/the prompt version -- this is the
#: CURATED SET's own version (ADR-0051 D2), advanced when cases are added,
#: removed, or re-labeled, never when the generator or prompt changes.
STEP_DEFINITION_EVAL_SET_VERSION = "1.0.0"

_TARGET_PACKAGE = "com.automation.steps"


@dataclass(frozen=True, slots=True)
class EvalCase:
    """One curated eval case: an id (for diagnosis) plus the real
    generation context a `StepDefinitionGenerator` would be called with."""

    case_id: str
    context: StepDefinitionGenerationContext


#: Seeded directly from `LoginSteps.java`'s own two real, currently-tracked,
#: currently-compiling step definitions -- the real corpus the
#: `gemini-2.5-flash` regression (`[[cap-compile-gap-closed]]`) was measured
#: against. A third case (no page-object interface expected) exercises the
#: `NOT_APPLICABLE` path `check_no_fabricated_page_object_class` needs to
#: prove it never treats an inapplicable check as a vacuous pass.
STEP_DEFINITION_EVAL_SET: tuple[EvalCase, ...] = (
    EvalCase(
        case_id="login_attempt_with_credentials",
        context=StepDefinitionGenerationContext(
            need=GherkinStepNeed(
                text="the user attempts to login with {string} credentials",
                step_type="When",
            ),
            target_package=_TARGET_PACKAGE,
            customqa_constraints=(),
            page_object_interface="com.automation.pages.LoginPage",
        ),
    ),
    EvalCase(
        case_id="login_invalid_credentials_error",
        context=StepDefinitionGenerationContext(
            need=GherkinStepNeed(
                text="the system displays an error message indicating invalid credentials",
                step_type="Then",
            ),
            target_package=_TARGET_PACKAGE,
            customqa_constraints=(),
            page_object_interface="com.automation.pages.LoginPage",
        ),
    ),
    EvalCase(
        case_id="system_reaches_ready_state",
        context=StepDefinitionGenerationContext(
            need=GherkinStepNeed(
                text="the system reaches a ready state",
                step_type="Given",
            ),
            target_package=_TARGET_PACKAGE,
            customqa_constraints=(),
            page_object_interface=None,
        ),
    ),
)


__all__ = ["STEP_DEFINITION_EVAL_SET", "STEP_DEFINITION_EVAL_SET_VERSION", "EvalCase"]
