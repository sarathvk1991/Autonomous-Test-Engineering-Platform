package com.automation.steps;

import com.automation.pages.ConfirmationPage;
import io.cucumber.java.en.Then;
import org.junit.jupiter.api.Assertions;

public class ConfirmationSteps {

    private final ConfirmationPage confirmationPage = new ConfirmationPage();

    @Then("the user should see a confirmation message")
    public void theUserShouldSeeAConfirmationMessage() {
        Assertions.assertTrue(confirmationPage.isConfirmationMessageDisplayed(), "Confirmation message was not visible on the page.");
    }
}