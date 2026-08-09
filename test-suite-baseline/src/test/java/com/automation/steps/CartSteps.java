package com.automation.steps;

import com.automation.base.DriverFactory;
import com.automation.pages.CartPage;
import io.cucumber.java.en.Then;
import org.junit.jupiter.api.Assertions;

public class CartSteps {

    private CartPage cartPage;

    @Then("the cart count should display {string}")
    public void theCartCountShouldDisplay(String expectedCount) {
        cartPage = cartPage != null ? cartPage : new CartPage(DriverFactory.get());
        Assertions.assertEquals(expectedCount, cartPage.getCartCount(), "The cart count does not match the expected value.");
    }
}