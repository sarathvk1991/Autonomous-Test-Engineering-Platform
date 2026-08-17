"""ADR-0051 D2's deterministic property/assertion checks for one generated
step-definition artifact.

**Composed, not invented (ADR-0051 D1, the reframe).** Each check here
targets exactly one of the three real, measured `gemini-2.5-flash` defects
this arc found (`docs/architecture/mentor-feedback-scoping.md`, Item 1;
`[[cap-compile-gap-closed]]`): a wrong Cucumber import package (8/17 real
generations), a markdown code fence violating an explicit no-markdown
prompt contract (2/17), and a fabricated/duplicate page-object class
declared inline instead of referencing the external one (3-4/17). None of
these is a new detection idea -- the wrong-import defect is exactly what
`suite_quality_governance.cp5.compile_check`'s real `mvn test-compile`
already fails on; the fabricated-duplicate-class defect is the same shape
`suite_quality_governance.cp5.near_duplicate_sweep` is already adjacent to.
What is new here is running an equivalent, purely string-level check
directly against one generator's own output, deterministically, without a
Maven toolchain or a whole assembled suite -- the property-level grain a
per-case, per-generator eval score needs (ADR-0051 D2), not the
whole-corpus grain CP5 itself operates at (ADR-0051 D4).

Every check is a pure function of ``(generated_text, context)`` -- no LLM
call, no filesystem access, no subprocess. Each returns
:class:`~eval_harness.models.PropertyCheckOutcome.NOT_APPLICABLE` rather
than a vacuous PASS when nothing in ``context`` gives the check anything to
evaluate (e.g. no Cucumber annotation present at all, or no page-object
interface was expected) -- ``NOT_APPLICABLE`` results are excluded from the
eval score's pass-rate denominator (:mod:`.scoring`), never silently
counted as evidence of quality.
"""

from __future__ import annotations

from collections.abc import Callable

from automation_engineering.generation.step_definition_generator import (
    StepDefinitionGenerationContext,
)
from eval_harness.models import PropertyCheckOutcome, PropertyCheckResult

#: The Cucumber-JVM annotation names this platform's step-definitions use --
#: the real defect (`[[cap-compile-gap-closed]]`) imported one of these from
#: the wrong package (`io.cucumber.java.When` instead of the correct
#: `io.cucumber.java.en.When`).
_CUCUMBER_ANNOTATIONS: tuple[str, ...] = ("Given", "When", "Then", "And", "But")

PropertyCheck = Callable[[str, StepDefinitionGenerationContext], PropertyCheckResult]


def check_valid_cucumber_import(
    generated_text: str, context: StepDefinitionGenerationContext
) -> PropertyCheckResult:
    """Catches the real, dominant `gemini-2.5-flash` defect (8/17 real
    generations, `[[cap-compile-gap-closed]]`): ``import io.cucumber.java.
    When;`` instead of the correct ``import io.cucumber.java.en.When;``.
    Both are syntactically valid Java imports -- only a compile against the
    real Cucumber-JVM classpath (or this literal string check) reveals the
    wrong one resolves to a package with no such annotation.

    ``NOT_APPLICABLE`` when the generated text carries no Cucumber
    annotation at all -- there is nothing to check an import against.
    """
    used = {name for name in _CUCUMBER_ANNOTATIONS if f"@{name}(" in generated_text}
    if not used:
        return PropertyCheckResult(
            check_name="valid_cucumber_import",
            outcome=PropertyCheckOutcome.NOT_APPLICABLE,
            reason="no Cucumber step annotation found to check an import against",
        )

    wrong_package = sorted(
        name for name in used if f"import io.cucumber.java.{name};" in generated_text
    )
    if wrong_package:
        return PropertyCheckResult(
            check_name="valid_cucumber_import",
            outcome=PropertyCheckOutcome.FAILED,
            reason=(
                "wrong Cucumber import package (io.cucumber.java.X instead of "
                f"io.cucumber.java.en.X) for: {wrong_package}"
            ),
        )

    missing_correct_package = sorted(
        name for name in used if f"import io.cucumber.java.en.{name};" not in generated_text
    )
    if missing_correct_package:
        return PropertyCheckResult(
            check_name="valid_cucumber_import",
            outcome=PropertyCheckOutcome.FAILED,
            reason=f"missing io.cucumber.java.en.* import for: {missing_correct_package}",
        )

    return PropertyCheckResult(
        check_name="valid_cucumber_import", outcome=PropertyCheckOutcome.PASSED
    )


