package com.automation.steps;

import io.cucumber.java.en.Given;
import com.automation.pages.PurchasePage;

public class PurchaseSteps {

    private final PurchasePage purchasePage = new PurchasePage();

    @Given("the user has completed a purchase")
    public void theUserHasCompletedAPurchase() {
        purchasePage.completePurchase();
    }
}