package com.automation.steps;

import io.cucumber.java.en.When;
import com.automation.pages.SortingPage;

public class SortingSteps {

    private final SortingPage sortingPage = new SortingPage();

    @When("the user selects the {string} sorting order")
    public void theUserSelectsTheSortingOrder(String sortOption) {
        sortingPage.selectSortingOrder(sortOption);
    }
}