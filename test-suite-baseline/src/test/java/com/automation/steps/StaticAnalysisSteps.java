package com.automation.steps;

import com.automation.pages.StaticAnalysisPage;
import io.cucumber.java.en.Given;

public class StaticAnalysisSteps {

    private final StaticAnalysisPage staticAnalysisPage = new StaticAnalysisPage();

    @Given("the static analysis tool is configured for naming conventions")
    public void theStaticAnalysisToolIsConfiguredForNamingConventions() {
        staticAnalysisPage.configureNamingConventions();
    }
}