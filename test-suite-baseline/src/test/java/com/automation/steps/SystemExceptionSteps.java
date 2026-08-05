package com.automation.steps;

import io.cucumber.java.en.Then;
import org.junit.jupiter.api.Assertions;
import com.automation.pages.SystemExceptionPage;

public class SystemExceptionSteps {

    private final SystemExceptionPage systemExceptionPage = new SystemExceptionPage();

    @Then("the system should handle the {string} appropriately")
    public void theSystemShouldHandleTheExpectedExceptionAppropriately(String expectedException) {
        Assertions.assertTrue(systemExceptionPage.isExceptionHandled(expectedException), 
            "The system failed to handle the expected exception: " + expectedException);
    }
}