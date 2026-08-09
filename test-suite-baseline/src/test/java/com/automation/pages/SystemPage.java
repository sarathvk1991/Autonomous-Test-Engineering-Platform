package com.automation.pages;

import com.automation.base.BasePage;
import org.openqa.selenium.By;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.support.ui.ExpectedConditions;

public class SystemPage extends BasePage {

    private final By systemInputLocator = By.id("system-input");

    public SystemPage(WebDriver driver) {
        super(driver);
    }

    public boolean isInputHandledAppropriately(String input) {
        try {
            wait.until(ExpectedConditions.visibilityOfElementLocated(systemInputLocator)).sendKeys(input);
            return wait.until(ExpectedConditions.attributeToBe(systemInputLocator, "value", input));
        } catch (Exception e) {
            return false;
        }
    }
}