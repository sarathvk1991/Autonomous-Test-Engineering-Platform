# ADR-0034 — TestableRequirement: the Layer 1 → Layer 2 Contract

- **Status:** Accepted
- **Date:** 2026-07-24
- **Supersedes:** nothing. **Amends:** nothing — `AnalysisResult` (`requirement_intelligence/analysis/analysis_models.py:26`) is not modified by this ADR; only its architectural role is redesignated (Decision).
- **Governing design:** none yet. This ADR freezes the contract's *properties*, not its full field list (see the TBD section) — a future Layer 2 LLD is the governing design for the field list, and must be built directly against this ADR without redesigning the six locked properties.
- **Depends on:** ADR-0031 (Authoritative Layer Model — defines Layer 1 and Layer 2); ADR-0032 (Layer 1 Capability Freeze — emitting this contract is its carve-out 1); ADR-0033 (Naming Disambiguation — this ADR uses `Requirement Quality Governance`, the renamed `requirement_intelligence/requirement_quality_governance/`); ADR-0017 (Quality Governance Framework — source of the `PASS`/`PASS_WITH_WARNINGS`/`FAIL` `QualityDecision` this contract gates on); ADR-0035 (Contract Consolidation — `RequirementPackage`, the abandoned prior attempt at this contract, is recorded there for removal; this ADR is its replacement).
- **Runtime status:** Not applicable. This is a **pure architecture freeze** — no code, model, or `PlatformContext` method is introduced. `TestableRequirement` and `TestableRequirementSet` are documented, dormant specifications. A future implementation milestone, authorized as ADR-0032 carve-out 1, builds against this ADR without deviation.

## Problem

`docs/audit/CODEBASE_AUDIT_2026-07-24.md` §3.2 established, and this ADR re-verifies directly: no frozen, typed contract exists between Layer 1 and Layer 2 today, because Layer 2 does not exist to consume one. Two candidate contracts are present in the repository and both fail the job:

