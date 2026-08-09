package com.automation.pages;

import com.automation.base.BasePage;
import org.openqa.selenium.By;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.WebElement;
import org.openqa.selenium.support.ui.ExpectedConditions;
import java.util.List;
import java.util.regex.Pattern;

public class ReportPage extends BasePage {

    private final By itemNamesLocator = By.cssSelector(".report-item-name");

    public ReportPage(WebDriver driver) {
        super(driver);
    }

    public boolean verifyNamingPatternForItems(String pattern) {
        try {
            List<WebElement> items = wait.until(ExpectedConditions.presenceOfAllElementsLocatedBy(itemNamesLocator));
            Pattern regex = Pattern.compile(pattern);
            
            for (WebElement item : items) {
                if (!regex.matcher(item.getText()).matches()) {
                    return false;
                }
            }
            return !items.isEmpty();
        } catch (Exception e) {
            return false;
        }
    }
}