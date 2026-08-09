package com.automation.steps;

import com.automation.base.DriverFactory;
import com.automation.pages.PurchasePage;
import io.cucumber.java.en.Given;

public class PurchaseSteps {

    private PurchasePage purchasePage;

    @Given("the user has completed a purchase")
    public void theUserHasCompletedAPurchase() {
        purchasePage = purchasePage != null ? purchasePage : new PurchasePage(DriverFactory.get());
        purchasePage.completePurchase();
    }
}