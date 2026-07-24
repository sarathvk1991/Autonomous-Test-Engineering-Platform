# Layer 2 — Feature Engineering Layer (LLD)

| Field | Value |
|---|---|
| Status | Submitted — under review. **Not approved.** |
| Type | Low-Level Design |
| Layer | Layer 2 — Feature Engineering |
| Source artifact | `Feature_Engineering_Layer.pptx` (22 slides), authored outside this repository |
| Transcribed | 2026-07-24 |
| Governs | Nothing yet. Informs ADR-0040 and a future Layer 2 architecture-freeze ADR. |

---

## Reviewer's note — superseded and pending items

This document is committed as the **record of what was proposed**, not as approved design.
The body below is a faithful transcription and has **not** been edited to reflect later
decisions. The following items are already superseded or unresolved. Do not implement from
this document without checking this list first.

| Section | Proposed here | Current position |
|---|---|---|
| §8, §14 | Azure OpenAI named as the LLM provider | Provider-agnostic via the existing `llm_factory`. Gemini in use; Azure pending management approval. No vendor in any contract or LLD. |
| §2 | `validated-requirement-model.json` with untyped, ID-less criteria arrays | Superseded by the `TestableRequirement` / `TestableRequirementSet` contract (ADR-0034). |
| §2 | `riskBasedScenarios` emitted by Layer 1 | Layer 1 emits **risks**; Layer 2 owns all scenario generation. Scenario generation lives in exactly one layer. |
| §5, §7, §20 | A new Prompt Registry (`prompt-registry.json`) built in Layer 2 | Use the existing governed prompt registry (ADR-0014, SHA-256 verified, versioned), extracted to a shared platform service. |
| §15, §16 | CP2 gating that includes LLM-judged criteria | CP2 gates **deterministically** only (ADR-0040). LLM assessments are advisory and may trigger human review, never gate. |
| §11 | Test data emitted as `positiveData` / `negativeData` / `boundaryData` JSON | Layer 2 owns `Examples` tables and emits a test-data **specification**. Java test data classes are a Layer 3 artifact. |
| §20 | Traceability held in `traceability.json` | Traceability IDs are emitted as Gherkin tags in the artifacts themselves; `traceability.json` becomes a derived index (ADR-0034). |
| §12 | "Gherkin Lint" via the npm `gherkin-lint` package | Rules to be ported to Python over the official Cucumber Gherkin parser, preserving `.gherkin-lintrc` verbatim as the config contract. Rule set is not to be extended. |
| §3, §18 | Undifferentiated "output package" | Generated `.feature` files land in the untracked per-run workspace at `src/test/resources/features/`; reports land in the run directory (ADR-0036, ADR-0037). |

**Not addressed anywhere in this LLD, and required:** run/stage state integration
(ADR-0036); idempotency and regeneration-on-change semantics; a bounded remediation loop
(max 2 attempts); a controlled step vocabulary to prevent near-duplicate step definitions
in Layer 3; token/cost budgeting.

---

## 1. Purpose

The Feature Engineering Layer transforms the Validated Requirement Model produced by the
Requirement Intelligence Layer into governed and executable BDD assets.

The layer is responsible for:

- Feature generation
- Scenario generation
- Scenario outline generation
- Test data generation
- Feature governance
- Gherkin compliance validation
- AI-assisted remediation
- CP2 validation

**Output:** Validated Feature Package

## 2. Inputs

**Primary input:** `validated-requirement-model.json`

**Produced by:** Requirement Intelligence Layer

**Contains:**

```json
{
  "feature": "Customer Login",
  "functionalAcceptanceCriteria": [],
  "securityAcceptanceCriteria": [],
  "qualityAcceptanceCriteria": [],
  "riskBasedScenarios": []
}
```

## 3. Outputs

| | Work product |
|---|---|
| Work Product 1 | Generated Feature Files |
| Work Product 2 | Feature Governance Report |
| Work Product 3 | CP2 Validation Report |
| Final Work Product | Validated Feature Package |

## 4. High Level Flow

Validated Requirement Model → Feature Generation Engine (drawing on the Prompt Library of
existing Copilot assets) → Generated Feature Files → Feature Governance Engine → Gherkin
Lint → Compliance Metrics Engine → AI Remediation Engine → CP2 Validation → Validated
Feature Package.

## 5. Key Design Principle

**Prompt-as-Asset Architecture.** Do not hardcode generation logic. Treat prompts as
reusable enterprise assets.

