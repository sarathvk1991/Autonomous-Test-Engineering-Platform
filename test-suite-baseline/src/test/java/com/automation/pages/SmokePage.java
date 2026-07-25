package com.automation.pages;

import com.automation.base.BasePage;
import com.automation.base.ConfigReader;
import org.openqa.selenium.WebDriver;

/** The skeleton's own self-test page object -- proves the driver/config/page-object wiring. */
public class SmokePage extends BasePage {

    public SmokePage(WebDriver driver) {
        super(driver);
    }

    public void openApplicationUnderTest() {
        open(ConfigReader.env("base.url"));
    }
}
