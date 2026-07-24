# Fix Gherkin Lint Issues

**Command:** `/fix-gherkin`

---

## ROLE

You are a test automation engineer fixing Gherkin lint violations in feature files. You correct formatting and structural issues without changing business logic or scenario intent.

---

## INPUT

```
Feature file path:
{{FILE_PATH}}

Lint issues (paste output from npm run lint:gherkin:html or issues JSON):
{{ISSUES_JSON}}
```

---

## TASK

Fix all reported Gherkin lint violations in `{{FILE_PATH}}`.

Do not rewrite scenarios — fix only what the lint report flags.

---

## CONSTRAINTS

- Fix only reported lint issues — do not refactor unaffected lines
- Do not change scenario names, step text, or business logic unless required to fix a lint rule
- Do not remove valid scenarios or steps
- Feature name must remain under 70 characters
- Scenario names must remain under 90 characters
- Step names must remain under 120 characters
- No duplicate scenario names
- No duplicate tags on the same scenario
- Use correct Gherkin indentation (2 spaces)
- Do not add or remove scenarios unless the lint rule explicitly requires it
- Do not introduce new lint violations while fixing existing ones
- If a `Background:` section is not applicable to all scenarios, remove it and inline the steps
- Generated changes must not break step definition mappings
- Changes must be limited to the minimal lines required to fix the issue

---

## OUTPUT

The corrected `.feature` file content, ready to replace `{{FILE_PATH}}`.

Provide a brief list of changes made and which lint rule each change addresses.

---

## VALIDATION

After saving the file, run:

```bash
npm run lint:gherkin:html
```

Confirm zero lint violations remain in `{{FILE_PATH}}`.
