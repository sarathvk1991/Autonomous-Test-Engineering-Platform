package com.automation.steps;

import io.cucumber.java.en.Given;
import com.automation.pages.CodebasePage;

public class CodebaseSteps {

    private final CodebasePage codebasePage = new CodebasePage();

    @Given("the codebase contains a method with {string} lines")
    public void theCodebaseContainsAMethodWithLines(String lineCount) {
        codebasePage.verifyMethodLineCount(lineCount);
    }
}