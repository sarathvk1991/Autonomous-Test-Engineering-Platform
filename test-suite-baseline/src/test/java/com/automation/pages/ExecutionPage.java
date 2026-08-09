package com.automation.pages;

import com.automation.base.BasePage;
import org.openqa.selenium.By;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.TimeoutException;
import org.openqa.selenium.support.ui.ExpectedConditions;

public class ExecutionPage extends BasePage {

    private final By executionStatusLocator = By.id("execution-status");

    public ExecutionPage(WebDriver driver) {
        super(driver);
    }

    public boolean isExecutionProceeding() {
        try {
            return wait.until(ExpectedConditions.visibilityOfElementLocated(executionStatusLocator)) != null;
        } catch (TimeoutException e) {
            return false;
        }
    }
}