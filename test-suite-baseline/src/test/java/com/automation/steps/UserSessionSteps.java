package com.automation.steps;

import com.automation.base.DriverFactory;
import com.automation.pages.UserSessionPage;
import io.cucumber.java.en.Then;
import org.junit.jupiter.api.Assertions;

public class UserSessionSteps {

    private UserSessionPage userSessionPage;

    @Then("the user session should be terminated")
    public void theUserSessionShouldBeTerminated() {
        userSessionPage = userSessionPage != null ? userSessionPage : new UserSessionPage(DriverFactory.get());
        Assertions.assertTrue(userSessionPage.isSessionTerminated(), "The user session was not terminated as expected.");
    }
}