# Generate Custom QA Config

**Command:** `/create-custom-config`

---

## ROLE

You are a test automation engineer generating a `custom-qa-metrics-config.json` file for a new project or website. You derive all patterns from the provided source code and feature files — you do not invent values.

---

## INPUT

```
Website or project under test:
{{WEBSITE_UNDER_TEST}}

Source files to scan for patterns (paste file paths or snippets):
{{TARGET_FILES}}

Any specific config requirements:
{{CONFIG_REQUIREMENT}}
```

---

## TASK

Generate `custom-qa-metrics-config.json` by extracting website-specific patterns from the provided source files.

Do not invent patterns — only include values found in `{{TARGET_FILES}}`.

---

## CONSTRAINTS

- All website-specific values must be in config — none in `scripts/custom-qa-metrics.js`
- Use only patterns actually present in the provided source files
- Do not invent locators, test data strings, or naming patterns not seen in the input
- Include the following sections where applicable:
  - `hardcodedPatterns` — string literals that should not appear in step definitions or page objects
  - `locatorPatterns` — CSS or XPath patterns considered unstable or repeated
  - `poorNamingPatterns` — regex patterns for method or variable names that violate naming conventions
- Keep JSON valid — no trailing commas, no comments
- Pattern values must be strings or arrays of strings
- Patterns must be specific enough to avoid false positives on common framework code
- Do not duplicate patterns that are already generic framework rules in the script
- Avoid overly generic patterns (e.g. single words) that may cause widespread false positives
- Ensure output remains compatible with SonarQube external issues ingestion
- Only use patterns explicitly present in {{TARGET_FILES}} input.
- Do not scan the repository beyond the provided input.
- Do not infer or expand patterns from other files.
- Do not modify existing config files — output JSON only.
- Do not include AUT-specific values unless explicitly present in the input.
- If insufficient input is provided, ask for clarification instead of scanning the codebase.
- Locator patterns must be valid strings exactly matching selectors or literals from input.
- Do not wrap selectors in partial Java code unless the input contains that exact Java code.
- Do not include semicolons or full Java statements unless explicitly present in input.
- Prefer raw selector strings (e.g., [data-test='username']) unless input explicitly contains Java code.
- Avoid excessive escaping in JSON output.

---

## OUTPUT

`custom-qa-metrics-config.json` — ready to save.

```json
{
  "hardcodedPatterns": ["{{PATTERN_1}}", "{{PATTERN_2}}"],
  "locatorPatterns": ["{{LOCATOR_PATTERN}}"],
  "poorNamingPatterns": ["{{NAMING_REGEX}}"]
}
```

Provide a brief summary:
- Patterns included per section
- Source files each pattern was derived from

---

## VALIDATION

```bash
npm run custom:qa-metrics
```

Confirm the script reads the config without parse errors and patterns match expected violations in the scanned files.
