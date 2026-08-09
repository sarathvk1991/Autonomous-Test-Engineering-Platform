package com.automation.steps;

import com.automation.base.DriverFactory;
import com.automation.pages.ExecutionPage;
import io.cucumber.java.en.Then;
import org.junit.jupiter.api.Assertions;

public class ExecutionSteps {

    private ExecutionPage executionPage;

    @Then("the execution should proceed immediately once the condition is met")
    public void theExecutionShouldProceedImmediatelyOnceTheConditionIsMet() {
        executionPage = executionPage != null ? executionPage : new ExecutionPage(DriverFactory.get());
        Assertions.assertTrue(executionPage.isExecutionProceeding(), "The execution did not proceed as expected.");
    }
}