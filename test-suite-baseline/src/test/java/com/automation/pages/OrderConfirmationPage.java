package com.automation.pages;

import com.automation.base.BasePage;
import org.openqa.selenium.WebDriver;

public class OrderConfirmationPage extends BasePage {

    public OrderConfirmationPage(WebDriver driver) {
        super(driver);
    }

    public void navigateToOrderConfirmation() {
        open("/order-confirmation");
    }
}