"""Proves ADR-0051 D2/D3's centerpiece claim directly, for the FOURTH
generator (`LivePageObjectGenerator`): each deterministic property check
catches the real defect shape it was built for, and passes real, clean,
tracked-corpus-shaped content unmodified. No LLM call, no I/O -- every case
here is a fixture string.

The three fixtures below are lifted directly from the real, currently-
tracked `test-suite-baseline/src/test/java/com/automation/pages/LoginPage.java`
and `InventoryPage.java` -- no reconstruction needed, since (like test-data,
unlike feature-content) a page object's raw generator output IS its final
Java text, no assembly step in between.
"""

from __future__ import annotations

from eval_harness.models import PropertyCheckOutcome
from eval_harness.page_object_eval_set import PAGE_OBJECT_EVAL_SET
from eval_harness.page_object_properties import (
    check_di_constructor,
    check_locator_validity,
    check_method_names_present,
    check_no_fictional_basepage_helper,
    run_property_checks,
)


def _context(case_id: str):  # type: ignore[no-untyped-def]
    return next(case.context for case in PAGE_OBJECT_EVAL_SET if case.case_id == case_id)


_ATTEMPT_LOGIN_CONTEXT = _context("login_attempt_with_credentials")
_ERROR_DISPLAYED_CONTEXT = _context("login_invalid_credentials_error")
_INVENTORY_SORTED_CONTEXT = _context("inventory_sorted_by_order")

#: Verbatim (module docstring, module fields) from the real, currently-tracked
#: `LoginPage.java`, scoped to `attemptLogin`'s own fields/method.
_CLEAN_ATTEMPT_LOGIN = (
    "package com.automation.pages;\n\n"
    "import com.automation.base.BasePage;\n"
    "import org.openqa.selenium.By;\n"
    "import org.openqa.selenium.WebDriver;\n"
    "import org.openqa.selenium.support.ui.ExpectedConditions;\n\n"
    "public class LoginPage extends BasePage {\n\n"
    '    private final By usernameField = By.id("username");\n'
    '    private final By passwordField = By.id("password");\n'
    '    private final By loginButton = By.id("login-button");\n\n'
    "    public LoginPage(WebDriver driver) {\n"
    "        super(driver);\n"
    "    }\n\n"
    "    public void attemptLogin(String credentials) {\n"
    "        wait.until(ExpectedConditions.visibilityOfElementLocated(usernameField))"
    ".sendKeys(credentials);\n"
    "        driver.findElement(passwordField).sendKeys(credentials);\n"
    "        driver.findElement(loginButton).click();\n"
    "    }\n"
    "}\n"
)

#: Verbatim from the real, currently-tracked `LoginPage.java`, scoped to
#: `isErrorMessageDisplayed`'s own field/method.
_CLEAN_ERROR_DISPLAYED = (
    "package com.automation.pages;\n\n"
    "import com.automation.base.BasePage;\n"
    "import org.openqa.selenium.By;\n"
    "import org.openqa.selenium.WebDriver;\n"
    "import org.openqa.selenium.support.ui.ExpectedConditions;\n\n"
    "public class LoginPage extends BasePage {\n\n"
    '    private final By errorMessage = By.id("error-message");\n\n'
    "    public LoginPage(WebDriver driver) {\n"
    "        super(driver);\n"
    "    }\n\n"
    "    public boolean isErrorMessageDisplayed() {\n"
    "        try {\n"
    "            return wait.until(ExpectedConditions.visibilityOfElementLocated(errorMessage))"
    ".isDisplayed();\n"
    "        } catch (Exception e) {\n"
    "            return false;\n"
    "        }\n"
    "    }\n"
    "}\n"
)

