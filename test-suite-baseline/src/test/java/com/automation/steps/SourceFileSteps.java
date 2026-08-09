package com.automation.steps;

import com.automation.base.DriverFactory;
import com.automation.pages.SourceFilePage;
import io.cucumber.java.en.When;

public class SourceFileSteps {

    private SourceFilePage sourceFilePage;

    @When("I scan the source file {string} for naming violations")
    public void iScanTheSourceFileForNamingViolations(String fileName) {
        sourceFilePage = sourceFilePage != null ? sourceFilePage : new SourceFilePage(DriverFactory.get());
        sourceFilePage.scanFileForNamingViolations(fileName);
    }
}