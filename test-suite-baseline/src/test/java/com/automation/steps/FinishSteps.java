package com.automation.steps;

import com.automation.base.DriverFactory;
import com.automation.pages.FinishPage;
import io.cucumber.java.en.When;

public class FinishSteps {

    private FinishPage finishPage;

    @When("the user clicks the finish button")
    public void theUserClicksTheFinishButton() {
        finishPage = finishPage != null ? finishPage : new FinishPage(DriverFactory.get());
        finishPage.clickFinishButton();
    }
}