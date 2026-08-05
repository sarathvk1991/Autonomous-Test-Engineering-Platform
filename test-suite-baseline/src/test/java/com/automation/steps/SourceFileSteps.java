package com.automation.steps;

import io.cucumber.java.en.When;
import com.automation.pages.SourceFileScannerPage;

public class SourceFileSteps {

    private final SourceFileScannerPage sourceFileScannerPage = new SourceFileScannerPage();

    @When("I scan the source file {string} for naming violations")
    public void iScanTheSourceFileForNamingViolations(String filePath) {
        sourceFileScannerPage.scanFileForNamingViolations(filePath);
    }
}