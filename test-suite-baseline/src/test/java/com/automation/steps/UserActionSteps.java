package com.automation.steps;

import io.cucumber.java.en.When;
import com.automation.base.DriverFactory;
import com.automation.pages.UserActionPage;

public class UserActionSteps {

    private UserActionPage userActionPage;

    @When("the user attempts to perform an action")
    public void theUserAttemptsToPerformAnAction() {
        userActionPage = userActionPage != null ? userActionPage : new UserActionPage(DriverFactory.get());
        userActionPage.performAction();
    }
}