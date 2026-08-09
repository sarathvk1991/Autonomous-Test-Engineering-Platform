package com.automation.pages;

import com.automation.base.BasePage;
import org.openqa.selenium.By;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.support.ui.ExpectedConditions;

public class RemoveItemPage extends BasePage {

    private final By removeButton = By.xpath("//button[contains(@aria-label, 'Remove %s')]");

    public RemoveItemPage(WebDriver driver) {
        super(driver);
    }

    public void clickRemoveButton(String itemName) {
        wait.until(ExpectedConditions.elementToBeClickable(
            By.xpath(String.format("//button[contains(@aria-label, 'Remove %s')]", itemName))
        )).click();
    }
}