"""ADR-0051 D5's fourth-generator curated eval set: `LivePageObjectGenerator`.

Same discipline as `step_definition_eval_set.py`/`feature_content_eval_set.py`/
`test_data_eval_set.py`, applied to a FOURTH artifact type: a Java page-object
class (locators + methods extending `BasePage`), not a Cucumber step, a
Gherkin scenario, or a SUT-unbound data class.

Seeded from the real, currently-tracked page-object catalog
(`test-suite-baseline/src/test/java/com/automation/pages/`, 34 files including
`BasePage.java` -- 33 real page objects) -- the SAME corpus the 2026-08-10
live regeneration run (`[[cap-page-object-live-regen-findings]]`) measured its
three real defects against. Each case's `PageObjectGenerationContext` mirrors
one real, currently-tracked, currently-compiling method on that corpus,
continuing `LoginPage`'s own two methods used by `STEP_DEFINITION_EVAL_SET`
(`LoginPage.attemptLogin`/`LoginPage.isErrorMessageDisplayed`,
`test-suite-baseline/.../pages/LoginPage.java`) plus a third, structurally
different real method (`InventoryPage.isInventorySortedBy`,
`.../pages/InventoryPage.java`) for a capture/parameter shape `LoginPage`
alone does not exercise (a `String` argument feeding the return value itself,
not just the action).

**`class_name` is supplied directly as the real, currently-tracked name
(`"LoginPage"`/`"InventoryPage"`), not derived from `need.text` via
`derive_page_object_class_name`.** Checked directly, not assumed: that
function is a deterministic UpperCamelCase-from-prose derivation with no
knowledge of an already-existing class, so it does not reproduce these real
names (`derive_page_object_class_name("the user attempts to login with
credentials")` returns `"UserAttemptsLoginCredentialsPage"`, not
`"LoginPage"`) -- this is the SAME class-name-mismatch gap
`page_object_reference_derivation.py` already exists to close for a real
step-def call site, via `PageObjectMethodNeed.class_name_override`
(`[[page-object-request-derivation]]`). Supplying the real tracked name
directly is the curated set's own equivalent of that override: it is what a
real production call site (one that already parsed an existing class
reference) would actually pass, not the raw from-scratch default a NO_MATCH
generation for a brand-new page object would use.
"""

from __future__ import annotations

from dataclasses import dataclass

from automation_engineering.catalog.models import JavaParameter, StepCapture
from automation_engineering.generation.page_object_generator import PageObjectGenerationContext
from automation_engineering.generation.page_object_orchestrator import (
    DEFAULT_CUSTOMQA_PAGE_OBJECT_CONSTRAINTS,
    DEFAULT_PAGE_OBJECT_TARGET_PACKAGE,
)
from automation_engineering.reuse.models import GherkinStepNeed

#: Independent from `GenerationIdentity`/the prompt version (ADR-0051 D2) --
#: this is the CURATED SET's own version, advanced when cases are added,
#: removed, or re-labeled, never when the generator or prompt changes.
PAGE_OBJECT_EVAL_SET_VERSION = "1.0.0"


@dataclass(frozen=True, slots=True)
class EvalCase:
    """One curated eval case: an id (for diagnosis) plus the real
    `PageObjectGenerationContext` a `PageObjectGenerator` would be called
    with."""

    case_id: str
    context: PageObjectGenerationContext


def _context(
    *,
    action_text: str,
    step_type: str,
    class_name: str,
    method_name: str,
    return_type: str,
    parameters: tuple[JavaParameter, ...],
) -> PageObjectGenerationContext:
    """Builds one real `PageObjectGenerationContext` the way a real
    production call site does: `method_name`/`return_type`/`parameters`
    caller-supplied (never left for the model to invent, per the
    `method_name`-required fix, `[[cap-page-object-defect1-method-name-fix]]`),
    `captures` derived from `parameters` one-to-one (mirroring
    `build_page_object_payload`'s own `_capture_payload_from_parameters`
    preference for call-site-derived arity over `need.captures`)."""
    captures = tuple(
        StepCapture(index=index, style="call_site", expression_type=parameter.java_type)
        for index, parameter in enumerate(parameters)
    )
    return PageObjectGenerationContext(
        need=GherkinStepNeed(text=action_text, step_type=step_type, captures=captures),
        class_name=class_name,
        target_package=DEFAULT_PAGE_OBJECT_TARGET_PACKAGE,
        customqa_constraints=DEFAULT_CUSTOMQA_PAGE_OBJECT_CONSTRAINTS,
        method_name=method_name,
        return_type=return_type,
        parameters=parameters,
    )


#: Seeded directly from `LoginPage.java`'s own two real, currently-tracked,
#: currently-compiling methods -- the SAME class the step-definition eval
#: set's own `login_attempt_with_credentials`/`login_invalid_credentials_error`
#: cases call through (`STEP_DEFINITION_EVAL_SET`), for continuity across the
#: harness's four built increments -- plus one real method from a second real
#: page object (`InventoryPage.isInventorySortedBy`) for a call-site parameter
#: shape `LoginPage` alone does not exercise.
PAGE_OBJECT_EVAL_SET: tuple[EvalCase, ...] = (
    EvalCase(
        case_id="login_attempt_with_credentials",
        context=_context(
            action_text="attempt login with credentials",
            step_type="When",
            class_name="LoginPage",
            method_name="attemptLogin",
            return_type="void",
            parameters=(JavaParameter(name="credentials", java_type="String"),),
        ),
    ),
    EvalCase(
        case_id="login_invalid_credentials_error",
        context=_context(
            action_text="the error message is displayed",
            step_type="Then",
            class_name="LoginPage",
            method_name="isErrorMessageDisplayed",
            return_type="boolean",
            parameters=(),
        ),
    ),
    EvalCase(
        case_id="inventory_sorted_by_order",
        context=_context(
            action_text="the inventory is sorted by order",
            step_type="Then",
            class_name="InventoryPage",
            method_name="isInventorySortedBy",
            return_type="boolean",
            parameters=(JavaParameter(name="order", java_type="String"),),
        ),
    ),
)


__all__ = ["PAGE_OBJECT_EVAL_SET", "PAGE_OBJECT_EVAL_SET_VERSION", "EvalCase"]
