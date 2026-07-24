# Architecture Baseline v2

| Attribute | Value |
| --- | --- |
| Document type | Architecture Baseline Index |
| Status | Living document — canonical answer to "what is locked" |
| Scope | Every architectural decision recorded 2026-07-24 in ADR-0031 through ADR-0039, plus the ADR-0020 status change and the ACT-001 closure those decisions produced |
| Source of truth | Each row's own ADR — this page is an index, not a governing document in its own right |
| Sibling documents | [Platform Capability Matrix](../governance/platform-capability-matrix.md) · [Architecture Freeze Index](../governance/architecture-freeze-index.md) · [Architecture Action Register](./architecture-action-register.md) · [Codebase Audit 2026-07-24](../audit/CODEBASE_AUDIT_2026-07-24.md) |

> This page **indexes** locked decisions; it does not **make** them. Each row's ADR is
> authoritative for its own decision. When a decision changes, its own ADR changes (or
> a new ADR supersedes it) and this index is updated to match — this index never drives
> a decision on its own.

---

## 1. Purpose

This is the single page a reader consults to answer "what is locked, and what is still open." It was created because nine architectural decisions were recorded in one sitting (2026-07-24), each with its own TBD items — without one index, a reader would have to open all nine ADRs to know what remains undecided.

## 2. The baseline

| Decision | ADR | Status | Summary | TBD it carries |
| --- | --- | --- | --- | --- |
| Authoritative Layer Model | [ADR-0031](../adr/0031-authoritative-layer-model.md) | Accepted | Locks the 7-layer model (L1 Requirement Intelligence → L2 Feature Engineering → L3 Automation Engineering → L4 Suite Quality Governance → L5 Test Execution → L6 Failure Intelligence & Self-Healing → L7 Governance Dashboard), sourced from JIRA/SonarQube/ZAP. Fully supersedes ADR-0020; ADR-0020's Continuous Learning/Prediction & Insights/Optimization/Autonomous Engineering/Organizational Intelligence layers are redesignated Layer 1 sub-capabilities — nothing deleted. | ADR-0020's Layer 2.5 (Executable Specification Engineering, CAP-087) is **not** redesignated by this decision — its placement is explicitly unresolved (ADR-0031 §D4). |
| Layer 1 Capability Freeze | [ADR-0032](../adr/0032-layer-1-capability-freeze.md) | Accepted | Freezes Layer 1 (incl. its redesignated sub-capabilities) at its current baseline — no new Layer 1 CAP number without a lifting ADR. Five carve-outs permitted: emitting `TestableRequirement`, integrating the run/stage state model, ADR-0033's package renames, bugfixes, tests. | None — the freeze and its lifting procedure are fully specified. |
| Naming Disambiguation and Package Renames | [ADR-0033](../adr/0033-naming-disambiguation-and-package-renames.md) | Accepted | Locks the mapping for the "Quality Governance" and "Execution" name collisions: `requirement_intelligence/quality_governance/` → `requirement_quality_governance/`; `requirement_intelligence/execution/` → `execution_package/`; top-level `quality_governance/` → `suite_quality_governance/`; top-level `execution/` → `test_execution/`. Artifact filenames unaffected. Accepted ADRs using old names are not edited. | The rename itself is not executed by this ADR — deferred to a future implementation task under ADR-0032 carve-out 3. |
| TestableRequirement — the Layer 1 → Layer 2 Contract | [ADR-0034](../adr/0034-testable-requirement-contract.md) | Accepted | `AnalysisResult` redesignated Layer-1-internal. `TestableRequirement`/`TestableRequirementSet` established as the sole frozen Layer 1 → Layer 2 contract: platform-assigned content-addressed `REQ-*` IDs with a `supersedes` lineage field, structured `AC-*` acceptance criteria (no free prose), a run-level `PASS`/`PASS_WITH_WARNINGS` gate (a `FAIL` run emits nothing), a `TestableRequirementSet` envelope with `contract_version`/`run_id`/provenance, and a versioned, schema-checked, compatibility-tested contract. | **Exact field list intentionally not specified** — deferred to Layer 2's own LLD (the only consumer). Also open: the hash algorithm, the same-logical-requirement detection mechanism for `supersedes`, the `AC-*` field list, `TestableRequirementSet` partitioning, the JSON Schema location, and whether `SourceRef` is salvaged from `canonical_requirement.py`. |
| Contract Consolidation and Dead Scaffolding Removal | [ADR-0035](../adr/0035-contract-consolidation-and-dead-scaffolding-removal.md) | Accepted | Records four items for future removal (not executed by this ADR): the unused `SourceConnector` Protocol in `shared/contracts/base.py` (`Schema` in the same file explicitly preserved); `canonical_requirement.py` (unused, `SourceRef` a salvage candidate); `requirement_package.py` (unused, replaced by ADR-0034); the declared-but-unimported `jira` SDK dependency (`requirements.txt:27`). | Whether `SourceRef` is salvaged into `TestableRequirement` before `canonical_requirement.py` is deleted — blocks that one removal item only. |
| Run and Stage State Model | [ADR-0036](../adr/0036-run-and-stage-state-model.md) | Accepted | `run_id` becomes the canonical run-directory identifier (`--execution-name` becomes an internal label). New `run_state.json` (additive to the unchanged `manifest.json`) tracks 19 stages (13 live Layer 1 stages + one reserved slot per Layer 2–7) through `PENDING`/`RUNNING`/`SUCCEEDED`/`FAILED`/`SKIPPED`. Resume from the first non-`SUCCEEDED` stage; stage inputs are artifact paths; stages must be idempotent; a lockfile prevents concurrent operation on one `run_id`. Filesystem only, no database. | `run_id` generation scheme; `run_state.json`'s exact schema; the lockfile's exact mechanism; whether Layer 7 (Governance Dashboard) genuinely participates as a per-run stage at all (ADR-0036 §D5 — structurally different from stages 1–18). |
| Generated Test Suite Target and SUT Binding | [ADR-0037](../adr/0037-generated-test-suite-target-and-sut-binding.md) | Accepted | Generated suite lives in this repository: Java + Cucumber BDD (`.feature`, step definitions, page objects, test data). Two-tier split locked: TRACKED baseline (build config, framework, base page objects, the versioned `customqa:*` SonarQube profile as a Layer 4 asset) vs. UNTRACKED per-run workspace (where generated assets land; Layer 6 self-healing operates here only). Promotion workspace → baseline is explicit and reviewed, never automatic. SUT environment binding (URL/env/credentials) comes only from config/env files; the requirement source contributes only `SourceArtifact.component`/`SourceArtifact.location` (not a field called "endpoint" — verified against the model, no such field exists). | The concrete Java stack (build tool, Java version, Cucumber-JVM version, runner, browser-automation lib, assertion lib, reporter) — to be mined from the sibling `Automation-POC` repository, not chosen fresh. Tracked baseline's exact repo path; exact promotion review mechanism. |
| Documentation Track Governance | [ADR-0038](../adr/0038-documentation-track-governance.md) | Accepted | Track A (`docs/adr/`, `docs/architecture/`, `docs/governance/`, `docs/proposals/`, `docs/reviews/`, `docs/releases/`) declared normative. Track B (`docs/product/`, `docs/handbook/`, `docs/standards/`) declared non-normative and frozen — kept, not maintained. Identifier collisions (`CAP-001` today) resolve by Track A precedence. Closes ACT-001 by precedence, not reconciliation (`docs/architecture/architecture-action-register.md` updated to Status: Closed, Verification Evidence: ADR-0038, in the same change). | None. |
| Execution Backend and CI/CD | [ADR-0039](../adr/0039-execution-backend-and-cicd.md) | **PROPOSED — NOT ACCEPTED** | Proposes Jenkins as the CI/CD tool, serving two roles that must not be conflated: (1) platform CI (ruff/mypy/pytest), (2) an execution backend for Layer 5 + the Layer 4 SonarQube scan of generated code — behind an `ExecutionBackend` interface, with a local Maven/Gradle runner as the default implementation so Layer 5 doesn't hard-depend on Jenkins. Flags that a Jenkins-delegated stage is asynchronous, making Layer 5 the pipeline's first non-synchronous stage under ADR-0036. `run_state.json` stays authoritative over Jenkins build history. | **The entire ADR is unratified** — nothing may be built against it until Accepted. Specifically open even once accepted: the async stage-execution mechanism, left to Layer 5's own future LLD. |

