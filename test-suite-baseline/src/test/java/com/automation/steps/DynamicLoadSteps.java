package com.automation.steps;

import com.automation.base.DriverFactory;
import com.automation.pages.DynamicLoadPage;
import io.cucumber.java.en.When;

public class DynamicLoadSteps {

    private DynamicLoadPage dynamicLoadPage;

    @When("I perform an action that triggers a dynamic element load")
    public void iPerformAnActionThatTriggersADynamicElementLoad() {
        dynamicLoadPage = dynamicLoadPage != null ? dynamicLoadPage : new DynamicLoadPage(DriverFactory.get());
        dynamicLoadPage.triggerDynamicElementLoad();
    }
}