This allows:

- Prompt Versioning
- Prompt Governance
- Prompt Reuse
- Prompt Evolution

Prompt Registry → Feature Generation Engine.

## 6. Components

| Component | Purpose |
|---|---|
| Prompt Registry | Stores approved prompt templates |
| Feature Generation Engine | Creates feature files |
| Scenario Generation Engine | Generates scenarios |
| Scenario Outline Generator | Generates data-driven scenarios |
| Test Data Generator | Creates example datasets |
| Feature Writer | Writes feature files |
| Feature Governance Engine | Validates generated features |
| Gherkin Lint Adapter | Executes lint validation |
| Compliance Metrics Engine | Calculates governance metrics |
| AI Remediation Engine | Fixes violations |
| CP2 Validation Engine | Determines feature readiness |

## 7. Prompt Registry

Reuse existing prompt templates.

Examples: `generate-feature.md`, `update-feature.md`, `generate-test-data.md`

Registry:

```json
{
  "featureGenerationPrompt": "generate-feature.md",
  "scenarioOutlinePrompt": "generate-scenario-outline.md",
  "testDataPrompt": "generate-test-data.md",
  "validationPrompt": "validate-feature.md"
}
```

## 8. Feature Generation Engine

**Sample input:**

```json
{
  "feature": "Customer Login",
  "functionalAcceptanceCriteria": [],
  "securityAcceptanceCriteria": [],
  "qualityAcceptanceCriteria": []
}
```

**Process:**

1. Select prompt from registry
2. Inject requirement model
3. Call Azure OpenAI
4. Generate feature content

**Sample output:**

```gherkin
@authentication
Feature: Customer Login

Scenario: Successful Login
Given user is on login page
When user enters valid credentials
Then user should be logged in
```

## 9. Scenario Generation Rules

Generate:

- **Positive scenarios** — happy path
- **Negative scenarios** — invalid credentials, locked user, missing data
- **Security scenarios**, derived from OWASP ZAP — brute force attempts, session timeout,
  unauthorized access
- **Quality scenarios**, derived from Sonar findings — input validation

## 10. Scenario Outline Generator

**Input:** Acceptance Criteria

**Output:** `Scenario Outline:` with an `Examples:` table, e.g. columns `| username | password |`

## 11. Test Data Generator

**Input:** Requirement Model

**Output:**

```json
{
  "positiveData": [],
  "negativeData": [],
  "boundaryData": []
}
```

## 12. Feature Governance Engine

Reuses existing POC components.

| Validation | Tool |
|---|---|
| Feature Naming | Gherkin Lint |
| Scenario Naming | Gherkin Lint |
| Duplicate Scenarios | Gherkin Lint |
| Empty Scenarios | Gherkin Lint |
| Missing Tags | Gherkin Lint |
| Scenario Length | Gherkin Lint |
| Formatting | Gherkin Lint |

## 13. Compliance Metrics Engine

Reuse metrics already implemented:

- Lint Violations Count
- % Compliant Feature Files
- Feature Naming Violations
- Scenario Naming Violations
- Missing Steps / Empty Scenarios
- Tagging Compliance %
- Tagging Violations
- Duplicate Scenarios
- Formatting Violations
- Structure Violations
- Total Scenarios
- Avg Scenario Length
- Max Scenario Length
- Scenario Size Violations

These become part of the Feature Governance Report.

## 14. AI Remediation Engine

**Purpose:** Automatically fix violations.

**Input:**

```json
{
  "rule": "no-dupe-scenario-names",
  "message": "Duplicate scenario detected"
}
```

**Process:** Violation → Remediation Prompt → Azure OpenAI → Updated Feature File

**Output:** Remediated Feature

## 15. CP2 Validation Rules

| Rule | Pass Criteria |
|---|---|
| Feature Generated | Yes |
| Lint Violations | 0 Critical |
| Naming Compliance | >95% |
| Tagging Compliance | >95% |
| Duplicate Scenarios | 0 |
| Empty Scenarios | 0 |
| Scenario Size Violations | Within threshold |
| Acceptance Criteria Coverage | 100% |

## 16. CP2 Validation Report

```json
{
  "controlPoint": "CP2",
  "status": "PASSED",
  "summary": {
    "featuresGenerated": 5,
    "totalScenarios": 25,
    "lintViolations": 0,
    "taggingCompliance": "100%",
    "acceptanceCriteriaCoverage": "100%"
  },
  "humanReviewRequired": false
}
```

