package com.automation.pages;

import com.automation.base.BasePage;
import org.openqa.selenium.By;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.support.ui.ExpectedConditions;

public class PostalCodePage extends BasePage {

    private final By postalCodeField = By.id("postal-code");

    public PostalCodePage(WebDriver driver) {
        super(driver);
    }

    public String getDisplayedPostalCode() {
        return wait.until(ExpectedConditions.visibilityOfElementLocated(postalCodeField)).getText();
    }
}