#: Verbatim from the real, currently-tracked `InventoryPage.java`.
_CLEAN_INVENTORY_SORTED = (
    "package com.automation.pages;\n\n"
    "import com.automation.base.BasePage;\n"
    "import org.openqa.selenium.By;\n"
    "import org.openqa.selenium.WebDriver;\n"
    "import org.openqa.selenium.WebElement;\n"
    "import org.openqa.selenium.support.ui.ExpectedConditions;\n"
    "import java.util.List;\n"
    "import java.util.stream.Collectors;\n"
    "import java.util.ArrayList;\n"
    "import java.util.Collections;\n\n"
    "public class InventoryPage extends BasePage {\n\n"
    '    private final By inventoryItemNames = By.className("inventory_item_name");\n\n'
    "    public InventoryPage(WebDriver driver) {\n"
    "        super(driver);\n"
    "    }\n\n"
    "    public boolean isInventorySortedBy(String order) {\n"
    "        List<WebElement> items = "
    "wait.until(ExpectedConditions.presenceOfAllElementsLocatedBy(inventoryItemNames));\n"
    "        List<String> names = items.stream()\n"
    "                .map(WebElement::getText)\n"
    "                .collect(Collectors.toList());\n\n"
    "        List<String> sortedNames = new ArrayList<>(names);\n"
    '        if ("asc".equalsIgnoreCase(order)) {\n'
    "            Collections.sort(sortedNames);\n"
    '        } else if ("desc".equalsIgnoreCase(order)) {\n'
    "            sortedNames.sort(Collections.reverseOrder());\n"
    "        }\n\n"
    "        return names.equals(sortedNames);\n"
    "    }\n"
    "}\n"
)


class TestCheckMethodNamesPresent:
    def test_passes_the_real_clean_corpus_text(self) -> None:
        result = check_method_names_present(_CLEAN_ATTEMPT_LOGIN, _ATTEMPT_LOGIN_CONTEXT)
        assert result.outcome == PropertyCheckOutcome.PASSED

    def test_catches_a_paraphrased_method_name(self) -> None:
        """Guards defect 1's regression -- 67% of requested method calls
        came back under a name the model paraphrased from `action_text`
        instead of the caller-supplied `method_name`,
        `[[cap-page-object-live-regen-findings]]`."""
        defective = _CLEAN_ATTEMPT_LOGIN.replace("attemptLogin", "loginWithCredentials")
        result = check_method_names_present(defective, _ATTEMPT_LOGIN_CONTEXT)
        assert result.outcome == PropertyCheckOutcome.FAILED
        assert "attemptLogin" in result.reason

    def test_always_applicable(self) -> None:
        result = check_method_names_present("", _ATTEMPT_LOGIN_CONTEXT)
        assert result.outcome != PropertyCheckOutcome.NOT_APPLICABLE


class TestCheckDiConstructor:
    def test_passes_the_real_clean_corpus_text(self) -> None:
        result = check_di_constructor(_CLEAN_ATTEMPT_LOGIN, _ATTEMPT_LOGIN_CONTEXT)
        assert result.outcome == PropertyCheckOutcome.PASSED

    def test_catches_a_no_arg_constructor(self) -> None:
        """Guards defect 2's regression -- `new XPage()` instead of a
        constructor-injected WebDriver, `[[cap-page-object-live-regen-
        findings]]`; the v1.3.0 prompt's own CONSTRAINTS text (ADR-0041
        D5)."""
        defective = _CLEAN_ATTEMPT_LOGIN.replace(
            "public LoginPage(WebDriver driver) {\n        super(driver);\n    }",
            "public LoginPage() {\n    }",
        )
        result = check_di_constructor(defective, _ATTEMPT_LOGIN_CONTEXT)
        assert result.outcome == PropertyCheckOutcome.FAILED
        assert "no-arg" in result.reason

    def test_catches_a_static_webdriver_field(self) -> None:
        defective = _CLEAN_ATTEMPT_LOGIN.replace(
            "public class LoginPage extends BasePage {\n",
            "public class LoginPage extends BasePage {\n"
            "    private static WebDriver staticDriver;\n",
        )
        result = check_di_constructor(defective, _ATTEMPT_LOGIN_CONTEXT)
        assert result.outcome == PropertyCheckOutcome.FAILED
        assert "statically" in result.reason

    def test_catches_a_missing_super_call(self) -> None:
        defective = _CLEAN_ATTEMPT_LOGIN.replace(
            "public LoginPage(WebDriver driver) {\n        super(driver);\n    }",
            "public LoginPage(WebDriver driver) {\n        this.localDriver = driver;\n    }",
        )
        result = check_di_constructor(defective, _ATTEMPT_LOGIN_CONTEXT)
        assert result.outcome == PropertyCheckOutcome.FAILED
        assert "super(driver)" in result.reason

    def test_always_applicable(self) -> None:
        result = check_di_constructor("", _ATTEMPT_LOGIN_CONTEXT)
        assert result.outcome != PropertyCheckOutcome.NOT_APPLICABLE


