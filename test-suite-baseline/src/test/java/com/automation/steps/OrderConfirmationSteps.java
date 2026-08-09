package com.automation.steps;

import com.automation.base.DriverFactory;
import com.automation.pages.OrderConfirmationPage;
import io.cucumber.java.en.When;

public class OrderConfirmationSteps {

    private OrderConfirmationPage orderConfirmationPage;

    @When("the user navigates to the order confirmation page")
    public void theUserNavigatesToTheOrderConfirmationPage() {
        orderConfirmationPage = orderConfirmationPage != null ? orderConfirmationPage : new OrderConfirmationPage(DriverFactory.get());
        orderConfirmationPage.navigateToOrderConfirmation();
    }
}