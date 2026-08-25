# ADR-0052 — Cross-Corpus Requirement Completeness (CAP-091)

- **Status:** Accepted (2026-08-25 — the reader, comparison engine, and report this ADR designs are
  now all built and tested; see the three Implementation Notes below)
- **Date:** 2026-08-24
- **Supersedes:** nothing. **Amends:** nothing.
- **Governing design:** none — this ADR follows directly from the design-surfacing task
  (`docs/architecture/mentor-feedback-scoping.md`, the "#3a ARC OPENED" note, 2026-08-24) rather
  than a preceding `docs/proposals/*.md` document, mirroring ADR-0051's own precedent of an ADR
  written straight from a scoping-doc surfacing. That note is read in full before this ADR and is
  this ADR's own evidentiary basis; it is not re-derived here.
- **Depends on:** ADR-0021 (Cross-Execution Data Architecture — the Truth Hierarchy and the
  multi-execution corpus this capability reasons over); ADR-0023 §D9/§D10 (Knowledge Graph
  Framework — the frozen boundary this capability must respect: `HistoricalExecutionRecord`
  "never exported past the `knowledge_graph` package boundary," "deliberately replicated rather
  than shared"; this capability builds its **own**, disjoint reader instead of importing it, D3
  below); the Historical Dataset arc's piece 2/3
  (`requirement_intelligence/knowledge_graph/engine/file_historical_dataset_provider.py` — the
  real, dict-level, mixed-directory-tolerant extraction pattern this capability's own reader
  mirrors, never reuses); ADR-0032 (Layer 1 Capability Freeze — this capability is not subject to
  it, D4 below); ADR-0034/ADR-0042 (`TestableRequirementSet` — the real, already-emitted Layer 1
  artifact this capability reads, across many executions' own copies of it); ADR-0048
  (Traceability Graph — the closest architectural precedent: a new, disjoint, placement-open
  capability reading real artifacts directly, report-only, no gating, registered in the open
  `CAP-060…` block).
- **Runtime status:** Not applicable. This is a **pure Architecture & Governance Freeze** — no
  code is written, no Python package is created, no service exists, no `PlatformContext` method is
  added, no policy object is instantiated, no runtime behaviour changes, no version constant
  changes, and no existing pipeline stage is touched. Every model and collaborator named in this
  document is a **documented, dormant specification**, not an implementation — mirroring the
  posture ADR-0030 established for Executable Specification Engineering (CAP-087) before any of it
  was built. This document is the governance baseline a future, separate implementation milestone
  must build against without deviation.

## Problem

Both mentors independently named the same top strategic risk, in Nitin's own words: a "house of
cards" — if the input requirements themselves are an incomplete picture of what should be tested,
every downstream capability (grounding, quality governance, feature generation, the traceability
graph's own coverage report) is complete only *relative to* that incomplete set, and none of them
can see the gap. The traceability graph (CAP-088, ADR-0048) already answers a real, adjacent, but
different question — given the requirements that exist, is each one fully tested (100%
Gherkin-authoring coverage / ~50% step-definition-binding coverage, on the real 20-requirement
corpus) — by traversing a graph built *from* the requirement set. A missing requirement is not a
node that graph ever sees; it structurally cannot answer input/corpus completeness.

The scoping doc's own design-surfacing task (the "#3a ARC OPENED" note) read the real code and
governing ADRs directly to answer two questions this ADR now resolves: what, concretely, would a
cross-corpus completeness capability compute, and is it actually blocked the way an earlier
surfacing (before the Historical Dataset arc existed) recorded it as being. It found: no, not
blocked — the two things that previously blocked it (no real historical data to compare against;
an assumed need to lift ADR-0032's freeze) are both resolved. This ADR is the architecture that
design decision authorizes, written before any code, per the platform's own standing discipline
for a Layer 2(-adjacent) capability (ADR-0022/0023's own precedent) — explicitly **not** repeating
the traceability graph's own build-then-ADR inversion (ADR-0048 D5, itself named as governance debt
closed after the fact).

## Decision

Introduce a new, governed capability, **CAP-091 — Cross-Corpus Requirement Completeness**, that
owns one thing: assessing whether one execution's requirement set is anomalously incomplete
relative to the distribution of requirement counts this platform's own historical executions have
produced. Six decisions, each detailed below:

1. **The capability (D1)** — a completeness *assessor*, not a requirement *generator* or
   *inferrer*: it flags a run whose requirement count is a statistical outlier against history; it
   never invents, drafts, or recommends a specific missing requirement.
2. **The granularity (D2)** — per-run-total requirement-count comparison only, honestly recorded as
   coarser than a hoped-for per-component comparison, which the real data does not support today.
3. **The reader (D3)** — its own, disjoint Layer 2+ reader over `output/executions/`, mirroring the
   Historical Dataset arc's proven extraction pattern, never importing
   `HistoricalExecutionRecord`/`HistoricalDatasetProvider` from `knowledge_graph/` (ADR-0023
   §D9/§D10, frozen).
4. **Layer placement and the ADR-0032 freeze (D4)** — a Layer-2-adjacent capability with its
   placement left explicitly open (mirroring CAP-088's own ADR-0048 D2 precedent), registered in
   the open `CAP-060…` Downstream/Future block — outside both of ADR-0032's frozen ranges, so this
   capability is not freeze-blocked.
5. **The output (D5)** — a report, never a gate, in this ADR's scope: `CorpusCompletenessReport` is
   structured and gate-ready, but nothing in this capability evaluates it against a threshold or
   produces a pass/fail verdict (scores-first, mirroring CAP-088 D5 and CP7's own rating-gating
   sequencing).
6. **Scope boundaries and reserved future work (D6)** — internal-consistency checking and
   subset-not-everything prioritization are explicitly **not** part of this capability; each is
   named, with what would unlock it, never silently folded in.

---

## D1 — The capability: a completeness assessor, not a requirement generator

**What CAP-091 computes, precisely.** Given one execution's `TestableRequirementSet` (its
`requirements` count) and the distribution of requirement counts across this platform's own
historical executions (read from `output/executions/`), CAP-091 answers: is this run's count an
outlier against that distribution — and if so, by how much and against what baseline. It never
infers *which* requirement is missing, never drafts one, never modifies `TestableRequirementSet` or
any Layer 1 artifact. This is a deliberate, narrow scope: the "house of cards" risk is that an
incomplete set goes *undetected*, not that this platform can yet author the missing content — flag
first, closing the gap is separate, later, likely human-in-the-loop work this ADR does not design.

**The real signal this rests on, verified against the actual corpus, not assumed.** Requirement
counts across the 13 real, qualifying executions in `output/executions/` (piece 2/3's own
qualification rule: a real `manifest.json` plus a non-empty `testable_requirement_set.json`)
cluster at three distinct values — **15, 20, 30** — never a single constant. This is genuine,
non-trivial variance a statistical comparison can reason over (e.g., "this run has 8 requirements;
history clusters at 15/20/30; 8 is unusually low"). The mechanism is deliberately simple in this
ADR's own decided scope — distributional comparison (min/median/max, or an outlier-bound check),
never a new AI-judgment capability — consistent with D4's placement argument below.

## D2 — The granularity: per-run-total, a recorded limitation, not a defect

**What was hoped for, checked, and found not to hold.** A finer-grained comparison — "component X
usually yields N requirements; this run's component X has fewer" — was considered, since it would
be a sharper signal than a single run-level total. **Checked directly against the real corpus, this
does not hold today:** `component` and `functionalTag` are constant **within** every execution
checked — every requirement in a given run shares the identical value (this platform's ingestion is
evidently scoped to one source file/component per run today). Per-component comparison therefore
collapses to exactly the same signal as the coarser per-run total in every real execution this
platform has produced; building the finer-grained version now would add complexity with no
additional resolving power against real data.

**Recorded honestly as a limitation, the same way ADR-0042 records `Risk.category`'s coarseness**
(§Decision 1's own additive correction: a field kept in the frozen shape, honestly caveated, rather
than silently dropped or silently overclaimed). CAP-091's first build is **per-run-total
completeness only**. Per-component completeness is reserved (D6) — it needs either a real corpus
whose ingestion spans multiple components per run, or a future Layer 1 capability that partitions
runs by component, neither of which exists today.

## D3 — The reader: its own, disjoint reader, respecting the frozen boundary

**The constraint, quoted verbatim, unchanged since piece 3 confirmed it.** ADR-0023 §D10 (frozen
permanently): *"The resolved dataset is an implementation detail — never a runtime contract, never
Historical Truth, never Derived Knowledge, never exported past the `knowledge_graph` package
boundary."* And §D9 (frozen, reused from ADR-0022 §D9): `knowledge_graph`'s
`HistoricalDatasetProvider`/`HistoricalDataset`/`HistoricalExecutionRecord` are *"deliberately
replicated rather than shared"* from Continuous Improvement's own disjoint copy. **CAP-091 must
never import any of these three names from `knowledge_graph/`.**

**What CAP-091 builds instead — a new, disjoint reader, mirroring, never reusing, the proven
pattern.** The Historical Dataset arc's piece 2/3
(`FileHistoricalDatasetProvider`/`_all_requirement_ids`) already proved, against the real corpus,
that reading `output/executions/<run>/manifest.json` and `testable_requirement_set.json` at the
dict level — never `model_validate`, tolerant of missing/malformed entries and mixed-completeness
directories (piece 1/2's own round-trip-looseness and mixed-directory findings) — is a real,
working, tested pattern. CAP-091's own reader (a future, separate package's module, D6) repeats this
exact discipline independently: its own manifest/requirement-set reading logic, its own tolerance
rules, never a shared import across the package boundary. This is the same "deliberately replicated
rather than shared" discipline ADR-0022/ADR-0023 already established between Continuous Improvement
and Knowledge Graph, applied a third time.

**Consequence for the "unblock" framing.** Piece 3's own correction (`docs/architecture/mentor-
feedback-scoping.md`) already established this precisely: the Historical Dataset arc did not hand
CAP-091 a consumable type — it proved a pattern and produced the real, readable data CAP-091's own
reader depends on. This ADR treats that as settled, not re-litigated.

## D4 — Layer placement and why the ADR-0032 freeze does not apply

**The freeze's actual, narrow enforcement mechanism, read directly, not paraphrased.** ADR-0032's
Decision text: *"Layer 1 (Requirement Intelligence, including every capability redesignated to it
as a sub-capability by ADR-0031 D3 — CAP-083 Continuous Improvement, CAP-084 Knowledge Graph,
CAP-085 Organizational Memory, CAP-086 Learning Framework)... no new CAP number may be allocated in
the Layer 1 series"* — concretely, `CAP-001…073` and `CAP-081…086`. The freeze is scoped to those
two ranges, not to "any new judgment capability anywhere in the platform."

**The precedent, already exercised three times, not invented here.** `docs/governance/platform-
capability-matrix.md` §3.1's open-ended `CAP-060…` "Downstream/Future" block already hosts three
capabilities whose own placement in the layer model is explicitly ambiguous or Layer-1-adjacent:
**CAP-087** (Executable Specification Engineering, self-described "the platform's first Layer 2.5
capability"), **CAP-088** (Traceability Graph — ADR-0048 §D2 states its own placement is *"left
explicitly open... it sits closer to Layer 1, reading Layer 1/Layer 2 Runtime Truth directly"* —
and was never freeze-blocked), **CAP-089**, **CAP-090**. None of the four needed the freeze lifted.
**CAP-091, registered at the next unused id in that same block, follows the identical path.**

**Layer placement, stated honestly, mirroring CAP-088's own posture rather than asserting a clean
fit.** CAP-091 reads `TestableRequirementSet` (a Layer 1 artifact, via the permitted-export carve-out
already established by ADR-0032's carve-out #1) across many executions — a Historical-Truth-shaped
question, per ADR-0021. It is **not** a strict ADR-0021 Layer 2 peer of Continuous Improvement/
Knowledge Graph/Organizational Memory/Learning, because it does not resolve through a
`HistoricalDatasetReference`-shaped indirection (D3 explicitly rejects that indirection, for the
identical reason ADR-0048 D6 rejected it for the traceability graph: introducing a synthetic
stand-in here would reproduce the exact defect the Historical Dataset arc exists to avoid). Its
placement is therefore **left explicitly open**, exactly as CAP-087's and CAP-088's own placements
are — a future amendment to ADR-0020/ADR-0031 is the right place to resolve it, not this ADR.

**What CAP-091 must never do, as a direct consequence.** It must never modify, extend, or be folded
into any existing Layer 1 subsystem's own governed pipeline (CP1, enhancement, grounding, quality
governance, recommendation) — it only *reads* their already-emitted output. It must never allocate a
CAP number from the frozen ranges. Both constraints are structural, not aspirational — a future
implementation milestone that violated either would be out of policy under ADR-0032, regardless of
this ADR's own existence.

## D5 — The output: report-only, scores-first, no gating in this ADR's scope

**`CorpusCompletenessReport` (sketched, not built).** A structured, versioned result naming:
the run's own `execution_id` and observed requirement count; the historical distribution it was
compared against (sample size, min/median/max — D2's per-run-total granularity); an outlier flag
and a plain-language rationale (e.g., "8 requirements; historical median 20, minimum observed 15;
below the observed range"); and provenance — which historical executions contributed to the
distribution, so the assessment is always explainable back to real, named prior runs, mirroring the
"at least one reference" discipline ADR-0019 §D7 and ADR-0021 already establish for every other
derived conclusion on this platform.

**Report-only, deliberately, in this ADR's own decided scope.** Nothing in CAP-091's first
increment evaluates the report against a threshold or produces a pass/fail verdict — the same
scores-first discipline CAP-088 D5 applied to `CompletenessReport` and CP7's own rating-gating
sequencing applied before gating on Sonar ratings: measure first, on real data, before deciding
whether and how to gate. Whether and how this ever gates a release is **reserved, future,
governance work** — not decided by this ADR, and, per ADR-0049's Engineering Constitution Article
VII ("Deterministic Gates Decide"), any future gate would need to be a deterministic,
policy-governed verdict — a rule-based outlier check, of the kind D1 already scopes this capability
to, satisfies that constraint in principle; that decision is still separate, later work.

## D6 — Scope boundaries: what CAP-091 is not, and what is reserved

**NOT internal-consistency checking.** The design-surfacing task identified three structurally-real,
within-run checks (a requirement with zero acceptance criteria; a requirement with zero `tracesTo`;
a duplicate `contentHash` across the set) and checked them against the one real corpus available:
**all three currently fire on zero of 20 requirements** — every requirement has exactly one
acceptance criterion, `tracesTo` is the identical 50-item consolidated list on every requirement
(not a per-requirement provenance signal in practice), zero duplicates. Real, buildable, and
explicitly **out of this capability's scope** — reserved as a separate, future, freeze-free slice
(it needs no history, no cross-run reader, nothing this ADR designs), unlocked whenever a real
corpus with actual internal variance exists to ground it against, mirroring CAP-090's own honest
"contract-grounded, not incident-grounded" posture for checks with no observed defect yet.

**NOT subset-not-everything (intelligent prioritization).** A structurally different problem: which
requirements reach the LLM prompt during Layer 1's own generation is a change to Layer 1's own
runtime behaviour (Engineering Context Orchestration / prompt composition), not a post-hoc analysis
of an already-emitted artifact — the same distinction that makes D3/D4's arm's-length reader
possible for cross-corpus completeness but does not extend to this sub-question. ADR-0032's own text
names this exact case ("if the platform genuinely needs Layer 1 itself to change... the freeze-lift
path is real, slower work"). **Reserved, blocked on either an ADR-0032 freeze-lift (all three
preconditions, not just the one already met) or a fundamentally different framing** — neither
designed here.

**NOT the ingestion-funnel proxy.** JIRA-fetch-count vs. final-`TestableRequirementSet`-count
drop-off remains a separate, cheaper, narrower, already-named slice (the prior #3a surfacing) —
independent of CAP-091, not designed or precluded by this ADR.

**NOT gating (D5).** Reserved, future, separate governance decision.

**NOT per-component granularity (D2).** Reserved, blocked on either a real multi-component-per-run
corpus or a future Layer 1 capability that partitions runs that way.

---

## Consequences

- **The "house of cards" risk becomes measurable, not merely recorded**, mirroring exactly how
  ADR-0048's own D5 turned Nitin's qualitative coverage-completeness concern into a real,
  re-runnable measurement — this ADR is the architectural step before CAP-091's own first real
  measurement exists.
- **No governance debt created.** Unlike the traceability graph (ADR-0048 D5, built before its own
  ADR, explicitly named as debt), this ADR is written before any CAP-091 code exists — the standing
  discipline every other Layer 2(-adjacent) capability on this platform followed (ADR-0022,
  ADR-0023, ADR-0030, ADR-0051).
- **Two follow-on governance actions are recommended, not performed here** (kept separate,
  mirroring ADR-0048's own Consequences and ADR-0050/ADR-0051's precedent): (1) a
  `docs/governance/platform-capability-matrix.md` §5.14 entry for `CAP-091`, confirmed as the next
  unused id in the open-ended `CAP-060…` block; (2) an `docs/architecture/architecture-baseline-v2.md`
  §3 register entry recording this ADR, mirroring how CAP-088/089/090 were each recorded there.
  Neither changes this ADR's own decisions.
- **The build is explicitly a future, separate milestone.** This ADR authorizes, but does not
  perform, a new package's own reader (D3), report model (D5), and distributional comparison logic
  (D1/D2) — mirroring ADR-0030's own "governance baseline a future implementation milestone must
  build against" posture. No package name is reserved by code; `requirement_intelligence/
  corpus_completeness/` is named here as the intended future location, not created.
- **Funding/prioritization is not decided by this ADR.** Whether and when to actually build CAP-091
  remains the user's own resourcing decision, unchanged by this document's existence — this ADR
  only resolves that the architectural path is clear, not that building is scheduled.

## Ownership, scope, and governance

- **Owns:** the cross-corpus, per-run-total requirement-completeness assessment; its own, disjoint
  reader over `output/executions/`; the `CorpusCompletenessReport` shape (sketched, not yet built).
- **Does not own:** internal-consistency checking (D6, reserved, separate future slice);
  subset-not-everything prioritization (D6, reserved, freeze-gated, separate); any gating decision
  over its own report (D5, reserved); per-component completeness (D2, reserved); any existing Layer
  1 subsystem's own governed pipeline (read-only consumer, never modifies); the Knowledge Graph
  (`knowledge_graph/`, ADR-0023, never imported); the traceability graph (`traceability_graph/`,
  ADR-0048, a distinct capability, not extended or duplicated by this one).
- **Runtime position (built, not wired into any pipeline):** `output/executions/<run>/manifest.json`
  + `testable_requirement_set.json` (many executions, read by CAP-091's own reader) → distributional
  comparison (`CorpusCompletenessEngine`) → `CorpusCompletenessReport` (report-only). All three exist
  and are tested (Implementation Notes below); no pipeline stage, no `PlatformContext` method, no
  Execution Package artifact wires this chain into any live run today — that remains future,
  separate, deliberate work, not decided by this ADR (Consequences).
- **Governance:** registered as `CAP-091` (recommended, not yet entered in the capability matrix —
  Consequences), in the open `CAP-060…` Downstream/Future block, outside ADR-0032's frozen `CAP-
  001…073`/`CAP-081…086` ranges (D4). This ADR is **Accepted** (2026-08-25): the reader (piece 1),
  comparison engine (piece 2), and report (piece 3) this ADR designs are now all built and tested —
  clearing the same "Accepted" bar ADR-0022/ADR-0023/ADR-0048 each cleared only once real, tested
  code existed behind them, not merely the lower "Proposed" bar ADR-0030 (CAP-087) accepted for an
  architecture-only freeze. Not wired into any live pipeline — that is separate, future, deliberate
  work this ADR does not authorize or schedule.

## Implementation Note (2026-08-25) — Piece 1: the reader

Built, additive, does not change any decision above: `requirement_intelligence/corpus_completeness/`
(D3's named future location) now exists, holding `CorpusExecutionReader`/`CorpusExecutionRecord` —
CAP-091's own, disjoint reader over `output/executions/`. It enumerates each run directory and reads
`manifest.json`/`testable_requirement_set.json` at the dict level (never `model_validate`),
extracting `execution_id`, `completed_timestamp`, `requirement_count` (D1's core signal), and the
representative (first-requirement) `component`/`functional_tag` (D2's honestly-available, currently
non-differentiating extra fields) per qualifying run — mirroring, never importing, the Historical
Dataset arc's own file-based-provider extraction discipline (piece 2/3). A malformed or partial run
directory (missing manifest, missing/empty requirement set, unparseable JSON) is silently skipped,
never fabricated, identically to that provider's own tolerance rules.

Proven against the real corpus, not only fixtures: 13 of 26 real run directories under
`output/executions/` qualify, and their extracted requirement counts cluster at exactly 15/20/30 —
confirming, with the reader's own code rather than an ad hoc script, the distributional signal D1
asserts. 22 new fixture-based unit tests (`tests/unit/test_corpus_execution_reader.py`) cover
extraction, chronological enumeration, mixed-directory tolerance, and determinism; a dedicated test
statically parses the reader module's own imports and asserts none names `knowledge_graph`,
proving D3's boundary holds, alongside a plain `grep` over the new package showing the same. `make
lint`/`make test` green (6167 passed, up from the 6145 baseline); mypy strict clean on the new
package, no rise in the platform's existing informational mypy baseline (436 pre-existing errors,
none in `corpus_completeness/`).

**Not built by this piece:** the distributional comparison (D1/D2) and `CorpusCompletenessReport`
(D5) remain entirely unbuilt — this piece only enumerates and extracts. This ADR's Status stays
**Proposed**; per this document's own Governance section, it moves to Accepted only once a future
milestone builds and tests the comparison engine and report as well, not on the reader alone.

## Implementation Note (2026-08-25, same day) — Piece 2: the comparison engine

Built, additive, does not change any decision above. `requirement_intelligence/corpus_completeness/
engine.py` now holds `CorpusCompletenessEngine`, reading THROUGH piece 1's reader — never
re-implementing corpus access — to assess a given run's requirement count against the historical
distribution (D1/D2).

**The one real design decision this piece carries, made and recorded rather than assumed.** D1 named
the mechanism only as "distributional comparison ... never a new AI-judgment capability," leaving the
concrete anomaly rule open. Checked directly against the real distribution piece 1 extracts (13
qualifying runs: 15×3, 20×7, 30×3 — mean 21.15, population stddev 5.25), a continuous-stats model does
not fit: one stddev below the mean (~15.9) sits ABOVE the real, three-times-repeated 15-cluster, so a
z-score rule would misflag a normal, recurring historical value as anomalous. The chosen rule is
**BELOW-HISTORICAL-MINIMUM** — a run's count is flagged only when it falls below the lowest count this
platform's real history has ever produced. This makes no assumption about the distribution's shape,
never flags an already-observed value, and yields a transparent, one-sentence rationale ("count 5 is
below the historical minimum of 15 (n=13, median=20, max=30)") rather than an opaque score. On the
real data BELOW-HISTORICAL-MINIMUM and BELOW-THE-LOWEST-CLUSTER coincide exactly (15 is both), so no
separate framing needed resolving. **Recorded as a genuine judgment call, not fully forced by the
data's shape — flagged here for Nitin's confirmation before this ever gates anything.** Low-risk to
revisit: D5 keeps this capability report-only, so a different threshold later is a non-breaking
change, not a correction to anything currently depended on.

**Cold-start honesty, per D1's "never fabricates."** Below `MIN_SAMPLE_SIZE_FOR_ASSESSMENT` (3 — the
smallest cluster size, shared by the 15- and 30-clusters, the real corpus has ever actually produced)
the engine returns `AssessmentStatus.INSUFFICIENT_HISTORY` with `flagged=False` and an honest reason,
never a forced verdict — proven for 0, 1, and 2 prior runs; the real 13-run corpus clears the bar with
room to spare.

**Report-only, structurally, not just by convention (D5).** `CompletenessAssessment` is a plain,
immutable dataclass with no method whose name contains "gate," "block," "fail," or "raise" — a
dedicated test asserts this directly by introspecting the type. `assess()` never raises on a flagged
result; it returns a value like any other.

**Per-run granularity, structurally (D2).** `assess()`'s public signature takes a bare
`requirement_count: int`, not a requirement object or a component/tag parameter — there is no API
surface to assess anything finer-grained than the per-run total.

**Boundary held (D3 / ADR-0023 §D9/§D10).** Zero `knowledge_graph` imports, proven the same two ways
as piece 1 (a package grep, and a dedicated AST-based test parsing the engine module's own imports).

**Proven against the real corpus, not only fixtures.** Assessing hypothetical counts against the real,
current 13-run distribution: a normal count (20) and the real minimum itself (15) are both correctly
NOT flagged; an anomalously low count (5) IS flagged, with the expected reason; a count above the real
maximum (35) is correctly NOT flagged — D1's scope is incompleteness (low counts), not general
outlier detection, so an unusually high count is deliberately not this capability's concern.

16 new fixture-based unit tests (`tests/unit/test_corpus_completeness_engine.py`), reading through a
real `CorpusExecutionReader` over a fixture corpus shaped like the real cluster distribution (never
the real gitignored `output/executions/` in committed tests). `make lint`/`make test` green (6183
passed, up from the 6167 post-piece-1 baseline); mypy strict clean on the new module, no rise in the
platform's existing informational mypy baseline (436 pre-existing errors, none in
`corpus_completeness/`).

**Not built by this piece:** `CorpusCompletenessReport` (D5) — the reader and engine only enumerate,
extract, and assess; nothing renders or serializes an assessment into the report shape D5 sketches.
This ADR's Status stays **Proposed** until that piece exists and is tested too.

## Implementation Note (2026-08-25, same day) — Piece 3 (final): the report; CAP-091 complete

Built, additive, does not change any decision above. `requirement_intelligence/corpus_completeness/
report.py` now holds `CorpusCompletenessReport` and `build_corpus_completeness_report` — the report-
only surfacing D5 sketched but left unbuilt. It carries no new design decision: it is a pure,
deterministic projection of piece 2's own `CompletenessAssessment` into D5's own vocabulary
(`outlier` for `flagged`, `rationale` for `reason`), passing `execution_id`, `requirement_count`,
`status`, and `distribution` straight through.

**Mirrors the platform's other report-only governance shapes, deliberately.** Both
`suite_quality_governance.cp7`'s own whole-suite quality report and the traceability graph's own
completeness report (ADR-0048) are plain, immutable results with no `overall_verdict`/`passed`/gate
field — a report presents a measurement, never decides pass/fail. `CorpusCompletenessReport` follows
the identical discipline, proven the same way CP7's own report is: a dedicated test asserts
`not hasattr(report, "overall_verdict")` / `not hasattr(report, "passed")` /
`not hasattr(report, "gate")` and pins the type's exact field set via `__dataclass_fields__`
(`execution_id`, `requirement_count`, `status`, `distribution`, `outlier`, `rationale` — nothing
else), plus a second test confirming no gate/block/fail/raise-shaped method exists on the type at
all, mirroring piece 2's identical structural proof on `CompletenessAssessment`.

**The transparent reason and cold-start honesty both carry through unchanged.** A flagged assessment
surfaces `outlier=True` with the same plain-language rationale piece 2 produced ("count 5 is below
the historical minimum of 15 (n=13, median=20, max=30)") — never an opaque score. An
`INSUFFICIENT_HISTORY` assessment (a thin corpus) surfaces that status and `outlier=False` honestly,
never a fabricated verdict — proven for both a 1-run corpus (a partial `distribution` still present,
for transparency) and a 0-run corpus (`distribution=None`).

**Scope discipline held.** D1's incompleteness-only scope carries through: a count far ABOVE the
historical maximum surfaces `outlier=False`, exactly as piece 2 computed it — the report never widens
the engine's one-sided signal into general outlier detection. Not wired into any live pipeline
(deliberately, mirroring how CP7's and the traceability graph's own reports were built report-only,
not-wired, first) — that remains separate, future, deliberate work.

**Boundary held (D3 / ADR-0023 §D9/§D10).** Zero `knowledge_graph` imports, proven the same way as
pieces 1 and 2 (a package grep, and a dedicated AST-based test parsing the report module's own
imports).

**Proven end-to-end against the real corpus, not only fixtures.** The full chain — reader → engine →
report — run over the real, current `output/executions/` corpus (13 qualifying runs, min=15/
median=20/max=30): a normal count (20) and the real minimum itself (15) both surface `outlier=False`;
an anomalously low hypothetical count (5) surfaces `outlier=True` with the expected rationale and
full provenance (13 contributing execution ids); a count above the real maximum (35) surfaces
`outlier=False`. CAP-091's cross-corpus completeness capability works end-to-end on real data.

11 new fixture-based unit tests (`tests/unit/test_corpus_completeness_report.py`), including one
exercising the full reader→engine→report chain over a fixture corpus shaped like the real cluster
distribution (never the real gitignored `output/executions/` in committed tests). `make lint`/`make
test` green (6194 passed, up from the 6183 post-piece-2 baseline); mypy strict clean on the new
module, no rise in the platform's existing informational mypy baseline (436 pre-existing errors, none
in `corpus_completeness/`).

**CAP-091 is now complete.** All three pieces this ADR designs — the disjoint reader (D3), the
distributional comparison engine with its below-historical-minimum anomaly rule (D1/D2), and the
report-only surfacing (D5) — are built and tested, end-to-end, against real data. This ADR's own
condition for Accepted (Governance, above) is met; **Status moves from Proposed to Accepted** as of
this note. Not wired into any live pipeline or `PlatformContext` composition root — that remains a
separate, deliberate, future decision, exactly as D5/Consequences always scoped it to be.
