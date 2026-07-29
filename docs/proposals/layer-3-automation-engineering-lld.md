# Layer 3 — Automation Engineering Layer (LLD)

| Field | Value |
|---|---|
| Status | Submitted — under review. **Not approved.** |
| Type | Low-Level Design |
| Layer | Layer 3 — Automation Engineering |
| Source artifact | `Automation_Engineering_Layer.pptx` (26 slides), authored outside this repository; committed alongside this transcription as `layer-3-automation-engineering-lld.pptx` |
| Transcribed | 2026-07-29 |
| Governs | Nothing yet. Informs a future Layer 3 architecture-freeze ADR. |

---

## Reviewer's note — superseded, locked, and pending items

This document is committed as the **record of what was proposed**, not as approved design.
The body below is a faithful transcription and has **not** been edited to reflect later
decisions. Three classes of finding are recorded here: items already superseded or corrected
by existing ADRs (do not implement from these), decisions locked by architecture review ahead
of a formal freeze ADR, and items the deck leaves underspecified. Do not implement from this
document without checking this note first.

### Superseded / corrected

| Item | Section | Proposed here | Current position |
|---|---|---|---|
| S1 | §3, §12, §20 (slides 3, 12, 20) | "Test Generator" emits `@RunWith(Cucumber.class)` JUnit4 runner classes per feature | **SUPERSEDED.** ADR-0041 D3 prohibits `@RunWith`/`@CucumberOptions`; the tracked `test-suite-baseline/RunCucumberTest.java` (`@Suite` + `@IncludeEngines`) already executes every feature. Layer 3 does **not** generate test/runner classes — the Test Generator component is **deleted** as a code generator. Feature/tag selection at execution time is a Layer 5 configuration concern, not generated Java. |
| S2 | §23 (slide 23) | Implementation Task Breakdown (Prompt Registry, Feature Generation Service, Gherkin Lint, CP2 Validation Engine, AI Remediation Service, ...) | **SUPERSEDED** — this is Layer 2's own task breakdown (`docs/proposals/layer-2-feature-engineering-lld.md` §20) pasted wholesale; every task named belongs to Feature Engineering, not Automation Engineering. Ignore slide 23 as an implementation guide for this layer; the Layer-3-appropriate breakdown is slide 26 (§26 below). |
| S7 | §18, §21, §22 (slides 18, 21, 22) | CP5/CP6 named as this layer's immediate downstream consumer | **OUT OF SCOPE** for Layer 3's own freeze. CP5 (suite-level integration governance) is Layer 4 (ADR-0040); CP6/execution is Layer 5. Layer 3's scope ends at CP3/CP4 and the Validated Automation Package hand-off — it does not define downstream layers' control points. |

### Locked decisions (architecture review, pre-freeze)

- **Q1 — Test Generator.** Deleted as a code-generating component (see S1 above).
- **Q2 — Asset catalog model.** Model B: a **persistent store**, RECONCILED from a baseline
  scan of the tracked codebase at the start of each run — not rebuilt from scratch every run,
  and not trusted blindly from a prior run either. Every semantic match the catalog
  participates in is **content-hash-validated** against the actual code before it is trusted
  (see Q2-safety, below).
- **Q2 — matching strategy.** Reuse discovery is **semantic**, not exact-string. This is the
  deck's own stated differentiator (slide 5, "Reuse First, Generate Later") and matches the
  intent already implied by slides 7, 8, and 19 — a catalog of *supported actions* (not literal
  strings), a match against free natural-language step text, and a "reuse confidence low"
  human-review trigger, none of which make sense for exact-string matching.
