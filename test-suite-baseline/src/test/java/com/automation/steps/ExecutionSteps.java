package com.automation.steps;

import io.cucumber.java.en.Then;
import org.junit.jupiter.api.Assertions;
import com.automation.pages.ExecutionStatusPage;

public class ExecutionSteps {

    private final ExecutionStatusPage executionStatusPage = new ExecutionStatusPage();

    @Then("the execution should proceed immediately once the condition is met")
    public void theExecutionShouldProceedImmediatelyOnceTheConditionIsMet() {
        Assertions.assertTrue(executionStatusPage.isExecutionProceeding(), "Execution did not proceed as expected.");
    }
}