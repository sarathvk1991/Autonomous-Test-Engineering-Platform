# Refactor Test Data

**Command:** `/refactor-test-data`

---

## ROLE

You are a Java test automation engineer refactoring test data organisation in a Selenium Cucumber framework. You improve constant naming, eliminate duplication, and centralise config usage without changing test behaviour.

---

## INPUT

```
File(s) to refactor:
{{FILE_PATH}}

Code to refactor (optional — paste specific class or snippet):
{{CODE_SNIPPET}}

Reason for refactor (e.g. duplicated constants, hardcoded values in steps, poor naming):
{{REASON}}
```

---

## TASK

Refactor the test data class(es) at `{{FILE_PATH}}`. Remove duplication, improve constant naming, and centralise config-driven values without changing the data values or breaking callers.

---

## CONSTRAINTS

- Do not change the actual data values — refactor structure and naming only
- Do not break step definitions or page objects that reference existing constants
- If renaming a constant, update all usages across the codebase
- Do not modify unrelated files beyond updating references to renamed constants
- Changes must be minimal and targeted to the identified issues
- Remove duplicated constants — a value must appear in exactly one place
- Extract hardcoded string/int literals from step definitions and page objects into this class
- Config-driven values (environment-specific) must be read via `ConfigReader`, not hardcoded
- Constants must be `public static final` with descriptive names (e.g. `VALID_USERNAME`, not `USER1`)
- Keep each test data class focused on one concern — split if the class has grown beyond one domain
- Utility class constructors must be `private`
- No unused constants or imports after refactor
- Do not introduce custom QA metric violations
- Code must compile and all tests must pass after refactor
- Do not move data between constants and config unless clearly environment-specific
- Preserve existing config property keys unless explicitly refactoring config structure
- Refactor must not introduce behavioral changes or test failures

---

## OUTPUT

The refactored file(s), ready to save at `{{FILE_PATH}}`.

Provide a brief summary:
- What was changed
- Why each change was made (duplication, naming, extraction, etc.)
- Any constants that were renamed and where references were updated

---

## VALIDATION

```bash
mvn clean verify -Dheadless=true
npm run custom:qa-metrics
```

Confirm build passes, all scenarios execute, and no hardcoded data or unused constant violations appear.
