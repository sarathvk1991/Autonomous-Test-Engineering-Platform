package com.automation.pages;

import com.automation.base.BasePage;
import org.openqa.selenium.By;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.support.ui.ExpectedConditions;

public class ProtectedPage extends BasePage {

    private final By protectedContentLocator = By.id("protected-content");

    public ProtectedPage(WebDriver driver) {
        super(driver);
    }

    public boolean isAccessAllowedAfterBackNavigation() {
        driver.navigate().back();
        try {
            return wait.until(ExpectedConditions.visibilityOfElementLocated(protectedContentLocator)) != null;
        } catch (Exception e) {
            return false;
        }
    }
}