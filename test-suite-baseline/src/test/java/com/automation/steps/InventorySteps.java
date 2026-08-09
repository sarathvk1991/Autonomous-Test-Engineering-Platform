package com.automation.steps;

import com.automation.base.DriverFactory;
import com.automation.pages.InventoryPage;
import io.cucumber.java.en.Then;
import org.junit.jupiter.api.Assertions;

public class InventorySteps {

    private InventoryPage inventoryPage;

    @Then("the inventory items should be displayed in {string} order")
    public void theInventoryItemsShouldBeDisplayedInOrder(String order) {
        inventoryPage = inventoryPage != null ? inventoryPage : new InventoryPage(DriverFactory.get());
        Assertions.assertTrue(inventoryPage.isInventorySortedBy(order), 
            "Inventory items were not displayed in the expected " + order + " order.");
    }
}