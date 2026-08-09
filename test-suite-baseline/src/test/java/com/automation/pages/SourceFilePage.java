package com.automation.pages;

import com.automation.base.BasePage;
import org.openqa.selenium.By;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.WebElement;
import org.openqa.selenium.support.ui.ExpectedConditions;

public class SourceFilePage extends BasePage {

    private final By sourceFileInput = By.id("source-file-input");
    private final By scanButton = By.id("scan-button");

    public SourceFilePage(WebDriver driver) {
        super(driver);
    }

    public void scanFileForNamingViolations(String fileName) {
        WebElement input = wait.until(ExpectedConditions.visibilityOfElementLocated(sourceFileInput));
        input.clear();
        input.sendKeys(fileName);
        wait.until(ExpectedConditions.elementToBeClickable(scanButton)).click();
    }
}