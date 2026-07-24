# Generate Test Data

**Command:** `/create-test-data`

---

## ROLE

You are a Java test automation engineer creating reusable test data support for a Selenium Cucumber framework. Test data must be decoupled from step definitions and page objects.

---

## INPUT

```
Data keys / fields needed:
{{TEST_DATA_KEYS}}

Target class or file name:
{{TARGET_FILE}}

Context (what test uses this data):
{{REQUIREMENT}}
```

---

## TASK

Generate a Java test data class or constants file named `{{TARGET_FILE}}` in `src/test/java/com/automation/utils/`.

Choose the appropriate pattern based on the data type:
- **Constants class** — for static, environment-independent values (e.g. expected labels, fixed inputs)
- **Config-driven** — for environment-specific values (e.g. base URL, credentials) read from `config.properties`
- **Data provider** — for tabular/parameterised data used in Scenario Outlines

---

## CONSTRAINTS

- Package: `com.automation.utils`
- No sensitive data (passwords, tokens) hardcoded in source — use `config.properties` or environment variables
- No test data hardcoded inside step definitions or page objects — reference this class instead
- Constants must be `public static final`
- Config-driven values must be read via `ConfigReader` — do not call `System.getProperty` directly in steps
- Keep the class focused — one concern per file
- No unused fields or imports
- Do not duplicate keys across multiple test data classes
- Prefer meaningful constant names over generic names like DATA1, VALUE1
- Generated code must not introduce custom QA metric violations
- Do not modify config.properties automatically.
- If new config keys are required, list them separately but do not update files.
- Test data generation must not introduce side effects in environment configuration.

---

## OUTPUT

**Option A — Constants class:**

```java
package com.automation.utils;

public class {{TARGET_FILE}} {

    public static final String {{KEY_1}} = "{{VALUE_1}}";
    public static final String {{KEY_2}} = "{{VALUE_2}}";

    private {{TARGET_FILE}}() {}
}
```

**Option B — Config-driven values (via ConfigReader):**

```java
package com.automation.utils;

public class {{TARGET_FILE}} {

    public static final String {{KEY_1}} = ConfigReader.get("{{PROPERTY_KEY_1}}");
    public static final String {{KEY_2}} = ConfigReader.get("{{PROPERTY_KEY_2}}");

    private {{TARGET_FILE}}() {}
}
```

Add the corresponding entries to `src/test/resources/config.properties`:

```properties
{{PROPERTY_KEY_1}}={{VALUE_1}}
{{PROPERTY_KEY_2}}={{VALUE_2}}
```

---

## VALIDATION

After saving, run:

```bash
mvn clean verify -Dheadless=true
npm run custom:qa-metrics
```

Confirm build passes, no hardcoded test data violations are introduced and no unused constants or imports are present
