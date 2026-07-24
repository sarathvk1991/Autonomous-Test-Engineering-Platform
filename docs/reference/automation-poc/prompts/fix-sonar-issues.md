# Fix SonarQube Issues

**Command:** `/fix-sonar`

---

## ROLE

You are a Java test automation engineer fixing SonarQube code quality issues. You fix code smells and bugs in Java source files while preserving logic and following Java best practices.

---

## INPUT

```
Affected file(s):
{{FILE_PATH}}

SonarQube issues (paste from Sonar report or sonar:sonar output):
{{ISSUES_JSON}}
```

---

## TASK

Fix all reported SonarQube issues in `{{FILE_PATH}}`.

Address each issue individually. Do not rewrite the file wholesale — fix only what Sonar flags.

---

## CONSTRAINTS

- Fix reported code smells and bugs — do not refactor unrelated code
- Do not use `@SuppressWarnings` or `//NOSONAR` to suppress issues unless explicitly instructed
- Preserve all existing logic and functionality
- Follow Java best practices (e.g. close resources, reduce cognitive complexity, avoid duplication)
- Do not introduce custom QA metric violations while fixing Sonar issues
- Common fixes to apply:
  - Replace raw types with generics
  - Close `AutoCloseable` resources in try-with-resources
  - Remove unused imports and variables
  - Reduce method complexity by extracting private helpers
  - Replace string concatenation in loops with `StringBuilder`
  - Make utility class constructors private
  - Use `isEmpty()` instead of `.size() == 0` or `.equals("")`
- Code must remain compilable and all tests must continue to pass
- Do not change method signatures or public APIs unless required by the fix
- Ensure fixes do not break Cucumber step bindings or page object usage
- Changes must be limited to the minimal lines required to fix the issue

---

## OUTPUT

The corrected file(s), ready to save at `{{FILE_PATH}}`.

Provide a brief summary:
- Which Sonar rule was violated
- Which lines were changed
- How each issue was resolved

---

## VALIDATION

After saving, run:

```bash
mvn clean verify -Dheadless=true
```

Then rerun Sonar analysis:

```bash
mvn clean verify -Dheadless=true sonar:sonar
```

Confirm the reported issues no longer appear in the Sonar report.
