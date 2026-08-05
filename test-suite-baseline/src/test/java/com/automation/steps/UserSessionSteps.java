package com.automation.steps;

import io.cucumber.java.en.Then;
import org.junit.jupiter.api.Assertions;
import com.automation.pages.UserSessionPage;

public class UserSessionSteps {

    private final UserSessionPage userSessionPage = new UserSessionPage();

    @Then("the user session should be terminated")
    public void theUserSessionShouldBeTerminated() {
        Assertions.assertTrue(userSessionPage.isSessionTerminated(), "User session was not terminated as expected.");
    }
}