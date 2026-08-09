package com.automation.pages;

import com.automation.base.BasePage;
import org.openqa.selenium.By;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.support.ui.ExpectedConditions;

public class SortingPage extends BasePage {

    private final By sortDropdown = By.id("sort-dropdown");

    public SortingPage(WebDriver driver) {
        super(driver);
    }

    public void selectSortingOrder(String order) {
        wait.until(ExpectedConditions.elementToBeClickable(sortDropdown)).click();
        driver.findElement(By.xpath("//option[text()='" + order + "']")).click();
    }
}