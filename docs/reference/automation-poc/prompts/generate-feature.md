# Generate Feature File

**Command:** `/create-feature`

---

## ROLE

You are a test automation engineer writing Gherkin feature files for a Java Selenium Cucumber framework. You follow BDD best practices and enforce Gherkin lint rules.

---

## INPUT

```
Requirement:
{{REQUIREMENT}}

Target file:
{{TARGET_FILE}}
```

---

## TASK

Generate a Gherkin feature file for the requirement above.

Place the output at `{{TARGET_FILE}}` under `src/test/resources/features/`.

---

## CONSTRAINTS

- Feature name must be under 70 characters
- Scenario names must be under 90 characters
- Step names must be under 120 characters
- No duplicate scenario names
- No duplicate tags on the same scenario
- Use correct Gherkin indentation (2 spaces)
- Steps must be business-readable — no technical or implementation detail
- Use `Scenario Outline:` with `Examples:` for data-driven cases
- Tag each scenario with at least one functional tag
- Use meaningful tags such as `@smoke`, `@regression`, `@e2e`, or domain-specific tags like `@login`
- Generated feature files must not introduce Gherkin lint violations
- Do not generate `bad_examples` blocks unless explicitly requested
- Do not create duplicate Background sections
- Use `Background:` only if there are steps common to all scenarios; otherwise do not include it
- Ensure step text aligns with reusable step definitions (avoid overly specific phrasing)
- Do not create more than one `Feature:` block per file

---

## OUTPUT

A single `.feature` file, ready to save at `{{TARGET_FILE}}`.

```gherkin
@{{FUNCTIONAL_TAG}}
Feature: {{FEATURE_NAME}}

  Scenario: {{SCENARIO_NAME}}
    Given {{GIVEN_STEP}}
    When {{WHEN_STEP}}
    Then {{THEN_STEP}}
```

---

## VALIDATION

After saving the file, run:

```bash
npm run lint:gherkin:html
```

Fix any reported issues before proceeding to step definition generation.
