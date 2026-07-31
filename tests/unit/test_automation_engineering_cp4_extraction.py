"""Locator extraction from page-object Java source (ADR-0044 D6).

Proves both real conventions extract correctly: the platform's own
generation convention (`private final By field = By.xxx("value")`) and the
PageFactory `@FindBy` annotation style the catalog already anticipates but
this platform does not itself generate -- plus that `By.cssSelector` and
`@FindBy(css=...)` normalize to the SAME strategy string, and that
non-locator fields are silently skipped, never guessed at.
"""

from __future__ import annotations

import pytest

from automation_engineering.cp4.extraction import Cp4Locator, extract_locators
from automation_engineering.cp4.models import Cp4PageObjectInput

pytestmark = pytest.mark.unit

_BY_STYLE_PAGE = """
package com.automation.pages;

import com.automation.base.BasePage;
import org.openqa.selenium.By;
import org.openqa.selenium.WebDriver;

public class LoginPage extends BasePage {
    private final By usernameField = By.id("user-name");
    private final By passwordField = By.xpath("//input[@type='password']");
    private final By loginButton = By.cssSelector("#login-button");
    private String pageTitle;

    public LoginPage(WebDriver driver) {
        super(driver);
    }
}
"""

_FINDBY_STYLE_PAGE = """
package com.automation.pages;

import org.openqa.selenium.WebElement;
import org.openqa.selenium.support.FindBy;

public class LegacyLoginPage {
    @FindBy(id = "user-name")
    private WebElement usernameField;

    @FindBy(css = "#login-button")
    private WebElement loginButton;
}
"""


def _page(class_name: str, source: str) -> Cp4PageObjectInput:
    return Cp4PageObjectInput(class_name=class_name, java_source=source)


def test_extracts_by_style_locators_with_correct_strategy_and_value() -> None:
    locators = extract_locators(_page("com.automation.pages.LoginPage", _BY_STYLE_PAGE))
    by_field = {loc.field_name: loc for loc in locators}

    assert by_field["usernameField"] == Cp4Locator(
        class_name="com.automation.pages.LoginPage",
        field_name="usernameField",
        strategy="id",
        value="user-name",
    )
    assert by_field["passwordField"].strategy == "xpath"
    assert by_field["passwordField"].value == "//input[@type='password']"
    # By.cssSelector normalizes to the canonical "css" strategy.
    assert by_field["loginButton"].strategy == "css"
    assert by_field["loginButton"].value == "#login-button"


def test_non_locator_field_is_not_extracted() -> None:
    locators = extract_locators(_page("com.automation.pages.LoginPage", _BY_STYLE_PAGE))
    assert "pageTitle" not in {loc.field_name for loc in locators}


def test_extracts_findby_annotation_style_locators() -> None:
    locators = extract_locators(_page("com.automation.pages.LegacyLoginPage", _FINDBY_STYLE_PAGE))
    by_field = {loc.field_name: loc for loc in locators}

    assert by_field["usernameField"].strategy == "id"
    assert by_field["usernameField"].value == "user-name"
    # @FindBy(css=...) normalizes to the SAME canonical strategy as By.cssSelector.
    assert by_field["loginButton"].strategy == "css"
    assert by_field["loginButton"].value == "#login-button"


def test_field_with_no_recognizable_initializer_is_skipped() -> None:
    source = """
    package com.automation.pages;
    import org.openqa.selenium.By;
    public class OddPage {
        private final By computed = someFactory.build();
    }
    """
    locators = extract_locators(_page("com.automation.pages.OddPage", source))
    assert locators == ()
