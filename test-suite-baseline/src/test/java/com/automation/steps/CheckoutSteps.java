package com.automation.steps;

import com.automation.base.DriverFactory;
import com.automation.pages.CheckoutPage;
import io.cucumber.java.en.When;

public class CheckoutSteps {

    private CheckoutPage checkoutPage;

    @When("the user submits the checkout form")
    public void theUserSubmitsTheCheckoutForm() {
        checkoutPage = checkoutPage != null ? checkoutPage : new CheckoutPage(DriverFactory.get());
        checkoutPage.submitForm();
    }
}