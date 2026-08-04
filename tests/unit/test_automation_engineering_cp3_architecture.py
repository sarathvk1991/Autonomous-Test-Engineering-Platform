"""CP3's `direct_webdriver_action` criterion (ADR-0044 D5 revision,
2026-08-04): a static, `javalang`-based, class-role-aware check for the
half of `customqa:*` SonarQube cannot natively express. No network call,
no subprocess, no live infrastructure anywhere in this module -- pure
function of in-memory Java source text, mirroring CP4's own static
discipline (`tests/unit/test_automation_engineering_cp4_gate.py`).

Proves: import-based detection, call-based detection, a clean pass, and
the class-role proof this whole build exists for -- the SAME WebDriver
usage that fails a step-definition class is left untouched on an
otherwise-identical page-object class, the precision a Sonar file-path
exclusion could only approximate.
"""

from __future__ import annotations

import pytest

from automation_engineering.cp3.architecture import (
    CRITERION_DIRECT_WEBDRIVER_ACTION,
    Cp3GeneratedClassInput,
    evaluate_direct_webdriver_action,
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