## 17. Human-in-the-Loop Conditions

Requires review when:

- Feature generation confidence low
- Acceptance criteria not mapped
- Lint violations persist after remediation
- Security scenarios missing
- Generated feature changes business intent
- CP2 validation fails

## 18. Output Package

> Transcribed from an image on the source slide.

```
validated-feature-package/
│
├── features/
│   ├── login.feature
│   ├── checkout.feature
│
├── governance/
│   ├── gherkin-lint-report.html
│   ├── feature-governance-report.json
│
├── validation/
│   └── cp2-validation-report.json
│
└── metadata/
    └── traceability.json
```

## 19. Integration with Next Layer

**Output:** Validated Feature Package

**Consumed by:** Automation Engineering Layer

The Automation Engineering Layer will use these feature files together with the existing
Copilot prompt library to generate Step Definitions, Page Objects, and Automation Code —
which is why preserving traceability from requirements → features is critical in this layer.

## 20. Implementation Task Breakdown

| Task | Sub-task | Output |
|---|---|---|
| Create Prompt Registry | Register approved prompt templates (generate-feature, update-feature, generate-test-data, generate-scenario-outline, validate-feature) | `prompt-registry.json` |
| Build Prompt Loader | Load prompts dynamically from registry | Prompt loading framework |
| Create Feature Generation Service | Read validated requirement model and invoke feature generation prompt | Generated feature content |
| Create Scenario Generation Service | Generate positive, negative, security, and quality scenarios | Scenario set |
| Create Scenario Outline Generator | Generate data-driven scenarios and examples tables | Scenario outlines |
| Create Test Data Generator | Generate positive, negative, boundary test data | Test data package |
| Create Feature Writer | Persist generated features to feature files | `*.feature` files |
| Create Traceability Generator | Map requirements → acceptance criteria → scenarios | `traceability.json` |
| Build Governance Engine | Orchestrate feature validation workflow | Governance workflow |
| Integrate Gherkin Lint | Execute lint checks against generated features | `gherkin-lint-report.json` |
| Integrate Existing HTML Report Generator | Reuse current gherkin HTML report solution | `gherkin-lint-report.html` |
| Integrate Existing Metrics Engine | Reuse current governance metrics calculations | Feature governance metrics |
| Build Compliance Metrics Aggregator | Consolidate lint and governance metrics | `feature-governance-report.json` |
| Build AI Remediation Service | Invoke remediation prompt for lint violations | Remediated feature files |
| Create Remediation Workflow | Re-run validation after remediation | Remediation cycle |
| Build CP2 Validation Engine | Execute CP2 rules and readiness checks | `cp2-validation-report.json` |
| Create Feature Package Builder | Bundle features, reports, validation results, and traceability | Validated Feature Package |
| Create Output Writer | Persist all work products | Output package |
| Create Unit Tests | Test prompt loader, generators, validators, remediation flow | Test results |
| Create Sample Requirement Models | Build representative inputs from CP1 outputs | Demo data |
| End-to-End Dry Run | Execute full CP1 → CP2 workflow | Validated Feature Package |

## 21. Definition of Done

The Feature Engineering Layer is complete when:

- Prompt Registry is operational
- Validated Requirement Model can generate feature files
- Positive, negative, security, and quality scenarios are generated
- Scenario outlines and test data are generated
- Requirement-to-scenario traceability is maintained
- Generated features pass Gherkin governance checks
- Compliance metrics are generated
- AI remediation successfully fixes common violations
- CP2 validation report is generated
- Validated Feature Package is produced
- Output can be consumed directly by the Automation Engineering Layer

## 22. Estimated Effort Summary

| Activity | Effort |
|---|---|
| Prompt Registry & Prompt Loader | 2 Days |
| Feature Generation Services | 3 Days |
| Scenario & Test Data Generation | 2 Days |
| Feature Writer & Traceability | 2 Days |
| Governance Integration (Reuse Existing Assets) | 2 Days |
| AI Remediation | 3 Days |
| CP2 Validation Engine | 2 Days |
| Output Packaging | 1 Day |
| Unit Testing | 2 Days |
| End-to-End Dry Run | 1 Day |

> Estimate predates the review. It assumes the Prompt Registry is built new (it exists) and
> excludes the Gherkin linter port, the conversion of agentic Copilot prompts into API
> prompts, run-state integration, and the step vocabulary mechanism.
