package com.automation.steps;

import com.automation.pages.CheckoutConfirmationPage;
import io.cucumber.java.en.Then;
import org.junit.jupiter.api.Assertions;

public class CheckoutConfirmationSteps {

    private final CheckoutConfirmationPage checkoutConfirmationPage = new CheckoutConfirmationPage();

    @Then("the system proceeds to the checkout confirmation page")
    public void theSystemProceedsToTheCheckoutConfirmationPage() {
        Assertions.assertTrue(checkoutConfirmationPage.isDisplayed(), "The system failed to navigate to the checkout confirmation page.");
    }
}