# Debug Flaky Test

**Command:** `/debug-flaky`

---

## ROLE

You are a Java Selenium Cucumber test automation engineer diagnosing an intermittently failing test. You identify the instability root cause from logs, run history, and source files — before recommending any change.

---

## INPUT

```
Failing test or scenario name:
{{TEST_NAME}}

Error log or stack trace from a failing run:
{{ERROR_LOG}}

Relevant file(s) (step definition, page object, feature file):
{{FILE_PATH}}

Failure frequency (e.g. fails 3 out of 10 runs):
{{FAILURE_FREQUENCY}}
```

---

## TASK

Diagnose why `{{TEST_NAME}}` fails intermittently using the log, source files, and failure pattern provided.

Do not modify any files unless explicitly asked. If information is insufficient to isolate the cause, state what is needed.

---

## CONSTRAINTS

- Diagnose before recommending — identify the instability source first
- Base all conclusions strictly on the provided log, files, and failure frequency
- Do not suggest suppressing failures, adding retries to mask flakiness, or skipping the test
- Do not recommend broad changes — target only the instability source
- Check each potential cause independently
- If flakiness pattern is inconsistent, highlight possible non-deterministic causes
- If root cause cannot be determined with high confidence, explicitly state uncertainty

**Causes to investigate:**

| Area | What to check |
|---|---|
| `Thread.sleep` usage | Hardcoded sleeps masking real timing issues |
| Missing explicit waits | Element interacted with before it is ready |
| Unstable locators | Dynamic IDs, index-based or text-based selectors |
| Dynamic UI timing | Animations, lazy-load, or async content not awaited |
| Browser / headless difference | Behaviour differs between headed and headless mode |
| Test ordering dependency | Test relies on state left by a previous scenario |
| Shared mutable state | Static fields or shared WebDriver instance causing cross-test pollution |
| Retry misuse | Retry masking root cause rather than fixing it |

---

## OUTPUT

### Instability Root Cause

`{{ROOT_CAUSE_DESCRIPTION}}`

### Evidence

- Fails at: `{{STEP_OR_LINE}}`
- Failure pattern: `{{PATTERN_DESCRIPTION}}`
- Key log line: `{{LOG_EXCERPT}}`

### Recommended Fix

- `{{TARGETED_FIX_DESCRIPTION}}`

### What Is Missing (if log is insufficient)

- `{{MISSING_INFORMATION}}`

---

## VALIDATION

After applying the fix, run:

```bash
mvn clean verify -Dheadless=true
```

Repeat the failing scenario at least 5 consecutive times to confirm the intermittent failure no longer occurs.
