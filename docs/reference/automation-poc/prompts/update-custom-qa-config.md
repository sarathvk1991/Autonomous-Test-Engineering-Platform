# Update Custom QA Config

**Command:** `/update-custom-config`

---

## ROLE

You are a test automation engineer updating `custom-qa-metrics-config.json` for a new website, module, or page added to the framework. You scan provided source files to derive new patterns and remove only stale patterns that no longer exist.

---

## INPUT

```
New page(s), module(s), or website being added:
{{WEBSITE_UNDER_TEST}}

Source files to scan (page objects, step definitions, utils, feature files):
{{TARGET_FILES}}

Specific config requirement or pattern to add/remove:
{{CONFIG_REQUIREMENT}}
```

---

## TASK

Update `custom-qa-metrics-config.json` based on patterns found in `{{TARGET_FILES}}`.

Add new patterns derived from the provided files. Remove stale patterns only if they no longer exist anywhere in the codebase.

---

## CONSTRAINTS

- Do not modify `scripts/custom-qa-metrics.js`
- Derive new patterns only from the provided source files — do not invent values
- Do not remove a pattern unless you can confirm it is no longer present in any source file
- Preserve existing config structure and all currently valid patterns
- Keep JSON valid — no trailing commas, no comments
- Do not duplicate patterns already present in the config
- New `hardcodedPatterns` must be specific enough to avoid false positives on framework internals
- New `locatorPatterns` must target unstable or repeated locator styles found in the provided files
- New `poorNamingPatterns` must be valid regex strings
- If a pattern is ambiguous or risky to add without more context, flag it rather than adding it silently
- Do not remove patterns unless verified across all modules, not just provided files
- Ensure output remains compatible with SonarQube external issues ingestion
- Do not modify custom-qa-metrics-config.json unless the user explicitly says “apply the update”.
- If the user says “do not modify files”, return the proposed JSON changes only.
- Treat “update config” as a proposal unless file modification is explicitly authorized.

---

## OUTPUT

The updated `custom-qa-metrics-config.json`, ready to save.

Provide a brief summary:
- Patterns added (with source file reference)
- Patterns removed (with reason)
- Patterns left unchanged

---

## VALIDATION

```bash
npm run custom:qa-metrics
```

Confirm the script reads the updated config without parse errors, new patterns fire on expected violations, and no existing rules regress.
