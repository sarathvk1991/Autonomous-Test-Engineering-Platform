package com.automation.steps;

import com.automation.pages.AuthenticationPage;
import io.cucumber.java.en.When;

public class AuthenticationSteps {

    private final AuthenticationPage authenticationPage = new AuthenticationPage();

    @When("the user authenticates with valid credentials")
    public void theUserAuthenticatesWithValidCredentials() {
        authenticationPage.performValidAuthentication();
    }
}