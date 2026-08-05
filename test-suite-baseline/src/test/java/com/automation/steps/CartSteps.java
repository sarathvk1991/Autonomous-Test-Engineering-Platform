package com.automation.steps;

import com.automation.pages.CartPage;
import io.cucumber.java.en.Then;
import org.junit.jupiter.api.Assertions;

public class CartSteps {

    private final CartPage cartPage = new CartPage();

    @Then("the cart count should display {string}")
    public void theCartCountShouldDisplay(String expectedCount) {
        Assertions.assertEquals(expectedCount, cartPage.getCartCount(), "The cart count does not match the expected value.");
    }
}