# ADR-0037 — Generated Test Suite Target and SUT Binding

- **Status:** Accepted
- **Date:** 2026-07-24
- **Supersedes:** nothing. **Amends:** nothing.
- **Governing design:** none. Evidentiary basis: `docs/audit/CODEBASE_AUDIT_2026-07-24.md` §2.2 (real SonarQube findings, including `customqa:*` rules, evaluated against a Java target `Automation-POC:src/test/java/com/automation/pages/badexamples/BadLoginPage.java`, seen in `output/latest/prompt.txt`), and `requirement_intelligence/models/source_artifact.py` (re-read for this ADR to confirm the exact field names available for SUT-scoping, D3).
- **Depends on:** ADR-0031 (Authoritative Layer Model — Layers 3/4/5/6 this generated suite serves); ADR-0034 (TestableRequirement Contract — the requirement/acceptance-criterion identity a generated scenario traces back to).
- **Runtime status:** Not applicable. This is a **pure architecture freeze** for a suite that does not exist yet — no repository structure, build file, or code is created by this ADR.

## Problem

The platform has never generated a feature file, a step definition, a page object, or test data (`docs/audit/CODEBASE_AUDIT_2026-07-24.md` §2.5/§2.6). Before Layers 2 and 3 (ADR-0031) can be designed, three questions that shape everything downstream must be answered: where does the generated suite live, what technology does it target, and — critically — where does a test's knowledge of *what system it runs against* come from. The third question has a concrete failure mode if left unanswered: a generated test's target environment could end up derived, even partially, from requirement-source content (a JIRA field), which would let an edit to a requirement ticket silently repoint what a test executes against — a reproducibility and safety hazard distinct from anything Layer 1 has had to consider, because Layer 1 never executes anything.

## Decision

### The generated suite lives in this repository

Target language: **Java**. Test framework: **Cucumber BDD**. Generated artifact types: `.feature` files, Java step definitions, Java page objects, Java test data classes.

### Two-tier split, locked

- **A TRACKED baseline module** — committed to this repository, holding: build configuration, framework code (drivers, base classes, utilities), runner configuration, **base page objects**, and the custom SonarQube quality profile — the `customqa:*` rule set already evidenced in this repository's own executed runs (`customqa:direct-webdriver-action`, `customqa:long-method`, per `docs/audit/CODEBASE_AUDIT_2026-07-24.md` §2.2). This profile is recorded here as **a Layer 4 (Suite Quality Governance) asset**: it is the rule set Layer 4 evaluates generated code against, so it belongs in the tracked baseline, versioned like any other framework code — not regenerated per run.
- **An UNTRACKED per-run workspace**, where generated assets (features, step definitions, page objects, test data for one run) land. **Self-healing (Layer 6) operates on the workspace, never on tracked baseline source.** A healing action can rewrite anything the workspace contains; it can never modify the tracked baseline directly.
- **Promotion from workspace to baseline is an explicit, reviewed step — never automatic.** No pipeline stage moves a workspace asset into the tracked baseline without a human or a separately-governed review gate approving it first.

### SUT binding boundary, locked

- **Environment binding — base URL, environment name, credentials — comes only from config/env files.** The same discipline `docs/audit/CODEBASE_AUDIT_2026-07-24.md` §3.5 already documents for the platform's own connector secrets (`resolve_secret_field`, env-var-name indirection, never a literal in tracked config) extends here: a generated test's target environment is resolved at execution time from configuration the requirement source never touches.
- **The requirement source contributes only *what* is under test** — never *where* it runs — via the existing, verified `SourceArtifact` fields `component` (owning component/module, `requirement_intelligence/models/source_artifact.py:102-105`) and `location` (a location pointer — "file path:line for SAST/DAST findings," `source_artifact.py:106-109`, and by the same pattern usable to carry an endpoint/route identifier for a functional requirement). No field named `endpoint` exists on `SourceArtifact` today; this ADR grounds itself in the two fields that actually exist rather than a name that does not (D3).

## D1 — Why Java and Cucumber, and why in this repository

The platform's own executed evidence already targets a Java, page-object-shaped codebase under SonarQube's `customqa:*` profile (`docs/audit/CODEBASE_AUDIT_2026-07-24.md` §2.2) — the platform is already being measured against exactly this stack in its live Layer 1 runs, via the sibling `Automation-POC` project the `customqa:*` findings are drawn from. Choosing a different language or framework for the generated suite would mean the platform's own quality-governance evidence (SonarQube findings against Java page objects) has nothing to gate. Housing the suite in this repository, rather than a separate one, keeps Layer 1 through Layer 6 inside the single deployable unit ADR-0001 already established for the platform.

## D2 — Why tracked/untracked, and why promotion is never automatic

