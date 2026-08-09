package com.automation.steps;

import com.automation.base.DriverFactory;
import com.automation.pages.PerformancePage;
import io.cucumber.java.en.Then;
import org.junit.jupiter.api.Assertions;

public class PerformanceSteps {

    private PerformancePage performancePage;

    @Then("the page should load within the defined performance threshold")
    public void thePageShouldLoadWithinTheDefinedPerformanceThreshold() {
        performancePage = performancePage != null ? performancePage : new PerformancePage(DriverFactory.get());
        Assertions.assertTrue(performancePage.isLoadTimeWithinThreshold(), "Page load time exceeded the defined performance threshold.");
    }
}