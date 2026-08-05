package com.automation.steps;

import io.cucumber.java.en.Then;
import org.junit.jupiter.api.Assertions;
import com.automation.pages.ModularityRequirementPage;

public class ModularityRequirementSteps {

    private final ModularityRequirementPage modularityRequirementPage = new ModularityRequirementPage();

    @Then("the system should report {string} regarding the modularity requirement")
    public void theSystemShouldReportRegardingTheModularityRequirement(String complianceStatus) {
        String actualStatus = modularityRequirementPage.getModularityComplianceStatus();
        Assertions.assertEquals(complianceStatus, actualStatus, "The modularity compliance status does not match the expected value.");
    }
}