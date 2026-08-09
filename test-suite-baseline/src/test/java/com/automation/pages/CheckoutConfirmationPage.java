package com.automation.pages;

import com.automation.base.BasePage;
import org.openqa.selenium.By;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.support.ui.ExpectedConditions;

public class CheckoutConfirmationPage extends BasePage {

    private final By confirmationHeader = By.id("checkout-confirmation-header");

    public CheckoutConfirmationPage(WebDriver driver) {
        super(driver);
    }

    public boolean isDisplayed() {
        try {
            return wait.until(ExpectedConditions.visibilityOfElementLocated(confirmationHeader)) != null;
        } catch (Exception e) {
            return false;
        }
    }
}