class TestCheckNoFictionalBasepageHelper:
    def test_passes_the_real_clean_corpus_text(self) -> None:
        result = check_no_fictional_basepage_helper(_CLEAN_ATTEMPT_LOGIN, _ATTEMPT_LOGIN_CONTEXT)
        assert result.outcome == PropertyCheckOutcome.PASSED

    def test_passes_the_real_clean_error_displayed_text(self) -> None:
        result = check_no_fictional_basepage_helper(
            _CLEAN_ERROR_DISPLAYED, _ERROR_DISPLAYED_CONTEXT
        )
        assert result.outcome == PropertyCheckOutcome.PASSED

    def test_catches_a_bare_call_to_a_name_with_no_real_api_at_all(self) -> None:
        """Guards defect 3's regression -- 31 of 32 generated classes called
        a fictional BasePage helper, `[[cap-page-object-live-regen-
        findings]]`. `isElementDisplayed` has no real API under that exact
        name anywhere (Selenium's own method is `isDisplayed()`)."""
        defective = _CLEAN_ERROR_DISPLAYED.replace(
            ".isDisplayed();", ";\n            return isElementDisplayed(errorMessage);"
        )
        result = check_no_fictional_basepage_helper(defective, _ERROR_DISPLAYED_CONTEXT)
        assert result.outcome == PropertyCheckOutcome.FAILED
        assert "isElementDisplayed" in result.reason

    def test_catches_a_bare_call_to_a_name_that_is_only_real_when_qualified(self) -> None:
        defective = _CLEAN_ATTEMPT_LOGIN.replace(
            "driver.findElement(loginButton).click();", "click();"
        )
        result = check_no_fictional_basepage_helper(defective, _ATTEMPT_LOGIN_CONTEXT)
        assert result.outcome == PropertyCheckOutcome.FAILED
        assert "click" in result.reason

    def test_a_qualified_call_to_the_same_ambiguous_name_is_not_flagged(self) -> None:
        """`driver.findElement(x).click()` is real Selenium usage -- the
        exact clean corpus text already exercises `sendKeys`/`click`
        qualified on `driver`, proving the qualifier distinction is not
        merely theoretical."""
        result = check_no_fictional_basepage_helper(_CLEAN_ATTEMPT_LOGIN, _ATTEMPT_LOGIN_CONTEXT)
        assert result.outcome == PropertyCheckOutcome.PASSED

    def test_always_applicable(self) -> None:
        result = check_no_fictional_basepage_helper("", _ATTEMPT_LOGIN_CONTEXT)
        assert result.outcome != PropertyCheckOutcome.NOT_APPLICABLE


class TestCheckLocatorValidity:
    def test_passes_the_real_clean_corpus_text(self) -> None:
        result = check_locator_validity(_CLEAN_ERROR_DISPLAYED, _ERROR_DISPLAYED_CONTEXT)
        assert result.outcome == PropertyCheckOutcome.PASSED

    def test_passes_the_real_clean_inventory_text(self) -> None:
        result = check_locator_validity(_CLEAN_INVENTORY_SORTED, _INVENTORY_SORTED_CONTEXT)
        assert result.outcome == PropertyCheckOutcome.PASSED

    def test_catches_an_absolute_xpath_locator(self) -> None:
        """Composes CP4's real, already-live `dynamic_xpath` criterion --
        proven, live, to fail on exactly this shape
        (`[[cp7-cp8-stage16-wiring]]`)."""
        defective = _CLEAN_ERROR_DISPLAYED.replace(
            'By.id("error-message")', 'By.xpath("/html/body/div[1]/span")'
        )
        result = check_locator_validity(defective, _ERROR_DISPLAYED_CONTEXT)
        assert result.outcome == PropertyCheckOutcome.FAILED
        assert "absolute XPath" in result.reason

    def test_not_applicable_for_unparseable_java(self) -> None:
        result = check_locator_validity("not even java", _ERROR_DISPLAYED_CONTEXT)
        assert result.outcome == PropertyCheckOutcome.NOT_APPLICABLE


class TestRunPropertyChecks:
    def test_runs_every_check_in_order_against_the_real_clean_corpus_text(self) -> None:
        results = run_property_checks(_CLEAN_ATTEMPT_LOGIN, _ATTEMPT_LOGIN_CONTEXT)
        assert [result.check_name for result in results] == [
            "method_names_present",
            "di_constructor",
            "no_fictional_basepage_helper",
            "locator_validity",
        ]
        assert all(result.outcome == PropertyCheckOutcome.PASSED for result in results)
