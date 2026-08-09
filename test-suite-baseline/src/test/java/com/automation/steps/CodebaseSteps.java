package com.automation.steps;

import com.automation.base.DriverFactory;
import com.automation.pages.CodebasePage;
import io.cucumber.java.en.Given;

public class CodebaseSteps {

    private CodebasePage codebasePage;

    @Given("the codebase contains a method with {string} lines")
    public void theCodebaseContainsAMethodWithLines(String lineCount) {
        codebasePage = codebasePage != null ? codebasePage : new CodebasePage(DriverFactory.get());
        codebasePage.verifyMethodLineCount(lineCount);
    }
}