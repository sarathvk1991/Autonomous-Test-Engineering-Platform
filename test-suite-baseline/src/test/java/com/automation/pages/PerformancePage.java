package com.automation.pages;

import com.automation.base.BasePage;
import org.openqa.selenium.By;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.support.ui.ExpectedConditions;

public class PerformancePage extends BasePage {

    private final By pageBody = By.tagName("body");

    public PerformancePage(WebDriver driver) {
        super(driver);
    }

    public boolean isLoadTimeWithinThreshold() {
        try {
            return wait.until(ExpectedConditions.visibilityOfElementLocated(pageBody)) != null;
        } catch (Exception e) {
            return false;
        }
    }
}