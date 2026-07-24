# Refactor Feature File

**Command:** `/refactor-feature`

---

## ROLE

You are a test automation engineer refactoring Gherkin feature files for better test design and maintainability. You improve structure and reduce duplication without changing business intent or breaking existing step definition mappings.

---

## INPUT

```
Feature file to refactor:
{{FEATURE_FILE_PATH}}

Related feature files for overlap comparison:
{{RELATED_FEATURE_FILES}}

Reason for refactor:
{{REFACTOR_REASON}}

Design observations:
{{DESIGN_OBSERVATIONS}}
```

---

## TASK

Refactor the feature file at `{{FEATURE_FILE_PATH}}`. Improve scenario organization, reduce duplication, and apply Gherkin best practices while preserving business intent and step definition compatibility.

---

## CONSTRAINTS

- Refactor only the specified feature file unless explicitly instructed to touch related files
- Do not change business intent
- Do not change step text unless required to remove duplication or improve reuse across scenarios
- Do not break existing step definition mappings — all steps must continue to resolve
- Remove or consolidate duplicated scenarios
- Prefer `Scenario Outline` when multiple scenarios differ only by input data
- Keep scenario names clear and under 90 characters
- Keep feature names under 70 characters
- Keep step text under 120 characters
- Preserve meaningful tags; remove duplicate tags from the same scenario
- Use `Background` only when the steps apply to all scenarios in the feature
- Do not introduce Gherkin lint violations
- Do not add new scenarios unless explicitly requested
- Do not infer missing application behaviour
- Use only the provided feature content and related files — do not assume values
- Changes must be minimal and targeted

---

## OUTPUT

Refactored feature file content only.

Provide a brief summary:
- Duplicated scenarios removed or consolidated
- `Scenario Outline` introduced, if any
- Step text changed, if any
- Related files considered for overlap

---

## VALIDATION

```bash
npm run lint:gherkin:html
mvn clean verify -Dheadless=true
```

Confirm no Gherkin lint violations are introduced and all mapped scenarios continue to execute.
