# Mentor Feedback — Scoping Document

| Attribute | Value |
| --- | --- |
| Document type | Decision-support analysis (not an ADR, not governance) |
| Status | Analysis only — no code, no ADR, no register entry produced by this document |
| Scope | The mentor's 8 feedback items, plus Nitin's reply, assessed against the platform's real, current architecture |
| Method | Every claim below is verified against a real artifact (an ADR's own Status line, real code, the register) as of this document's own date. Where this document's characterization of an item differs from the source feedback's own framing, that is called out explicitly — the artifacts win. |
| Date | 2026-08-11 |
| Owner | None yet — this is analysis; adoption of any item is a future, separate decision (per-item ADR/task) |

> **How to read this document.** Eight assessment blocks, one per mentor item, each ending in a
> recommendation. A synthesis section groups the eight by disposition and proposes a sequence — a
> recommendation, not a lock. The user decides what gets built and in what order.

---

## Pre-flight

Clean tree, `main`, tip `54e800b` (the promotion-multi-method-gap surfacing, committed). `make lint`
clean. `make test`: 5736 passed, unchanged. This document adds one new file; nothing else in the
repository is touched.

---

## Ground truth consulted

- **Layer/CP model:** ADR-0031 (Authoritative Layer Model, Accepted), ADR-0040 (Control Point Model,
  Accepted) — read directly (already in this session's own working context from the register's own
  ADR-summary table, §2, cross-checked against the ADRs' own Status lines below).
- **Live stage roster, ground truth for what's built vs. reserved:**
  `requirement_intelligence/run_state/stages.py::STAGE_DEFINITIONS` — read directly. This is the
  single most authoritative source in the repository for "what actually runs" (every stage's own
  `layer`/`governing_citation`, and the derived `LIVE_STAGE_IDS` tuple).
- **The ADR-0020 lineage (constitution + Continuous Learning capabilities):** ADR-0020, 0021, 0022,
  0023, 0024, 0025, 0026, 0027, 0028, 0029, 0030 — each read at least at its own Status/Depends-
  on/Runtime-status header. This lineage turned out to be the single largest, most consequential
  discovery of this scoping pass (see items #3 and #5 below) — it was not part of this session's
  prior working context and is reported here for the first time.
- **Track governance:** ADR-0038 (Documentation Track Governance, Accepted) — Track A
  (`docs/adr/`, `docs/architecture/`, `docs/governance/`, `docs/proposals/`, `docs/reviews/`,
  `docs/releases/`) is normative; Track B (`docs/product/`, `docs/handbook/`, `docs/standards/`) is
  declared non-normative and frozen.
- **The generation/prompt model:** `automation_engineering/stage/runner.py`, the `LiveStepDefinitionGenerator`/`LivePageObjectGenerator` family, `scripts/run_requirement_analysis.py`'s own
  `STEP_DEF_GEMINI_MODEL` scoping — read in depth in prior sessions this arc and re-confirmed here.
- **The provider seam:** `requirement_intelligence/llm/providers/` (`base_provider.py`,
  `gemini_provider.py`, `azure_openai_provider.py`), `llm_factory.py`, `provider_registry.py` — read
  directly.
- **L1 ingestion:** `requirement_intelligence/connectors/jira/connector.py` — read directly.
- **Completeness usage today:** grepped across `requirement_intelligence/` — found in
  `enhancement/`, `grounding/`, `recommendation/`.
- **The register:** `docs/architecture/architecture-baseline-v2.md` — consulted for L1 freeze
  (ADR-0032's carve-outs), CP7 gating (item 34), and the open-latents section (§4a).

---

## The 8 assessment blocks

### Item 1 — Nitin's reply (cross-cutting)

Nitin's reply is not one item — it is eight compact points that partly overlap the mentor's own
eight, and partly stand alone. Mapped as instructed, then the standalone remainder assessed on its
own:

| Nitin's point | Maps to | Treatment |
| --- | --- | --- |
| Constitution | #5 | See #5 below — not re-analyzed here |
| Agent/re-run token loss | #2 | See #2 below — not re-analyzed here |
| Knowledge Graph | #3 | See #3 below — not re-analyzed here |
| Input quality | #3 (subset/completeness) | See #3 below — not re-analyzed here |
| Pass-bias meaning-check | *(not covered elsewhere)* | Own sub-item, below |
| Catalog hygiene thresholds | *(not covered elsewhere)* | Own sub-item, below |
| Eval harness with golden sets | *(not covered elsewhere)* | Own sub-item, below |
| Playwright | *(not covered elsewhere)* | Own sub-item, below |

**Pass-bias meaning-check.** Verified a concrete, real instance of exactly the shape Nitin is
warning about, not a hypothetical: the platform's own `CP1CriterionRegistry`-style composition rule
(reused verbatim by CP7's rating gate, register item 34) treats an **unmeasured** metric as `WARN`,
never `FAIL` (`FAIL > WARN > PASS`). This is a real, already-made, already-documented design
tradeoff (a metric the server genuinely has no value for should not silently fail a gate it was
never able to evaluate) — but it is also *exactly* the kind of judgment call a "pass-bias
meaning-check" review exists to interrogate: does `WARN` read, downstream, close enough to `PASS`
that an unmeasured criterion is effectively invisible to whoever consumes the aggregate verdict?
**Recommendation:** a small, standalone audit task — walk every `WARN`-not-`FAIL` judgment call
across CP1–CP8 and confirm each is still the right call, not a redesign. Low risk, no ADR
amendment implied unless the audit finds something to change.

**Catalog hygiene thresholds.** The reuse engine's `DEFAULT_CONFIDENCE_THRESHOLD`
(`automation_engineering/reuse/engine.py`) is a real, governed, single constant — reuse-matching
hygiene already has a threshold. What does **not** exist: any periodic/scheduled catalog
maintenance (pruning stale or superseded assets, auditing drift) — promotion only ever *adds*
catalogued assets; content-hash duplicate detection runs at promotion time, not as a standing
hygiene pass over the whole catalog. **Recommendation:** a genuinely absent, small-to-medium future
capability if this becomes a real problem (catalog growth is still young) — not urgent today.

**Eval harness with golden sets.** Already built, but for a materially different purpose than this
point likely intends: `tests/productization/test_golden_baseline.py` /
`tests/productization/fixtures/golden_dataset.py` is a **schema/determinism regression harness** —
does the platform's own deterministic output structure still match a frozen baseline across
capability milestones (re-baselined at nearly every CAP built this arc, most recently `1.5.0` →
`1.6.0` for the Knowledge Graph runtime activation). It is **not** an LLM-output-*quality* eval
harness (grading whether a generated step-definition or page object is *good*, against curated
exemplars) — that capability does not exist; this arc's own defect-finding (the page-object
live-regen defects, the `gemini-2.5-flash` 76%-defect-rate measurement) was done as ad hoc,
one-off live runs, not a standing harness. **Recommendation:** clarify with the mentor which one
they mean — the existing mechanism already satisfies "golden-set regression"; a quality-grading
harness would be new, real work.

**Playwright.** Not built. Two possible homes exist, verified, with materially different cost:
(a) `docs/adr/0030-executable-specification-engineering.md` (CAP-087, **Proposed**, Layer 2.5's own
placement still unresolved per ADR-0031 §D4/ADR-0042 Decision 7) already designs a governed
`RendererRegistry` where "Adding Playwright, Selenium, API Test Specifications... is therefore
purely additive... zero architectural redesign" — but this depends on an ADR that is not yet
Accepted and a capability whose own placement in the layer model is still an open question. (b) A
direct amendment to **ADR-0041** (Accepted, locks Selenium 4.25.0 for the current
`test-suite-baseline/` generated suite) — technically possible but genuinely disruptive to a frozen,
shipped decision, for a renderer the platform has already designed a cleaner extension point for
elsewhere. **Recommendation:** defer to CAP-087's own resolution; do not amend ADR-0041 directly.

**Agent/re-run token loss (deltas/re-run cost).** Overlaps item #2, but its specific "don't re-pay
the full cost on every re-run" angle is **already substantially solved**, and by a foundational,
Accepted mechanism: `RunStateManager.should_skip(stage_id, input_artifacts=, output_artifacts=)`
(ADR-0036) is used by every stage this platform runs (`execute_automation_engineering_stage` and
its siblings all call it) to skip unchanged work on resume. This is a strong already-done finding,
not a gap.

---

### Item 2 — Skills-first, agents-next (token minimization)

**What it is:** prefer small, deterministic, narrowly-scoped LLM calls ("skills") over autonomous,
multi-step agent loops, to keep token spend low and behavior predictable.

**What it touches:** the entire generation architecture — `automation_engineering/generation/`,
`automation_engineering/stage/runner.py`, the prompt registry (ADR-0014), Engineering Context
Orchestration (ADR-0015/CAP-076).

**Already-partly-done?** Yes — and more completely than the mentor's own framing may assume. There
is no agent/tool-loop architecture anywhere in this platform. Every LLM call verified this arc
(`LiveStepDefinitionGenerator`, `LivePageObjectGenerator`, `LiveFeatureRemediator`, `LiveUtilityGenerator`) is a single-shot, stateless, narrowly-scoped call, sequenced by ordinary
Python control flow (a per-need `for` loop in `stage/runner.py`), never an autonomous agent
deciding its own next step. The platform never reached for "agents" in the first place — it is
already "skills-first" in the strongest sense: there is nothing to migrate away from. Token
minimization already has a concrete, Accepted, live mechanism: CAP-076D's "water-filled evidence
budget" for Engineering Context Orchestration prompt assembly (this session's own persistent
context), plus per-stage model scoping (`STEP_DEF_GEMINI_MODEL`) that right-sizes model cost per
call type rather than using one model for everything.

**Additive vs amends-frozen:** neither — this affirms existing, Accepted architecture. No ADR
conflict.

**Effort + blast radius:** none, if the ask is "adopt this principle" (already true). If the mentor
means something more specific not yet identified, effort is unknown until clarified.

**Consensus signal:** high — Nitin's "agent/re-run token loss" raises the same theme independently.

**Recommendation: clarify-with-mentor.** The platform likely already satisfies the spirit of this
suggestion. Worth asking directly: is there a *specific* gap in mind (e.g., concern about a future
Layer 6 self-healing loop — the one place in the roadmap where something agent-shaped might
plausibly first be considered, and which does not exist yet, register-confirmed "none yet")?

**CLARIFICATION RECEIVED (2026-08-11) — Nitin's actual meaning, and a correction to this block's
own prior framing.** Nitin clarified what "skills-first, agents-next" means: decompose the
platform's work into discrete, **named, reusable SKILLS** (e.g., a code-generation skill, a
linting/quality-check skill) as the default building block wherever possible, and reserve
**agents** for the specific places genuine autonomy is actually needed — skills where you can,
agents where you must. This connects to a separate, earlier point of his: codify knowledge as
skills first (viable even inside a single-agent harness), then layer multi-agent structure on top
only where warranted — the same "skills as the primary abstraction, agents added where needed"
idea, restated.

**This is a real gap, not the already-partly-done finding above.** The assessment above answered a
different question than the one Nitin was actually asking. "Is generation wastefully
multi-agent?" — no, confirmed, and that finding stands (there genuinely is no agent/tool-loop
architecture here). But that is not the same question as "is the platform's work organized as a
composable catalog of discrete, named, individually-invokable skills?" — and the honest answer to
*that* question is also no: the platform has generator *classes*
(`LiveStepDefinitionGenerator`, `LivePageObjectGenerator`, and siblings), each doing one job well,
but they are not exposed, named, or governed as a first-class **skill catalog** the way, say, the
prompt registry (ADR-0014) governs prompts as first-class, versioned, registered objects. Being
single-shot is not the same as being skill-structured. The "already-partly-done" reading above is
corrected, not retracted — it remains true and worth keeping (the platform really did avoid the
specific failure mode of wasteful multi-agent looping) — but it does not answer what Nitin was
actually asking, and #2 should now be treated as a real, open item.

**The sizing question this raises — recorded, not answered here.** Whether adopting a skill-catalog
structure is a **re-framing** (the existing generator classes are already effectively discrete
skills — just not named, registered, or exposed as a catalog; making them first-class may be mostly
organizational: a registry, a consistent interface, consistent naming, mirroring the prompt
registry's own shape) or a genuine **re-architecture** (a real skill-selection/routing layer, skills
as independently-invokable units with their own governed contracts, agent-vs-skill routing decided
per step) is not determined by this note. That is exactly the question a future #2
design-surfacing task would need to resolve, by reading the real generator/orchestrator structure
in `automation_engineering/generation/` and `stage/runner.py` against what a genuine skill catalog
would require — not assumed here either way.

**Recommendation, updated:** from `clarify-with-mentor` (now done — see above) to
**surface-as-own-design-task** — the next step is a dedicated design-surfacing task to resolve the
re-framing-vs-re-architecture sizing question above, not a build.

---

### Item 3 — Requirements Intelligence: subset-not-everything + completeness + Knowledge Graph (Neo4j)

**What it is:** don't feed the whole requirement corpus into every LLM call; build in a genuine
completeness check (are we missing requirements, not just are existing ones well-formed); build a
Neo4j-style knowledge graph over requirements.

**What it touches:** Layer 1 (frozen by **ADR-0032**), the JIRA connector
(`requirement_intelligence/connectors/jira/connector.py`), and — the single largest discovery of
this scoping pass — an entire pre-existing "Continuous Learning" lineage: ADR-0020 (Superseded),
0021/0024/0025/0026/0028 (all **Proposed**), 0022/0023/0027/0029 (all **Accepted, live**), and the
already-built `requirement_intelligence/knowledge_graph/` package (~35 files: models, a governed
rule catalog, a deterministic engine, node/edge projectors, a subgraph detector).

**Already-partly-done? — the honest answer has three different parts, and they differ sharply:**

1. *Subset-not-everything (ingestion volume).* **Partially.** The JIRA connector already has an
   "upper bound on total issues fetched, guarding against unbounded pagination," plus an optional
   `jql` restriction that "scopes retrieval at the source." Real, but coarse — a volume cap and an
   optional manual filter, not intelligent prioritization of *which* requirements matter most.
2. *Completeness.* **Partially, at the wrong grain.** `completeness` already appears as a real
   concept in `enhancement/` (rules, policy) and `grounding/` (metrics) — but scoped **per
   requirement** (is this one requirement's own fields/acceptance-criteria complete), never
   **across the corpus** (are we missing whole requirements, or the relationships between them).
   The corpus-level question — the one both mentors are actually worried about — is genuinely new.
3. *Knowledge Graph (Neo4j).* **Substantially built, but not what was asked for.** ADR-0023
   (Accepted; "Runtime status: **Live**," CAP-084C) built a real, governed, deterministic
   `requirement_intelligence/knowledge_graph/` subsystem — typed `KnowledgeNode`/`KnowledgeEdge`/
   `KnowledgeSubgraph` models, a `DeterministicKnowledgeGraphEngine`, projected into the Execution
   Package (`knowledge_graph_result.json`/`report.md`/`metrics.md`). But: **(a) it is not Neo4j** —
   a bespoke, in-repo, pure-Python deterministic model; no graph database anywhere in this stack
   (grepped, confirmed absent). **(b) It answers a different question** — "how does everything in
   this platform relate to everything else" (which requirement traces to which evidence/module/
   finding), a cross-subsystem structural graph, not specifically a requirement-completeness
   reasoning tool. **(c) It is honestly documented as running on a thin proxy today** — ADR-0023's
   own Runtime-status line: "over a single-execution `HistoricalDatasetReference`... no real,
   multi-execution Historical Dataset implementation exists yet (ADR-0021 §Stage 6)." The graph
   the mentor is picturing would need that real, multi-execution dataset to have anything
   meaningful to reason over — and that prerequisite is itself unbuilt, and its own governing ADR
   (0021) is still **Proposed**.

**Additive vs amends-frozen — the real conflict.** Genuine corpus-level completeness reasoning and
intelligent subsetting are new **Layer 1** reasoning. ADR-0032 froze Layer 1 ("no new Layer 1 CAP
number without a lifting ADR"), with exactly five carve-outs (emitting `TestableRequirement`,
run/stage-state integration, ADR-0033 renames, bugfixes, tests) — none of which cover this. The
existing Knowledge Graph (ADR-0023) predates the freeze and was grandfathered in as part of "the
current baseline" at freeze time (dated 2026-07-15/16, before ADR-0032's 2026-07-24); a *new*
completeness capability would not get that same grandfathering — it would need to either lift the
freeze (a real, separate governance action, mirroring how ADR-0043 had to investigate — and fail —
a freeze-lift for Layer 2) or be scoped as an arm's-length **Layer 2+** consumer that never touches
Layer 1's own frozen internals, the same pattern Continuous Improvement/Knowledge Graph/Learning
already use against Historical Truth.

**Effort + blast radius: LARGE.** Even the cheapest real path requires: (1) resolving the
freeze-question first (its own small design task); (2) a genuine multi-execution Historical Dataset
(ADR-0021 §Stage 6) — a real prerequisite the *existing* Knowledge Graph is itself still waiting on,
not something this new work would be first to need; (3) a deliberate choice between extending the
already-built deterministic KG engine vs. introducing Neo4j as new infrastructure (no graph DB
dependency exists anywhere today).

**Consensus signal: highest of all eight items.** Both mentors flag this independently (Nitin's
"house of cards"/input-quality framing; the mentor's completeness + KG framing) — this is squarely
both mentors' shared #1 strategic risk, even though it is also the heaviest single item on this
list.

**Recommendation: surface-as-own-design-task**, not adopt-now. The single highest-leverage next
question — cheaper to answer than the whole item — is: **can requirement completeness be scoped as
a new, arm's-length Layer 2+ consumer of `TestableRequirementSet` (mirroring Continuous
Improvement/Knowledge Graph's own existing pattern against Historical Truth), avoiding the
ADR-0032 freeze-lift question entirely?** If yes, this item's blast radius shrinks dramatically. If
the platform genuinely needs Layer 1 itself to change (e.g., ingestion-time prioritization), the
freeze-lift path is real, slower work. Either way: a dedicated design-surfacing task, before any
code, exactly like the #3+#6 page-object-wiring and #1 promotion-multi-method decisions already
made this arc.

---

### Item 4 — Spec-based development (features, page objects, artifacts)

**What it is:** drive generation from structured specifications (feature files, page-object
contracts, typed artifacts) rather than ad hoc free-text prompting.

**What it touches:** `TestableRequirementSet` (ADR-0034/0042), Gherkin `.feature` files (ADR-0043),
`automation_engineering/generation/page_object_reference_derivation.py` (ADR-0044 D4), the prompt
registry (ADR-0014).

**Already-partly-done? Yes — substantially, and this is one of the platform's own deepest,
already-deliberate architectural choices.** Three concrete, verified instances: (1) `TestableRequirementSet` is itself a structured, versioned, schema-checked spec-contract between
Layer 1 and Layer 2 — never free text. (2) A `.feature` file is the canonical spec Layer 3 generates
against (ADR-0043); no LLM decomposition of raw requirement text happens downstream of it. (3) Most
precisely on-point: ADR-0044 D4's own explicit design rationale (verified in depth this session) —
"which specific method a not-yet-written step definition will call is NOT KNOWABLE UNTIL a future
generator actually writes that call" — so page-object generation requests are **derived from
already-generated code's own call sites**
(`page_object_reference_derivation.py::derive_page_object_requests`), never inferred from prose.
The call site literally *is* the spec. This is close to a literal match for the mentor's own
"features, page objects, artifacts" framing, already built and tested.

**Additive vs amends-frozen:** neither — affirms existing, Accepted architecture (ADR-0043, ADR-0044
D4, ADR-0014). If the mentor means something larger — e.g., CAP-087/ADR-0030's own proposal that a
canonical domain model, not Gherkin itself, should be the true source or truth, with Gherkin as one
of several renderers — that is a materially different, larger, still-Proposed ask tied to the same
unresolved Layer 2.5 placement question flagged under item #3.

**Effort:** none for what already exists. CAP-087, if that is the real ask, is its own large,
already-Proposed-but-unresolved item.

**Consensus signal:** not raised by Nitin's own points as listed.

**Recommendation: clarify-with-mentor.** Very likely already substantially satisfied by the current
Gherkin/call-site-derivation chain. Ask specifically whether the suggestion means the current chain
(done) or CAP-087's own canonical-domain-model idea (a materially bigger, still-open ask).

---

### Item 5 — Centralized constitution

**What it is:** one canonical document stating the platform's engineering/behavioral principles.

**What it touches:** ADR-0020 (**Superseded by ADR-0031**, but literally titled "Platform Evolution
Roadmap & **Architectural Constitution**," and its own text: "it is the platform's architectural
constitution"); the full constitutional-tier lineage — ADR-0021/0024/0025/0026/0028, **every one of
them still Proposed, never Accepted**; `docs/standards/STD-000-platform-constitution.md`; ADR-0038
(Track A/B governance, Accepted).

**Already-partly-done? Yes — richly, but fragmented in a way that is itself the finding.** This is
not a novel idea for this platform; "constitution" is already a recurring, deliberately-used
architectural term here. But: ADR-0020, the *original* single constitution, is Superseded — its
layer/lifecycle content lives on inside ADR-0031 (Accepted), but its Vision/Philosophy content's
current authoritative home is unclear (echoed only in a document that is itself unratified — next
point). Beyond it, a whole further lineage of narrower "constitutional" ADRs exists (0021 Truth
Hierarchy, 0024 Historical Truth, 0025 Derived Knowledge, 0026 Organizational Knowledge, 0028
Learning) — **every single one of these is still Status: Proposed**, even though the *capabilities*
built on top of them (0022 Continuous Improvement, 0023 Knowledge Graph, 0027 Organizational Memory,
0029 Learning Framework) are all Accepted and live in the pipeline. The platform is running real,
Accepted, live capabilities on a constitutional foundation that has never itself been formally
Accepted — a genuine governance-consistency gap, and itself a strong, independent argument for
consolidating and ratifying rather than leaving it fragmented. Separately, `docs/standards/STD-000-platform-constitution.md` is an actual document literally titled "Platform
Constitution" — but it is (a) Track B, declared **non-normative and frozen** by ADR-0038, (b)
itself still "Draft — pending architecture review," never ratified even within its own frozen
track, (c) explicitly scoped to Vision/Principles/Philosophy — "Out of Scope: Implementation...
runtime behaviour" — so even if promoted, it likely would not, by itself, cover the concrete
engineering rules (pass-bias defaults, gate composition, human-gate requirements) a mentor asking
for "a constitution" plausibly also wants governed.

**Additive vs amends-frozen — real conflict.** Ratifying/promoting STD-000 into Track A would
require amending ADR-0038's own Track A/B declaration. Writing a brand-new Track-A constitution
risks orphaning or duplicating the existing 0020/0021/0024–0026/0028/STD-000 lineage — this needs an
explicit reconciliation decision (which document is authoritative, what happens to the Superseded/
Proposed/frozen documents it draws from), not a silent new write.

**Effort + blast radius:** the document-writing itself could be small — much of the raw content
already exists, scattered across Accepted-but-superseded and Proposed-but-unratified sources. The
real cost is the reconciliation decision, which is a governance question, not a large engineering
one.

**Consensus signal: high** — both Nitin and the mentor raise this independently.

**Recommendation: adopt-now, but as a scoped reconciliation task, not a blank-page write.** Given
strong pre-existing raw material and near-consensus mentor interest, this is a good near-term
candidate. The first, cheap step: decide whether to (a) ratify/promote STD-000 (requires amending
ADR-0038), or (b) write a new, short, Track-A "Engineering Constitution" ADR that explicitly
consolidates ADR-0020's surviving philosophy, the shared principles across the Proposed
constitutional-tier ADRs, and concrete engineering rules (pass-bias defaults, fail-closed
conventions, the human-gate principle from item #6) — and, in the same act, formally resolves
0021/0024/0025/0026/0028's own long-Proposed status. Make this decision deliberately; do not let a
new document silently become a ninth "constitution" alongside the existing eight.

---

### Item 6 — Human-controlled gate after failure analysis (no unbounded auto-remediate)

**What it is:** any AI-proposed fix for a *test failure* must stop at a human checkpoint; never loop
indefinitely on its own.

**What it touches:** Layer 6 (Failure Intelligence & Self-Healing) — confirmed via
`requirement_intelligence/run_state/stages.py`: stage 18, `layer="L6"`,
`governing_citation="none yet"`. **Genuinely not built** — there is nothing today for this principle
to gate.

**Already-partly-done? Not as the L6 capability itself — but the exact PRINCIPLE is already a
proven, live pattern elsewhere in this platform**, and that precedent is directly reusable when L6
is eventually designed. ADR-0040's own Decision text: "Repair loops bounded at 2 LLM attempts, then
human-in-the-loop" — governing CP2/CP3 remediation today, with a real production instance already
on record from this arc: the Live Feature Remediator, where one live remediation escalated because
the model claimed a fix it had not actually made, and the platform's own tag-preservation/D5 check
caught it rather than trusting the model's own claim. Also worth noting, though a different
subsystem: CAP-086A.2 is literally named "Learning Decision Governance & **Deterministic Execution
Constitution**" — a *learning*-subsystem-scoped precedent for bounded, deterministic decision
governance, not the same thing as test-failure remediation, but evidence the platform already
treats "don't let an AI decision run unchecked" as a first-class, recurring design concern.

**Additive vs amends-frozen:** fully additive — nothing exists to amend. When L6 is designed, this
principle should be a *starting* requirement of that design, not a later bolt-on.

**Effort + blast radius:** not applicable today (bake-in-when-built). When L6 is eventually
designed, incorporating this is low incremental cost given the proven ADR-0040 bounded-remediation
pattern already exists to mirror — but this genuinely cannot be built in isolation; it is L6-shaped
work, and L6 does not exist.

**Consensus signal: high** — both mentors raise it.

**Recommendation: adopt-when-building-that-layer.** Not a standalone task today. Record as a hard
design constraint for L6's own future architecture-freeze ADR, citing ADR-0040's bounded-remediation
precedent as the pattern to mirror, not reinvent.

*(Note: this item does **not** belong in a "do first" group alongside item #5, despite both being
flagged as near-consensus — item #6 is blocked on a layer that does not exist yet, while item #5 is
buildable today. See synthesis, below, for the corrected grouping.)*

---

### Item 7 — Dashboard: BI tools

**What it is:** a governance dashboard, possibly integrated with or built on existing BI tooling
rather than bespoke.

**What it touches:** Layer 7 (Governance Dashboard) — confirmed via `stages.py`: stage 19,
`layer="L7"`, `governing_citation="none yet, structurally different (ADR-0036 D5)"`. **Not built**,
and ADR-0036 §D5 itself records an unresolved question about L7's own *shape* — whether it
genuinely participates as a per-run stage at all, or is structurally different from every other
stage (implying: possibly a standing service reading accumulated artifacts, not a per-run
generator).

**Already-partly-done?** The raw material a BI tool would consume already exists in abundance and
is well-structured: every layer emits versioned, schema-checked Execution Package artifacts (JSON +
Markdown) at every stage — CP1 through CP8, Knowledge Graph, Continuous Improvement, and more. A
real BI tool could plausibly point at this JSON artifact corpus directly with comparatively little
new "dashboard" engineering — *if* ADR-0036 §D5's own open shape question resolves toward "L7 reads
accumulated artifacts across runs" rather than "L7 is itself a per-run stage."

**Additive vs amends-frozen:** fully additive, nothing frozen to touch — but ADR-0036 §D5's own
open question should be resolved *before* choosing a BI-tool integration shape, since the two
possible shapes (per-run stage vs. standing service) are architecturally quite different, and only
one of them (standing service reading an accumulated corpus) is what a real BI tool actually wants.

**Effort:** not applicable today (bake-in-when-built). When tackled, likely medium rather than
large — mostly artifact-to-BI-tool plumbing, given the rich existing artifact corpus, not new domain
logic.

**Consensus signal:** raised only by the mentor, not clearly present in Nitin's own points.

**Recommendation: adopt-when-building-that-layer**, combined with **clarify-with-mentor** on which
specific BI tool (an external, license/tooling decision, similar in kind to item #8's own
license-dependent caveat). Resolve ADR-0036 §D5's shape question first — it changes what "BI tool
integration" architecturally means.

---

### Item 8 — Per-stage LLM assignment (Sonnet 5 / Haiku / OpenAI, license-dependent)

**What it is:** assign different models/providers to different governance/generation roles
(generation vs. structural governance vs. semantic governance) based on task shape and licensing.

**What it touches:** `automation_engineering/generation/live_step_definition_generator.py` +
`scripts/run_requirement_analysis.py`'s `STEP_DEF_GEMINI_MODEL` scoping;
`requirement_intelligence/llm/providers/` (`base_provider.py`, `gemini_provider.py`,
`azure_openai_provider.py`), `llm_factory.py`, `provider_registry.py`.

**Already-partly-done? Yes — both halves of the pattern are already proven and shipped.**
(1) *Per-stage model scoping* already exists and is empirically, not aesthetically, motivated:
`STEP_DEF_GEMINI_MODEL` gives step-definition generation its own dedicated model config,
independent of every other Gemini caller — introduced after a real measurement
(`gemini-2.5-flash` showed a 76% defect rate at scale; corrected to `gemini-3.5-flash`). This *is*
per-stage LLM assignment, just within one provider family today. (2) *Multi-provider abstraction*
already exists structurally, not just in theory: `LLMProvider` (an ABC base), `GeminiProvider`, and
— almost a literal match for this item's own "license-dependent" framing —
`AzureOpenAIProvider`, whose own module docstring reads: **"Azure OpenAI provider stub. This
provider will be enabled once the organisation's Azure OpenAI licence becomes available. The class
satisfies the `LLMProvider` interface so the factory and tests can reference it today without any
real SDK dependency."** This is exactly the shape item #8 describes — a governed provider seam,
built and tested, gated on a real-world licensing decision, not an engineering one. No Anthropic
(Sonnet/Haiku) provider exists today — that specific vendor would be new.

**Additive vs amends-frozen:** additive. No ADR locks the platform to Gemini-only; the provider
abstraction is explicitly designed to add providers, and `AzureOpenAIProvider` already proves the
pattern works. Adding an Anthropic provider plus the specific "generation=Sonnet,
structural-governance=Haiku, semantic-governance=OpenAI" assignment fits the existing extension
point precisely. No frozen-ADR conflict found.

**Effort + blast radius: small-to-medium for the engineering, and it is genuinely the cheapest item
on this list.** A new provider mirrors `AzureOpenAIProvider`'s already-proven shape; the per-stage
assignment mechanism is the already-shipped `STEP_DEF_GEMINI_MODEL`-style env-scoped pattern,
directly reusable, not new design. The real blocker is entirely non-engineering — licensing/cost —
exactly as the mentor's own "license-dependent" framing already acknowledges.

**Consensus signal:** not directly echoed by Nitin's own listed points (token-loss is adjacent but
distinct).

**Recommendation: adopt-now for the engineering pattern, once a license/vendor decision is made.**
This is the cheapest of all eight items to actually build, since both halves of the mechanism
(per-stage scoping, multi-provider seam) are already proven in production. The only real blocker is
the procurement decision the mentor's own framing already names as a precondition.

---

## Cross-cutting: the "build individual layers first, then wire" sequencing principle

A separate piece of guidance surfaced alongside the eight items: build each new layer or capability
standalone, prove it in isolation, and only then wire it into the live pipeline — don't design and
integrate at the same time. This is not a ninth peer item; it is a methodology principle that
governs **how** several of the eight get sequenced, so it is recorded here, cross-cutting, rather
than as its own assessment block.

**The honest tension, first.** This platform's own ground truth (§"Ground truth consulted," and the
`stages.py` reading behind items #6/#7 above) is that **Layers 1 through 4 are not merely designed
— they are already built AND wired, live, and CLI-invocable**: L1 (stages 1–13, `stages.py`), L2
(stage 14, Feature Engineering, ADR-0043), L3 (stage 15, Automation Engineering, ADR-0044, behind
its own opt-in flag), and L4 (stage 16, Suite Quality Governance, wired per the register's own item
28, nested behind L3's opt-in flag). Only L5 (stage 17), L6 (stage 18), and L7 (stage 19) are
genuinely unbuilt — every one of them carries `governing_citation="none yet"` in `stages.py`
(L7 additionally: "structurally different, ADR-0036 §D5"). Given that, the principle **cannot**
mean "unwire and rebuild L1–L4 standalone" — that would contradict a working, extensively tested,
live system this whole arc has been building and validating, for no stated benefit. Any useful
reading of the principle has to be forward-looking, not a rework mandate for what already works.

**Three readings, verified against what the doc has already established:**

**(a) Unbuilt layers (L5/L6/L7) — the principle applies directly, with no tension at all.** This is
exactly what group (d) below already recommends, independently arrived at: #6 and #7 are deferred
to "bake in as founding design constraints whenever Layer 6 and Layer 7 respectively get their own
architecture-freeze ADRs" — i.e., design and prove each layer's own architecture in isolation
first, the same shape every prior layer in this platform followed (ADR-0043 froze L2's design
before any L2 code existed; ADR-0044 froze L3's before stage 15 was wired). Nothing to add here
beyond making the connection explicit.

**(b) New capabilities inside already-wired layers (the KG/completeness work under #3, the
constitution under #5, a new LLM provider under #8) — build and prove standalone before wiring
live. This is not new discipline for this platform; it is already-established practice**, evidenced
twice over in this same arc: (i) page-object generation itself was built, live-regenerated, and
defect-hunted entirely through a **script harness**, run after run, before any question of live-
stage wiring was even asked — and the platform's own recorded decision on wiring it live
(`[[cap-page-object-live-wiring-decision]]`, a prior task this arc) explicitly recommended "wire it
live as ONE bundle... once prioritized — not urgent... a completeness feature," i.e., prove
standalone first, wire only when the standalone capability has already earned its place. (ii)
`AzureOpenAIProvider` (item #8) is itself a complete, testable module satisfying the `LLMProvider`
interface in total isolation from any live stage, gated purely on a later "flip it on" decision.
For new work, this principle doesn't ask the platform to change anything — it names and generalizes
something the platform already does.

**(c) The already-wired L1–L4 pipeline — "unwire and rebuild" is not a coherent reading here.** Two
readings survive instead: **(i) validate modifications to L1–L4 in isolation before
re-integrating** — ordinary, sound change discipline, and also already this platform's own standing
practice (every CP-gate's own test suite, the golden-baseline regression harness, and
`RunStateManager.should_skip`'s own artifact-diffing all exist to let a change be proven before it
re-enters the live sequence). If #3's completeness work ultimately does need to touch Layer 1
internals rather than sit arm's-length in Layer 2+, this reading is the concrete discipline to hold
it to. **(ii) Clarify with the mentor** — does the suggestion already account for L1–L4 being built
and wired live today, or was it made without that context? Both readings are worth carrying forward;
this document does not resolve which the mentor intended.

**Key connections to the eight items above.** This principle *validates*, rather than changes, two
things the assessment blocks already concluded independently: item #3's own recommendation
(surface-as-own-design-task) gains a concrete lens from reading (b) — build the completeness
capability as a standalone, arm's-length Layer 2+ consumer, prove it against real data, *then*
decide whether and how it ever touches Layer 1 — which de-risks the ADR-0032 freeze question rather
than forcing it upfront. And group (d)'s #6/#7 disposition is, precisely, reading (a) already
applied.

**The caveat, stated plainly.** This is a forward-looking lens for *new* work and for the three
*unbuilt* layers — not a mandate to rework the four layers that are already built, wired, and
proven. Reading it as license to touch L1–L4's own live wiring would contradict this document's own
verified ground truth and should be treated as a misapplication if it comes up.

---

## Synthesis

This section's own "Suggested sequence," below, already embodies the build-then-wire principle just
described — new capabilities scoped standalone-first (item 3, item 3's own dedicated design task),
unbuilt layers deferred until they can be designed and proven in isolation (items 6 and 7) — without
this document having set out to apply it as a rule; the cross-cutting section above makes that
alignment explicit rather than changing anything in the sequence itself.

### Disposition groups (verified, not assumed — the task's own guessed grouping is corrected below)

**(a) Do first — cheap, high-agreement, fits existing architecture:**
- **#5 (centralized constitution)** — high consensus, real reconciliation work but not large,
  strong pre-existing raw material.
- **#8 (per-stage LLM assignment)** — cheapest of all eight, both halves of the mechanism already
  shipped; blocked only on a non-engineering licensing decision.

**(b) Already-partly-done / clarify-with-mentor before building anything:**
- ~~**#2 (skills-first)** — the platform already has no agent architecture to migrate away from.~~
  **Reclassified (2026-08-11), see item #2's own CLARIFICATION note above.** Nitin's actual meaning
  ("organize the work as a catalog of discrete, reusable skills, agents only where genuine autonomy
  is needed") is a different question than the one this bullet answered — #2 is no longer
  already-partly-done. Moved out of this group; see the new "Reclassified after mentor
  clarification" note below, group (c)/(d).
- **#4 (spec-based development)** — the call-site-is-the-spec design (ADR-0044 D4) is close to a
  literal match already.
- **#3's own Knowledge Graph sub-part** — a real, Accepted, live KG subsystem already exists; it
  answers a different question than "Neo4j for requirement completeness," so this needs
  clarification even though something real is already there.
- Nitin's eval-harness point and re-run-token-loss point — both substantially already-solved by
  existing mechanisms (the golden-baseline regression harness; `RunStateManager.should_skip`).

**(c) Heaviest / touches a frozen layer / biggest new build:**
- **#3's completeness + subset sub-parts** — touches ADR-0032's Layer 1 freeze directly, and its
  own cleanest fix depends on a Historical Dataset prerequisite (ADR-0021, still Proposed) that the
  *existing* Knowledge Graph is itself still waiting on. Confirmed as the heaviest item on this
  list, exactly as hypothesized — but heavier than the task's own framing assumed, since it also
  surfaced that the KG's own foundational ADRs are themselves unratified (see item #5's own
  discovery).

**(d) Future-layer bake-in — cannot be built in isolation, low urgency today:**
- **#6 (human-gate)** — genuinely blocked on Layer 6 (`governing_citation="none yet"`). **This is a
  correction to the task's own initial hypothesis**, which grouped #6 alongside #5 in "do first" —
  verified against `stages.py` directly: #6 cannot be built at all today, because nothing exists
  yet for it to gate. It belongs here, not in group (a).
- **#7 (dashboard)** — genuinely blocked on Layer 7 (`governing_citation="none yet"`, and ADR-0036
  §D5's own shape question still open).

**Reclassified after mentor clarification (2026-08-11):**
- **#2 (skills-first)** — no longer group (b). Nitin's clarification (item #2's own note, above)
  revealed the platform lacks a real skill catalog, not merely that it avoided wasteful
  multi-agent looping. Does not fit group (c) either (no frozen layer, no Layer-1 conflict) or
  group (d) (nothing is layer-blocked — the generator classes this would restructure already
  exist and run today). It is its own kind of item: **a real gap, additive, no ADR conflict, size
  genuinely unknown until its own design-surfacing task determines re-framing vs. re-architecture**
  (see item #2's own note). Recorded here rather than force-fit into an existing group.

### The completeness thread

Both mentors' own #1 strategic risk is the same thing under two names: Nitin's "house of cards" /
input-quality framing, and the mentor's own completeness + Knowledge Graph framing, are both
pointing at the same underlying question — **does this platform know when its own requirement
corpus is incomplete, not just whether the requirements it has are individually well-formed?**
Verified: no corpus-level completeness check exists anywhere today (only per-requirement
completeness, in `enhancement/`/`grounding/`). This is simultaneously the heaviest item on this
list (group c) and, by both mentors' own independent framing, the single highest-strategic-value
item — the "surface-as-own-design-task" recommendation under #3 should be read as carrying more
weight than its size alone would suggest.

### Conflicts with Accepted ADRs (need the additive-amendment treatment, never a silent adopt)

| Item | Conflicts with | Nature of conflict |
| --- | --- | --- |
| #3 (completeness/subset) | **ADR-0032** (Layer 1 freeze, Accepted) | New Layer 1 reasoning is not covered by any of the freeze's 5 carve-outs; needs a freeze-lift or an arm's-length Layer 2+ scoping (recommended). |
| #5 (constitution) | **ADR-0038** (Track A/B governance, Accepted) | Ratifying/promoting `STD-000` into Track A requires amending ADR-0038's own declaration; a fresh Track-A document instead needs to explicitly reconcile, not silently orphan, the existing 0020/0021/0024–0026/0028/STD-000 lineage. |
| Nitin's Playwright point | **ADR-0041** (Java stack, Accepted, locks Selenium) | Only if added directly to the current baseline — avoidable by using CAP-087's own already-designed `RendererRegistry` extension point instead (recommended). |
| #2, #4, #6, #7, #8 | *(none found)* | Each either affirms existing Accepted architecture or is additive to a layer that does not exist yet. |

### Suggested sequence (a recommendation, not a lock)

1. **#5 — resolve the reconciliation question, then write.** Cheap relative to its consensus value;
   the raw material already exists.
2. **Clarify with the mentor:** ~~#2,~~ #4, and #3's own KG sub-part, plus Nitin's eval-harness and
   token-loss points — confirm what specifically is still wanted once the "already-done" state is
   shown, before spending any build effort here. (#2 struck: clarification already received — see
   item #2's own CLARIFICATION note; it moves to step 2a below, not this clarify-first step.)
2a. **#2's own dedicated design-surfacing task (added 2026-08-11)** — resolve the re-framing-vs-
    re-architecture sizing question (item #2's own note, above) by reading the real generator/
    orchestrator structure against what a genuine skill catalog would require. No ADR conflict, no
    frozen layer — buildable whenever prioritized, size unknown until this task runs.
3. **#3's own dedicated design-surfacing task** — specifically to answer the one question that
   determines this item's real size: can completeness be scoped as an arm's-length Layer 2+
   consumer (small-ish), or does it genuinely require lifting ADR-0032 (large)? Given both mentors'
   independent agreement this is the top strategic risk, this deserves the next big investment
   after the cheap items above are cleared.
4. **#8 — build once a vendor/license decision is made.** Purely a scheduling question at that
   point; the engineering pattern is proven.
5. **Nitin's catalog-hygiene and pass-bias points** — small, standalone, low-risk; can slot in
   alongside anything else above without blocking or being blocked by it.
6. **Playwright** — defer to CAP-087's own resolution; do not fast-track ahead of that ADR.
7. **#6 and #7** — defer; bake in as founding design constraints whenever Layer 6 and Layer 7
   respectively get their own architecture-freeze ADRs.

Steps 3 and 7 above are the build-then-wire sequencing principle in practice, not a coincidence: a
new capability proven standalone before it earns a wiring decision (step 3), and unbuilt layers left
alone until each can be designed and proven in isolation, the same way every prior layer in this
platform already was (step 7). See "Cross-cutting: the 'build individual layers first, then wire'
sequencing principle," above, for the full reasoning and its own explicit caveat against reading it
as license to rework the already-wired L1–L4 pipeline.

---

## Confirmation

Analysis-only document. No ADR, no register entry, and no code were modified to produce this
scoping document — `docs/architecture/architecture-baseline-v2.md` is untouched, and every
capability described as "already-partly-done" above was verified by reading the real, current
artifact, not asserted from this document's own prior framing. Adopting any item is a future,
separate decision requiring its own ADR and/or build task.
