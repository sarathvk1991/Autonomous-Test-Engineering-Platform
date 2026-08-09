package com.automation.pages;

import com.automation.base.BasePage;
import org.openqa.selenium.By;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.WebElement;
import org.openqa.selenium.support.ui.ExpectedConditions;
import java.util.List;
import java.util.stream.Collectors;
import java.util.ArrayList;
import java.util.Collections;

public class InventoryPage extends BasePage {

    private final By inventoryItemNames = By.className("inventory_item_name");

    public InventoryPage(WebDriver driver) {
        super(driver);
    }

    public boolean isInventorySortedBy(String order) {
        List<WebElement> items = wait.until(ExpectedConditions.presenceOfAllElementsLocatedBy(inventoryItemNames));
        List<String> names = items.stream()
                .map(WebElement::getText)
                .collect(Collectors.toList());

        List<String> sortedNames = new ArrayList<>(names);
        if ("asc".equalsIgnoreCase(order)) {
            Collections.sort(sortedNames);
        } else if ("desc".equalsIgnoreCase(order)) {
            sortedNames.sort(Collections.reverseOrder());
        }

        return names.equals(sortedNames);
    }
}