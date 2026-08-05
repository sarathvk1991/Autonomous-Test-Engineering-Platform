package com.automation.steps;

import io.cucumber.java.en.Then;
import org.junit.jupiter.api.Assertions;
import com.automation.pages.InventoryPage;

public class InventorySteps {

    private final InventoryPage inventoryPage = new InventoryPage();

    @Then("the inventory items should be displayed in {string} order")
    public void theInventoryItemsShouldBeDisplayedInOrder(String expectedOrder) {
        Assertions.assertTrue(inventoryPage.isInventorySortedBy(expectedOrder), 
            "Inventory items are not displayed in the expected order: " + expectedOrder);
    }
}