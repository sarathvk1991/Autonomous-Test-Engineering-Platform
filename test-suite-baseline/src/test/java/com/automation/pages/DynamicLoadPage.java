package com.automation.pages;

import com.automation.base.BasePage;
import org.openqa.selenium.By;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.support.ui.ExpectedConditions;

public class DynamicLoadPage extends BasePage {

    private final By startButton = By.cssSelector("#start button");

    public DynamicLoadPage(WebDriver driver) {
        super(driver);
    }

    public void triggerDynamicElementLoad() {
        wait.until(ExpectedConditions.elementToBeClickable(startButton)).click();
    }
}