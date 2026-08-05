package com.automation.steps;

import io.cucumber.java.en.Then;
import org.junit.jupiter.api.Assertions;
import com.automation.pages.ReportPage;

public class ReportSteps {

    private final ReportPage reportPage = new ReportPage();

    @Then("the report should indicate that all {string} follow the required naming pattern")
    public void theReportShouldIndicateThatAllFollowTheRequiredNamingPattern(String elementType) {
        boolean isNamingPatternValid = reportPage.verifyNamingPatternForElements(elementType);
        Assertions.assertTrue(isNamingPatternValid, "The report indicates that some " + elementType + " do not follow the required naming pattern.");
    }
}