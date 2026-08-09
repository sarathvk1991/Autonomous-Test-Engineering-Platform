package com.automation.steps;

import com.automation.base.DriverFactory;
import com.automation.pages.AuthenticationPage;
import io.cucumber.java.en.When;

public class AuthenticationSteps {

    private AuthenticationPage authenticationPage;

    @When("the user authenticates with valid credentials")
    public void theUserAuthenticatesWithValidCredentials() {
        authenticationPage = authenticationPage != null ? authenticationPage : new AuthenticationPage(DriverFactory.get());
        authenticationPage.performValidAuthentication();
    }
}