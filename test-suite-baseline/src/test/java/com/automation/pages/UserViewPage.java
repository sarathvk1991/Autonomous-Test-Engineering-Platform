package com.automation.pages;

import com.automation.base.BasePage;
import org.openqa.selenium.By;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.support.ui.ExpectedConditions;

public class UserViewPage extends BasePage {

    private final By bodyLocator = By.tagName("body");

    public UserViewPage(WebDriver driver) {
        super(driver);
    }

    public boolean isTextVisible(String text) {
        try {
            return wait.until(ExpectedConditions.textToBePresentInElementLocated(bodyLocator, text));
        } catch (Exception e) {
            return false;
        }
    }
}