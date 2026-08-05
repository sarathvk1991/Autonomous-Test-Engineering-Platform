package com.automation.steps;

import com.automation.pages.ShoppingCartPage;
import io.cucumber.java.en.Then;
import org.junit.jupiter.api.Assertions;

public class ShoppingCartSteps {

    private final ShoppingCartPage shoppingCartPage = new ShoppingCartPage();

    @Then("the user is redirected to the shopping cart page")
    public void theUserIsRedirectedToTheShoppingCartPage() {
        Assertions.assertTrue(shoppingCartPage.isDisplayed(), "User was not redirected to the shopping cart page.");
    }
}