package com.automation.steps;

import io.cucumber.java.en.Then;
import org.junit.jupiter.api.Assertions;
import com.automation.pages.AccessDeniedPage;

public class AccessDeniedSteps {

    private final AccessDeniedPage accessDeniedPage = new AccessDeniedPage();

    @Then("the system should display an access denied message")
    public void theSystemShouldDisplayAnAccessDeniedMessage() {
        Assertions.assertTrue(accessDeniedPage.isAccessDeniedMessageDisplayed(), "Access denied message was not displayed.");
    }
}