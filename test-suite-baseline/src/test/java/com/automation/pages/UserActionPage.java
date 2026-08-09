package com.automation.pages;

import com.automation.base.BasePage;
import org.openqa.selenium.By;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.support.ui.ExpectedConditions;

public class UserActionPage extends BasePage {

    private final By actionButton = By.id("action-button");

    public UserActionPage(WebDriver driver) {
        super(driver);
    }

    public void performAction() {
        wait.until(ExpectedConditions.elementToBeClickable(actionButton)).click();
    }
}