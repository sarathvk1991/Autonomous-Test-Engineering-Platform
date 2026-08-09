package com.automation.steps;

import com.automation.base.DriverFactory;
import com.automation.pages.AccessDeniedPage;
import io.cucumber.java.en.Then;
import org.junit.jupiter.api.Assertions;

public class AccessDeniedSteps {

    private AccessDeniedPage accessDeniedPage;

    @Then("the system should display an access denied message")
    public void theSystemShouldDisplayAnAccessDeniedMessage() {
        accessDeniedPage = accessDeniedPage != null ? accessDeniedPage : new AccessDeniedPage(DriverFactory.get());
        Assertions.assertTrue(accessDeniedPage.isAccessDeniedMessageDisplayed(), "Access denied message was not displayed as expected.");
    }
}