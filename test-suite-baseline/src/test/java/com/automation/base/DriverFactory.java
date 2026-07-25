package com.automation.base;

import java.time.Duration;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.chrome.ChromeDriver;
import org.openqa.selenium.chrome.ChromeOptions;
import org.openqa.selenium.edge.EdgeDriver;
import org.openqa.selenium.edge.EdgeOptions;
import org.openqa.selenium.firefox.FirefoxDriver;
import org.openqa.selenium.firefox.FirefoxOptions;

/**
 * Owns the WebDriver lifecycle in a {@link ThreadLocal} (ADR-0041 D5) -- the moment
 * {@code cucumber.execution.parallel.enabled} is set, a static or per-instance driver produces
 * failures indistinguishable from flakiness. Driver binaries are resolved by Selenium Manager
 * (bundled since Selenium 4.6); no WebDriverManager dependency exists in this module.
 */
public final class DriverFactory {

    private static final ThreadLocal<WebDriver> DRIVER = new ThreadLocal<>();

    private DriverFactory() {
    }

    public static WebDriver create() {
        String browser = ConfigReader.env("browser");
        boolean headless = Boolean.parseBoolean(ConfigReader.env("headless"));

        WebDriver driver =
                switch (browser) {
                    case "firefox" -> {
                        FirefoxOptions options = new FirefoxOptions();
                        if (headless) {
                            options.addArguments("-headless");
                        }
                        yield new FirefoxDriver(options);
                    }
                    case "edge" -> {
                        EdgeOptions options = new EdgeOptions();
                        if (headless) {
                            options.addArguments("--headless=new");
                        }
                        yield new EdgeDriver(options);
                    }
                    case "chrome" -> {
                        ChromeOptions options = new ChromeOptions();
                        if (headless) {
                            options.addArguments("--headless=new");
                        }
                        yield new ChromeDriver(options);
                    }
                    default -> throw new IllegalStateException("Unsupported env.browser: " + browser);
                };

        long implicitWaitSeconds = Long.parseLong(ConfigReader.env("implicit.wait"));
        driver.manage().timeouts().implicitlyWait(Duration.ofSeconds(implicitWaitSeconds));

        DRIVER.set(driver);
        return driver;
    }

    public static WebDriver get() {
        WebDriver driver = DRIVER.get();
        if (driver == null) {
            throw new IllegalStateException("No WebDriver for this thread -- was DriverFactory.create() called?");
        }
        return driver;
    }

    public static void quit() {
        WebDriver driver = DRIVER.get();
        if (driver != null) {
            driver.quit();
            DRIVER.remove();
        }
    }
}