## 3. Related state changes this baseline produced

- **`docs/adr/0020-platform-evolution-roadmap.md`** — status line changed from `Proposed` to `Superseded by ADR-0031`. Body untouched (historical record preserved per this batch's constraint against retro-editing Accepted/Proposed ADR bodies).
- **`docs/architecture/architecture-action-register.md`** — ACT-001 changed from `Identified` to `Closed`, Verification Evidence set to ADR-0038, register version bumped to 1.2, metrics updated (Open 8→7, Closed 0→1).

## 4. Open questions this baseline does not resolve (consolidated from the TBD column)

1. Where does ADR-0020's Layer 2.5 (Executable Specification Engineering, CAP-087, Proposed, no code) fit under ADR-0031's model? Left to Layer 2's own LLD.
2. What is `TestableRequirement`'s and `TestableRequirementSet`'s exact field list, hash algorithm, and `supersedes`-detection mechanism? Left to Layer 2's own LLD — Layer 2 is the only consumer and gets the vote (ADR-0034 §D5).
3. Is `canonical_requirement.py`'s `SourceRef` salvaged into `TestableRequirement`, or discarded with the rest of the file? Blocks one item of ADR-0035's removal list.
4. What is the exact `run_id` scheme, `run_state.json` schema, and lockfile mechanism? Deferred to ADR-0036's future implementation.
5. Does Layer 7 (Governance Dashboard) genuinely participate in the per-run stage sequence, or is it a separate cross-run service? Structurally unresolved by ADR-0036 §D5.
6. What is the concrete Java stack (build tool, Java version, Cucumber-JVM version, runner, browser-automation and assertion libraries, reporter) for the generated suite? To be mined from the sibling `Automation-POC` repository per ADR-0037 §D4, not chosen here.
7. Is ADR-0039 (Jenkins, execution backend) ratified? It is Proposed only — nothing in Layer 4 or Layer 5's future architecture may be built against it until it is Accepted.
8. How does an asynchronous, Jenkins-delegated Layer 5 stage fit the otherwise-synchronous stage model ADR-0036 defines? Explicitly left to Layer 5's own future architecture-freeze ADR (ADR-0039 §D2).

## 5. How to use this page

- To find out whether a specific decision is locked, find its row above and read its own ADR — this page's summary is not a substitute for the ADR.
- To find out what remains open before a given layer can be built, read that layer's TBD column entries and §4's consolidated list.
- This page is updated whenever a future ADR changes, supersedes, or resolves a TBD item recorded here — by adding a row (new decision), editing a row's Status/TBD columns (a decision changed or a TBD resolved), or adding a note under §3 (a non-ADR state change, like a status-line edit or a register update).
