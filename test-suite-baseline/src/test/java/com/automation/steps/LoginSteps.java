package com.automation.steps;

import io.cucumber.java.en.When;
import com.automation.pages.LoginPage;

public class LoginSteps {

    private final LoginPage loginPage = new LoginPage();

    @When("the user attempts to login with {string} credentials")
    public void theUserAttemptsToLoginWithCredentials(String scenarioType) {
        loginPage.attemptLoginWithCredentials(scenarioType);
    }
}