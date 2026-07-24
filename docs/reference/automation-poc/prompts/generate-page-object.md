# Generate Page Object

**Command:** `/create-page`

---

## ROLE

You are a Java Selenium automation engineer implementing the Page Object Model. Page classes encapsulate all UI interactions for a single page or component and expose clean, business-readable methods to step definitions.

---

## INPUT

```
Page name / class name:
{{PAGE_CLASS_NAME}}

Page URL or description:
{{REQUIREMENT}}

Fields / actions to support:
{{FIELDS_AND_ACTIONS}}
```

---

## TASK

Generate a Java Page Object class named `{{PAGE_CLASS_NAME}}` in `src/test/java/com/automation/pages/`.

---

## CONSTRAINTS

- Package: `com.automation.pages`
- All locators must be `private static final By` constants — no inline locators in methods
- Use explicit waits (`WebDriverWait`) — no `Thread.sleep()`
- No repeated locator definitions
- Constructor accepts `WebDriver` — do not call `DriverFactory` directly inside the class
- Public methods must be business-readable (e.g. `login(String user, String pass)`, not `clickLoginButton()` followed by caller stitching)
- Keep each method focused on one business action or page query
- No test data hardcoded in this class — accept values as method parameters
- Import only what is used
- Do not use driver.findElement directly in public methods
- All interactions must go through explicit wait conditions
- Avoid exposing WebDriver outside the class
- Generated code must not introduce custom QA metric violations
- Prefer private helper methods for repeated wait/action patterns
- Do not expose low-level click/type methods unless existing project style requires it
- Include both action methods (click, type) and query methods (getText, isDisplayed) where applicable

---

## OUTPUT

A single Java class file, ready to save at `src/test/java/com/automation/pages/{{PAGE_CLASS_NAME}}.java`.

```java
package com.automation.pages;

import org.openqa.selenium.By;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.support.ui.ExpectedConditions;
import org.openqa.selenium.support.ui.WebDriverWait;
import java.time.Duration;

public class {{PAGE_CLASS_NAME}} {

    private final WebDriver driver;
    private final WebDriverWait wait;

    private static final By {{LOCATOR_NAME}} = By.{{LOCATOR_STRATEGY}}("{{LOCATOR_VALUE}}");

    public {{PAGE_CLASS_NAME}}(WebDriver driver) {
        this.driver = driver;
        this.wait = new WebDriverWait(driver, Duration.ofSeconds(10));
    }

    public void {{BUSINESS_METHOD}}({{PARAMETERS}}) {
        click({{LOCATOR_NAME}});
    }

    private void click(By locator) {
        wait.until(ExpectedConditions.elementToBeClickable(locator)).click();
    }

    private void type(By locator, String value) {
        wait.until(ExpectedConditions.visibilityOfElementLocated(locator)).sendKeys(value);
    }
}
```

---

## VALIDATION

After saving the file, run:

```bash
mvn clean verify -Dheadless=true
```

Then run to check custom QA metrics for locator and method quality:

```bash
npm run custom:qa-metrics
```
