package com.automation.steps;

import com.automation.base.DriverFactory;
import com.automation.pages.CheckoutConfirmationPage;
import io.cucumber.java.en.Then;
import org.junit.jupiter.api.Assertions;

public class CheckoutConfirmationSteps {

    private CheckoutConfirmationPage checkoutConfirmationPage;

    @Then("the system proceeds to the checkout confirmation page")
    public void theSystemProceedsToTheCheckoutConfirmationPage() {
        checkoutConfirmationPage = checkoutConfirmationPage != null ? checkoutConfirmationPage : new CheckoutConfirmationPage(DriverFactory.get());
        Assertions.assertTrue(checkoutConfirmationPage.isDisplayed(), "The system failed to navigate to the checkout confirmation page.");
    }
}