Self-healing (Layer 6) is, by definition, code performing unsupervised edits to test code. Letting it edit tracked source directly would mean an autonomous process can silently rewrite the repository's own committed history of what the suite looks like — exactly the failure mode ADR-0031's Layer 6 boundary ("auditable, governed, reversible," inherited from ADR-0020 §Layer 6) exists to prevent. Splitting workspace (healable, untracked, disposable) from baseline (stable, tracked, framework-level) means a healing action's blast radius is structurally bounded to one run's disposable output, never the framework every run depends on. Making promotion an explicit, reviewed step — rather than, say, auto-promoting a workspace asset once a run passes — keeps a human (or a separately governed gate) as the actual decision-maker for what becomes permanent, which is the same posture ADR-0032's freeze-lifting procedure takes toward Layer 1's own growth: deliberate, visible acts, not automatic accretion.

## D3 — Why the SUT binding boundary is locked this precisely, and why `SourceArtifact`'s real fields are cited instead of "endpoint"

A JIRA ticket is content a business stakeholder edits routinely, for reasons entirely unrelated to test infrastructure. If a generated test's target environment could be derived, even partially, from a JIRA field, then editing a ticket's description could — invisibly to whoever runs the suite — repoint what URL, environment, or credential set a test executes against. That breaks two things at once: reproducibility (the same `run_id`'s test should always target what it targeted originally, per ADR-0036) and safety (a compromised or careless requirement-source edit should never be able to redirect test execution). Locking environment binding to config/env files only, and confirming — by re-reading `source_artifact.py` directly rather than trusting the phrase "component, endpoint" at face value — that `SourceArtifact` actually offers `component` and `location`, not a field called `endpoint`, keeps this boundary grounded in the real contract rather than a plausible-sounding name that does not exist in code. Using the wrong field name in an architecture document would be exactly the kind of uncorrected error this task's verification rule exists to prevent.

## D4 — Why the concrete Java stack is TBD, and why it is mined, not chosen fresh

Choosing a build tool, Java version, Cucumber-JVM version, test runner, browser automation library, assertion library, and reporter from a blank slate risks re-deriving decisions a working, real project has already made. The sibling `Automation-POC` repository is the SonarQube-scanned source of this platform's own live `customqa:*` evidence (D1) — it is a real, existing Java/Maven project (`pom.xml` present), already carrying a `sonar-project.properties` and Gherkin-lint tooling, i.e. already operating in the same problem space this ADR's suite must occupy. Mining its actual stack choices, rather than picking fresh ones, is both less work and more likely to produce a stack this platform's existing SonarQube integration and quality profile already know how to evaluate.

---

## TBD — deferred to implementation

- **The concrete Java stack**: build tool (Maven vs. Gradle), Java version, Cucumber-JVM version, test runner, browser automation library, assertion library, reporter. **To be mined from the `Automation-POC` repository's actual choices, not chosen fresh** (D4) — resolved when Layer 3's architecture-freeze ADR is written.

  **Resolution note (additive only, ADR-0041).** This TBD is resolved by ADR-0041 (Java Stack for the Generated Test Suite): Maven, Java 21, JUnit/Cucumber BOM-managed versions, JUnit Platform Suite runner (not JUnit 4), JUnit Jupiter–only assertions, Selenium 4.25.0 with Selenium Manager (no WebDriverManager), and the three-reporter (message/junit/html) split feeding Layer 6. See ADR-0041 for the full decision and its provenance against `docs/reference/automation-poc/pom.xml`. This ADR's remaining TBDs — the tracked baseline's exact repository path and the promotion review mechanism — are unaffected and remain open.
- The tracked baseline module's exact directory location within this repository.
- The exact promotion review mechanism (human approval, a governed gate, or both).
- The exact shape of the base page objects and framework code the tracked baseline holds on day one.

## Recommendations (permanent)

1. **Self-healing never writes to the tracked baseline.** Enforced structurally by the workspace/baseline split, not by convention alone, once implemented.
2. **No environment-binding value is ever sourced from `SourceArtifact` or any requirement-source field.** Config/env files are the only sanctioned source.
3. **The `customqa:*` SonarQube profile is versioned alongside the tracked baseline it governs**, never regenerated ad hoc per run.
4. **Promotion from workspace to baseline is never automated**, even after this ADR's TBD items are resolved, unless a future ADR explicitly revisits this decision.

## Ownership, scope, and governance

- **Owns:** the generated suite's language/framework choice, its repository location, the tracked/untracked split, promotion discipline, and the SUT binding boundary.
- **Does not own:** the concrete Java stack's specific tool versions (TBD, D4); `SourceArtifact`'s own field list (unchanged, owned by CAP-002 Mappers); Layer 6's own architecture beyond the workspace-only constraint this ADR imposes on it.
- **Governance:** Accepted as an architecture freeze. No suite exists until Layer 3's future architecture-freeze ADR builds against this ADR's locked boundaries.
