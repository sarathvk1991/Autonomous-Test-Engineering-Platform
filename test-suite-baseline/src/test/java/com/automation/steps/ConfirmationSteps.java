package com.automation.steps;

import com.automation.base.DriverFactory;
import com.automation.pages.ConfirmationPage;
import io.cucumber.java.en.Then;
import org.junit.jupiter.api.Assertions;

public class ConfirmationSteps {

    private ConfirmationPage confirmationPage;

    @Then("the user should see a confirmation message")
    public void theUserShouldSeeAConfirmationMessage() {
        confirmationPage = confirmationPage != null ? confirmationPage : new ConfirmationPage(DriverFactory.get());
        Assertions.assertTrue(confirmationPage.isConfirmationMessageDisplayed(), "The confirmation message was not displayed.");
    }
}