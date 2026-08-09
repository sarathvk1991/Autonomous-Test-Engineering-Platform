package com.automation.steps;

import com.automation.base.DriverFactory;
import com.automation.pages.CancelPage;
import io.cucumber.java.en.When;

public class CancelSteps {

    private CancelPage cancelPage;

    @When("the user clicks the cancel button")
    public void theUserClicksTheCancelButton() {
        cancelPage = cancelPage != null ? cancelPage : new CancelPage(DriverFactory.get());
        cancelPage.clickCancelButton();
    }
}