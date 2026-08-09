package com.automation.steps;

import com.automation.base.DriverFactory;
import com.automation.pages.SystemPage;
import io.cucumber.java.en.Then;
import org.junit.jupiter.api.Assertions;

public class SystemSteps {

    private SystemPage systemPage;

    @Then("the system should handle the {string} appropriately")
    public void theSystemShouldHandleTheAppropriately(String input) {
        systemPage = systemPage != null ? systemPage : new SystemPage(DriverFactory.get());
        Assertions.assertTrue(systemPage.isInputHandledAppropriately(input), 
            "The system failed to handle the input: " + input);
    }
}