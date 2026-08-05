"""CP3's `direct_webdriver_action` and `long_method` criteria (ADR-0044 D5
revisions, 2026-08-04 and 2026-08-05): two static, `javalang`-based checks
for BOTH halves of `customqa:*`, neither Sonar-gated. No network call, no
subprocess, no live infrastructure anywhere in this module -- pure function
of in-memory Java source text, mirroring CP4's own static discipline
(`tests/unit/test_automation_engineering_cp4_gate.py`).

`direct_webdriver_action` proves: import-based detection, call-based
detection, a clean pass, and the class-role proof this whole build exists
for -- the SAME WebDriver usage that fails a step-definition class is left
untouched on an otherwise-identical page-object class, the precision a
Sonar file-path exclusion could only approximate.

`long_method` proves: a >40-line method flagged, a <=40-line method clean,
and -- unlike `direct_webdriver_action` -- that the check applies to EVERY
generated class kind (step definition, page object, utility), not just
step definitions.
"""

from __future__ import annotations

import pytest

from automation_engineering.cp3.architecture import (
    CRITERION_DIRECT_WEBDRIVER_ACTION,
    CRITERION_LONG_METHOD,
    MAX_METHOD_LINES,
    Cp3GeneratedClassInput,
    evaluate_direct_webdriver_action,
    evaluate_long_method,
)
from shared.enums.base import ValidationVerdict

pytestmark = pytest.mark.unit

_CLEAN_STEP_DEFINITION = """package com.automation.steps;

import io.cucumber.java.en.Given;
import com.automation.pages.LoginPage;

public class LoginSteps {

    private final LoginPage loginPage;

    public LoginSteps(LoginPage loginPage) {
        this.loginPage = loginPage;
    }

    @Given("I log in as {string}")
    public void iLogInAs(String username) {
        loginPage.enterUsername(username);
        loginPage.submit();
    }
}
"""

_CALL_BASED_VIOLATION_STEP_DEFINITION = """package com.automation.steps;

import io.cucumber.java.en.Given;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.By;

public class LoginSteps {

    private WebDriver driver;

    @Given("I log in as {string}")
    public void iLogInAs(String username) {
        driver.findElement(By.id("username")).sendKeys(username);
    }
}
"""

_IMPORT_ONLY_VIOLATION_STEP_DEFINITION = """package com.automation.steps;

import org.openqa.selenium.WebDriver;

public class LoginSteps {

    public void doNothingYet() {
    }
}
"""

_PAGE_OBJECT_WITH_WEBDRIVER = """package com.automation.pages;

import org.openqa.selenium.WebDriver;
import org.openqa.selenium.By;

public class LoginPage {

    private WebDriver driver;

    public void enterUsername(String username) {
        driver.findElement(By.id("username")).sendKeys(username);
    }

    public void submit() {
        driver.findElement(By.id("submit")).click();
    }
}
"""


def test_clean_step_definition_routing_through_page_object_passes() -> None:
    result = evaluate_direct_webdriver_action(
        [Cp3GeneratedClassInput(class_name="LoginSteps", java_source=_CLEAN_STEP_DEFINITION)]
    )

    assert result.criterion == CRITERION_DIRECT_WEBDRIVER_ACTION
    assert result.verdict == ValidationVerdict.PASS
    assert result.messages == ()


def test_import_based_detection_fails_a_step_definition_that_imports_webdriver() -> None:
    result = evaluate_direct_webdriver_action(
        [
            Cp3GeneratedClassInput(
                class_name="LoginSteps", java_source=_IMPORT_ONLY_VIOLATION_STEP_DEFINITION
            )
        ]
    )

    assert result.verdict == ValidationVerdict.FAIL
    assert len(result.messages) == 1
    assert "imports org.openqa.selenium.WebDriver directly" in result.messages[0]


def test_call_based_detection_fails_a_step_definition_that_calls_webdriver_directly() -> None:
    result = evaluate_direct_webdriver_action(
        [
            Cp3GeneratedClassInput(
                class_name="LoginSteps", java_source=_CALL_BASED_VIOLATION_STEP_DEFINITION
            )
        ]
    )

    assert result.verdict == ValidationVerdict.FAIL
    # Both proscriptions fire independently: the import AND the direct call.
    joined = " | ".join(result.messages)
    assert "imports org.openqa.selenium.WebDriver directly" in joined
    assert "driver.findElement(...)" in joined


def test_page_object_calling_webdriver_directly_is_not_flagged() -> None:
    """The class-role proof: identical WebDriver usage (import + direct
    findElement call) is untouched when the class's own parsed package is
    com.automation.pages, not com.automation.steps -- WebDriver legitimately
    belongs there."""
    result = evaluate_direct_webdriver_action(
        [
            Cp3GeneratedClassInput(
                class_name="LoginPage", java_source=_PAGE_OBJECT_WITH_WEBDRIVER
            )
        ]
    )

    assert result.verdict == ValidationVerdict.PASS
    assert result.messages == ()


def test_step_definition_fails_while_an_otherwise_identical_page_object_passes_in_one_run() -> (
    None
):
    """The precise, class-role-aware proof, both classes evaluated
    together in one call -- proving discrimination, not a coincidence of
    separate calls."""
    result = evaluate_direct_webdriver_action(
        [
            Cp3GeneratedClassInput(
                class_name="LoginSteps", java_source=_CALL_BASED_VIOLATION_STEP_DEFINITION
            ),
            Cp3GeneratedClassInput(
                class_name="LoginPage", java_source=_PAGE_OBJECT_WITH_WEBDRIVER
            ),
        ]
    )

    assert result.verdict == ValidationVerdict.FAIL
    assert len(result.messages) == 2  # both from LoginSteps; none from LoginPage
    assert all("LoginSteps" in message for message in result.messages)


