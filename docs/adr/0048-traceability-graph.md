# ADR-0048 — Traceability Graph (Requirement → Scenario → Step Completeness)

- **Status:** Accepted
- **Date:** 2026-08-12
- **Supersedes:** nothing. **Amends:** nothing. (Two follow-on governance actions are recommended,
  not performed by this ADR — see Consequences: a `docs/governance/platform-capability-matrix.md`
  entry for `CAP-088`, mirroring `CAP-087`'s own row; and an `ADR-0020` roadmap note, mirroring how
  ADR-0030 registered `CAP-087` as an unanticipated addition to ADR-0020's own capability list.)
- **Governing design:** none. No `docs/proposals/*.md` design document precedes this ADR — the
  capability was built first (`requirement_intelligence/traceability_graph/`, 2026-08-12,
  scores-first), and this ADR is the retroactive architecture record for what already exists,
  tested, in the repository, rather than the usual freeze-before-code precedent every other Layer 2
  peer (ADR-0022, ADR-0023) followed. See D5 for why, and Consequences for the governance debt this
  closes.
- **Depends on:** ADR-0023 (Knowledge Graph Framework — the architectural *pattern* this capability
  reuses: typed node/edge vocabulary, deterministic identity, a governed pipeline shape — and the
  frozen Historical-Truth-only boundary, D2/Recommendation 1/Recommendation 9, this capability
  deliberately does **not** reuse, D2 below); ADR-0021 (Cross-Execution Data Architecture — the
  Truth Hierarchy this capability's own placement does not cleanly satisfy, D2 below); ADR-0042/
  ADR-0034 (`TestableRequirementSet` — the real Layer 1 input this capability reads); ADR-0043
  (Layer 2 Feature Engineering architecture — `FeatureEngineeringPackage` and the `.feature` files
  this capability re-parses, the real Layer 2 input it reads).
- **Runtime status:** Built and tested — `requirement_intelligence/traceability_graph/` (7 modules:
  `models`, `identity`, `projection`, `traversal`, `completeness`, `serialization`, `__init__`), 15
  deterministic unit tests (`tests/unit/test_traceability_graph.py`), all fixture-based, no LLM
  calls. Measured once against real production artifacts — a real live run's own
  `testable_requirement_set.json` and `feature_engineering_package.json` (D5). **Not wired into any
  execution pipeline.** No `PlatformContext` composition-root method exists for it; nothing calls
  `project_traceability_graph` or `evaluate_completeness` at runtime. A future, separate milestone
  would wire it live, mirroring ADR-0022 §D11 / ADR-0023 §D12's own runtime-integration pattern.

## Problem

Both this platform's own LLD review (`docs/architecture/lld-review-findings.md`) and Nitin's own
mentor feedback (`docs/architecture/mentor-feedback-scoping.md`, item #3) independently named the
same gap: **no mechanism anywhere in this platform answers whether the requirement corpus itself is
complete** — not "is each requirement well-formed" (a real, already-built check, scoped per
requirement, in `enhancement/`/`grounding/`), but "does every requirement have a test, and does
every scenario have steps." Nitin's own framing — "house of cards," input-quality, corpus
completeness — recurs across both his original feedback and his later reply
(`mentor-feedback-scoping.md` item #3's own Consensus-signal note), making it, by his own repeated
emphasis, this program's single highest-strategic-value open item.

The scoping doc's own design-surfacing task (item #3, "GRAPHS DESIGN SURFACED") read the real
`requirement_intelligence/knowledge_graph/` code directly (ADR-0023) to answer the obvious first
question — can the existing Knowledge Graph, already Accepted and live, simply be extended to
answer this? — and found a real, evidenced constraint that made the answer no (D2, below). This ADR
is the architectural record of the capability built to answer that question anyway, as its own
independent, minimal-slice sibling.

## Decision

Introduce a new, governed package, **`requirement_intelligence/traceability_graph/`**, that owns
one thing: a deterministic `requirement → scenario → step` graph projected from real, already-
produced Layer 1/Layer 2 artifacts, and a completeness report computed by traversing it. It:

1. Introduces canonical models — `TraceabilityNodeType`, `TraceabilityEdgeType`, `TraceabilityNode`,
   `TraceabilityEdge`, `TraceabilityGraph`, `UncoveredRequirement`, `CompletenessReport` — frozen,
   camelCase, reference-not-copy, mirroring the `Schema` conventions ADR-0015 onward established and
   ADR-0023 §Recommendation 2/3 specifically apply to a typed graph.
2. Deliberately does **not** reuse `KnowledgeGraphService`, `HistoricalDatasetReference`, or any
   other ADR-0023 runtime object — it reuses the *pattern* only (D2, D3).
3. Models the minimal slice only: `requirement —[HAS_SCENARIO]→ scenario —[HAS_STEP]→ step`. No
   page-object hop, no execution-result hop, no change-impact graph, no state/flow graph — each
   named as explicit, deferred future scope, not silently out of mind (D4).
4. Projects from real artifacts directly — `TestableRequirementSet` and `FeatureEngineeringPackage`
   — never a synthetic stand-in (D6).
5. Surfaces completeness as a **report**, never a **gate** — `CompletenessReport` is a structured,
   machine-readable, gate-ready object; nothing in this package evaluates it against a threshold or
   produces a pass/fail verdict (D5).

---

## D1 — Why this capability exists: Nitin's completeness concern, made queryable

Requirement→scenario→step traversal answers exactly the question that was previously unanswerable
anywhere in this platform: given the full requirement corpus, which requirements have no test at
all, and why (no scenario ever generated, or a scenario with no steps)? This is the concrete
mechanism the scoping doc's own "completeness thread" synthesis names as Nitin's own top strategic
risk, restated across both rounds of his feedback (`mentor-feedback-scoping.md`, "The completeness
thread" section). Before this capability, "is the corpus complete" was a qualitative worry;
`evaluate_completeness` makes it a deterministic query with a real, checkable answer (D5's own first
measurement: 100% at this minimal slice, for the current corpus).

## D2 — Why this is Layer-2-*adjacent*, not a Layer 2 peer in ADR-0021's strict sense

ADR-0021's Truth Hierarchy is explicit and, per Recommendation 11, mandatory for every Layer 2
capability: consume Historical Truth only, never a Layer 1 runtime contract directly. ADR-0023
itself is built strictly to this rule — `KnowledgeGraphService.build` takes exactly one parameter,
`HistoricalDatasetReference`, and Recommendation 1 states plainly that Knowledge Graph "never
imports a Layer 1 subsystem." This is precisely the boundary that made extending ADR-0023
impossible for this capability: `project_traceability_graph` takes a real `TestableRequirementSet`
(Layer 1) and a real `FeatureEngineeringPackage` (Layer 2) as direct parameters — genuine Runtime
Truth, not a `HistoricalDatasetReference`. Routing this data through the Historical Truth boundary
instead would require the real, multi-execution Historical Dataset ADR-0021 §Stage 6 reserves and
still does not exist (the same prerequisite already blocking the scoping doc's own completeness
sub-item) — and would be a poor fit regardless, since this capability's whole value is querying
*this run's own* fresh artifacts, not an accumulated cross-execution history.

**Consequence, stated honestly rather than glossed over:** this capability reuses Layer 2's
architectural *pattern* (typed nodes/edges, a deterministic pipeline, a governed vocabulary) without
satisfying Layer 2's own constitutional Truth Hierarchy placement (ADR-0021/ADR-0025). It is not,
in the strict sense those ADRs define, a Layer 2 peer of Continuous Improvement/Knowledge Graph/
Organizational Memory/Learning — it sits closer to Layer 1, reading Layer 1/Layer 2 Runtime Truth
directly, the same way `SpecificationEngineeringResult` (ADR-0030) does. **This capability's own
precise placement in the platform's layer model is left explicitly open**, mirroring ADR-0042
Decision 7's own still-open placement of `CAP-087`/Layer 2.5 — a future amendment to ADR-0020 (or
ADR-0031, the currently authoritative layer model) is the right place to resolve it, not this ADR.
What this ADR does lock is the architectural fact the placement question turns on: this capability
consumes Runtime Truth, by design, and that is exactly why it could not be built as an ADR-0023
extension.

## D3 — The containment invariant: independence from ADR-0023 enforced by test, not convention

`requirement_intelligence/traceability_graph/` never imports, calls, or modifies anything under
`requirement_intelligence/knowledge_graph/`. This is not a documentation-only claim:
`tests/unit/test_traceability_graph.py::TestScopeDiscipline::
test_does_not_import_the_frozen_adr_0023_service` walks every module's own AST and asserts no
`knowledge_graph` import exists anywhere in the package — the same containment-test discipline
ADR-0022 §D6/ADR-0023 §D6 already use to keep their own Layer 2 peers independent of each other,
applied here to keep this capability independent of the service it deliberately does not extend.
ADR-0023's own code is unmodified by this capability — referenced, never edited.

## D4 — The minimal slice, and the named deferred hops

The graph models `requirement → scenario → step` only. Each deferred hop is named explicitly, not
silently out of scope:

- **Page-object hop** (`scenario/step → page-object`) — the real data exists
  (`automation_engineering/generation/page_object_reference_derivation.py`'s own call-site
  derivation gives method-level step→page-object linkage) but is not wired into this graph. Per the
  scoping doc's own data-availability finding, this hop is also not live-wired by default in the
  generation pipeline itself (`cap-page-object-live-wiring-decision`).
- **Execution-result hop** (`step → execution-result`) — genuinely blocked. Layer 5
  (`test_execution`, `requirement_intelligence/run_state/stages.py` stage 17) carries
  `governing_citation="none yet"`; no execution outcome of any kind exists anywhere in this platform
  today.
- **Change-impact graph** (code/pages → elements → steps → scenarios) — a distinct capability the
  scoping doc's own design-surfacing task separately scoped; method-level linkage is buildable from
  the same page-object call-site data above, but element/selector-level mapping (Nitin's own
  "selector change → 8 affected tests" example) has no structured source anywhere yet.
- **State/flow graph** — named by Nitin as a fourth graph type but explicitly not prioritized by
  him; deferred without further design work here.

None of these require a redesign of this capability when built — each is an additive extension of
the same node/edge/traversal pattern (D2), not a change to what already exists.

## D5 — Scores-first: report-only completeness, and the first real measurement

`CompletenessReport` (`total_requirements`, `tested_requirement_count`,
`untested_requirement_count`, `coverage_percentage`, `untested_requirements` with a per-requirement
`reason`) is structured so a future gate could evaluate it directly — but **no gate, threshold, or
fail logic exists anywhere in this package**, enforced by the model's own consistency invariant
(counts must sum correctly) and nothing more. This was a deliberate choice, not an oversight: build
the measurement first, see the real numbers, decide gating with real data in hand rather than
against a guessed threshold — the same "a threshold locked against data collected before the
underlying defect is even fixable is a guess dressed as a number" discipline ADR-0047 D3 already
applies to a different metric, applied here to completeness gating instead of Sonar ratings.

**This is also why this ADR itself is written after the code, not before it** — the platform's own
standing discipline (every prior Layer 2 peer, ADR-0022/ADR-0023, froze architecture before any
engine code) was inverted here on purpose, to get a real measurement fast rather than spend a design
cycle on ceremony proportionate to a much larger capability. This ADR is the acknowledgment of that
inversion and the governance debt it created — see Consequences.

**The first real measurement, now recorded.** Run against a real live run's own artifacts
(`testable_requirement_set.json` + `feature_engineering_package.json`, not fixtures, not the
synthetic ADR-0023 provider — D6): 20 requirements, 20 scenarios, 67 steps, **100% requirement→
scenario→step coverage** — zero uncovered requirements, for this specific corpus. Cross-referenced
against the same run's `cp3_report.json` and `automation_engineering_package.json`: **34 of those
same 67 steps have no step-definition binding** (CP3: "34/67 steps unmapped, 49.3% step coverage,"
`overallVerdict: fail`; matching exactly 30 of 60 unique step-definition needs `escalated`, a clean
50/50 split). This is not a contradiction — it is two distinct, both-real completeness layers:
Gherkin-authoring completeness (this graph, 100%) and step-definition-binding completeness (CP3,
~49–50%) on the identical step set. A requirement this report counts as "covered" has a scenario and
steps written; it does not yet have a proven, passing generated test — precisely the gap D4's
deferred page-object/step-definition hop would need to close. Full detail:
`docs/architecture/mentor-feedback-scoping.md` item #3, "REAL COMPLETENESS MEASURED."

## D6 — Real data over synthetic: no historical-reference indirection

`project_traceability_graph` takes `TestableRequirementSet` and `FeatureEngineeringPackage`
directly as parameters — there is no `HistoricalDatasetReference`-shaped indirection layer and no
`HistoricalDatasetProvider`-shaped synthetic default. ADR-0023's own default provider
(`DeterministicHistoricalDatasetProvider`) SHA-256-synthesizes every id it emits, including the
"requirement" id — the live Knowledge Graph in production today is referentially disconnected from
this platform's real corpus. This capability's own D5 measurement is only possible, and only
meaningful, because it reads real ids from real artifacts from the start; introducing a synthetic
indirection layer here — even one that superficially mirrors ADR-0023's own shape — would have
reproduced the exact defect this capability exists to avoid.

---

## Consequences

- **Nitin's #1 strategic concern is now measurable, not just recorded.** The scoping doc's
  "completeness thread" synthesis moves from a qualitative risk to a real, re-runnable measurement
  (D5).
- **The governance debt this ADR closes.** This capability was built before this ADR existed — the
  inversion D5 names explicitly. This ADR is written *before any further extension* of the
  capability (the deferred hops in D4, or live wiring), exactly as the build's own memory record
  (`cap-traceability-graph-minimal-build`) recommended: close the debt before extending, not after.
- **Two follow-on governance actions are recommended, not performed here** (kept separate
  deliberately, mirroring how ADR-0046/ADR-0047's own amendment notes were recorded as distinct
  actions from the freeze itself): (1) a `docs/governance/platform-capability-matrix.md` entry for
  `CAP-088` — Traceability Graph, mirroring `CAP-087`'s own row, since `CAP-087` is confirmed the
  last assigned id in the `CAP-060…` Downstream/Future block (§3.1); (2) a
  `docs/architecture/architecture-baseline-v2.md` register entry recording this ADR and the D5
  measurement, mirroring how ADR-0046/ADR-0047 were each recorded there. Neither changes this ADR's
  own Decision text if performed later.
- **D2's placement question is open, not resolved.** A future ADR-0020 or ADR-0031 amendment should
  resolve where this capability sits in the platform's layer model — this ADR locks the
  architectural fact (Runtime Truth consumption) the placement decision turns on, not the placement
  itself.
- **Deferred, each with a named trigger (D4):** the page-object hop (trigger: a decision to wire
  page-object generation live, `cap-page-object-live-wiring-decision`); the execution-result hop
  (trigger: Layer 5 existing at all); the change-impact graph (trigger: its own separate
  design-then-build task); state/flow (trigger: a future, explicit decision to prioritize it — not
  made by Nitin to date); gating on top of `CompletenessReport` (trigger: a deliberate future
  decision, informed by D5's own first real numbers, never a silent addition).
- **Live wiring is not authorized by this ADR.** No `PlatformContext` composition-root method exists
  for this capability and none is added here — a future, separate milestone would design and build
  that, mirroring ADR-0022 §D11/ADR-0023 §D12's own runtime-integration pattern, including its own
  golden-baseline re-baseline if wired into the live Execution Package.

## Ownership, runtime position, governance

- **Owns:** the `requirement → scenario → step` traceability graph, its deterministic projection
  from real `TestableRequirementSet`/`FeatureEngineeringPackage` artifacts, and the corpus
  completeness report computed by traversing it.
- **Does not own:** the existing Knowledge Graph (`knowledge_graph/`, ADR-0023, unmodified) or any
  of its runtime objects; the page-object, execution-result, change-impact, or state/flow hops (D4,
  future, separate work); any gating or threshold decision over `CompletenessReport` (D5, future,
  separate decision); Layer 1/Layer 2 generation itself (`contracts/testable_requirement.py`,
  `feature_engineering/`, both read-only inputs, never modified).
- **Runtime position (not wired):** `TestableRequirementSet` + `FeatureEngineeringPackage` + on-disk
  `.feature` files → `project_traceability_graph` → `TraceabilityGraph` →
  `evaluate_completeness` → `CompletenessReport` → `render_completeness_json`/
  `render_completeness_report` (projection only, computes nothing). No pipeline stage, no
  `PlatformContext` method, no Execution Package artifact calls into this chain today; the one real
  measurement on record (D5) was produced by a standalone, uncommitted script harness reading a
  real run's own already-written artifacts, not a live pipeline invocation.
- **Governance:** registered as `CAP-088` (recommended, not yet entered in the capability matrix —
  Consequences) for the Requirement Intelligence Platform. This ADR is **Accepted** — the capability
  is not merely designed but built, tested, and measured once against real data, matching the bar
  ADR-0022/ADR-0023 each cleared before their own "Accepted" status, exceeding the bar ADR-0030 (a
  pure paper freeze, "Proposed") cleared for its own. No staged `CAP-088A/B/B.1/C` lettering is used
  — unlike ADR-0022/0023/0030, this capability was not built in separate, ADR-gated milestones; it
  was built once, out of the platform's own normal order, and this ADR records that fact rather than
  retrofitting a staged history that did not happen.
