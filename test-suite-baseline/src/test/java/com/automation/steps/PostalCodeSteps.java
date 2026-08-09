package com.automation.steps;

import com.automation.base.DriverFactory;
import com.automation.pages.PostalCodePage;
import io.cucumber.java.en.Then;
import org.junit.jupiter.api.Assertions;

public class PostalCodeSteps {

    private PostalCodePage postalCodePage;

    @Then("the system should display {string} for the postal code")
    public void theSystemShouldDisplayForThePostalCode(String expectedPostalCode) {
        postalCodePage = postalCodePage != null ? postalCodePage : new PostalCodePage(DriverFactory.get());
        Assertions.assertEquals(expectedPostalCode, postalCodePage.getDisplayedPostalCode(), "The displayed postal code does not match the expected value.");
    }
}