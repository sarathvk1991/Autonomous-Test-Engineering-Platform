package com.automation.pages;

import com.automation.base.BasePage;
import org.openqa.selenium.By;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.support.ui.ExpectedConditions;

public class UserSessionPage extends BasePage {

    private final By sessionIndicator = By.id("user-session-status");

    public UserSessionPage(WebDriver driver) {
        super(driver);
    }

    public boolean isSessionTerminated() {
        try {
            return wait.until(ExpectedConditions.invisibilityOfElementLocated(sessionIndicator));
        } catch (Exception e) {
            return false;
        }
    }
}