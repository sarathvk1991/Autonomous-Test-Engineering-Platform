package com.automation.pages;

import com.automation.base.BasePage;
import org.openqa.selenium.By;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.TimeoutException;
import org.openqa.selenium.support.ui.ExpectedConditions;

public class OrderPage extends BasePage {

    private final By successMessageLocator = By.id("order-success-message");

    public OrderPage(WebDriver driver) {
        super(driver);
    }

    public boolean isTransactionCompleted() {
        try {
            return wait.until(ExpectedConditions.visibilityOfElementLocated(successMessageLocator)).isDisplayed();
        } catch (TimeoutException e) {
            return false;
        }
    }
}