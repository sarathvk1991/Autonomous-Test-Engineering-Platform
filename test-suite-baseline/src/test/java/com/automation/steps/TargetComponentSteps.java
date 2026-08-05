package com.automation.steps;

import io.cucumber.java.en.Then;
import com.automation.pages.TargetComponentPage;

public class TargetComponentSteps {

    private final TargetComponentPage targetComponentPage = new TargetComponentPage();

    @Then("the system should wait for the {string} of the target component")
    public void theSystemShouldWaitForTheElementStateOfTheTargetComponent(String elementState) {
        targetComponentPage.waitForComponentState(elementState);
    }
}