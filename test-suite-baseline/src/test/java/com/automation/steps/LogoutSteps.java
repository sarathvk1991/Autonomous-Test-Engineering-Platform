package com.automation.steps;

import com.automation.base.DriverFactory;
import com.automation.pages.LogoutPage;
import io.cucumber.java.en.When;

public class LogoutSteps {

    private LogoutPage logoutPage;

    @When("the user performs the logout action")
    public void theUserPerformsTheLogoutAction() {
        logoutPage = logoutPage != null ? logoutPage : new LogoutPage(DriverFactory.get());
        logoutPage.performLogout();
    }
}