def test_empty_input_passes_vacuously() -> None:
    result = evaluate_direct_webdriver_action([])

    assert result.verdict == ValidationVerdict.PASS
    assert result.messages == ()


def test_unparsable_source_is_skipped_not_a_criterion_failure() -> None:
    result = evaluate_direct_webdriver_action(
        [Cp3GeneratedClassInput(class_name="Broken", java_source="this is not { java at all")]
    )

    assert result.verdict == ValidationVerdict.PASS
    assert result.messages == ()


def test_deterministic_same_input_same_result() -> None:
    classes = [
        Cp3GeneratedClassInput(
            class_name="LoginSteps", java_source=_CALL_BASED_VIOLATION_STEP_DEFINITION
        )
    ]

    first = evaluate_direct_webdriver_action(classes)
    second = evaluate_direct_webdriver_action(classes)

    assert first == second


# --- long_method -------------------------------------------------------


def _class_with_method(
    package: str, class_name: str, method_name: str, body_line_count: int
) -> str:
    """A single-method class whose method spans exactly
    ``2 + body_line_count`` lines: the signature line, ``body_line_count``
    statement lines, and the closing-brace line."""
    body = "\n".join(f'        System.out.println("line {i}");' for i in range(body_line_count))
    return (
        f"package {package};\n\n"
        f"public class {class_name} {{\n\n"
        f"    public void {method_name}() {{\n"
        f"{body}\n"
        f"    }}\n"
        f"}}\n"
    )


def test_a_method_at_exactly_the_threshold_is_clean() -> None:
    # 1 signature line + 38 body lines + 1 closing-brace line == 40.
    source = _class_with_method("com.automation.pages", "AtLimitPage", "atLimit", 38)

    result = evaluate_long_method(
        [Cp3GeneratedClassInput(class_name="AtLimitPage", java_source=source)]
    )

    assert result.criterion == CRITERION_LONG_METHOD
    assert result.verdict == ValidationVerdict.PASS
    assert result.messages == ()


def test_a_method_one_line_over_the_threshold_is_flagged() -> None:
    # 1 signature line + 39 body lines + 1 closing-brace line == 41.
    source = _class_with_method("com.automation.pages", "OverLimitPage", "overLimit", 39)

    result = evaluate_long_method(
        [Cp3GeneratedClassInput(class_name="OverLimitPage", java_source=source)]
    )

    assert result.verdict == ValidationVerdict.FAIL
    assert len(result.messages) == 1
    assert result.messages[0] == (
        "OverLimitPage.overLimit: this method has 41 lines, which is greater than the "
        f"{MAX_METHOD_LINES} lines authorized. Split it into smaller methods."
    )


def test_long_method_applies_to_step_definitions_page_objects_and_utilities_alike() -> None:
    """Unlike direct_webdriver_action (step-definitions only), long_method
    has no class-role scope -- a >40-line method is a violation in any of
    the three generated-asset kinds."""
    step_def = _class_with_method("com.automation.steps", "LoginSteps", "iLogInAs", 39)
    page_object = _class_with_method("com.automation.pages", "LoginPage", "openPage", 39)
    utility = _class_with_method("com.automation.utils", "ConfigReader", "readAll", 39)

    result = evaluate_long_method(
        [
            Cp3GeneratedClassInput(class_name="LoginSteps", java_source=step_def),
            Cp3GeneratedClassInput(class_name="LoginPage", java_source=page_object),
            Cp3GeneratedClassInput(class_name="ConfigReader", java_source=utility),
        ]
    )

    assert result.verdict == ValidationVerdict.FAIL
    assert len(result.messages) == 3
    assert any("LoginSteps.iLogInAs" in m for m in result.messages)
    assert any("LoginPage.openPage" in m for m in result.messages)
    assert any("ConfigReader.readAll" in m for m in result.messages)


def test_a_short_method_alongside_a_long_one_only_the_long_one_is_flagged() -> None:
    source = (
        "package com.automation.pages;\n\n"
        "public class MixedPage {\n\n"
        "    public void shortMethod() {\n"
        '        System.out.println("short");\n'
        "    }\n\n" + _method_only("longMethod", 39) + "}\n"
    )

    result = evaluate_long_method(
        [Cp3GeneratedClassInput(class_name="MixedPage", java_source=source)]
    )

    assert result.verdict == ValidationVerdict.FAIL
    assert len(result.messages) == 1
    assert "MixedPage.longMethod" in result.messages[0]
    assert "shortMethod" not in result.messages[0]


def _method_only(method_name: str, body_line_count: int) -> str:
    body = "\n".join(f'        System.out.println("line {i}");' for i in range(body_line_count))
    return f"    public void {method_name}() {{\n{body}\n    }}\n\n"


def test_long_method_empty_input_passes_vacuously() -> None:
    result = evaluate_long_method([])

    assert result.verdict == ValidationVerdict.PASS
    assert result.messages == ()


def test_long_method_unparsable_source_is_skipped_not_a_criterion_failure() -> None:
    result = evaluate_long_method(
        [Cp3GeneratedClassInput(class_name="Broken", java_source="this is not { java at all")]
    )

    assert result.verdict == ValidationVerdict.PASS
    assert result.messages == ()


def test_long_method_deterministic_same_input_same_result() -> None:
    classes = [
        Cp3GeneratedClassInput(
            class_name="OverLimitPage",
            java_source=_class_with_method("com.automation.pages", "OverLimitPage", "over", 39),
        )
    ]

    first = evaluate_long_method(classes)
    second = evaluate_long_method(classes)

    assert first == second
