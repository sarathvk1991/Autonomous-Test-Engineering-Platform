# ADR-0042 — TestableRequirement Field Specification

- **Status:** Accepted
- **Date:** 2026-07-24
- **Supersedes:** nothing. **Amends:** nothing. **Resolves:** the majority of ADR-0034's TBDs — `TestableRequirement`'s and `TestableRequirementSet`'s field lists, the `REQ-*`/`AC-*`/`RSK-*` hash algorithm and normalization procedure, the `AC-*` record's own field list, `TestableRequirementSet` partitioning, and the JSON Schema location (`docs/adr/0034-testable-requirement-contract.md`, TBD section, items 1, 2, 3, 5, 6, 7). Item 4 (`supersedes`-detection mechanism) is explicitly **not** resolved (Decision 5). Item 8 (`SourceRef` salvage) is resolved (Decision 4). **Unblocks:** ADR-0035's removal item 2 (`canonical_requirement.py`), whose salvage note blocked removal until the `SourceRef` question was decided — it is now decided (Decision 4). Inline resolution notes are added at ADR-0034's TBD section and ADR-0035's item 2 — see those ADRs for the added text. No other line of either changes.
- **Governing design:** none. Evidentiary basis: `docs/proposals/layer-2-feature-engineering-lld.md` (Reviewer's note, §2, §9, §11 — re-read directly for this ADR); `docs/reference/automation-poc/.gherkin-lintrc` (re-read directly); `requirement_intelligence/models/canonical_requirement.py` (re-read directly, `SourceRef`'s actual field list verified against what ADR-0035's salvage note already reported).
- **Depends on:** ADR-0034 (TestableRequirement contract — the six locked properties this ADR's field list must satisfy without redesigning); ADR-0035 (Contract Consolidation — the removal item this ADR's Decision 4 unblocks); ADR-0036 (Run and Stage State Model — `run_id` and artifact-path/idempotency discipline this ADR's `run_id` and `content_hash` fields align with); ADR-0014 (Prompt Registry — the governed `(prompt_id, version, sha256)` provenance this ADR's `provenance` block cites); ADR-0040 (Control Point Model — CP2's deterministic-gate discipline, relevant to how `polarity_hints` and other structured fields must remain advisory-free, non-scoring data).
- **Runtime status:** Not applicable. Documentation-only. This ADR specifies a contract; no Pydantic model, JSON Schema file, or ID-generation function is created by this ADR. A future implementation milestone, authorized as ADR-0032 carve-out 1, builds against this ADR without deviation.

## Problem

ADR-0034 locked six architectural properties of the Layer 1 → Layer 2 boundary but deferred the actual field list to "Layer 2's own LLD... the only consumer" (ADR-0034 §D5). The committed `docs/proposals/layer-2-feature-engineering-lld.md` is the closest thing to that LLD that exists, but its own Reviewer's note states it is "Submitted — under review, not approved," and several of its sections are already superseded (its `validated-requirement-model.json` shape, its `riskBasedScenarios`, its Azure OpenAI references). What it does provide, and what survives its own supersession, is usable evidentiary material: `.gherkin-lintrc`'s name-length rule, `generate-feature.md`'s functional-tag constraint, and §9's positive/negative/security/quality scenario taxonomy. This ADR specifies the field list ADR-0034 deferred, using that surviving evidence plus the platform's own already-committed models (`canonical_requirement.py`, the Prompt Registry) as its grounding — not the LLD's superseded sections.

## Decision 1 — Field specification

### `TestableRequirementSet`

Run-scoped envelope; replaces the deleted `RequirementPackage` (ADR-0034, ADR-0035 item 3).

| Field | Type / value | Notes |
|---|---|---|
| `contract_version` | semver string, `"1.0.0"` | Governs the compatibility test (Decision 6). |
| `run_id` | string | Per ADR-0036 — the run's canonical directory identifier. |
| `generated_at` | timestamp | When this set was written. |
| `provenance.prompt_id` | string | From the existing Prompt Registry (ADR-0014). |
| `provenance.prompt_version` | string | From the existing Prompt Registry (ADR-0014). |
| `provenance.prompt_sha256` | string | The registry's own verified fingerprint field, named `sha256` in `requirement_intelligence/prompts/models/prompt_metadata.py:85` and `framework/prompt_loader.py:67` — re-read directly for this ADR. Nested here as `provenance.prompt_sha256` to disambiguate from `content_hash` (Decision 3), not because the registry itself uses that exact name. |
| `provenance.provider` | string | From `llm_factory`. **No vendor name is hardcoded in the schema** — the field is populated at runtime, never a literal enum member naming a specific vendor. |
| `provenance.model` | string | From `llm_factory`, same discipline. |
| `provenance.requirement_quality_governance_decision` | `PASS` \| `PASS_WITH_WARNINGS` | The run-level gate ADR-0034 property 4 already locked — `FAIL` runs never reach this envelope at all. |
| `provenance.governance_report_ref` | string (artifact path) | Points at the Requirement Quality Governance report for this run, per ADR-0036's artifact-path-not-object discipline. |
| `requirements[]` | `TestableRequirement[]` | — |

### `TestableRequirement`

| Field | Type / value | Traces to |
|---|---|---|
| `requirement_id` | `REQ-<8 hex>`, platform-assigned, content-addressed | ADR-0034 properties 1–2; algorithm in Decision 2. |
| `content_hash` | sha256 hex string | Decision 3 — the field an implementation uses to satisfy ADR-0036's idempotency requirement for this stage. ADR-0036 itself names no hash mechanism; this field is this ADR's own contribution toward that requirement, not a citation of something ADR-0036 already specifies. |
| `supersedes` | `REQ-*` \| `null` | ADR-0034 property 2 / D2. Specified, deferred — Decision 5. |
| `title` | string, ≤ 70 chars, enforced pre-emission | Becomes the Gherkin `Feature:` name. The 70-char ceiling traces exactly to `docs/reference/automation-poc/.gherkin-lintrc:17` — `"name-length": ["on", { "Feature": 70, ... }]`, re-verified by direct read for this ADR. |
| `component` | string, from `ConsolidatedArtifact`'s grouping key | Determines the generated `.feature` file's path (Decision 1(b)). |
| `functional_tag` | string, e.g. `"@login"`, platform-supplied | Traces to `docs/reference/automation-poc/prompts/generate-feature.md`'s CONSTRAINTS: "Tag each scenario with at least one functional tag" / "Use meaningful tags such as `@smoke`, `@regression`, `@e2e`, or domain-specific tags like `@login`" — re-verified by direct read for this ADR. |
| `narrative` | string, optional | Business context for the generation prompt. No structural constraint beyond ADR-0034 property 3's free-prose prohibition, which applies to acceptance criteria, not this field. |
| `priority` | `HIGH` \| `MEDIUM` \| `LOW` | — |
| `acceptance_criteria[]` | `AcceptanceCriterion[]` | ADR-0034 property 3. |
| `risks[]` | `Risk[]` | Decision 1(a). |
| `traces_to[]` | `SourceRef[]` | Decision 4. |

**Correction note (additive, 2026-07-25).** During Part 2 emitter implementation, `priority` was found to be marked required (no `optional`/`| null` marker) while `AnalysisResult` — the sole Layer 1 output this contract is populated from — carries no honest per-requirement priority signal (verified: the only priority signal is inbound `SourceArtifact.priority` formatted into the prompt, never emitted back). Per this ADR's own rule against fabricating absent signal, the field is corrected to **optional, nullable** for `contract_version` 1.0.0, emitting `null`. It remains in the schema as a reserved, known-future field: populating it requires a future Layer 1 signal (a categorization/prioritization capability), which is a new Layer 1 capability and therefore gated behind ADR-0032's freeze-lifting procedure. The field's presence-and-nullability is stable; only its future population is deferred.

### `AcceptanceCriterion`

| Field | Type / value | Traces to |
|---|---|---|
| `criterion_id` | `AC-<REQ short>-NN` | Decision 2. |
| `category` | `FUNCTIONAL` \| `SECURITY` \| `QUALITY` | `docs/proposals/layer-2-feature-engineering-lld.md` §2's three acceptance-criteria buckets (`functionalAcceptanceCriteria`, `securityAcceptanceCriteria`, `qualityAcceptanceCriteria`) — re-verified by direct read. §2's own JSON shape (untyped, ID-less arrays) is superseded (Reviewer's note); only the three-bucket taxonomy survives into this field. |
| `statement` | string, single, atomic, testable | Free prose prohibited — ADR-0034 property 3. |
| `polarity_hints[]` | `POSITIVE` \| `NEGATIVE` \| `BOUNDARY` | **Partial trace, recorded honestly.** LLD §9 ("Scenario Generation Rules") literally names **Positive** and **Negative** scenario categories, verified by direct read: "Positive scenarios — happy path" / "Negative scenarios — invalid credentials, locked user, missing data." §9 does **not** use the word "Boundary" anywhere. The literal source of the "boundary" term in this LLD is §11 (`positiveData`/`negativeData`/`boundaryData`), a test-data JSON shape already flagged superseded in the Reviewer's note (Layer 2 emits a test-data *specification*, not that JSON). This ADR adopts `BOUNDARY` as this contract's own third value — a standard refinement of the "missing data" edge cases §9's Negative bucket already gestures at — rather than claiming §9 names it verbatim. §9's own Security/Quality scenario categories are not duplicated here; they are already covered by `category` above, since `polarity_hints` is an orthogonal axis (a security criterion can itself have positive/negative/boundary variants). |
| `data_fields[]` | optional | Seeds `Examples:` tables and Layer 3's test-data spec. |
| `traces_to[]` | `SourceRef[]` | — |

**Correction note (additive, 2026-07-25).** `AcceptanceCriterion.traces_to` cannot be honestly populated in `contract_version` 1.0.0. Verified during Part 2: `AnalysisResult` carries only group-level provenance (`source_consolidated_id`, one `ConsolidatedArtifact` id) and flat, unattributed criterion strings — no criterion-to-`SourceArtifact` link exists anywhere in Layer 1's output. The link is structurally absent by design: the LLM is never shown an artifact identifier, the output schema mandates bare string statements with no citation field, and Grounding (ADR-0016) exists precisely to **compute** requirement-evidence support because no such link is carried upstream. Per this ADR's rule against fabricating absent signal, `AcceptanceCriterion.traces_to` emits an empty list in 1.0.0 and is reserved. Requirement-level provenance **is** honestly available and is carried on `TestableRequirement.traces_to` (populated from `source_consolidated_id`'s `SourceArtifact` set). AC-level attribution requires a future Layer 1 capability (criterion-level source attribution, distinct from Grounding's support judgement) and is therefore gated behind ADR-0032's freeze-lifting procedure. The traceability spine is coarse (requirement→group) in 1.0.0, not precise (criterion→artifact); this is a recorded limitation, not a defect.

Note the deliberate asymmetry with `Risk.traces_to`, which **is** populated (group-level, same source set as `TestableRequirement.traces_to`). A risk is itself a group-level judgement derived from the whole `ConsolidatedArtifact`, so the group-level trace is its true and complete provenance — not a coarse approximation of a finer link. An acceptance criterion is a sub-requirement claim whose meaningful provenance would be the specific artifact that evidenced it; that link is structurally absent, so a group-level trace on a criterion would overclaim attribution and is therefore emitted empty instead. The two fields differ because their honest granularity differs, not because of the string shape they share.

### `Risk`

| Field | Type / value |
|---|---|
| `risk_id` | `RSK-<8 hex>` |
| `statement` | string |
| `category` | `SECURITY` \| `QUALITY` \| `FUNCTIONAL` |
| `traces_to[]` | `SourceRef[]` |

**Correction note (additive, 2026-07-25).** During Part 2 emitter implementation, `Risk.category` was found to be marked required (no `optional`/`| null` marker) while `AnalysisResult` — the sole Layer 1 output this contract is populated from — carries no honest per-risk category signal (verified: risks are a flat string array with no categorization anywhere in the pipeline). Per this ADR's own rule against fabricating absent signal, the field is corrected to **optional, nullable** for `contract_version` 1.0.0, emitting `null`. It remains in the schema as a reserved, known-future field: populating it requires a future Layer 1 signal (a categorization capability), which is a new Layer 1 capability and therefore gated behind ADR-0032's freeze-lifting procedure. The field's presence-and-nullability is stable; only its future population is deferred.

### `SourceRef` — salvaged from `canonical_requirement.py`, actual fields (Decision 4)

`requirement_intelligence/models/canonical_requirement.py:27-32` was re-read directly for this ADR. Its **actual** current field list is:

```python
class SourceRef(Schema):
    system: SourceSystem       # StrEnum: "jira" | "sonarqube" | "owasp_zap"
    external_id: str
    url: str | None = None
```

**This does not match the four-field shape this task's own prompt proposed** (`source_id`, `source_type`, `native_key`, `url`). Specifically:

- `system` (an enum, not a bare string field) plays the role the prompt called `source_id`. Its three values (`jira`, `sonarqube`, `owasp_zap`, verified against `shared/enums/base.py:13-18`) do match the prompt's proposed value list, so no value-level discrepancy exists — only a name/type discrepancy (enum field named `system`, not a string field named `source_id`).
- `external_id` plays the role the prompt called `native_key`. Name discrepancy only; same purpose (`PROJ-1234`, `java:S2925@path/File.java:88`, `zap-alert-10202` are all valid `external_id` values under the real model).
- `url` matches exactly.
- **There is no `source_type` field** (`requirement` \| `sast` \| `dast`) anywhere in the real model. The prompt's proposed shape invents a discriminator that does not exist in the source being salvaged.

**Decision:** salvage the model **as it actually exists** — `system`, `external_id`, `url` — rather than the invented four-field shape. `source_type` is not carried forward; a source's requirement/SAST/DAST character is already recoverable from `system` alone (`jira` → requirement, `sonarqube` → SAST, `owasp_zap` → DAST is a stable 1:1 mapping today), so no information is lost by omitting a separate field. If a future source is added whose `system` does not imply a single `source_type` (unlikely under ADR-0031's three-source freeze, which permits a fourth source only via its own ADR), a `source_type` field can be added under this contract's versioning discipline (Decision 6) — it is not invented preemptively here.

### Boundary decisions embedded in this shape

**(a) Layer 1 emits `risks`, not `riskBasedScenarios`.** Scenario generation lives only in Layer 2. This overrides LLD §2 — already flagged in its own Reviewer's note ("Layer 1 emits **risks**; Layer 2 owns all scenario generation. Scenario generation lives in exactly one layer.").

**(b) One `TestableRequirement` maps to exactly one `.feature` file.** `title` becomes the Feature name (≤70 chars, per the `.gherkin-lintrc` citation above); `component` determines the path. Decomposition is deterministic and reuses `ConsolidationEngine`'s existing grouping rather than introducing new grouping logic.

**(c) No scenario IDs in this contract.** `SCN-*` is assigned by Layer 2, **after** its remediation loop (ADR-0040's CP2, bounded at 2 attempts), because remediation can split or rename scenarios — fixing a scenario-size violation splits one scenario into two; fixing a name-length violation renames one — either of which would orphan any `SCN-*` ID assigned before remediation runs.

## Decision 2 — ID generation

Platform-assigned, never LLM-invoked (ADR-0034 property 1). One shared normalization function — casefold, collapse whitespace, strip punctuation — used by every ID type, so `REQ-*`, `AC-*`, and `RSK-*` all derive from the same normalization discipline.

- `REQ-<first 8 hex of sha256(normalized title + sorted source native_keys)>`
- `AC-<REQ short>-<2-digit ordinal, stable within the requirement>`
- `RSK-<first 8 hex of sha256(normalized statement + sorted source native_keys)>`

**Requirement:** identical input yields an identical ID across processes and runs, with no coordination. This is what makes ADR-0036's stage idempotency achievable for this stage — the ID-minting step itself needs no external state.

## Decision 3 — `content_hash`

`sha256` over the requirement's canonical JSON, **excluding** `requirement_id`, `content_hash`, and `supersedes` (excluding these three avoids a hash that depends on its own output, or on a lineage field that by definition changes independently of content). This is the field a future implementation uses to decide whether ADR-0036's stage may be marked `SKIPPED` on resume — re-stating precisely: ADR-0036 requires idempotency and permits `SKIPPED` on unchanged input, but does not itself name the mechanism; `content_hash` is this ADR's proposed mechanism for that stage, introduced here rather than in ADR-0036.

## Decision 4 — `SourceRef` is salvaged

`SourceRef` is preserved (moved, not deleted) when `canonical_requirement.py` is removed, using its **actual** field shape (`system`, `external_id`, `url` — see Decision 1's `SourceRef` table and the discrepancy note there). This decides ADR-0034's TBD item 8 and **unblocks ADR-0035's removal item 2** (`requirement_intelligence/models/canonical_requirement.py`), whose salvage note explicitly required this decision before removal could proceed. Removal itself remains a future task, per ADR-0035's own governance line — this ADR unblocks it, it does not execute it.

**Sequencing.** `canonical_requirement.py` is **not** deleted by the renames-and-deletions task (ADR-0035 items 1, 3, 4, per that ADR's own Recommendation 1). It is deleted in the **same change** that creates the `TestableRequirement` contract module, so `SourceRef` moves directly into its new home rather than being staged in a temporary location or orphaned by an earlier deletion. "Unblocked" (above, and in ADR-0035's own resolution note) means the salvage question is decided, **not** that the file may be removed independently of the contract work.

## Decision 5 — `supersedes` is specified but deferred

The field exists in the schema from v1.0.0 and **emits `null` in v1.0.0**.

Stated plainly: content-addressed IDs (Decision 2) mean any content change to a requirement produces a new `REQ-*` — that is the entire point of content-addressing (ADR-0034 D2). Linking a new requirement to the one it logically replaces therefore requires a **stable logical identity** independent of content — most plausibly the sorted source `external_id`s (formerly "native keys") a requirement traces to — which in turn requires a **cross-run requirement index**: something that remembers, across runs, which `REQ-*` IDs a given set of source keys has produced over time. ADR-0036's filesystem-only, per-run model provides no such index today. This ADR records that index as an **explicit prerequisite** for populating `supersedes` — not a detail to be filled in casually by whichever implementation gets to it first. **No implementation may invent a `supersedes` mechanism before a future ADR resolves this**, consistent with ADR-0034's own D2, which left the detection mechanism to a future decision rather than guessing it.

## Decision 6 — Set partitioning and schema

**One `TestableRequirementSet` per run**, containing all requirements for that run. **Not** partitioned by component. Rationale: this matches ADR-0036's run-scoped stage model directly — a stage produces one artifact per run, and per-component partitioning would require a second, unfrozen grouping decision this ADR has no evidence to justify over the simpler, already-consistent one.

**JSON Schema location.** No existing repo convention was found: this ADR's own search confirmed there is no top-level `contracts/` directory and no `schemas/` directory anywhere in the repository outside `.venv`'s third-party packages. `shared/contracts/base.py` holds Python base classes (`Schema`), not JSON Schema files. This ADR therefore **establishes** the convention rather than following a pre-existing one: `contracts/schemas/testable_requirement_set.schema.json`.

`contract_version` is semver. **A compatibility test must fail if a field is added, removed, or retyped without a version bump** — the mechanism ADR-0034 property 6 already locked; this ADR specifies where the schema lives, not a new obligation.

## Decision 7 — ADR-0020's Layer 2.5 (CAP-087, Executable Specification Engineering)

Baseline register §4 open question 1 deferred this to Layer 2's LLD; the committed `docs/proposals/layer-2-feature-engineering-lld.md` does not address it anywhere — confirmed by direct read; CAP-087 is not named in that document.

`docs/adr/0020-platform-evolution-roadmap.md:129-145` (Layer 2.5 section, as amended by ADR-0030) and `docs/governance/platform-capability-matrix.md:319` (CAP-087's row) were both re-read directly for this decision.

**Finding: materially different, not the same responsibility. This ADR does not decide it.**

Two concrete, structural differences, not merely a naming collision:

1. **Input contract.** CAP-087's own frozen dependency boundary (ADR-0020:143, as amended) consumes exactly five contracts **directly**: `RequirementEnhancementResult`, `GroundingResult`, `ValidationResult`, `RecommendationResult`, and `LearningResult`. These are Layer-1-internal, same-execution runtime contracts — precisely the class of artifact ADR-0034 Recommendation 1 forbids anything outside Layer 1 from depending on directly ("No component outside Layer 1 ever imports or depends on `AnalysisResult`. `TestableRequirement`/`TestableRequirementSet` are the only sanctioned entry point"). ADR-0031's own Layer 2 (Feature Engineering) is defined to consume `TestableRequirementSet` — the frozen boundary this very ADR specifies — and nothing else. CAP-087, as currently frozen, structurally bypasses that boundary. Reconciling the two would require either redesigning CAP-087's dependency boundary (a decision ADR-0030 owns, not this ADR) or redesigning ADR-0034's boundary (a decision this ADR has no mandate to make either).
2. **Output shape.** CAP-087 produces a **renderer-agnostic Specification Model** — the capability matrix states plainly that "Cucumber is the first reserved renderer target," implying other renderers are anticipated. ADR-0031's Layer 2 is defined, unconditionally, as generating **Cucumber BDD feature files** — no renderer abstraction exists or is implied anywhere in ADR-0031, ADR-0034, or ADR-0040.

A capability that consumes different inputs than the boundary this platform has actually frozen, and produces a differently-abstracted output, is not "the same responsibility with a different name" — it is either a distinct capability, a redesign candidate for CAP-087 itself, or a redesign candidate for Layer 2's future architecture-freeze ADR to explicitly evaluate against. None of those is this ADR's call to make; Layer 2's own future architecture-freeze ADR is where ADR-0031 §D4 already placed this question, and that placement stands.

**Baseline register wording sharpened, question left open** (see Step 4): the question is restated to name the specific conflict (CAP-087's dependency-boundary bypass of `TestableRequirementSet`, and its renderer-agnostic vs. Cucumber-committed output) so the next reader does not have to re-derive it.

## Consequences

- **ADR-0034's TBDs resolved:** field list (`TestableRequirement`, `TestableRequirementSet`, `AC-*`), hash algorithm and normalization procedure, JSON Schema location, `SourceRef` salvage decision, set partitioning. **Still open:** the `supersedes`-detection mechanism (Decision 5) — explicitly blocked on a cross-run requirement index ADR-0036's filesystem-only model does not provide.
- **ADR-0035's item 2 removal is unblocked** — `canonical_requirement.py` may now proceed to removal in a future task, using this ADR's Decision 4 as the record of what was salvaged and where it goes.
- **Layer 2's generation prompt takes a structured `TestableRequirement`, not the prose `{{REQUIREMENT}}` blob** `docs/reference/automation-poc/prompts/generate-feature.md` currently accepts. Converting that prompt to consume this contract's structured fields is Layer 2 implementation work, **not covered by this ADR**.
- **LLD §2's `validated-requirement-model.json` shape is formally superseded** by this contract, consistent with its own Reviewer's note.
- **No change to ADR-0036, ADR-0037, ADR-0040.**
- **Decision 7 leaves CAP-087's placement genuinely unresolved** — a future decision (Layer 2's architecture-freeze ADR, or a CAP-087-specific revision) must resolve the dependency-boundary conflict and the renderer-agnostic-vs-Cucumber conflict identified above before CAP-087 can be built against this contract, if it ever is.

## Recommendations (permanent)

1. No `REQ-*`, `AC-*`, or `RSK-*` ID is ever assigned by anything other than the shared, deterministic normalization + hash function (Decision 2) — never by an LLM, never by a per-run counter.
2. No implementation populates `supersedes` with a guessed or heuristic value before the cross-run requirement index (Decision 5's prerequisite) exists and a future ADR authorizes a specific detection mechanism.
3. `source_type` is not added to `SourceRef` speculatively — only if and when a real `SourceSystem` value is added whose requirement/SAST/DAST character is not already implied 1:1 by `system` (Decision 4).
4. Any future ADR that touches CAP-087's placement must explicitly address the two conflicts Decision 7 identifies (dependency-boundary bypass; renderer-agnostic vs. Cucumber-committed output) — restating the question without addressing them is not a resolution.

## Ownership, scope, and governance

- **Owns:** the concrete field list, ID-generation scheme, `content_hash` definition, `supersedes` deferral rationale, set partitioning, and JSON Schema location for `TestableRequirement`/`TestableRequirementSet` — resolving the majority of ADR-0034's TBDs and unblocking ADR-0035's item 2.
- **Does not own:** the `supersedes`-detection mechanism itself (explicitly deferred, Decision 5); CAP-087/Layer 2.5's placement (explicitly left open, Decision 7); Layer 2's prompt-conversion work (future Layer 2 implementation); ADR-0036's `run_id` generation scheme or `run_state.json` schema (unchanged, owned there).
- **Governance:** Accepted. Resolves ADR-0034's TBDs by additive inline note there; unblocks ADR-0035's item 2 by additive inline note there. Does not amend or supersede any other ADR.
