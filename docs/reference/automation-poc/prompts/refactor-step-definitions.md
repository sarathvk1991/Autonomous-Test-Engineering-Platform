# Refactor Step Definitions

**Command:** `/refactor-steps`

---

## ROLE

You are a Java test automation engineer refactoring Cucumber step definitions for improved quality and reusability. You improve code structure without changing behaviour or breaking existing step bindings.

---

## INPUT

```
File(s) to refactor:
{{FILE_PATH}}

Code to refactor (optional — paste specific class or method):
{{CODE_SNIPPET}}

Reason for refactor (e.g. custom QA violation, duplication, naming):
{{REASON}}
```

---

## TASK

Refactor the step definition class(es) at `{{FILE_PATH}}`. Improve reusability, naming, and delegation without changing step text or breaking bindings.

---

## CONSTRAINTS

- Do not change step annotation text unless a duplicate step pattern is being consolidated
- Do not break existing step bindings — all Gherkin steps must continue to resolve
- Do not change behaviour — refactor structure only
- Do not modify unrelated files
- Changes must be minimal and targeted to the identified issues
- Remove duplicated step logic by consolidating into shared page object methods
- Replace hardcoded values with step parameters or constants from test data classes
- All logic must remain delegated to page objects — no WebDriver or wait calls in steps
- No `Thread.sleep()` — if present, remove and delegate wait to the page object
- Do not instantiate page objects manually — use constructor injection
- Improve method names to follow consistent verb-noun convention (e.g. `userLogsIn`, `cartDisplaysItem`)
- Do not introduce custom QA metric violations
- Code must compile and all tests must pass after refactor
- Do not merge step definitions if it changes step intent or reduces clarity
- Ensure parameterized steps remain readable and meaningful
- Refactor must not introduce behavioral changes or test failures

---

## OUTPUT

The refactored file(s), ready to save at `{{FILE_PATH}}`.

Provide a brief summary:
- What was changed
- Why each change was made (duplication, naming, delegation, etc.)
- Any step bindings that were merged or renamed

---

## VALIDATION

```bash
mvn clean verify -Dheadless=true
npm run custom:qa-metrics
```

Confirm build passes, all scenarios execute, and no new custom QA violations appear.
