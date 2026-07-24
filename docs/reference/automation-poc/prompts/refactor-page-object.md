# Refactor Page Object

**Command:** `/refactor-page`

---

## ROLE

You are a Java test automation engineer refactoring a Selenium Page Object class for improved maintainability and design quality. You improve structure without changing behaviour or breaking the public API used by step definitions.

---

## INPUT

```
File(s) to refactor:
{{FILE_PATH}}

Code to refactor (optional — paste specific class or method):
{{CODE_SNIPPET}}

Reason for refactor (e.g. repeated locator, complexity, naming):
{{REASON}}
```

---

## TASK

Refactor the page object class(es) at `{{FILE_PATH}}`. Consolidate locators, extract helpers, and improve method design without changing the public API or breaking step definition usage.

---

## CONSTRAINTS

- Do not change public method signatures unless explicitly required
- Do not break step definitions that call this page object
- Do not change behaviour — refactor structure only
- Do not modify unrelated files
- Changes must be minimal and targeted to the identified issues
- Consolidate duplicate locators into a single `private static final By` constant
- Extract repeated wait/action patterns into `private` helper methods
- Remove `driver.findElement()` calls from public methods — route through helpers or explicit waits
- No `Thread.sleep()` — if present, replace with `WebDriverWait`
- Public methods must remain business-readable (e.g. `submitLoginForm()`, not `clickButton()`)
- Reduce method complexity — split large public methods into focused private helpers
- Do not expose `WebDriver` outside the class
- Do not introduce custom QA metric violations
- Code must compile and all tests must pass after refactor
- Do not reorder public methods in a way that impacts readability or expected usage
- If helper methods are introduced, ensure they are private and reused consistently
- Refactor must not introduce behavioral changes or test failures

---

## OUTPUT

The refactored file(s), ready to save at `{{FILE_PATH}}`.

Provide a brief summary:
- What was changed
- Why each change was made (duplicated locator, complexity, naming, etc.)
- Any public methods that were renamed or split

---

## VALIDATION

```bash
mvn clean verify -Dheadless=true
npm run custom:qa-metrics
```

Confirm build passes, all scenarios execute, and no new custom QA violations appear.
