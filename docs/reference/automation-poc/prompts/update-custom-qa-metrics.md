# Update Custom QA Metrics Script

**Command:** `/update-custom-qa`

---

## ROLE

You are a Node.js automation engineer modifying an existing custom QA metrics script. You add or update only the requested rule or metric without changing existing rules, weakening thresholds, or moving website-specific data into the script.

---

## INPUT

```
New rule or metric to add / update:
{{NEW_RULE_OR_METRIC}}

Description of what it should detect:
{{RULE_DESCRIPTION}}

Relevant source files or patterns (optional):
{{TARGET_FILES}}
```

---

## TASK

Update `scripts/custom-qa-metrics.js` to add or modify `{{NEW_RULE_OR_METRIC}}`.

Change only what is required for the new rule. Preserve all existing rules, output format, and config structure.

---

## CONSTRAINTS

- Add or modify only the requested rule or metric — do not touch unrelated rules
- Do not hardcode website-specific patterns in the JS — add new patterns to `custom-qa-metrics-config.json` instead
- Preserve the existing SonarQube external issues output format exactly
- Do not weaken existing rules or lower thresholds unless explicitly instructed
- Maintain backward compatibility with existing `custom-qa-metrics-config.json` keys
- New issues must include all mandatory fields: `engineId`, `ruleId`, `severity`, `type`, `primaryLocation`
- `textRange` must have valid offsets — `startColumn` must be less than `endColumn`
- New rule must include `ruleId`, `name`, and `description` in rule metadata
- Exit code behavior must be configurable:
  - default: exit `0` after generating report so Sonar can ingest issues
  - optional strict mode: exit `1` if violations are found
- Code must not break on files that do not trigger the new rule
- Do not remove or rename existing config keys
- Ensure new rule does not conflict with existing rules (no duplicate detection)
- Ensure output remains compatible with SonarQube external issues ingestion


---

## OUTPUT

The updated `scripts/custom-qa-metrics.js`, ready to save.

Provide a brief summary:
- What was added or changed
- New config keys required in `custom-qa-metrics-config.json` (if any)
- Existing rules confirmed unchanged

---

## VALIDATION

```bash
npm run custom:qa-metrics
mvn clean verify -Dheadless=true sonar:sonar
```

Confirm the new rule fires on a known violation, existing rules still pass, and Sonar ingests the report without errors.
