# Automation-POC Reference Material

These are reference artifacts mined from the sibling `Automation-POC` repository (the same
project ADR-0037 sources its `customqa:*` SonarQube profile and Java/Cucumber stack
decisions from). They are **not live platform assets** and are **not loaded by any code**.

## Prompt assets

`prompts/` contains **5 of the POC's roughly 26–30 Copilot slash-commands** — the subset
reviewed for ADR-0040 (Control Point Model and Layer 4 Redefinition):

- `generate-feature.md` (`/create-feature`)
- `refactor-feature.md` (`/refactor-feature`)
- `generate-test-data.md` (`/create-test-data`)
- `validate-generated-feature.md` (`/validate-feature`)
- `fix-gherkin-lint.md` (`/fix-gherkin`)

These are **Copilot slash-commands**, written for an interactive coding-agent session —
not API prompts. They are not wired into the platform's LLM call path. When Layer 2 is
built, the subset that remains relevant will be ported into the governed prompt registry
(ADR-0014, SHA-256 verified, versioned) rather than used as-is. The remaining prompts in the
POC (page objects, step definitions, SonarQube/custom-qa config, debugging and analysis
commands) were not copied here and are out of scope for this amendment; a future Layer 3 or
Layer 4 amendment may reference them separately.

## `.gherkin-lintrc`

A snapshot of the POC's Gherkin-lint configuration — 17 rules (naming, duplication, tagging,
formatting, indentation, size limits). It becomes live configuration only when the linter is
ported (Python, over the official Cucumber Gherkin parser, per
`docs/proposals/layer-2-feature-engineering-lld.md`'s Reviewer's note, §12). The rule set
itself is not to be extended in that port — this file is preserved verbatim as the config
contract.
