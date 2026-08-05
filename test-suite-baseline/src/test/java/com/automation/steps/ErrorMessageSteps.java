package com.automation.steps;

import com.automation.pages.LoginPage;
import io.cucumber.java.en.Then;
import org.junit.jupiter.api.Assertions;

public class ErrorMessageSteps {

    private final LoginPage loginPage = new LoginPage();

    @Then("the system displays an error message indicating invalid credentials")
    public void theSystemDisplaysAnErrorMessageIndicatingInvalidCredentials() {
        Assertions.assertTrue(loginPage.isInvalidCredentialsErrorMessageDisplayed(), 
            "The error message for invalid credentials was not displayed.");
    }
}