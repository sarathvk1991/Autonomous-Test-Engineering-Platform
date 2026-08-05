package com.automation.steps;

import com.automation.pages.UserPage;
import io.cucumber.java.en.When;

public class UserSteps {

    private final UserPage userPage = new UserPage();

    @When("the user performs the logout action")
    public void theUserPerformsTheLogoutAction() {
        userPage.performLogout();
    }
}