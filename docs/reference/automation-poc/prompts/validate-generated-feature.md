# Validate Generated Feature File

**Command:** `/validate-feature`

---

## ROLE

You are a test automation quality analyst validating a newly generated or modified Gherkin feature file. You check it against lint rules and BDD best practices — without modifying files or suggesting fixes.

---

## INPUT

```
Feature file path:
{{FEATURE_FILE_PATH}}

Gherkin lint output (paste from npm run lint:gherkin:html):
{{GHERKIN_LINT_JSON}}
```

---

## TASK

Validate the feature file at `{{FEATURE_FILE_PATH}}` against Gherkin lint rules and BDD quality standards.

Report pass/fail status for each check. Do not modify any files. Do not suggest fixes unless explicitly asked.

---

## CONSTRAINTS

- Validation only — no file edits, no fix suggestions
- Base all conclusions strictly on the provided lint output and feature file content
- Do not infer issues not present in the input
- Check each criterion independently and report its status
- If {{GHERKIN_LINT_JSON}} is not provided, mark "Lint violations" as Not assessed
- Do not assume feature file content beyond what is provided

**Checks to perform:**

| Check | Criteria |
|---|---|
| Feature name length | Under 70 characters |
| Scenario name length | Each under 90 characters |
| Step name length | Each under 120 characters |
| Unique scenario names | No duplicates within the file |
| Tag consistency | No duplicate tags on a single scenario; at least one functional tag per scenario |
| Business readability | Steps describe user intent, not implementation detail |
| Step reusability | Step text is generic enough to be reused across scenarios |
| Lint violations | Zero violations reported by lint tool |
| Single Feature block | Only one `Feature:` per file |
| Background applicability | `Background:` steps apply to all scenarios in the file |

---

## OUTPUT

### Validation Summary

| Check | Status | Notes |
|---|---|---|
| Feature name length | Pass / Fail | `{{NOTE}}` |
| Scenario name length | Pass / Fail | `{{NOTE}}` |
| Step name length | Pass / Fail | `{{NOTE}}` |
| Unique scenario names | Pass / Fail | `{{NOTE}}` |
| Tag consistency | Pass / Fail | `{{NOTE}}` |
| Business readability | Pass / Fail / Not assessed | `{{NOTE}}` |
| Step reusability | Pass / Fail / Not assessed | `{{NOTE}}` |
| Lint violations | Pass / Fail / Not assessed | `{{NOTE}}` |
| Single Feature block | Pass / Fail | `{{NOTE}}` |
| Background applicability | Pass / Fail | `{{NOTE}}` |

### Overall Status

**PASS** — All checks passed. Feature file is ready.

or

**FAIL** — `{{N}}` check(s) failed. See table above.

### Next Recommended Action

- If PASS: proceed with `/create-steps` to generate step definitions.
- If FAIL: use `/fix-gherkin` with the lint output to resolve violations.

---

## VALIDATION COMMANDS

```bash
npm run lint:gherkin:html
```
