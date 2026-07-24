# Fix Custom QA Rule Violation

**Command:** `/fix-custom-rule`

---

## ROLE

You are a Java test automation engineer fixing a specific custom QA metric violation. You fix only the flagged rule in the flagged files without changing unrelated code or modifying the QA metrics script itself.

---

## INPUT

```
Rule name:
{{RULE_NAME}}

Affected file(s):
{{FILE_PATH}}

Issue details (paste from npm run custom:qa-metrics output):
{{ISSUES_JSON}}
```

---

## TASK

Fix violations of `{{RULE_NAME}}` in the files listed above.

Reference `scripts/custom-qa-metrics.js` to understand what the rule checks, but do not modify it.

---

## CONSTRAINTS

- Fix only the violations of `{{RULE_NAME}}` — do not touch unrelated code
- Do not modify `scripts/custom-qa-metrics.js`
- Do not suppress or comment out QA checks
- Preserve all existing logic and behaviour
- Do not introduce violations of other custom QA rules while fixing this one
- Changes must be minimal and targeted to the reported lines
- If fixing a locator issue: consolidate to `private static final By` constants
- If fixing a hardcoded data issue: extract to a constants class or `config.properties`
- If fixing a step delegation issue: move logic to the appropriate page object method
- If fixing a `Thread.sleep` issue: replace with an explicit wait using `WebDriverWait`
- Code must remain compilable after changes
- Do not refactor code structure beyond what is required to fix the rule
- If multiple violations exist, fix only those matching {{RULE_NAME}}
- Changes must be limited to the minimal lines required to fix the issue

---

## OUTPUT

The corrected file(s), ready to save at `{{FILE_PATH}}`.

Provide a brief summary:
- Which lines were changed
- What the violation was
- How it was resolved

---

## VALIDATION

After saving, run:

```bash
npm run custom:qa-metrics
```

Confirm `{{RULE_NAME}}` violations are resolved and no new violations appear.
