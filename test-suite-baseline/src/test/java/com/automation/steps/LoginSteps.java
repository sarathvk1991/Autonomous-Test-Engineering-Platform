package com.automation.steps;

import com.automation.base.DriverFactory;
import com.automation.pages.LoginPage;
import io.cucumber.java.en.Then;
import io.cucumber.java.en.When;
import org.junit.jupiter.api.Assertions;

public class LoginSteps {

    private LoginPage loginPage;

    @Then("the system displays an error message indicating invalid credentials")
    public void theSystemDisplaysAnErrorMessageIndicatingInvalidCredentials() {
        loginPage = loginPage != null ? loginPage : new LoginPage(DriverFactory.get());
        Assertions.assertTrue(loginPage.isErrorMessageDisplayed(), "Error message for invalid credentials was not displayed.");
    }

    @When("the user attempts to login with {string} credentials")
    public void theUserAttemptsToLoginWithCredentials(String credentials) {
        loginPage = loginPage != null ? loginPage : new LoginPage(DriverFactory.get());
        loginPage.attemptLogin(credentials);
    }

}