package com.automation.steps;

import io.cucumber.java.en.Then;
import org.junit.jupiter.api.Assertions;
import com.automation.base.DriverFactory;
import com.automation.pages.TargetComponentPage;

public class TargetComponentSteps {

    private TargetComponentPage targetComponentPage;

    @Then("the system should wait for the {string} of the target component")
    public void theSystemShouldWaitForTheOfTheTargetComponent(String state) {
        targetComponentPage = targetComponentPage != null ? targetComponentPage : new TargetComponentPage(DriverFactory.get());
        boolean isStateReached = targetComponentPage.waitForState(state);
        Assertions.assertTrue(isStateReached, "The target component did not reach the expected state: " + state);
    }
}