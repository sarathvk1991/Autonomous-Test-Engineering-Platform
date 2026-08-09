package com.automation.steps;

import com.automation.base.DriverFactory;
import com.automation.pages.RemoveItemPage;
import io.cucumber.java.en.When;

public class RemoveItemSteps {

    private RemoveItemPage removeItemPage;

    @When("the user clicks the remove button for {string}")
    public void theUserClicksTheRemoveButtonFor(String itemName) {
        removeItemPage = removeItemPage != null ? removeItemPage : new RemoveItemPage(DriverFactory.get());
        removeItemPage.clickRemoveButton(itemName);
    }
}