- **`AnalysisResult`** (`requirement_intelligence/analysis/analysis_models.py:26`) is what Layer 1 actually produces and persists (`output/*/analysis_result.json`). It is a flat, LLM-shaped record — plain string lists (`functional_requirements`, `security_requirements`, `quality_requirements`) with **no per-requirement identity**, no acceptance-criteria structure, and no quality gate. Coupling Layer 2 to it directly would mean a prompt wording change (Layer 1's own internal concern) could silently break Layer 2, and there would be no way to tell which generated feature file came from which requirement across two runs.
- **`CanonicalRequirement`** and **`RequirementPackage`** (`requirement_intelligence/models/{canonical_requirement,requirement_package}.py`) were designed as exactly this kind of contract but were never wired in — `ConsolidationEngine` explicitly documents (`consolidation_engine.py:10`) that it does *not* build a `RequirementPackage`, and `grep` confirms neither model is constructed anywhere outside its own defining file. `RequirementPackage`'s own docstring names Azure OpenAI — itself an unimplemented provider stub — as its intended consumer.

Layer 2 (Feature Engineering, per ADR-0031) cannot be designed, let alone built, without a real answer to "what, exactly, does Layer 1 hand it."

## Decision

**`AnalysisResult` is redesignated Layer-1-internal.** It remains exactly what it is today — the immediate, persisted record of one Gemini call — consumed only by Layer 1's own downstream subsystems (Requirement Enhancement, Grounding, Validation, CP1, Requirement Quality Governance, Recommendation) and by the Execution Package's persistence. It is never again treated as, or designed toward being, a boundary artifact for anything outside Layer 1.

**`TestableRequirement`, carried inside the run-scoped envelope `TestableRequirementSet`, is established as the sole frozen contract Layer 2 may consume.** It replaces the abandoned `RequirementPackage` as the platform's answer to "what crosses the Layer 1 → Layer 2 boundary" (ADR-0035 records `RequirementPackage` for removal on this basis). Six properties are locked now; the exact field list is explicitly deferred (TBD section).

### Locked properties

1. **IDs are platform-assigned, never LLM-assigned.** No identifier a `TestableRequirement` carries may originate from Gemini's output text. The platform mints every ID deterministically from already-computed inputs (property 2).
2. **IDs are content-addressed.** `REQ-<short hash over the normalized requirement statement + sorted source keys>` — the same input (statement text plus the set of source artifacts it traces to) always yields the same ID, across runs, without coordination. A `supersedes` field carries revision lineage when the same logical requirement's content changes between runs (D2).
3. **Acceptance criteria are structured and individually identified (`AC-*`), owned by the requirement.** Free-prose acceptance criteria are prohibited — an acceptance criterion that cannot be individually identified cannot be individually traced to a scenario. Layer 2 scenarios (`SCN-*`) map to acceptance criteria, never to requirements directly (D3).
4. **Only a run whose `QualityDecision` (ADR-0017) is `PASS` or `PASS_WITH_WARNINGS` crosses the boundary.** `QualityDecision` is a single, run-scoped verdict (ADR-0017 §D23) — this gate therefore operates at the level of the whole run, not per-requirement: a `FAIL` run emits no `TestableRequirementSet` at all (D4).
5. **The run-scoped envelope is `TestableRequirementSet`**, carrying `contract_version`, `run_id`, and prompt/model provenance (which prompt version and which LLM model produced the run this set derives from) — the direct functional replacement for the abandoned `RequirementPackage`.
6. **The contract is versioned, has a checked-in JSON Schema, and a compatibility test.** A future change to `TestableRequirement`'s or `TestableRequirementSet`'s shape is a version bump plus a passing compatibility test against the previous version — never a silent field addition or removal.

## D1 — Why `AnalysisResult` cannot also be the boundary contract

A boundary contract must be stable against changes on either side of the boundary it separates. `AnalysisResult`'s shape is downstream of prompt wording and the LLM provider's raw output — both purely Layer 1 concerns Layer 2 must never need to know about (ADR-0031's layer-ownership discipline, inherited from ADR-0020 Stage 6: "a capability does not own another capability's contract"). Letting Layer 2 read `AnalysisResult` directly would make every future prompt-governance change (already a live, versioned subsystem under ADR-0014) a potential Layer 2 breaking change. Keeping `AnalysisResult` Layer-1-internal and introducing a distinct, frozen `TestableRequirement` is what makes prompt evolution and feature-generation evolution independent of each other.

## D2 — Why content-addressed IDs need a `supersedes` field at all

Content-addressing (property 2) is deliberate: the same input always produces the same ID, which is what makes a `TestableRequirement` reproducible and comparable across two runs over unchanged source data — no run-specific counter, no database sequence, no coordination between concurrent runs. But it has a direct consequence: if the underlying requirement's content changes between runs (a JIRA ticket is edited, new evidence arrives), the hash changes, and a **new** `REQ-*` ID is minted — content-addressing does not, and structurally cannot, preserve identity across a content change. Without `supersedes`, two runs of the same logical requirement would look like two unrelated requirements to everything downstream (Layer 2 scenarios, Layer 5 execution history, Layer 6 failure diagnosis). `supersedes` is what stitches successive content-addressed IDs of the same logical requirement into one lineage a human or a future capability can follow. The exact mechanism for detecting "this is the same logical requirement, just revised" (candidate: matching source keys with a materially different statement hash) is left to the Layer 2 LLD (TBD section) — this ADR locks only that the field must exist and what problem it solves.

## D3 — Why acceptance criteria are structured, and why scenarios map to them, not to requirements

A requirement is a statement of intent; an acceptance criterion is a specific, checkable condition; a scenario is one concrete way of checking it. Collapsing acceptance criteria into free prose inside the requirement statement (as `AnalysisResult` and the abandoned `RequirementPackage` both did — plain requirement strings with no criteria substructure) makes it impossible for Layer 2 to know how many scenarios a requirement needs, or to tell a partially-covered requirement from a fully-covered one, without re-parsing prose. Individually identified `AC-*` records give Layer 2 a concrete unit to map scenarios against, and give every later layer (Layer 4's validation, Layer 6's failure diagnosis) a concrete unit to report against. This is the same "structured, never free prose" discipline `docs/adr/0017-quality-governance-framework.md` §D30 already applies to `DecisionExplanation` — no generated prose stands in for structured data crossing a governed boundary.

## D4 — Why the gate is a run-level filter, not a per-requirement filter

`QualityDecision` (ADR-0017) is frozen as "the governed release decision for **one Requirement Intelligence run**" (ADR-0017 §D-QualityDecision docstring) — it is not, and was never designed to be, a per-requirement verdict. Building a per-requirement filter on top of a run-level verdict would require inventing a second, unfrozen judgement this ADR has no mandate to create. The simpler, already-consistent rule is adopted instead: a run that does not pass Requirement Quality Governance produces no `TestableRequirementSet` at all. A future, separately-decided capability could introduce per-requirement filtering on top of this gate; this ADR does not preclude that, but does not build it either.

## D5 — Why the exact field list is deferred rather than specified here

Layer 2 is the **only** consumer of this contract. Specifying every field of `TestableRequirement` and `TestableRequirementSet` now, without Layer 2's own design having a say, risks freezing a shape Layer 2 cannot actually build against — exactly the mistake this ADR exists to prevent by learning from `RequirementPackage`'s fate. The six properties above are locked because they are architectural (identity source, identity scheme, criteria structure, the release gate, the envelope's existence and provenance, and the versioning discipline) — none of them require knowing Layer 2's internal shape to decide. The field list does.

---

## TBD — to be finalised against the Layer 2 LLD

**Explicitly not decided by this ADR:**

- The exact field list of `TestableRequirement` (beyond: it has a platform-assigned, content-addressed `id`; a `supersedes` field; and one or more structured `AC-*` acceptance criteria records).
- The exact field list of `TestableRequirementSet` (beyond: `contract_version`, `run_id`, and prompt/model provenance).
- The exact hash algorithm and normalization procedure behind the content-addressed `REQ-*` id (property 2 names the inputs — normalized statement, sorted source keys — not the algorithm).
- The exact mechanism for detecting that two `TestableRequirement`s across runs represent "the same logical requirement, revised" for the purpose of populating `supersedes`.
- The `AC-*` record's own field list.
- Whether `TestableRequirementSet` is one object per run or is further partitioned (e.g. per module) — `ConsolidatedArtifact`'s own per-module grouping (`docs/audit/CODEBASE_AUDIT_2026-07-24.md` §3.2) is a candidate precedent, not a decision.
- The JSON Schema file's location and the compatibility test's exact mechanism (precedent: the Prompt Registry's SHA-256 manifest, ADR-0014 — a candidate, not a decision).
- Whether `CanonicalRequirement`'s `SourceRef` model (`requirement_intelligence/models/canonical_requirement.py:27-32`) is salvaged into this contract — ADR-0035 flags it as a candidate; this ADR does not decide it.

**Resolution path:** Layer 2's architecture-freeze ADR (the future ADR that plays the role ADR-0016 played for Grounding, or ADR-0030 played for Executable Specification Engineering) is where these are decided, with Layer 2's own designers as the deciding voice. This ADR's six locked properties are binding constraints on that future ADR, not a placeholder for it.

---

## Traceability spine

This contract is what makes the following chain possible, end to end, once Layers 2–6 exist (naming per ADR-0031; `SCN-*` and later stages are named here for spine completeness, not frozen by this ADR beyond `TestableRequirement`/`TestableRequirementSet` themselves):

```
source key (JIRA/SonarQube/ZAP record)
    ↓
REQ-*  (TestableRequirement, this ADR)
    ↓
AC-*   (structured acceptance criterion, this ADR)
    ↓
SCN-*  (Layer 2 scenario — future Layer 2 architecture)
    ↓
generated asset (Layer 3 page object / step definition / test data — future Layer 3 architecture)
    ↓
run_id (Layer 5 execution — ADR-0036)
    ↓
failure (Layer 6 diagnosis — future Layer 6 architecture)
    ↓
heal (Layer 6 repair — future Layer 6 architecture)
```

Every hop from `REQ-*` onward is only possible because `TestableRequirement` carries a platform-assigned, stable, content-addressed identity that nothing upstream (an LLM) can silently change out from under it (property 1), and because acceptance criteria are individually addressable rather than buried in prose (property 3). This spine is the practical justification for locking properties 1–3 now, even though the layers that consume the later hops do not exist yet.

## Recommendations (permanent)

1. **No component outside Layer 1 ever imports or depends on `AnalysisResult`.** `TestableRequirement`/`TestableRequirementSet` are the only sanctioned entry point (mirrors ADR-0020 Stage 6's runtime-contract-only integration rule).
2. **No ID crossing this boundary is ever assigned by the LLM.** Enforced by construction once implemented: the platform's ID-minting step runs after generation, over already-fixed inputs.
3. **No acceptance criterion crosses this boundary as free prose.** A structured `AC-*` record is mandatory.
4. **A `FAIL` run crosses this boundary with nothing.** No partial or best-effort `TestableRequirementSet` is emitted for a failed run.
5. **The field lists deferred above are Layer 2's to finalise, not to be pre-empted by any other future ADR.**

## Ownership, scope, and governance

- **Owns:** the existence, identity scheme, acceptance-criteria structure, release gate, envelope, and versioning discipline of the Layer 1 → Layer 2 boundary.
- **Does not own:** `AnalysisResult`'s own shape (unchanged, Layer 1-internal); the release decision itself (`QualityDecision`, owned by ADR-0017); Layer 2's internal architecture or the exact field lists (deferred, owned by Layer 2's future architecture-freeze ADR); the removal of `RequirementPackage` (owned by ADR-0035).
- **Governance:** Accepted as an architecture freeze. No implementation exists until a future milestone builds it under ADR-0032 carve-out 1, directly against this ADR's six locked properties, without redesigning them.