- **Q2 — reuse-safety model.** A semantic reuse binding is trusted only when **all three** of
  the following hold:
  1. Match confidence ≥ a set threshold, else **escalate to human review** (slide 19's own
     condition).
  2. **Content-hash validation** that the catalogued asset's code is still current — catches
     catalog staleness.
  3. **Signature/parameter fit** between the step definition and the Gherkin step it is bound
     to — catches gross mis-binding.

  Stated plainly, because it is the reason all three are required and not just one: a wrong
  semantic binding produces a test that runs **green while testing the wrong behavior** —
  invisible to every deterministic downstream gate (CP3's coverage counts, CP4's locator
  health, SonarQube's code quality). Content-hash catches staleness; signature-fit catches
  gross errors; the confidence gate plus human-in-the-loop catches the remaining case — a
  plausible-but-wrong match that is neither stale nor structurally mismatched. This is the one
  Layer 3 failure mode nothing downstream detects, which is why all three checks are locked as
  required, not optional hardening.
- **Q3 — CP4 scope.** STATIC-only locator health: uniqueness, anti-pattern detection,
  dynamic-XPath thresholds, duplicate detection, and well-formedness, computed from
  page-object *source* alone. Live-DOM validation ("does this locator match a real element on
  a running page") is Layer 5's job, at runtime, against a real SUT — Layer 3 has **no
  running-browser or SUT dependency** at all, and CP4 must not acquire one.
- **Q4 — CP3 gating vs. reporting.** Reuse % is **reported**, never gated. CP3 gates
  deterministically on: step coverage = 100%, scenario coverage = 100%, zero unmapped steps,
  zero duplicate steps — criteria that are always meaningful regardless of catalog maturity.
  Reuse % is a governance metric that matures as the catalog grows across runs; gating on it
  would fail the bootstrap run outright (an empty catalog reuses 0%, *correctly*, not
  incorrectly). This mirrors ADR-0043 D5's own resolution, which replaced the Layer 2 LLD's
  soft ">95%" thresholds with exact floors.

### Underspecified / TBD (resolve at freeze or implementation)

| Item | Slide(s) | Open question |
|---|---|---|
| S3 | §2, §11 (slides 2, 11) — test data | Layer 3 generates Java test-data classes **from** Layer 2's emitted test-data *specification* (ADR-0043 D7) — it does not re-derive test data itself. The converted `generate-test-data` prompt is already registered and waiting; its output shape (`com.automation.utils`, `Constants`/`ConfigReader`/`DataProvider`) must reconcile with the walking skeleton's existing `env.*`/`data.*` config split. TBD: the exact specification → Java mapping. |
| S4 | §18 (slide 18) — SonarQube/CP3 | The `customqa:*` SonarQube profile is a Layer 3/CP-adjacent asset; running Sonar against generated Java is a runtime dependency (a live JVM + scanner) the deck never costs or schedules. TBD: is SonarQube part of CP3, or a separate gate? ADR-0043's own CP model assigned SonarQube-on-generated-Java to CP3 — confirm this alignment at freeze, since slide 15's CP3 rule table names only coverage/reuse/duplicate criteria while slide 18 treats Sonar as a distinct step feeding "CP5" (see S7 above, which places CP5 out of Layer 3's scope entirely). |
| S-new | (not in the deck) — semantic-match implementation | Embeddings vs. a per-step LLM call, for the MATCH step specifically (not the GENERATE step). Embeddings are cheaper, batchable, and cacheable, and reduce the free-tier 429 exposure the Layer 2 live measurement already exposed (`DEMO_RUNBOOK.md` Stage 17). LLM calls should be reserved for GENERATING genuinely-missing assets, never for matching against the catalog. TBD: resolve at implementation; lean embeddings-for-match. |
| S6 | §7 (slide 7) — asset catalog | The persistent catalog's storage location relative to the tracked `test-suite-baseline/` and the untracked per-run workspace — TBD at freeze. |
| — | §5 (slide 5) — differentiator framing | "Reuse First, Generate Later" is a valid differentiator, but reuse is 0% until the catalog is populated across multiple runs. Frame reuse as a metric that *matures*, not a launch-day claim — the bootstrap run's own 0% reuse is the correct, expected number (see Q4 above), not a failure to demo around. |

**Also note, outside the table above:** slide 26's effort estimate (28 PD) includes "Test
Generator 3 PD," which the S1 deletion removes — the real estimate is lower than 28 PD.

---

## 1. Purpose

The Automation Engineering Layer transforms validated feature files into governed and
executable automation assets.

**Responsibilities:**

- Discover reusable automation assets
- Generate missing Step Definitions
- Generate Page Objects
- Generate Test Classes
- Generate Utility Classes
- Generate Test Data Components
- Validate generated assets
- Measure automation coverage
- Perform code quality checks
- Generate CP3 & CP4 validation reports

**Output:** Validated Automation Package

## 2. Inputs

**Primary Input:** Validated Feature Package

**Produced by:** Feature Engineering Layer

**Contains:**

- Feature Files
- Governance Reports
- Traceability Reports
- CP2 Validation Report

## 3. Outputs

| | Work product |
|---|---|
| Work Product 1 | Step Definitions |
| Work Product 2 | Page Objects |
| Work Product 3 | Automation Scripts |
| Work Product 4 | Automation Coverage Report |
| Work Product 5 | CP3 Validation Report |
| Work Product 6 | CP4 Validation Report |
| Final Output | Validated Automation Package |

## 4. High Level Flow

Validated Feature Package → Automation Reuse Engine (Search Existing Assets) → Automation
Generation Engine → Step Definitions / Page Objects / Tests / Utilities → CP3 Validation
(Coverage & Reuse) → CP4 Validation (Locator Health) → SonarQube Governance → Validated
Automation Package.

> Reconstructed from the slide's flowchart boxes and connector directions (arrow rotations),
> not free text on the slide — the slide itself carries no prose description of the flow.

## 5. Key Design Principle

**Reuse First, Generate Later.**

The biggest mistake many AI automation platforms make: Generate Everything.

The architecture should: Search Existing Assets → Reuse → Generate Only Missing Assets.

This is a major differentiator from generic AI test generation solutions.

## 6. Components

| Component | Purpose |
|---|---|
| Automation Asset Catalog | Inventory of reusable assets |
| Reuse Discovery Engine | Searches existing assets |
| Copilot Prompt Registry | Stores approved generation prompts |
| Step Definition Generator | Generates missing steps |
| Page Object Generator | Generates page classes |
| Test Generator | Generates automation scripts |
| Utility Generator | Generates helper classes |
| Coverage Analyzer | Measures feature-to-code coverage |
| Locator Validator | Validates generated locators |
| CP3 Validation Engine | Coverage & reuse validation |
| CP4 Validation Engine | Locator health validation |
| SonarQube Adapter | Code quality governance |
| Automation Package Builder | Creates deployable automation package |

## 7. Automation Asset Catalog

Maintain inventory of reusable assets.

**Example:**

```json
{
  "stepDefinitions": [
    {
      "name": "LoginSteps",
      "supportedActions": [
        "login",
        "logout",
        "authentication"
      ]
    }
  ]
}
```

## 8. Reuse Discovery Engine

**Input:**

```
When user logs in
```

**Searches:**

- Existing Step Definitions
- Existing Pages
- Existing Utilities

**Output:**

```json
{
  "matchFound": true,
  "asset": "LoginSteps"
}
```

## 9. Copilot Prompt Registry

Reuse existing POC prompts.

**Examples:**

- Generate Step Definitions
- Generate Page Objects
- Generate Selenium Test
- Generate Utility Methods

These become governed enterprise prompts.

## 10. Step Definition Generator

**Input:**

```
When user submits valid credentials
```

**Output:**

```java
@When("user submits valid credentials")
public void submitCredentials() {
    loginPage.login(username,password);
}
```

## 11. Page Object Generator

**Input:**

```
Given user navigates to login page
```

**Output:**

```java
public class LoginPage {
   private By username;
   private By password;
}
```

## 12. Test Generator

**Input:**

```
Feature File
  Step Definitions
  Page Objects
```

**Output:**

```java
@RunWith(Cucumber.class)
  public class LoginTest {
    }
```

## 13. Utility Generator

**Generates:**

- WaitUtils
- DriverUtils
- TestDataUtils
- APIUtils

Only when missing.

## 14. Automation Coverage Analyzer

**Measures:**

- Feature Coverage
- Scenario Coverage
- Step Coverage
- Reuse %
- Generated %

**Example:**

```json
{
  "totalSteps": 100,
  "reusedSteps": 80,
  "generatedSteps": 20,
  "reusePercentage": 80
}
```

## 15. CP3 Validation Engine

Validate automation coverage and reuse.

| Rule | Pass Criteria |
|---|---|
| Feature Coverage | 100% |
| Scenario Coverage | 100% |
| Step Coverage | 100% |
| Reuse Percentage | >70% |
| Duplicate Steps | 0 |
| Unmapped Steps | 0 |

**Output**

```json
{
 "controlPoint":"CP3",
 "status":"PASSED"
}
```

## 16. Locator Validator

**Validates:**

- XPath Stability
- CSS Stability
- ID Availability
- Locator Uniqueness

**Sources:**

- Generated Page Objects

## 17. CP4 Validation Engine

**Purpose:** Validate locator health.

| Rule | Pass Criteria |
|---|---|
| Broken Locators | 0 |
| Duplicate Locators | 0 |
| Dynamic XPath Count | Threshold |
| Locator Uniqueness | 100% |

**Output**

```json
{
 "controlPoint":"CP4",
 "status":"PASSED"
}
```

## 18. SonarQube Governance

Reuse existing POC setup.

**Checks:**

- Code Smells
- Maintainability
- Duplication
- Coverage

**Output:** `sonar-report.json`

This becomes the bridge into CP5.

## 19. Human-in-the-Loop Conditions

Review required when:

- Reuse confidence low
- Step mapping ambiguous
- Locator generation fails
- Coverage below threshold
- Sonar quality gate fails

## 20. Work Product

| Work Product | Produced By |
|---|---|
| Step Definitions | Step Generator |
| Page Objects | Page Generator |
| Utilities | Utility Generator |
| Automation Scripts | Test Generator |
| Coverage Report | Coverage Analyzer |
| CP3 Report | CP3 Validation |
| CP4 Report | CP4 Validation |
| Sonar Report | SonarQube |
| Validated Automation Package | Package Builder |

## 21. Integration with Next Layer

**Output:** Validated Automation Package

**Containing:**

- Step Definitions
- Page Objects
- Automation Scripts
- Utilities
- Automation Coverage Report
- CP3 Validation Report
- CP4 Validation Report
- Sonar Analysis Report
- Traceability Report

**Consumed by:** Execution & Quality Governance Layer (CP5 + CP6)

## 22. Handover Artifacts

| Artifact | Consumed By |
|---|---|
| Step Definitions | Jenkins Execution Pipeline |
| Page Objects | Selenium Test Execution |
| Automation Scripts | Jenkins |
| Utilities | Test Runtime |
| CP3 Validation Report | CP5 Governance |
| CP4 Validation Report | CP5 Governance |
| Sonar Report | CP5 Quality Gate |
| Coverage Report | Governance Dashboard |
| Traceability Report | Audit & Reporting |

## 23. Implementation Task Breakdown

> See the Reviewer's note (S2, above): this table is Layer 2's own task breakdown, pasted
> wholesale. It is transcribed verbatim below as the record of what the slide actually says —
> not as a Layer 3 implementation guide.

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

## 24. Definition of Done

The Automation Engineering Layer is considered complete when:

**Reuse Discovery**

- Asset catalog can be loaded successfully.
- Existing step definitions can be discovered.
- Existing page objects can be discovered.
- Existing utilities can be discovered.
- Reuse confidence scores are generated.

**Automation Generation**

- Missing step definitions are generated.
- Missing page objects are generated.
- Missing automation scripts are generated.
- Missing utilities are generated.
- Traceability is maintained from feature → automation asset.

**Governance**

- Coverage report is generated.
- Feature coverage = 100%.
- Scenario coverage = 100%.
- Step coverage = 100%.
- Reuse percentage is reported.
- CP3 validation report is generated.

**Locator Validation**

- Locator validation executes successfully.
- Broken locators are identified.
- Duplicate locators are identified.
- CP4 validation report is generated.

## 25. Definition of Done (continued)

**Sonar Governance**

- SonarQube analysis executes successfully.
- Quality Gate result is available.
- Code smells, maintainability, and duplication metrics are generated.

**Packaging**

- Validated Automation Package is generated.
- Reports are generated.
- Output is consumable by the Execution & Quality Governance Layer.

**Final Acceptance**

- CP3 status = PASSED
- CP4 status = PASSED
- Sonar Quality Gate = PASSED
- Automation Package successfully handed off to CP5/CP6 layer

## 26. Estimated Effort Summary

| Workstream | Effort |
|---|---|
| Asset Catalog & Reuse Engine | 4 PD |
| Prompt Registry Integration | 1 PD |
| Step Definition Generator | 3 PD |
| Page Object Generator | 3 PD |
| Test Generator | 3 PD |
| Utility Generator | 1 PD |
| Coverage Analyzer | 3 PD |
| CP3 Validation | 2 PD |
| Locator Validator & CP4 | 3 PD |
| SonarQube Governance | 1 PD |
| Outputs & Testing | 4 PD |
| **Total** | **28 PD** |

> Estimate predates the review. It includes "Test Generator 3 PD," which the S1 deletion
> (Reviewer's note, above) removes — the real estimate is lower than 28 PD. It also does not
> cost the semantic-match implementation question (S-new) or the SonarQube/CP3 runtime
> dependency (S4), both still open at transcription time.
