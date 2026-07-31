"""CP4 -- static locator health (ADR-0044 D6).

Proves, deterministically and with zero live calls: a clean page object
(the platform's own established `LoginPage` fixture, the same shape
`test_automation_engineering_catalog.py` uses -- no real `LoginPage.java`
is committed to `test-suite-baseline/` yet, only the locator-free
`SmokePage`, so this is the most honest stand-in for "a real baseline page
object") passes all four criteria; each criterion fails INDEPENDENTLY --
uniqueness, duplicates, dynamic-xpath, and well-formedness each fail alone,
never masquerading as one another; the intra-class/cross-class split
between uniqueness and duplicate_locators is mutually exclusive by
construction; and the whole gate is a pure function (deterministic, no
network call).
"""

from __future__ import annotations

import socket

import pytest

from automation_engineering.cp4.gate import evaluate_cp4
from automation_engineering.cp4.models import (
    CRITERION_DUPLICATE_LOCATORS,
    CRITERION_DYNAMIC_XPATH,
    CRITERION_LOCATOR_UNIQUENESS,
    CRITERION_WELL_FORMEDNESS,
    Cp4PageObjectInput,
)
from shared.enums.base import ValidationVerdict

pytestmark = pytest.mark.unit

#: The platform's own established LoginPage fixture -- the SAME shape
#: `tests/unit/test_automation_engineering_catalog.py::_FIXTURE_PAGE_OBJECT`
#: uses to prove the catalog's own locator-field extraction, extended here
#: with a third, stable locator so all three real `By` strategies this
#: platform's generation prompt names (id/xpath/cssSelector) appear at
#: least once.
_LOGIN_PAGE = """
package com.automation.pages;

import com.automation.base.BasePage;
import org.openqa.selenium.By;
import org.openqa.selenium.WebDriver;

/** Fixture login page -- proves locator field extraction. */
public class LoginPage extends BasePage {

    private final By usernameField = By.id("user-name");
    private final By passwordField = By.id("password");
    private final By loginButton = By.cssSelector("#login-button");

    public LoginPage(WebDriver driver) {
        super(driver);
    }

    public void login(String username, String password) {
        open("/login");
    }
}
"""


def _page(class_name: str, source: str) -> Cp4PageObjectInput:
    return Cp4PageObjectInput(class_name=class_name, java_source=source)


def test_the_real_baseline_style_login_page_passes_all_four_criteria() -> None:
    result = evaluate_cp4((_page("com.automation.pages.LoginPage", _LOGIN_PAGE),))

    assert result.overall_verdict == ValidationVerdict.PASS
    assert result.passed is True
    for criterion in (
        CRITERION_LOCATOR_UNIQUENESS,
        CRITERION_DUPLICATE_LOCATORS,
        CRITERION_DYNAMIC_XPATH,
        CRITERION_WELL_FORMEDNESS,
    ):
        assert result.criterion(criterion).verdict == ValidationVerdict.PASS
        assert result.criterion(criterion).messages == ()


def test_two_fields_sharing_a_locator_fails_only_uniqueness() -> None:
    source = """
    package com.automation.pages;
    import org.openqa.selenium.By;
    public class LoginPage {
        private final By usernameField = By.id("user-name");
        private final By loginField = By.id("user-name");
    }
    """
    result = evaluate_cp4((_page("com.automation.pages.LoginPage", source),))

    assert result.overall_verdict == ValidationVerdict.FAIL
    uniqueness = result.criterion(CRITERION_LOCATOR_UNIQUENESS)
    assert uniqueness.verdict == ValidationVerdict.FAIL
    assert "usernameField" in uniqueness.messages[0]
    assert "loginField" in uniqueness.messages[0]
    # Independence: nothing else fails.
    assert result.criterion(CRITERION_DUPLICATE_LOCATORS).verdict == ValidationVerdict.PASS
    assert result.criterion(CRITERION_DYNAMIC_XPATH).verdict == ValidationVerdict.PASS
    assert result.criterion(CRITERION_WELL_FORMEDNESS).verdict == ValidationVerdict.PASS


def test_identical_locator_across_two_classes_fails_only_duplicate_locators() -> None:
    login_page = _page(
        "com.automation.pages.LoginPage",
        """
        package com.automation.pages;
        import org.openqa.selenium.By;
        public class LoginPage {
            private final By submit = By.id("submit-button");
        }
        """,
    )
    checkout_page = _page(
        "com.automation.pages.CheckoutPage",
        """
        package com.automation.pages;
        import org.openqa.selenium.By;
        public class CheckoutPage {
            private final By submit = By.id("submit-button");
        }
        """,
    )
    result = evaluate_cp4((login_page, checkout_page))

    assert result.overall_verdict == ValidationVerdict.FAIL
    duplicates = result.criterion(CRITERION_DUPLICATE_LOCATORS)
    assert duplicates.verdict == ValidationVerdict.FAIL
    assert "LoginPage" in duplicates.messages[0]
    assert "CheckoutPage" in duplicates.messages[0]
    # Independence: a CROSS-class collision never trips the INTRA-class check.
    assert result.criterion(CRITERION_LOCATOR_UNIQUENESS).verdict == ValidationVerdict.PASS
    assert result.criterion(CRITERION_DYNAMIC_XPATH).verdict == ValidationVerdict.PASS
    assert result.criterion(CRITERION_WELL_FORMEDNESS).verdict == ValidationVerdict.PASS


