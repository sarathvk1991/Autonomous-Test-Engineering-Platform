package com.automation.steps;

import com.automation.base.DriverFactory;
import com.automation.pages.SortingPage;
import io.cucumber.java.en.When;

public class SortingSteps {

    private SortingPage sortingPage;

    @When("the user selects the {string} sorting order")
    public void theUserSelectsTheSortingOrder(String order) {
        sortingPage = sortingPage != null ? sortingPage : new SortingPage(DriverFactory.get());
        sortingPage.selectSortingOrder(order);
    }
}