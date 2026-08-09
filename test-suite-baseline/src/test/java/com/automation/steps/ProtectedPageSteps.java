package com.automation.steps;

import com.automation.base.DriverFactory;
import com.automation.pages.ProtectedPage;
import io.cucumber.java.en.Then;
import org.junit.jupiter.api.Assertions;

public class ProtectedPageSteps {

    private ProtectedPage protectedPage;

    @Then("the user should not be able to access protected pages using the back button")
    public void theUserShouldNotBeAbleToAccessProtectedPagesUsingTheBackButton() {
        protectedPage = protectedPage != null ? protectedPage : new ProtectedPage(DriverFactory.get());
        Assertions.assertFalse(protectedPage.isAccessAllowedAfterBackNavigation(), "User was able to access protected page via back button");
    }
}