package com.automation.steps;

import com.automation.base.DriverFactory;
import com.automation.pages.OrderPage;
import io.cucumber.java.en.Then;
import org.junit.jupiter.api.Assertions;

public class OrderSteps {

    private OrderPage orderPage;

    @Then("the order transaction should be completed successfully")
    public void theOrderTransactionShouldBeCompletedSuccessfully() {
        orderPage = orderPage != null ? orderPage : new OrderPage(DriverFactory.get());
        Assertions.assertTrue(orderPage.isTransactionCompleted(), "The order transaction was not completed successfully.");
    }
}