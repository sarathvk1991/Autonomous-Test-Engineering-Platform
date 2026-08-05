package com.automation.steps;

import io.cucumber.java.en.When;
import com.automation.pages.CancelButtonPage;

public class CancelButtonSteps {

    private final CancelButtonPage cancelButtonPage = new CancelButtonPage();

    @When("the user clicks the cancel button")
    public void theUserClicksTheCancelButton() {
        cancelButtonPage.clickCancel();
    }
}