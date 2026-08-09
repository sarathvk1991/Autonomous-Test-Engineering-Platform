package com.automation.pages;

import com.automation.base.BasePage;
import org.openqa.selenium.By;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.support.ui.ExpectedConditions;

public class LogoutPage extends BasePage {

    private final By logoutButton = By.id("logout-button");

    public LogoutPage(WebDriver driver) {
        super(driver);
    }

    public void performLogout() {
        wait.until(ExpectedConditions.elementToBeClickable(logoutButton)).click();
    }
}