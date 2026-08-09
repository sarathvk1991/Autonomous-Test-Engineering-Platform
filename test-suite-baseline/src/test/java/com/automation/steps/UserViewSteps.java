package com.automation.steps;

import com.automation.base.DriverFactory;
import com.automation.pages.UserViewPage;
import io.cucumber.java.en.Then;
import org.junit.jupiter.api.Assertions;

public class UserViewSteps {

    private UserViewPage userViewPage;

    @Then("the user should see the {string}")
    public void theUserShouldSeeThe(String expectedText) {
        userViewPage = userViewPage != null ? userViewPage : new UserViewPage(DriverFactory.get());
        Assertions.assertTrue(userViewPage.isTextVisible(expectedText), "Expected text was not visible: " + expectedText);
    }
}