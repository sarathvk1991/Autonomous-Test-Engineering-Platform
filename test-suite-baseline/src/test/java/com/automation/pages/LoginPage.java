package com.automation.pages;

import com.automation.base.BasePage;
import org.openqa.selenium.By;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.support.ui.ExpectedConditions;

public class LoginPage extends BasePage {

    private final By usernameField = By.id("username");
    private final By passwordField = By.id("password");
    private final By loginButton = By.id("login-button");
    private final By errorMessage = By.id("error-message");

    public LoginPage(WebDriver driver) {
        super(driver);
    }

    public void attemptLogin(String credentials) {
        wait.until(ExpectedConditions.visibilityOfElementLocated(usernameField)).sendKeys(credentials);
        driver.findElement(passwordField).sendKeys(credentials);
        driver.findElement(loginButton).click();
    }

    public boolean isErrorMessageDisplayed() {
        try {
            return wait.until(ExpectedConditions.visibilityOfElementLocated(errorMessage)).isDisplayed();
        } catch (Exception e) {
            return false;
        }
    }
}