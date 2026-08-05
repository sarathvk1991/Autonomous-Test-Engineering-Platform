package com.automation.steps;

import io.cucumber.java.en.When;
import com.automation.pages.DynamicElementPage;

public class DynamicElementSteps {

    private final DynamicElementPage dynamicElementPage = new DynamicElementPage();

    @When("I perform an action that triggers a dynamic element load")
    public void iPerformAnActionThatTriggersADynamicElementLoad() {
        dynamicElementPage.triggerDynamicLoad();
    }
}