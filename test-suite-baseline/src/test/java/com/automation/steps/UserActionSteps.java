package com.automation.steps;

import io.cucumber.java.en.When;
import com.automation.pages.UserActionPage;

public class UserActionSteps {

    private final UserActionPage userActionPage = new UserActionPage();

    @When("the user attempts to perform an action")
    public void theUserAttemptsToPerformAnAction() {
        userActionPage.performAction();
    }
}