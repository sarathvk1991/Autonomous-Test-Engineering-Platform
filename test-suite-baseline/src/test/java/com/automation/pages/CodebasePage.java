package com.automation.pages;

import com.automation.base.BasePage;
import org.openqa.selenium.By;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.support.ui.ExpectedConditions;

public class CodebasePage extends BasePage {

    private final By methodLineCountLocator = By.xpath("//div[contains(@class, 'method-line-count')]");

    public CodebasePage(WebDriver driver) {
        super(driver);
    }

    public void verifyMethodLineCount(String lineCount) {
        wait.until(ExpectedConditions.textToBePresentInElementLocated(methodLineCountLocator, lineCount));
    }
}