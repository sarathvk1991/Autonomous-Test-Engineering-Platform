package com.automation.steps;

import com.automation.base.DriverFactory;
import com.automation.pages.ReportPage;
import io.cucumber.java.en.Then;
import org.junit.jupiter.api.Assertions;

public class ReportSteps {

    private ReportPage reportPage;

    @Then("the report should indicate that all {string} follow the required naming pattern")
    public void theReportShouldIndicateThatAllFollowTheRequiredNamingPattern(String itemType) {
        reportPage = reportPage != null ? reportPage : new ReportPage(DriverFactory.get());
        Assertions.assertTrue(reportPage.verifyNamingPatternForItems(itemType), 
            "The report did not indicate that all " + itemType + " follow the required naming pattern.");
    }
}