package com.automation.steps;

import com.automation.pages.OrderPage;
import io.cucumber.java.en.Then;
import org.junit.jupiter.api.Assertions;

public class OrderSteps {

    private final OrderPage orderPage = new OrderPage();

    @Then("the order transaction should be completed successfully")
    public void theOrderTransactionShouldBeCompletedSuccessfully() {
        Assertions.assertTrue(orderPage.isTransactionCompleted(), "The order transaction was not completed successfully.");
    }
}