package com.automation.steps;

import com.automation.base.DriverFactory;
import com.automation.pages.ModularityPage;
import io.cucumber.java.en.Then;
import org.junit.jupiter.api.Assertions;

public class ModularitySteps {

    private ModularityPage modularityPage;

    @Then("the system should report {string} regarding the modularity requirement")
    public void theSystemShouldReportRegardingTheModularityRequirement(String expectedReport) {
        modularityPage = modularityPage != null ? modularityPage : new ModularityPage(DriverFactory.get());
        Assertions.assertTrue(modularityPage.isModularityReportMatching(expectedReport), 
            "The system report did not match the expected modularity requirement: " + expectedReport);
    }
}