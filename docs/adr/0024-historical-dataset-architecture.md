# ADR-0024 — Historical Dataset & Historical Truth Constitution

- **Status:** Proposed
- **Date:** 2026-07-16
- **Supersedes:** nothing. **Amends:** nothing. **Elevates:** the Historical Dataset Resolution Principle, previously discovered and independently frozen as ADR-0022 Recommendation 10 (Continuous Improvement) and reaffirmed in equivalent form by ADR-0023 §D10/§D11 (Knowledge Graph), into a single, platform-wide, constitutional rule every future Layer 2+ capability inherits without rediscovering it.
- **Governing design:** none — this ADR *is* the governing design, exactly as ADR-0020 and ADR-0021 introduce no proposal document because neither is subsystem architecture.
- **Depends on:** ADR-0020 (Platform Evolution Roadmap & Architectural Constitution — defines the seven layers and their dependency direction) and ADR-0021 (Cross-Execution Data Architecture & Historical Intelligence Constitution — defines the Truth Hierarchy and names the Historical Dataset as Layer 2's canonical owner of historical executions, ADR-0021 §Stage 6, without yet constitutionally specifying *how* that ownership is exercised). Informed by ADR-0022 (Continuous Improvement Framework) and ADR-0023 (Knowledge Graph Framework) — the two existing Layer 2 capabilities whose independently duplicated `HistoricalDatasetReference` and `HistoricalDatasetProvider` patterns are the empirical precedent this ADR generalizes into constitution.
- **Runtime status:** Not applicable. This is a **documentation-only constitutional milestone**: no runtime behaviour, no implementation, no models, no runtime contracts, no `PlatformContext` changes, no policies, no services, no serializers, no Execution Package changes, no manifest changes, no CLI changes, and no version bumps (Architecture, Platform, or otherwise). It permanently defines what Historical Truth is, who owns it, how it evolves, and how every future Layer 2+ capability must consume it — it does not build any part of that ownership.

## Scope note

ADR-0020 defines **platform evolution** — the seven architectural layers and their dependency direction. ADR-0021 defines **data evolution across time** — the three-level Truth Hierarchy (Runtime Truth → Historical Truth → Derived Knowledge) and the permanent rule that a fact about one execution can never be confused with a conclusion inferred from many. Both are constitutional; neither specifies the concrete shape of the seam between them. ADR-0021 §Stage 6 names the Historical Dataset as Layer 2's canonical owner of historical executions — ordering, lineage, retention, indexing, search, organization — but stops there: it does not freeze what a *reference* to that dataset looks like, how an engine *resolves* one, or how storage may evolve underneath it without breaking every consumer built on top. CAP-083 (Continuous Improvement) and CAP-084 (Knowledge Graph) each independently answered those questions the same way, because ADR-0021 left them to. ADR-0024 takes that convergent answer — proof by two independent implementations that it is the right one — and freezes it once, permanently, as the constitution every third, fourth, and future Layer 2+ capability inherits instead of reinventing.

This is **not** a subsystem ADR. It defines no `requirement_intelligence/` package, no `PlatformContext` method, no policy, no model, no service. It is a constitutional document, exactly like ADR-0020 and ADR-0021.

---

## Stage 0 — Repository assessment

Before writing this ADR, the following were reviewed:

- **ADR-0021's Truth Hierarchy** (§Stage 3): Runtime Truth (Layer 1, execution-scoped, never inferred) → Historical Truth (Layer 2, append-only accumulation of Runtime Truth) → Derived Knowledge (Layers 2–7, reproducible, never canonical history). The hierarchy is intact and unchanged by every subsystem built since: `ContinuousImprovementResult` and `KnowledgeGraphResult` are both correctly Derived Knowledge (ADR-0022 §D3, ADR-0023 §D3), and neither has ever been mistaken for, or promoted to, Historical Truth.
- **ADR-0022 (Continuous Improvement)**: `HistoricalDatasetReference` (provenance only — dataset id/version, execution range, history window, generation timestamp), a private, constructor-injected `HistoricalDatasetProvider` resolving that reference into an engine-internal `HistoricalDataset`, and the Historical Dataset Resolution Principle frozen as Recommendation 10 (ADR-0022) and reaffirmed permanently at CAP-083B.1 (ADR-0022 §D10).
- **ADR-0023 (Knowledge Graph)**: the identical pattern, independently re-derived — `HistoricalDatasetReference` duplicated (not imported) with the same seven fields and the same validator, its own private `HistoricalDatasetProvider`, and the same resolution principle reaffirmed at CAP-084B.1 (ADR-0023 §D11).
- **`HistoricalDatasetReference` in both subsystems** (`requirement_intelligence/continuous_improvement/models/historical_dataset_reference.py` and `requirement_intelligence/knowledge_graph/models/historical_dataset_reference.py`): read side by side. They are **structurally identical** — `dataset_id`, `dataset_version`, `first_execution_id`, `last_execution_id`, `execution_count`, `history_window`, `generated_at`, and the identical `execution_count <= history_window` validator — differing only in which package's docstring cross-references which ADR. Confirmed deliberate: each docstring explicitly states the type is "duplicated, not imported," citing the same self-containment discipline every subsystem's identity/version base classes already follow (ADR-0015 §C and successors).
- **`HistoricalDatasetProvider` implementations**: `DeterministicHistoricalDatasetProvider` in each subsystem synthesizes reproducible per-execution facts as a pure function of the reference's own provenance fields (SHA-256 digests — no UUID, no clock, no real historical storage). Neither is backed by a real Historical Dataset implementation. Both are private, engine-internal, constructor-injected, and never exported past their own package boundary — confirmed by the containment tests each subsystem's own freeze milestone added (`test_continuous_improvement_result_freeze.py::TestRuntimeBoundary::test_no_module_outside_the_package_names_the_provider`, and the equivalent, symmetrically-excluding test in `test_knowledge_graph_result_freeze.py`).
- **The Historical Dataset Resolution Principle**: present in both ADRs, worded almost identically, each independently arriving at "the reference carries provenance only; a private collaborator may resolve it; the resolved dataset is never a runtime contract; the public boundary never changes." ADR-0022 gave it a numbered Recommendation (10); ADR-0023 reaffirmed the identical content within its own §D10/§D11 without a matching numbered Recommendation of its own — a documentation gap, not an architectural one, and the direct motivation for elevating the principle here rather than leaving a third subsystem to either copy prose or invent its own numbering.

**Confirmed:**

- No canonical Historical Dataset exists anywhere in the repository — no storage, no schema, no query surface, no `serialization/`-style package, no file format. A full-repository grep for a real (non-synthetic) Historical Dataset implementation, storage adapter, or persistence layer under `requirement_intelligence/` returns nothing.
- No Layer owns Historical Truth yet in an implemented sense. ADR-0021 §Stage 6 *names* the Historical Dataset as Layer 2's canonical owner in principle; nothing in the repository *is* that owner today. Both existing Layer 2 capabilities consume a reference to a dataset that does not exist, resolved through a provider that synthesizes substitute facts solely to exercise their own deterministic engines end to end.
- Provider duplication across `continuous_improvement/` and `knowledge_graph/` is intentional, not accidental: each package's own docstring says so, each package's own ADR says so (ADR-0022 §D9, ADR-0023 §D10), and each package's own freeze-milestone test explicitly excludes the *other* package from its "provider is never named outside this package" containment check — a deliberate, structural acknowledgment that two subsystems independently reused the same generic class name for two genuinely distinct, unrelated private classes.
- Duplication is architectural, not accidental: it follows the same self-containment discipline every prior subsystem's identity and version base classes already apply (ADR-0015 §C, ADR-0016 §D6, ADR-0017 identity module docstring, ADR-0018 §D5, ADR-0019 §D5, ADR-0022 identity module docstring, ADR-0023 identity module docstring) — acknowledged platform debt (eventual promotion to `shared/`), never an oversight.

> No inconsistency found. The two existing Layer 2 capabilities converged, independently, on the identical answer to a question ADR-0021 left open. Proceeding to freeze that convergent answer as constitution.

---

## Stage 1 — Introducing ADR-0024

This document, `docs/adr/0024-historical-dataset-architecture.md`, is **Proposed**. It is a constitutional ADR, not a subsystem ADR — it defines no runtime contract, no policy, no model, no service, and no `PlatformContext` registration of its own. Its purpose is the **Historical Dataset & Historical Truth Constitution**: the permanent definition of what Historical Truth is, who owns it, how it evolves, and how every future Layer 2+ capability must consume it, so that the third, fourth, and every subsequent Continuous Learning capability inherits one already-settled answer instead of re-deriving — or worse, silently diverging from — the one CAP-083 and CAP-084 each found independently.

---

## Stage 2 — Historical Truth, frozen permanently

**Historical Truth is:**

- **immutable** — once appended, an entry is never altered;
- **append-only** — new entries are added; no entry is ever removed (Stage 8);
- **execution-derived** — constructed exclusively from completed Layer 1 Runtime Truth, never from a report, a manifest, or any other projection (ADR-0021 §Stage 7);
- **deterministic** — the same set of source executions always yields the same Historical Truth;
- **replayable** — the same dataset version, resolved again, reproduces the same result (Stage 7);
- **versioned** — the dataset's own schema/organization evolves on an independent axis (ADR-0021 §Stage 9; Recommendation 11 below);
- **explainable** — every entry traces to the Execution Package and the Runtime Truth it packaged (Stage 9);
- **independently evolvable** — its storage, schema, and organization may all change without forcing any consuming Layer 2+ contract to change (Stage 6).

**Historical Truth is not:**

- **Derived Knowledge** — a trend, a finding, a structural observation, or any other conclusion inferred *about* history is never itself history (ADR-0021 §Stage 3);
- **Runtime Truth** — a single execution's own contract is Layer 1's canonical record, never itself the aggregated corpus (ADR-0021 §Stage 3/§Stage 4);
- **Knowledge Graph** — `KnowledgeGraphResult` is Derived Knowledge, one layer above Historical Truth, never a substitute for it or a second place it is recorded (ADR-0023 §D3);
- **Continuous Improvement** — `ContinuousImprovementResult` is likewise Derived Knowledge, never Historical Truth (ADR-0022 §D3);
- **Recommendation** — a Layer 1 runtime contract, execution-scoped, never a cross-execution record (ADR-0021 §Stage 3);
- **Feature** — a future Layer 3 Derived Knowledge product, reserved (ADR-0020);
- **Prediction** — a future Layer 4 Derived Knowledge product, reserved (ADR-0020).

This restates and freezes ADR-0021 §Stage 3/§Stage 5 in one place, as the anchor every subsequent stage of this ADR builds on.

---

## Stage 3 — Historical Dataset ownership, frozen

**Historical Dataset owns only completed Runtime Truth** — the immutable, execution-scoped contracts Layer 1 already produces (`EngineeringContext`, `AnalysisResult`, `RequirementEnhancementResult`, `GroundingResult`, `ValidationResult`, `CP1Result`, `QualityGovernanceResult`, `RecommendationResult`, and their future Layer 1 peers), read directly, never through a report or a manifest (ADR-0021 §Stage 7).

**It never owns:**

- **Derived Knowledge** — no trend, finding, structural observation, feature, prediction, optimization, or autonomous plan is ever stored inside the Historical Dataset (Recommendation 3 below);
- **Knowledge Graphs** — `KnowledgeGraphResult` and its constituent nodes/edges/subgraphs/observations/findings are Derived Knowledge, consumed from the Historical Dataset, never written back into it (mirrors ADR-0023's own Derived Knowledge principle, ADR-0023 §D11);
- **Predictions** — a future Layer 4 product; the Historical Dataset never anticipates or stores one;
- **Optimization** — a future Layer 5 product; out of scope by construction;
- **Autonomous actions** — a future Layer 6 product; the Historical Dataset records what happened, never what a future autonomous engine decided to do about it.

A single ownership violation — any Layer 2+ capability writing its own output back into the Historical Dataset — would collapse the Truth Hierarchy ADR-0021 exists to protect. This stage exists to make that violation structurally nameable, not merely implied.

---

## Stage 4 — Historical Dataset lifecycle, frozen

```
Execution completes
        ↓
Execution Package frozen
        ↓
Historical Dataset updated
        ↓
Historical Truth becomes immutable
        ↓
Layer 2 consumes
        ↓
Layer 3 consumes Layer 2
        ↓
Never rewritten
```

Each arrow is a one-way, non-skippable transition (Stage 10). An execution's Runtime Truth is frozen the moment its Execution Package is written (ADR-0021 §Stage 4); the Historical Dataset appends a reference to that frozen execution and, from that instant, the corresponding Historical Truth entry is itself immutable (Stage 2). Layer 2 reads the Historical Dataset — never the raw Execution Package (ADR-0021 §Stage 6) — and every layer above Layer 2 reads only the layer immediately below it (ADR-0021 §Stage 10), never reaching back to rewrite anything earlier in this chain.

---

## Stage 5 — Historical Dataset Resolution Principle, elevated to constitution

Previously frozen independently by ADR-0022 (as Recommendation 10) and reaffirmed in equivalent, unnumbered form by ADR-0023 (§D10/§D11). This ADR elevates it once, permanently, for every present and future Layer 2+ capability:

```
HistoricalDatasetReference
        ↓
Provider
        ↓
HistoricalDataset
        ↓
Layer 2 Engine
```

`HistoricalDatasetReference` intentionally carries provenance only — dataset identity/version, the execution range it spans (by id, never by embedding the executions themselves), the governed history window it was bounded to, and when it was minted. It is never the dataset's content.

**The provider is:**

- **private** — an internal collaborator, never exported past its own subsystem's package boundary;
- **replaceable** — any future provider, including one backed by a real Historical Dataset implementation, may replace a synthetic one without changing anything upstream or downstream of it;
- **storage-independent** — its resolution logic knows nothing about SQL, a file format, or any other storage technology; it merely returns an internal `HistoricalDataset` shape its own engine already understands;
- **constructor injected** — supplied to the engine that uses it at construction time, never looked up globally, never a singleton, never reached for by any collaborator that was not handed it directly.

**Consequence for every future Layer 2+ capability.** A capability built after this ADR does not need its own ADR section deriving this principle from first principles, and it does not need to duplicate ADR-0022's or ADR-0023's prose to restate it. It cites ADR-0024 §Stage 5 and proceeds — exactly the same way a future Layer 1 subsystem cites ADR-0015's identity/version pattern instead of re-deriving it. The pattern itself — `HistoricalDatasetReference` duplicated per subsystem, a private per-subsystem `HistoricalDatasetProvider`, the same resolution shape — remains **per-subsystem duplication by design** (Stage 0), not a shared implementation; what is now constitutional is the *shape* of that duplication, not a shared class.

---

## Stage 6 — Storage independence, frozen permanently

Historical Truth must be independent of the storage technology that eventually persists it — explicitly including, but not limited to:

- SQL, PostgreSQL, SQLite
- S3, Parquet, JSON
- Neo4j, RDF, property graph
- document database
- filesystem

**Storage changes must never change runtime contracts.** `HistoricalDatasetReference`'s shape, every Layer 2+ engine's public method signature (`ContinuousImprovementService.improve`, `KnowledgeGraphService.build`, and every future Layer 2+ peer), and every runtime contract those engines produce (`ContinuousImprovementResult`, `KnowledgeGraphResult`, and every future peer) must all remain byte-identical regardless of what eventually replaces today's synthetic providers. This is the direct generalization of ADR-0022 Recommendation 10 and ADR-0023 Recommendation 5/12, no longer scoped to one subsystem's own graph-storage or historical-storage concern but frozen once for the whole platform.

---

## Stage 7 — Replay principle, frozen

```
HistoricalDatasetReference
        ↓
provider
        ↓
dataset
```

Given the same `HistoricalDatasetReference`, resolved through the same provider, against the same underlying dataset version, the result must be the same Historical Truth every time. This is not a new requirement — every existing deterministic provider already satisfies it by construction (pure SHA-256 functions of the reference's own fields, no UUID, no clock) — but it was previously an implementation property of two subsystems, never a constitutional guarantee every future one must uphold.

**This enables:**

- **deterministic replay** — regenerating a historical view without depending on wall-clock state or hidden mutation;
- **regression** — comparing two builds of the same reference and expecting identical output, the same discipline every golden-baseline test in this platform already depends on;
- **auditing** — proving, after the fact, that a Layer 2+ conclusion could only have come from the historical entries it names;
- **compliance** — demonstrating that historical records were never silently altered between two points in time.

---

## Stage 8 — Dataset evolution, frozen

**Historical Dataset may evolve by append only.**

- **Never rewrite** — an existing entry's content is never modified in place.
- **Never delete** — an entry is never removed, even when it is no longer directly useful (retention/indexing per ADR-0021 §Stage 6 may change how an entry is *found*, never whether it *exists*, mirroring ADR-0021 §Stage 5).
- **Never mutate history** — no field of a previously-appended entry is ever changed after the fact.

**Corrections create new versions. Never overwrite.** If an execution's Runtime Truth was later found to be wrong, the platform-wide correction mechanism is unchanged from ADR-0021 §Stage 4: a *new* execution runs, producing its *own* new Runtime Truth and its *own* new Historical Truth entry. The old entry is never reopened — it accurately recorded what that execution actually produced at the time, and remains permanently as that record.

---

## Stage 9 — Historical explainability, frozen

Every Historical Dataset entry must trace to:

```
Execution Package
        ↓
Runtime Truth
        ↓
Execution
```

**Nothing historical may exist without provenance.** An entry that cannot name the Execution Package it was frozen from, the Runtime Truth contract that package carried, and the execution that produced it, is not explainable and must not be constructible — the same "at least one reference" discipline ADR-0019 §D7 froze for a single `Recommendation`, and ADR-0021 §Stage 8 already required end-to-end across the historical chain. This stage restates that requirement as the Historical Dataset's own, permanent obligation, not merely a property inherited from what it happens to reference.

---

## Stage 10 — Layer rules, frozen

```
Layer 1
produces Runtime Truth
        ↓
Execution Package
        ↓
Historical Dataset
        ↓
Layer 2
        ↓
Layer 3
        ↓
Layer 4
        ↓
Layer 5
        ↓
Layer 6
        ↓
Layer 7
```

**Never reverse** — no later layer's output is ever written back into an earlier layer's record (Stage 3, Stage 8). **Never skip** — a layer consumes only the layer immediately below it (ADR-0021 §Stage 10); Layer 3 (Feature Engineering) consumes Layer 2's Derived Knowledge, never raw Runtime Truth or the Historical Dataset directly (Recommendation 10 below), exactly as Layer 2 itself never reads an Execution Package directly (ADR-0021 §Stage 6). This restates ADR-0021 §Stage 10's dependency chain, anchored explicitly to the Historical Dataset seam this ADR governs.

---

## Stage 11 — Future evolution (reserved)

The following are named as future work. **None are introduced by this milestone:**

- Historical Dataset Store
- Historical Dataset Builder
- Dataset Merge
- Dataset Compaction
- Retention
- Archiving
- Replay Engine
- Distributed Storage
- Streaming
- Incremental Updates

Each, when eventually built, must satisfy Stage 5 (resolved through a private, replaceable, constructor-injected provider), Stage 6 (storage-independent), Stage 7 (replayable), and Stage 8 (append-only) without requiring a change to `HistoricalDatasetReference`'s shape or any Layer 2+ runtime contract already frozen.

---

## Stage 12 — Constitutional recommendations, frozen permanently

### Recommendation 1

Historical Truth is immutable.

### Recommendation 2

Historical Truth is append-only.

### Recommendation 3

Historical Truth never stores Derived Knowledge.

### Recommendation 4

Providers remain private.

### Recommendation 5

Storage remains replaceable.

### Recommendation 6

Historical Dataset is replayable.

### Recommendation 7

Historical Dataset is explainable.

### Recommendation 8

Execution Package is the only ingress.

### Recommendation 9

Layer 2 consumes Historical Truth.

### Recommendation 10

Feature Engineering consumes Derived Knowledge, never Historical Truth directly.

### Recommendation 11

Historical Dataset versioning is independent of runtime contract versioning.

### Recommendation 12

Storage technology must never influence platform architecture.

---

## Stage 13 — ADR-0020 cross-reference

`docs/adr/0020-platform-evolution-roadmap.md` §Layer 2 — Continuous Learning is updated to cross-reference this ADR as the constitutional foundation of Layer 2's historical-data seam, alongside the existing reference to ADR-0021. No roadmap restructuring: the CAP-083/CAP-084 lifecycle lines, capability list, and layer ordering are unchanged — this is a citation addition only.

---

## Stage 14 — Verification

This milestone is documentation only. Verified:

- zero runtime changes — no file under `requirement_intelligence/` was touched;
- zero model changes — no Pydantic model, dataclass, or contract was added or modified;
- zero policy changes — no `*Policy` class or governed default was touched;
- zero `PlatformContext` changes — `platform_context.py` was not touched;
- zero service changes — no `*Service` class was added or modified;
- zero serializer changes — no `serialization/` package was added or modified;
- zero Execution Package changes — `execution_data.py`, `execution_writer.py`, `manifest_builder.py` were not touched;
- zero golden changes — the golden dataset and its version are unchanged;
- zero version bumps — Architecture Version (`1.2.0`), Platform Version (`1.0.0`), and every existing runtime contract/policy/framework version are unchanged.

Ruff, the full repository test suite, productization, and golden verification were run after this change; all pass, and the repository remains byte-identical outside this one new documentation file and the one-line ADR-0020 cross-reference.

---

## Stage 15 — Final constitutional review

1. **Is Historical Truth permanently defined?** Yes — Stage 2: immutable, append-only, execution-derived, deterministic, replayable, versioned, explainable, independently evolvable; and explicitly not Derived Knowledge, Runtime Truth, Knowledge Graph, Continuous Improvement, Recommendation, Feature, or Prediction.
2. **Is Historical Dataset ownership permanently frozen?** Yes — Stage 3: owns only completed Runtime Truth; never Derived Knowledge, Knowledge Graphs, Predictions, Optimization, or Autonomous actions.
3. **Is the append-only principle frozen?** Yes — Stage 8: append only; never rewrite, delete, or mutate; corrections create new versions, never overwrites.
4. **Is replayability permanently defined?** Yes — Stage 7: the same `HistoricalDatasetReference`, resolved through the same provider against the same dataset version, reproduces the same Historical Truth — enabling deterministic replay, regression, auditing, and compliance.
5. **Is storage independence permanently frozen?** Yes — Stage 6: Historical Truth is independent of SQL, PostgreSQL, SQLite, S3, Parquet, JSON, Neo4j, RDF, property graph, document database, and filesystem; storage changes must never change runtime contracts.
6. **Is the Historical Dataset Resolution Principle now constitutional?** Yes — Stage 5: elevated from ADR-0022's own Recommendation 10 (and ADR-0023's equivalent, unnumbered reaffirmation) into a single platform-wide rule every future Layer 2+ capability inherits by citation.
7. **Is provider privacy permanently frozen?** Yes — Stage 5/Recommendation 4: providers remain private, replaceable, storage-independent, and constructor injected.
8. **Is the Layer 1 → Historical Dataset → Layer 2 dependency permanently frozen?** Yes — Stage 10: Layer 1 → Execution Package → Historical Dataset → Layer 2 → … → Layer 7, never reversed, never skipped.
9. **Does this milestone introduce zero runtime behavior?** Confirmed — Stage 14: documentation-only diff (one new ADR file, one cross-reference line in ADR-0020); Ruff, the full test suite, productization, and golden verification are all unaffected.
10. **Is the repository constitutionally ready to continue Layer 2 evolution?** Yes. A third Layer 2+ capability may now be built directly against ADR-0024's constitution without independently re-deriving the Historical Dataset Resolution Principle, exactly as CAP-083 and CAP-084 each did before this ADR existed to cite.

---

## Ownership, scope, and governance

- **Owns:** the definition of Historical Truth (Stage 2), Historical Dataset ownership (Stage 3), the Historical Dataset lifecycle (Stage 4), the Historical Dataset Resolution Principle as platform constitution (Stage 5), storage independence (Stage 6), the replay principle (Stage 7), append-only dataset evolution (Stage 8), historical explainability (Stage 9), and the Layer 1 → Historical Dataset → Layer 2–7 dependency chain (Stage 10).
- **Does not own:** the Truth Hierarchy itself (Runtime Truth / Historical Truth / Derived Knowledge remains ADR-0021 §Stage 3's); any Layer 1 runtime contract, policy, engine, orchestration, or Execution Package (ADR-0011 through ADR-0019); any Layer 2+ capability's own internal design, models, policy, or engine (those remain the province of their own subsystem ADRs — ADR-0022, ADR-0023, and every future Layer 2+ ADR, each still required by ADR-0021 Recommendation 11 to declare its own Truth Hierarchy level); any concrete Historical Dataset implementation (Stage 11, reserved future work, not introduced here).
- **Governance:** registered alongside ADR-0020 and ADR-0021 as a platform constitutional document. **Proposed** — it becomes **Accepted** once a future capability (or a dedicated future milestone) builds the first real Historical Dataset implementation against it without deviation; until then, CAP-083 and CAP-084 continue operating exactly as before, now formally citing this ADR instead of independently justifying the pattern each already followed.
