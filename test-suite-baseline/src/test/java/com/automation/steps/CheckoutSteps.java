package com.automation.steps;

import com.automation.pages.CheckoutPage;
import io.cucumber.java.en.When;

public class CheckoutSteps {

    private final CheckoutPage checkoutPage = new CheckoutPage();

    @When("the user submits the checkout form")
    public void theUserSubmitsTheCheckoutForm() {
        checkoutPage.submitForm();
    }
}