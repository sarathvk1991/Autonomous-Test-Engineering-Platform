package com.automation.steps;

import com.automation.base.DriverFactory;
import com.automation.pages.SmokePage;
import io.cucumber.java.en.Given;
import io.cucumber.java.en.Then;
import org.junit.jupiter.api.Assertions;

/** Step definitions for the baseline's own smoke self-test. JUnit Jupiter assertions only. */
public class SmokeSteps {

    private SmokePage smokePage;

    @Given("I open the application under test")
    public void iOpenTheApplicationUnderTest() {
        smokePage = new SmokePage(DriverFactory.get());
        smokePage.openApplicationUnderTest();
    }

    @Then("the page title is not empty")
    public void thePageTitleIsNotEmpty() {
        Assertions.assertFalse(
                smokePage.currentTitle().isEmpty(), "Expected a non-empty page title after navigation");
    }
}
