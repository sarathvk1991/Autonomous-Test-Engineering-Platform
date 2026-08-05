package com.automation.steps;

import com.automation.pages.FinishPage;
import io.cucumber.java.en.When;

public class FinishSteps {

    private final FinishPage finishPage = new FinishPage();

    @When("the user clicks the finish button")
    public void theUserClicksTheFinishButton() {
        finishPage.clickFinishButton();
    }
}