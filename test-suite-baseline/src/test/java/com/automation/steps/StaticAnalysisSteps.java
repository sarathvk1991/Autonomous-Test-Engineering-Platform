package com.automation.steps;

import com.automation.base.DriverFactory;
import com.automation.pages.StaticAnalysisPage;
import io.cucumber.java.en.Given;

public class StaticAnalysisSteps {

    private StaticAnalysisPage staticAnalysisPage;

    @Given("the static analysis tool is configured for naming conventions")
    public void theStaticAnalysisToolIsConfiguredForNamingConventions() {
        staticAnalysisPage = staticAnalysisPage != null ? staticAnalysisPage : new StaticAnalysisPage(DriverFactory.get());
        staticAnalysisPage.configureNamingConventions();
    }
}