def check_no_markdown_fence(
    generated_text: str, context: StepDefinitionGenerationContext
) -> PropertyCheckResult:
    """Catches the second real defect (2/17, `[[cap-compile-gap-closed]]`):
    a fenced ```` ``` ```` code block wrapping the response despite the
    governed prompt's own explicit no-markdown contract. Always applicable
    -- every generated artifact is either fenced or it isn't.
    """
    if "```" in generated_text:
        return PropertyCheckResult(
            check_name="no_markdown_fence",
            outcome=PropertyCheckOutcome.FAILED,
            reason="generated text contains a markdown code fence ('```')",
        )
    return PropertyCheckResult(check_name="no_markdown_fence", outcome=PropertyCheckOutcome.PASSED)


def check_no_fabricated_page_object_class(
    generated_text: str, context: StepDefinitionGenerationContext
) -> PropertyCheckResult:
    """Catches the third real defect (3-4/17, `[[cap-compile-gap-closed]]`):
    an inline, fabricated page-object class declared in the same file
    instead of referencing the external one the generation context expected
    (``context.page_object_interface``).

    ``NOT_APPLICABLE`` when ``context.page_object_interface`` is ``None`` --
    this need expected no page-object binding, so there is nothing to check
    a reference against.
    """
    if context.page_object_interface is None:
        return PropertyCheckResult(
            check_name="no_fabricated_page_object_class",
            outcome=PropertyCheckOutcome.NOT_APPLICABLE,
            reason="no page-object interface was expected for this need",
        )

    expected_simple_name = context.page_object_interface.rsplit(".", 1)[-1]

    if f"class {expected_simple_name}" in generated_text:
        return PropertyCheckResult(
            check_name="no_fabricated_page_object_class",
            outcome=PropertyCheckOutcome.FAILED,
            reason=(
                f"declares its own '{expected_simple_name}' class body instead of "
                f"referencing the external {context.page_object_interface}"
            ),
        )

    if expected_simple_name not in generated_text:
        return PropertyCheckResult(
            check_name="no_fabricated_page_object_class",
            outcome=PropertyCheckOutcome.FAILED,
            reason=f"never references the expected page object {context.page_object_interface}",
        )

    return PropertyCheckResult(
        check_name="no_fabricated_page_object_class", outcome=PropertyCheckOutcome.PASSED
    )


#: ADR-0051 D2/D5's own first-build check set -- targets exactly the three
#: real defect shapes on record. Ordered deterministically; a caller wanting
#: a different or extended set (e.g. once the judge layer, D5, exists)
#: composes its own tuple rather than mutating this one.
STEP_DEFINITION_PROPERTY_CHECKS: tuple[PropertyCheck, ...] = (
    check_valid_cucumber_import,
    check_no_markdown_fence,
    check_no_fabricated_page_object_class,
)


def run_property_checks(
    generated_text: str,
    context: StepDefinitionGenerationContext,
    checks: tuple[PropertyCheck, ...] = STEP_DEFINITION_PROPERTY_CHECKS,
) -> tuple[PropertyCheckResult, ...]:
    """Run every check in ``checks`` against one generated artifact,
    deterministically, in order -- no LLM call, no I/O."""
    return tuple(check(generated_text, context) for check in checks)


__all__ = [
    "STEP_DEFINITION_PROPERTY_CHECKS",
    "PropertyCheck",
    "check_no_fabricated_page_object_class",
    "check_no_markdown_fence",
    "check_valid_cucumber_import",
    "run_property_checks",
]