def test_absolute_xpath_fails_only_dynamic_xpath() -> None:
    source = """
    package com.automation.pages;
    import org.openqa.selenium.By;
    public class CartPage {
        private final By total = By.xpath("/html/body/div/span");
    }
    """
    result = evaluate_cp4((_page("com.automation.pages.CartPage", source),))

    assert result.overall_verdict == ValidationVerdict.FAIL
    dynamic = result.criterion(CRITERION_DYNAMIC_XPATH)
    assert dynamic.verdict == ValidationVerdict.FAIL
    assert "absolute XPath" in dynamic.messages[0]
    # Independence.
    assert result.criterion(CRITERION_LOCATOR_UNIQUENESS).verdict == ValidationVerdict.PASS
    assert result.criterion(CRITERION_DUPLICATE_LOCATORS).verdict == ValidationVerdict.PASS
    assert result.criterion(CRITERION_WELL_FORMEDNESS).verdict == ValidationVerdict.PASS


def test_indexed_predicate_xpath_fails_dynamic_xpath() -> None:
    source = """
    package com.automation.pages;
    import org.openqa.selenium.By;
    public class CartPage {
        private final By row = By.xpath("//table//tr[3]/td");
    }
    """
    result = evaluate_cp4((_page("com.automation.pages.CartPage", source),))

    dynamic = result.criterion(CRITERION_DYNAMIC_XPATH)
    assert dynamic.verdict == ValidationVerdict.FAIL
    assert "positional/indexed" in dynamic.messages[0]


def test_auto_generated_looking_id_fails_dynamic_xpath_regardless_of_strategy() -> None:
    source = """
    package com.automation.pages;
    import org.openqa.selenium.By;
    public class CartPage {
        private final By widget = By.id("ext-gen-104829");
    }
    """
    result = evaluate_cp4((_page("com.automation.pages.CartPage", source),))

    assert result.overall_verdict == ValidationVerdict.FAIL
    dynamic = result.criterion(CRITERION_DYNAMIC_XPATH)
    assert dynamic.verdict == ValidationVerdict.FAIL
    assert "auto-generated" in dynamic.messages[0]
    # Independence -- a well-formed, unique, non-xpath id-strategy locator.
    assert result.criterion(CRITERION_LOCATOR_UNIQUENESS).verdict == ValidationVerdict.PASS
    assert result.criterion(CRITERION_DUPLICATE_LOCATORS).verdict == ValidationVerdict.PASS
    assert result.criterion(CRITERION_WELL_FORMEDNESS).verdict == ValidationVerdict.PASS


def test_malformed_locator_fails_only_well_formedness() -> None:
    source = r"""
    package com.automation.pages;
    import org.openqa.selenium.By;
    public class CartPage {
        private final By item = By.xpath("//div[@id='foo");
    }
    """
    result = evaluate_cp4((_page("com.automation.pages.CartPage", source),))

    assert result.overall_verdict == ValidationVerdict.FAIL
    well_formed = result.criterion(CRITERION_WELL_FORMEDNESS)
    assert well_formed.verdict == ValidationVerdict.FAIL
    assert "unbalanced" in well_formed.messages[0]
    # Independence.
    assert result.criterion(CRITERION_LOCATOR_UNIQUENESS).verdict == ValidationVerdict.PASS
    assert result.criterion(CRITERION_DUPLICATE_LOCATORS).verdict == ValidationVerdict.PASS
    assert result.criterion(CRITERION_DYNAMIC_XPATH).verdict == ValidationVerdict.PASS


def test_evaluate_cp4_is_deterministic() -> None:
    page_objects = (_page("com.automation.pages.LoginPage", _LOGIN_PAGE),)
    assert evaluate_cp4(page_objects) == evaluate_cp4(page_objects)


def test_evaluate_cp4_makes_no_network_call(monkeypatch: pytest.MonkeyPatch) -> None:
    """CP4 is pure static analysis -- proven, not merely claimed: patch
    `socket.socket` to raise if CP4 ever tries to open one."""

    def _forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("CP4 attempted to open a network socket")

    monkeypatch.setattr(socket, "socket", _forbidden)
    result = evaluate_cp4((_page("com.automation.pages.LoginPage", _LOGIN_PAGE),))

    assert result.passed is True


def test_empty_page_object_set_passes_vacuously() -> None:
    result = evaluate_cp4(())
    assert result.overall_verdict == ValidationVerdict.PASS
