package com.automation.pages;

import com.automation.base.BasePage;
import org.openqa.selenium.By;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.support.ui.ExpectedConditions;

public class ModularityPage extends BasePage {

    private final By modularityReportLocator = By.id("modularity-report-message");

    public ModularityPage(WebDriver driver) {
        super(driver);
    }

    public boolean isModularityReportMatching(String expectedMessage) {
        try {
            String actualText = wait.until(ExpectedConditions.visibilityOfElementLocated(modularityReportLocator)).getText();
            return actualText != null && actualText.contains(expectedMessage);
        } catch (Exception e) {
            return false;
        }
    }
}