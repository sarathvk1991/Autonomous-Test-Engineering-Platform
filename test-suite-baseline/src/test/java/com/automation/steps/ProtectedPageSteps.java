package com.automation.steps;

import io.cucumber.java.en.Then;
import org.junit.jupiter.api.Assertions;
import com.automation.pages.ProtectedPage;

public class ProtectedPageSteps {

    private final ProtectedPage protectedPage = new ProtectedPage();

    @Then("the user should not be able to access protected pages using the back button")
    public void theUserShouldNotBeAbleToAccessProtectedPagesUsingTheBackButton() {
        Assertions.assertFalse(protectedPage.isAccessibleAfterBackNavigation(), 
            "User was able to access protected page after clicking the back button.");
    }
}