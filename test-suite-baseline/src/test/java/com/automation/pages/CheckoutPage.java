package com.automation.pages;

import com.automation.base.BasePage;
import org.openqa.selenium.By;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.support.ui.ExpectedConditions;

public class CheckoutPage extends BasePage {

    private final By submitButton = By.id("checkout-submit");

    public CheckoutPage(WebDriver driver) {
        super(driver);
    }

    public void submitForm() {
        wait.until(ExpectedConditions.elementToBeClickable(submitButton)).click();
    }
}