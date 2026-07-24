# Generate Step Definitions

**Command:** `/create-steps`

---

## ROLE

You are a Java test automation engineer writing Cucumber step definitions for a Selenium framework. Step definitions are thin glue code — they delegate all UI interaction to page objects.

---

## INPUT

```
Feature file path:
{{FEATURE_FILE_PATH}}

Step definition class name:
{{STEP_CLASS_NAME}}

Relevant page object(s):
{{PAGE_CLASS_NAME}}
```

---

## TASK

Generate a Java Cucumber step definition class named `{{STEP_CLASS_NAME}}` in `src/test/java/com/automation/steps/`.

Read the steps from `{{FEATURE_FILE_PATH}}` and map each unique step to a method.

---

## CONSTRAINTS

- Package: `com.automation.steps`
- Each step method must delegate to a page object method — no direct WebDriver calls
- No `Thread.sleep()` — use explicit waits in the page object layer
- No hardcoded test data — accept values from step parameters or pass constants
- Reuse existing step definitions if a matching step already exists
- Keep methods short and single-purpose
- Class must compile cleanly with no unused imports
- Use `@Given`, `@When`, `@Then`, `@And` annotations from `io.cucumber.java.en`
- Inject page objects via the constructor using Cucumber's PicoContainer or `@Autowired`
- Do not include any strings like "standard_user", "secret_sauce", or product names directly
- Do not instantiate page objects manually using new
- Generated code must not introduce custom QA metric violations
- Do not use `new Bad...` or reference any `badexamples` classes

---

## OUTPUT

A single Java class file, ready to save at `src/test/java/com/automation/steps/{{STEP_CLASS_NAME}}.java`.

```java
package com.automation.steps;

import com.automation.pages.{{PAGE_CLASS_NAME}};
import io.cucumber.java.en.Given;
import io.cucumber.java.en.Then;
import io.cucumber.java.en.When;

public class {{STEP_CLASS_NAME}} {

    private final {{PAGE_CLASS_NAME}} {{PAGE_INSTANCE}};

    public {{STEP_CLASS_NAME}}({{PAGE_CLASS_NAME}} {{PAGE_INSTANCE}}) {
        this.{{PAGE_INSTANCE}} = {{PAGE_INSTANCE}};
    }

    @Given("{{GIVEN_STEP_TEXT}}")
    public void {{GIVEN_METHOD_NAME}}() {
        {{PAGE_INSTANCE}}.{{PAGE_METHOD}}();
    }
}
```

---

## VALIDATION

After saving the file, run:

```bash
mvn clean verify -Dheadless=true
npm run custom:qa-metrics
```

Confirm the build compiles, scenarios execute, and no custom QA violations are introduced.
