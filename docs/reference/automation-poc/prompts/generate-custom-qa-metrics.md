# Generate Custom QA Metrics Script

**Command:** `/create-custom-qa`

---

## ROLE

You are a Node.js automation engineer creating a custom QA metrics script for a Java Selenium Cucumber framework. The script reads website-specific configuration from a JSON file and produces a SonarQube external issues report.

---

## INPUT

```
Website or project under test:
{{WEBSITE_UNDER_TEST}}

Target source files / directories to scan:
{{TARGET_FILES}}

Config file path (default: custom-qa-metrics-config.json):
{{CONFIG_FILE}}
```

---

## TASK

Generate `scripts/custom-qa-metrics.js` from scratch.

The script must read all website-specific patterns from `custom-qa-metrics-config.json` and write a SonarQube-compatible external issues report to `sonar-custom-qa-issues.json`.

---

## CONSTRAINTS

- Do not hardcode website-specific values (locators, patterns, test data strings) in the JS file — all must come from config
- Read config at runtime via `fs.readFileSync` / `JSON.parse`
- Output must be valid SonarQube external issues JSON format
- Each issue must include: `engineId`, `ruleId`, `severity`, `type`, `primaryLocation` (with `message`, `filePath`, `textRange`)
- `textRange` must have `startLine`, `endLine`, `startColumn`, `endColumn` — `startColumn` must be less than `endColumn`
- Include rule metadata with `name` and `description` per rule
- Include a summary section with violation counts per rule
- Include calculated percentage metrics where applicable (e.g. naming compliance %, reusable step %)
- Exit code behavior must be configurable:
  - default: exit `0` after generating report so Sonar can ingest issues
  - optional strict mode: exit `1` if violations are found
- Do not swallow errors silently — surface file read and parse failures
- Do not scan node_modules, target/, or generated files
- Ensure output remains compatible with SonarQube external issues ingestion

---

## OUTPUT

`scripts/custom-qa-metrics.js` — ready to save.

Provide a brief summary:
- Rules implemented
- Metrics calculated
- Config keys expected in `custom-qa-metrics-config.json`

---

## VALIDATION

```bash
node scripts/custom-qa-metrics.js
npm run custom:qa-metrics
mvn clean verify -Dheadless=true sonar:sonar
```

Confirm script runs without error, issues report is valid JSON, and Sonar ingests the report without `textRange` errors.
