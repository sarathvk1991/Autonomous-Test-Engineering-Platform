"""Proves ADR-0051 D2/D3's centerpiece claim directly: each deterministic
property check catches the real, specific `gemini-2.5-flash` defect shape
it was built for (`[[cap-compile-gap-closed]]`), and passes the real,
currently-tracked-baseline `LoginSteps.java` content unmodified. No LLM
call, no I/O -- every case here is a fixture string.
"""

from __future__ import annotations

from automation_engineering.generation.step_definition_generator import (
    StepDefinitionGenerationContext,
)
from automation_engineering.reuse.models import GherkinStepNeed
from eval_harness.models import PropertyCheckOutcome
from eval_harness.step_definition_properties import (
    check_no_fabricated_page_object_class,
    check_no_markdown_fence,
    check_valid_cucumber_import,
    run_property_checks,
)

#: Verbatim from the real, currently-tracked, currently-compiling
#: `test-suite-baseline/src/test/java/com/automation/steps/LoginSteps.java`
#: -- the exact corpus `[[cap-compile-gap-closed]]`'s real `gemini-2.5-flash`
#: measurement regenerated and found 76% defective.
_CLEAN_LOGIN_ATTEMPT = """\
package com.automation.steps;

import com.automation.base.DriverFactory;
import com.automation.pages.LoginPage;
import io.cucumber.java.en.When;

public class LoginSteps {

    private LoginPage loginPage;

    @When("the user attempts to login with {string} credentials")
    public void theUserAttemptsToLoginWithCredentials(String credentials) {
        loginPage = loginPage != null ? loginPage : new LoginPage(DriverFactory.get());
        loginPage.attemptLogin(credentials);
    }

}
"""

_CONTEXT_WITH_PAGE_OBJECT = StepDefinitionGenerationContext(
    need=GherkinStepNeed(
        text="the user attempts to login with {string} credentials", step_type="When"
    ),
    target_package="com.automation.steps",
    customqa_constraints=(),
    page_object_interface="com.automation.pages.LoginPage",
)

_CONTEXT_WITHOUT_PAGE_OBJECT = StepDefinitionGenerationContext(
    need=GherkinStepNeed(text="the system reaches a ready state", step_type="Given"),
    target_package="com.automation.steps",
    customqa_constraints=(),
    page_object_interface=None,
)


class TestCheckValidCucumberImport:
    def test_passes_the_real_clean_corpus_text(self) -> None:
        result = check_valid_cucumber_import(_CLEAN_LOGIN_ATTEMPT, _CONTEXT_WITH_PAGE_OBJECT)
        assert result.outcome == PropertyCheckOutcome.PASSED

    def test_catches_the_real_defect_1_shape_wrong_import_package(self) -> None:
        """The dominant real defect: 8/17 real generations imported
        `io.cucumber.java.When` instead of `io.cucumber.java.en.When`
        (`[[cap-compile-gap-closed]]`)."""
        defective = _CLEAN_LOGIN_ATTEMPT.replace(
            "import io.cucumber.java.en.When;", "import io.cucumber.java.When;"
        )
        result = check_valid_cucumber_import(defective, _CONTEXT_WITH_PAGE_OBJECT)
        assert result.outcome == PropertyCheckOutcome.FAILED
        assert "io.cucumber.java.en" in result.reason

    def test_fails_when_the_correct_import_is_missing_entirely(self) -> None:
        defective = _CLEAN_LOGIN_ATTEMPT.replace("import io.cucumber.java.en.When;\n", "")
        result = check_valid_cucumber_import(defective, _CONTEXT_WITH_PAGE_OBJECT)
        assert result.outcome == PropertyCheckOutcome.FAILED

    def test_not_applicable_when_no_cucumber_annotation_is_present(self) -> None:
        no_annotation_text = "package com.automation.steps;\n\npublic class NoOpSteps {}\n"
        result = check_valid_cucumber_import(no_annotation_text, _CONTEXT_WITHOUT_PAGE_OBJECT)
        assert result.outcome == PropertyCheckOutcome.NOT_APPLICABLE


class TestCheckNoMarkdownFence:
    def test_passes_the_real_clean_corpus_text(self) -> None:
        result = check_no_markdown_fence(_CLEAN_LOGIN_ATTEMPT, _CONTEXT_WITH_PAGE_OBJECT)
        assert result.outcome == PropertyCheckOutcome.PASSED

    def test_catches_the_real_defect_2_shape_markdown_fence(self) -> None:
        """The second real defect: 2/17 real generations wrapped the
        response in a markdown code fence despite an explicit no-markdown
        prompt contract (`[[cap-compile-gap-closed]]`)."""
        defective = f"```java\n{_CLEAN_LOGIN_ATTEMPT}```\n"
        result = check_no_markdown_fence(defective, _CONTEXT_WITH_PAGE_OBJECT)
        assert result.outcome == PropertyCheckOutcome.FAILED

    def test_always_applicable(self) -> None:
        result = check_no_markdown_fence("", _CONTEXT_WITHOUT_PAGE_OBJECT)
        assert result.outcome != PropertyCheckOutcome.NOT_APPLICABLE


class TestCheckNoFabricatedPageObjectClass:
    def test_passes_the_real_clean_corpus_text(self) -> None:
        result = check_no_fabricated_page_object_class(
            _CLEAN_LOGIN_ATTEMPT, _CONTEXT_WITH_PAGE_OBJECT
        )
        assert result.outcome == PropertyCheckOutcome.PASSED

    def test_catches_the_real_defect_3_shape_fabricated_duplicate_class(self) -> None:
        """The third real defect: 3-4/17 real generations fabricated an
        inline duplicate page-object class instead of referencing the
        external one (`[[cap-compile-gap-closed]]`)."""
        defective = _CLEAN_LOGIN_ATTEMPT.replace(
            "import com.automation.pages.LoginPage;\n",
            "",
        ).replace(
            "public class LoginSteps {",
            (
                "class LoginPage {\n"
                "    boolean attemptLogin(String credentials) { return true; }\n"
                "}\n\n"
                "public class LoginSteps {"
            ),
        )
        result = check_no_fabricated_page_object_class(defective, _CONTEXT_WITH_PAGE_OBJECT)
        assert result.outcome == PropertyCheckOutcome.FAILED
        assert "LoginPage" in result.reason

    def test_fails_when_the_expected_page_object_is_never_referenced(self) -> None:
        unrelated_text = "package com.automation.steps;\n\npublic class LoginSteps {}\n"
        result = check_no_fabricated_page_object_class(unrelated_text, _CONTEXT_WITH_PAGE_OBJECT)
        assert result.outcome == PropertyCheckOutcome.FAILED

    def test_not_applicable_when_no_page_object_was_expected(self) -> None:
        result = check_no_fabricated_page_object_class("anything", _CONTEXT_WITHOUT_PAGE_OBJECT)
        assert result.outcome == PropertyCheckOutcome.NOT_APPLICABLE


class TestRunPropertyChecks:
    def test_runs_every_check_in_order_against_the_real_clean_corpus_text(self) -> None:
        results = run_property_checks(_CLEAN_LOGIN_ATTEMPT, _CONTEXT_WITH_PAGE_OBJECT)
        assert [result.check_name for result in results] == [
            "valid_cucumber_import",
            "no_markdown_fence",
            "no_fabricated_page_object_class",
        ]
        assert all(result.outcome == PropertyCheckOutcome.PASSED for result in results)
