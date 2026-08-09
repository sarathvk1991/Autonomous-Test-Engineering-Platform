package com.automation.pages;

import com.automation.base.BasePage;
import org.openqa.selenium.By;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.support.ui.ExpectedConditions;

public class TargetComponentPage extends BasePage {

    private final By targetComponent = By.id("target-component");

    public TargetComponentPage(WebDriver driver) {
        super(driver);
    }

    public boolean waitForState(String state) {
        try {
            return wait.until(ExpectedConditions.attributeContains(targetComponent, "data-state", state)) != null;
        } catch (Exception e) {
            return false;
        }
    }
}