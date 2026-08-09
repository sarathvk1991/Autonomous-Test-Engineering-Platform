package com.automation.pages;

import com.automation.base.BasePage;
import org.openqa.selenium.By;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.support.ui.ExpectedConditions;

public class ShoppingCartPage extends BasePage {

    private final By cartContainer = By.id("shopping-cart-container");

    public ShoppingCartPage(WebDriver driver) {
        super(driver);
    }

    public boolean isDisplayed() {
        try {
            return wait.until(ExpectedConditions.visibilityOfElementLocated(cartContainer)) != null;
        } catch (Exception e) {
            return false;
        }
    }
}