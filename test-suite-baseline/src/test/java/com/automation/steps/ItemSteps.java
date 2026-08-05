package com.automation.steps;

import com.automation.pages.ItemPage;
import io.cucumber.java.en.When;

public class ItemSteps {

    private final ItemPage itemPage = new ItemPage();

    @When("the user clicks the remove button for {string}")
    public void theUserClicksTheRemoveButtonForItem(String itemName) {
        itemPage.clickRemoveButtonForItem(itemName);
    }
}