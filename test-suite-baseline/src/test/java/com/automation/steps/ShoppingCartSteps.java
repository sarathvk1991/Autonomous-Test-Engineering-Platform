package com.automation.steps;

import com.automation.base.DriverFactory;
import com.automation.pages.ShoppingCartPage;
import io.cucumber.java.en.Then;
import org.junit.jupiter.api.Assertions;

public class ShoppingCartSteps {

    private ShoppingCartPage shoppingCartPage;

    @Then("the user is redirected to the shopping cart page")
    public void theUserIsRedirectedToTheShoppingCartPage() {
        shoppingCartPage = shoppingCartPage != null ? shoppingCartPage : new ShoppingCartPage(DriverFactory.get());
        Assertions.assertTrue(shoppingCartPage.isDisplayed(), "User was not redirected to the shopping cart page.");
    }
}