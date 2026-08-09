package com.automation.pages;

import com.automation.base.BasePage;
import org.openqa.selenium.By;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.support.ui.ExpectedConditions;

public class PurchasePage extends BasePage {

    private final By checkoutButton = By.id("checkout-button");
    private final By confirmPurchaseButton = By.id("confirm-purchase");

    public PurchasePage(WebDriver driver) {
        super(driver);
    }

    public void completePurchase() {
        wait.until(ExpectedConditions.elementToBeClickable(checkoutButton)).click();
        wait.until(ExpectedConditions.elementToBeClickable(confirmPurchaseButton)).click();
    }
}