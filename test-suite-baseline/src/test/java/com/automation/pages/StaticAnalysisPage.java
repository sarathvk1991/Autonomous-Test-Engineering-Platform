package com.automation.pages;

import com.automation.base.BasePage;
import org.openqa.selenium.By;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.support.ui.ExpectedConditions;

public class StaticAnalysisPage extends BasePage {

    private final By namingConventionsCheckbox = By.id("naming-conventions-config");
    private final By saveButton = By.id("save-analysis-config");

    public StaticAnalysisPage(WebDriver driver) {
        super(driver);
    }

    public void configureNamingConventions() {
        wait.until(ExpectedConditions.elementToBeClickable(namingConventionsCheckbox)).click();
        wait.until(ExpectedConditions.elementToBeClickable(saveButton)).click();
    }
}