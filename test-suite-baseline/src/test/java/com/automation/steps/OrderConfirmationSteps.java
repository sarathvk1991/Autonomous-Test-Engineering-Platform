package com.automation.steps;

import com.automation.pages.OrderConfirmationPage;
import io.cucumber.java.en.When;

public class OrderConfirmationSteps {

    private final OrderConfirmationPage orderConfirmationPage = new OrderConfirmationPage();

    @When("the user navigates to the order confirmation page")
    public void theUserNavigatesToTheOrderConfirmationPage() {
        orderConfirmationPage.navigateToConfirmation();
    }
}