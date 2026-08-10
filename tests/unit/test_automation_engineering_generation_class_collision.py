"""Deterministic merge for two independently generated Java classes that
collide on the same class name (:mod:`automation_engineering.generation.class_collision`).

Proves the gap a live regeneration run hit and fixed by hand
(``[[cap-compile-gap-closed]]`` -- two step-def needs, "the user attempts to
login..." / "the system displays an error message...", both independently
named ``LoginSteps``, silently overwritten on the first assembly pass,
caught only by a catalog count mismatch, fixed with a manual text-level
merge): merging is now DETECTED and DETERMINISTIC, never a silent pick of
one side over the other, and a merge that is not safe to resolve
automatically escalates instead of guessing.
"""

from __future__ import annotations

import pytest

from automation_engineering.generation.class_collision import (
    UnsafeClassMergeError,
    merge_java_classes,
)

_EXISTING = """package com.automation.steps;

import io.cucumber.java.en.When;

public class LoginSteps {

    private LoginPage loginPage;

    @When("the user attempts to login with valid credentials")
    public void theUserAttemptsToLoginWithValidCredentials() {
        loginPage = loginPage != null ? loginPage : new LoginPage(DriverFactory.get());
        loginPage.login();
    }
}
"""

_INCOMING = """package com.automation.steps;

import io.cucumber.java.en.Then;
import org.junit.jupiter.api.Assertions;

public class LoginSteps {

    private LoginPage loginPage;

    @Then("the system displays an error message")
    public void theSystemDisplaysAnErrorMessage() {
        loginPage = loginPage != null ? loginPage : new LoginPage(DriverFactory.get());
        Assertions.assertTrue(loginPage.hasErrorMessage());
    }
}
"""


class TestSafeMerge:
    def test_both_methods_present_in_merged_output(self) -> None:
        merged = merge_java_classes(_EXISTING, _INCOMING)
        assert "theUserAttemptsToLoginWithValidCredentials" in merged
        assert "theSystemDisplaysAnErrorMessage" in merged
        assert merged.count("public class LoginSteps") == 1

    def test_merged_output_is_valid_java(self) -> None:
        import javalang

        merged = merge_java_classes(_EXISTING, _INCOMING)
        tree = javalang.parse.parse(merged)
        classes = [node for _, node in tree.filter(javalang.tree.ClassDeclaration)]
        assert len(classes) == 1
        method_names = {m.name for m in classes[0].methods}
        assert method_names == {
            "theUserAttemptsToLoginWithValidCredentials",
            "theSystemDisplaysAnErrorMessage",
        }

    def test_imports_from_both_sides_are_present(self) -> None:
        merged = merge_java_classes(_EXISTING, _INCOMING)
        assert "import io.cucumber.java.en.When;" in merged
        assert "import io.cucumber.java.en.Then;" in merged
        assert "import org.junit.jupiter.api.Assertions;" in merged

    def test_shared_identical_field_is_not_duplicated(self) -> None:
        merged = merge_java_classes(_EXISTING, _INCOMING)
        assert merged.count("private LoginPage loginPage;") == 1

    def test_merge_is_idempotent_against_the_same_incoming_source(self) -> None:
        merged_once = merge_java_classes(_EXISTING, _INCOMING)
        merged_twice = merge_java_classes(merged_once, _INCOMING)
        assert merged_twice == merged_once

    def test_identical_incoming_source_is_a_no_op(self) -> None:
        assert merge_java_classes(_EXISTING, _EXISTING) == _EXISTING

    def test_new_field_from_incoming_side_is_unioned_in(self) -> None:
        existing = """package com.automation.steps;

public class CheckoutSteps {

    public void placeOrder() {
        System.out.println("noop");
    }
}
"""
        incoming = """package com.automation.steps;

public class CheckoutSteps {

    private CheckoutPage checkoutPage;

    public void confirmOrder() {
        System.out.println("noop");
    }
}
"""
        merged = merge_java_classes(existing, incoming)
        assert "private CheckoutPage checkoutPage;" in merged
        assert "placeOrder" in merged
        assert "confirmOrder" in merged


class TestUnsafeMergeEscalatesRatherThanGuesses:
    def test_conflicting_method_body_under_the_same_name_is_unsafe(self) -> None:
        existing = """package com.automation.steps;

public class LoginSteps {

    public void theUserLogsIn() {
        System.out.println("A");
    }
}
"""
        incoming = """package com.automation.steps;

public class LoginSteps {

    public void theUserLogsIn() {
        System.out.println("B");
    }
}
"""
        with pytest.raises(UnsafeClassMergeError, match="theUserLogsIn"):
            merge_java_classes(existing, incoming)

    def test_conflicting_field_declaration_under_the_same_name_is_unsafe(self) -> None:
        existing = """package com.automation.steps;

public class LoginSteps {

    private LoginPage loginPage;

    public void theUserLogsIn() {
        System.out.println("noop");
    }
}
"""
        incoming = """package com.automation.steps;

public class LoginSteps {

    private CheckoutPage loginPage;

    public void anotherMethod() {
        System.out.println("noop");
    }
}
"""
        with pytest.raises(UnsafeClassMergeError, match="loginPage"):
            merge_java_classes(existing, incoming)

    def test_different_package_is_unsafe(self) -> None:
        existing = """package com.automation.steps;

public class LoginSteps {

    public void theUserLogsIn() {
        System.out.println("noop");
    }
}
"""
        incoming = """package com.automation.other;

public class LoginSteps {

    public void anotherMethod() {
        System.out.println("noop");
    }
}
"""
        with pytest.raises(UnsafeClassMergeError, match="package mismatch"):
            merge_java_classes(existing, incoming)

    def test_different_superclass_is_unsafe(self) -> None:
        existing = """package com.automation.pages;

public class LoginPage extends BasePage {

    public void doThing() {
        System.out.println("noop");
    }
}
"""
        incoming = """package com.automation.pages;

public class LoginPage {

    public void doOtherThing() {
        System.out.println("noop");
    }
}
"""
        with pytest.raises(UnsafeClassMergeError, match="superclass mismatch"):
            merge_java_classes(existing, incoming)

    def test_different_class_name_is_unsafe(self) -> None:
        existing = """package com.automation.steps;

public class LoginSteps {

    public void a() {
        System.out.println("noop");
    }
}
"""
        incoming = """package com.automation.steps;

public class CheckoutSteps {

    public void b() {
        System.out.println("noop");
    }
}
"""
        with pytest.raises(UnsafeClassMergeError, match="class-name mismatch"):
            merge_java_classes(existing, incoming)

    def test_more_than_one_top_level_class_is_unsafe(self) -> None:
        existing = """package com.automation.steps;

public class LoginSteps {

    public void a() {
        System.out.println("noop");
    }
}
"""
        incoming = """package com.automation.steps;

public class LoginSteps {

    public void b() {
        System.out.println("noop");
    }
}

class Helper {
}
"""
        with pytest.raises(UnsafeClassMergeError, match="exactly one top-level class"):
            merge_java_classes(existing, incoming)
