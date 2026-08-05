package com.automation.steps;

import io.cucumber.java.en.Then;
import org.junit.jupiter.api.Assertions;
import com.automation.pages.ResultPage;

public class ResultSteps {

    private final ResultPage resultPage = new ResultPage();

    @Then("the user should see the {string}")
    public void theUserShouldSeeTheExpectedResult(String expectedResult) {
        Assertions.assertTrue(resultPage.isResultDisplayed(expectedResult), 
            "The expected result '" + expectedResult + "' was not found on the page.");
    }
}