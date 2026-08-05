package com.automation.steps;

import io.cucumber.java.en.Then;
import org.junit.jupiter.api.Assertions;
import com.automation.pages.PerformancePage;

public class PerformanceSteps {

    private final PerformancePage performancePage = new PerformancePage();

    @Then("the page should load within the defined performance threshold")
    public void thePageShouldLoadWithinTheDefinedPerformanceThreshold() {
        Assertions.assertTrue(performancePage.isWithinPerformanceThreshold(), 
            "Page load time exceeded the defined performance threshold.");
    }
}