package com.automation.pages;

import com.automation.base.BasePage;
import org.openqa.selenium.By;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.support.ui.ExpectedConditions;

public class AuthenticationPage extends BasePage {

    private final By usernameField = By.id("username");
    private final By passwordField = By.id("password");
    private final By loginButton = By.id("login-button");

    public AuthenticationPage(WebDriver driver) {
        super(driver);
    }

    public void performValidAuthentication() {
        wait.until(ExpectedConditions.visibilityOfElementLocated(usernameField)).sendKeys("validUser");
        driver.findElement(passwordField).sendKeys("validPassword");
        driver.findElement(loginButton).click();
    }
}