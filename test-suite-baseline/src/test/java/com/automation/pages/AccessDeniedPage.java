package com.automation.pages;

import com.automation.base.BasePage;
import org.openqa.selenium.By;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.support.ui.ExpectedConditions;

public class AccessDeniedPage extends BasePage {

    private final By accessDeniedMessage = By.id("access-denied-message");

    public AccessDeniedPage(WebDriver driver) {
        super(driver);
    }

    public boolean isAccessDeniedMessageDisplayed() {
        try {
            return wait.until(ExpectedConditions.visibilityOfElementLocated(accessDeniedMessage)).isDisplayed();
        } catch (Exception e) {
            return false;
        }
    }
}