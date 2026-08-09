package com.automation.pages;

import com.automation.base.BasePage;
import org.openqa.selenium.By;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.support.ui.ExpectedConditions;

public class FinishPage extends BasePage {

    private final By finishButton = By.id("finish");

    public FinishPage(WebDriver driver) {
        super(driver);
    }

    public void clickFinishButton() {
        wait.until(ExpectedConditions.elementToBeClickable(finishButton)).click();
    }
}