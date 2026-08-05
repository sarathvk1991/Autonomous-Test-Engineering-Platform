package com.automation.steps;

import io.cucumber.java.en.Then;
import org.junit.jupiter.api.Assertions;
import com.automation.pages.PostalCodePage;

public class PostalCodeSteps {

    private final PostalCodePage postalCodePage = new PostalCodePage();

    @Then("the system should display {string} for the postal code")
    public void theSystemShouldDisplayValidationResultForThePostalCode(String validationResult) {
        Assertions.assertEquals(validationResult, postalCodePage.getPostalCodeValidationMessage(), 
            "The displayed postal code validation message does not match the expected result.");
    }
}