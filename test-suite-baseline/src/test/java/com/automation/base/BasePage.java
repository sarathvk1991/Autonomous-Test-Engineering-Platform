package com.automation.base;

import java.time.Duration;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.support.ui.WebDriverWait;

/**
 * Base page object. RECEIVES a driver (constructor injection); it must never construct one and
 * must never hold one in a static field (ADR-0041 D5) -- a page object that owns its own driver
 * cannot be parallel-safe once {@code cucumber.execution.parallel.enabled} is set.
 */
public abstract class BasePage {

    protected final WebDriver driver;
    protected final WebDriverWait wait;

    protected BasePage(WebDriver driver) {
        this.driver = driver;
        long explicitWaitSeconds = Long.parseLong(ConfigReader.env("explicit.wait"));
        this.wait = new WebDriverWait(driver, Duration.ofSeconds(explicitWaitSeconds));
    }

    public void open(String url) {
        driver.get(url);
    }

    public String currentTitle() {
        return driver.getTitle();
    }
}
