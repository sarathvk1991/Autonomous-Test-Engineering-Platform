package com.automation.pages;

import com.automation.base.BasePage;
import org.openqa.selenium.By;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.TimeoutException;
import org.openqa.selenium.support.ui.ExpectedConditions;

public class ConfirmationPage extends BasePage {

    private final By confirmationMessage = By.id("confirmation-message");

    public ConfirmationPage(WebDriver driver) {
        super(driver);
    }

    public boolean isConfirmationMessageDisplayed() {
        try {
            return wait.until(ExpectedConditions.visibilityOfElementLocated(confirmationMessage)) != null;
        } catch (TimeoutException e) {
            return false;
        }
    }
}