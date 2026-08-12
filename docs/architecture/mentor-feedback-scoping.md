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

**NITIN'S CLARIFICATION (2026-08-12) — confirms the quality-grading reading, with specifics.** Nitin
means quality-grading, not structural regression (which he treats as already covered, separately).
His model: treat each skill/agent as a software component, each with its own curated eval set
(expected outputs, or rubrics, per component) and a score tracked over time, so that a change to a
model, prompt, or framework that causes silent quality drift is caught in CI before it is adopted,
not discovered later in production or by accident. His own example, healthcare-specific: a model swap
that silently starts missing allergy validation or insurance eligibility rules should be caught by
CI, not by a person noticing downstream. He is explicit both mechanisms are needed together, not
either/or: structural regression (does the shape/consistency still hold — the existing golden-
baseline harness) plus quality eval (a generated artifact can compile cleanly and still validate the
wrong state, which structural regression cannot catch).

**Confirms an existing gap, doesn't invent a new one.** This validates a defect this document (and
this arc) already found the hard way: the `gemini-2.5-flash` 76%-defect-rate measurement was caught
by a one-off, manual, ad hoc live-regen run — exactly the kind of silent quality drift Nitin's harness
is meant to catch automatically, in CI, before a model swap ships.

**Reclassification.** No longer `clarify-with-mentor` (resolved: quality-grading, not structural
regression — confirmed, not "already-done"). Moved to **real build item** — a genuinely new
capability (curated eval sets per generator/skill, a tracked score, a CI gate on drift), distinct
from and additive to the existing golden-baseline harness. **Nothing designed or built here —
recorded only.**

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

**NITIN'S CLARIFICATION (2026-08-12) — a finer grain than the stage-level skip already found; not
"already-done" once his actual ask is read.** Nitin wants caching pushed below the stage level to the
**artifact level, content-addressed**: key each individual artifact on spec-slice + prompt-version +
model-version + source-snapshot, so that if only one rule changes, only the downstream scenarios/
steps/assets that actually depend on it regenerate — not the full suite `should_skip` currently
protects at the stage boundary. He explicitly combines this with **delta-scoped regeneration** driven
by the change-impact graph (his own graph-type (2), recorded under item #3's KG clarification, above)
— the cache tells you an artifact is stale; the change-impact graph tells you exactly which
downstream artifacts that staleness actually reaches.

Three further, concrete pieces of his answer:

- **(a) Separate deterministic generation from LLM inference.** Scaffolding, imports, and templates
  should be produced deterministically, with the LLM reserved only for the parts that genuinely need
  judgment, binding, or repair — narrowing what even needs to be cached/re-run through the expensive
  path at all.
- **(b) Pin and version models and prompts explicitly.** Makes cache keys meaningful, changes
  intentional (not silent drift), and lets an eval-harness trigger (his eval-harness answer, above)
  target exactly what changed rather than re-validating everything.
- **(c) — his own emphasis, "Critically" — instrument token consumption by stage and by run.** Find
  out, with real data, where token spend is actually concentrated before optimizing anything else.
  This is his explicitly highest-priority, cheapest concrete ask of the four clarifications: pure
  observability, no architecture change, and it is what would tell the platform where the other three
  pieces (artifact caching, delta-scoping, deterministic/LLM split) pay off most.

**Reclassification.** No longer `clarify-with-mentor` / "already-substantially-solved" — the
stage-level `should_skip` finding stands (it is real and still true), but it answers a coarser
question than the one Nitin is actually asking. Moved to **real, multi-part build item**: artifact-
level content-addressed caching + delta-scoped regeneration (via the change-impact graph, item #3) +
deterministic/LLM separation + explicit model/prompt pinning + token-consumption instrumentation.
Token instrumentation (c) is the cheap, high-value, no-architecture-change first step he flagged as
critical — a natural first slice if this item is ever sequenced. **Nothing designed or built here —
recorded only.**

**TOKEN INSTRUMENTATION BUILT (2026-08-12).** Piece (c) — the "Critically"-flagged first slice — is
now built: `requirement_intelligence/llm/token_usage.py` (`TokenUsageTracker`/`TokenUsageTotals`),
threaded as an optional `usage_recorder` collaborator through all 7 LLM call sites (L1's
`RequirementAnalysisService`; L2's `LiveFeatureContentGenerator`/`LiveFeatureRemediator`; L3's
`LiveStepDefinitionGenerator`/`LivePageObjectGenerator`/`LiveUtilityGenerator`/
`LiveTestDataGenerator`), wired live in `scripts/run_requirement_analysis.py`'s `handle_analyze` for
the four call sites the CLI actually constructs today. Purely additive measurement, as scoped:
capture was already present at the provider (`GeminiProvider._extract_usage`) but discarded by every
caller; this build attributes it per call type and surfaces a `token_usage.json` + console breakdown
at the end of a run — nothing about generation, gating, caching, or skipping changed. The other four
pieces (artifact-level caching, delta-scoped regeneration, deterministic/LLM separation, pinning)
remain unbuilt, as does the traceability/change-impact graph work (item #3) and the eval harness.

**REAL TOKEN DISTRIBUTION CAPTURED (2026-08-12), live run
`run-20260812T064317663150Z-a20b0cc2` (real Gemini, real JIRA/Sonar/ZAP evidence, 20 requirements,
`--with-automation-engineering`).** 49,291 tokens total across 41 calls. Not a single dominant sink
(Nitin's own 60/15 framing) — two near-equal co-dominant call types instead:
`feature_content_generation` 22,383 tokens (45.4%, 20 calls) and `test_data_generation` 21,387 tokens
(43.4%, 20 calls), together ~89% of the run; `requirement_analysis` a distant third at 5,521 tokens
(11.2%, 1 call) — though on a **per-call** basis that single L1 call (5,521 tokens) dwarfs the
per-call average of either co-dominant type (~1,119 and ~1,069 tokens/call respectively).
**`step_definition_generation` and `feature_remediation` recorded ZERO tokens this run** — verified
against `automation_engineering_package.json` as a real finding, not an instrumentation gap: of 60
step-definition needs, 30 were catalog reuse hits (`outcome=bound`, no LLM call) and 30 escalated at
the reuse-decision stage itself (`signature_fit`/`confidence` failures) before ever reaching the
generator; feature generation was CP2-clean for all 20 requirements on the first pass, so the
remediation loop never fired. **The diagnostic:** with step-definition generation absorbed by reuse/
pre-generation escalation this run, optimization leverage points toward feature-content and
test-data generation jointly, not a single stage — the opposite of a one-stage-dominates picture,
though a corpus with a colder catalog (more step-def cache misses) could shift this substantially,
which is itself an argument for the artifact-level caching + delta-scoped regeneration pieces above
rather than treating this one run's shape as fixed. **The known caveat still applies in full:**
`LivePageObjectGenerator`/`LiveUtilityGenerator` are not live-constructed in `handle_analyze`, so
page-object/utility generation — a heavy step earlier in this arc's own live-regen findings — is
absent from this distribution entirely; the true full-pipeline picture requires wiring them live
first (the #3+#6 decision, [[cap-page-object-live-wiring-decision]]). This run's own artifact:
`output/executions/run-20260812T064317663150Z-a20b0cc2/token_usage.json` (gitignored, not tracked).

**THE THROUGH-LINE (2026-08-12) — Nitin's own framing across all four answers, recorded, not
interpreted.** Nitin states his own recommendations are meant to "contain bias, save
token-maxxing costs, optimize iteratively" — a single stated intent behind all four clarifications,
not four unrelated asks. Read together, the four answers interconnect directly, each in his own
words already cited above: **spec-slicing (#4)** scopes what a generation run may touch in the first
place; the **change-impact graph (#3)** is what a delta-scoped regeneration would query to know
what a change actually reaches; **caching (re-run)** needs **pinning** (also re-run, piece (b)) to
have a meaningful, invalidatable key; and the **traceability graph (#3)** is the mechanism that makes
corpus-level completeness queryable — tying this whole cluster back to the "completeness thread"
already identified (Synthesis, below) as both mentors' shared top strategic risk. Recorded here as
one coherent architecture, not four isolated features — **no sequencing or design decision is made
by this note**; that remains for each item's own future design-surfacing task.

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

**NITIN'S CLARIFICATION (2026-08-12) — a specific graph taxonomy, and a correction to what the
existing built KG actually is.** Nitin's "Knowledge Graph" point is not one graph — he names four
graph types, and is specific about which value each one adds:

1. **Traceability/coverage graph** — requirement → behavior → scenario → step → page-object →
   execution-result. Its value: makes gaps *queryable* — requirements with no test, behaviors never
   covered.
2. **Change-impact graph** — code/pages → elements → steps → scenarios. His own example: "a selector
   change should let you identify the 8 affected tests, not rerun hundreds."
3. **State/flow graph** — application states and journeys, exposing untested states.
4. **Asset/catalog graph** — reuse, similarity, and provenance, to prevent wrong reuse.

His own steer, direct: **"your current structural graph is closest to (4), the asset/catalog graph;
(1) traceability and (2) change-impact add holistic value"** on top of it — i.e. the block above's
finding that the built `knowledge_graph/` subsystem "answers a different question" is correct, and
Nitin's own words now say *which* question it does answer (asset/catalog) and which two it does not
(traceability, change-impact). On tooling: a graph database (Neo4j/GraphDB) should be used **only
when scale or query complexity actually warrants it** — Neo4j is explicitly not required now; a
bespoke structure (mirroring how the existing KG engine is already bespoke, not Neo4j) is fine as a
first cut.

**Two connections, both his own.** The **traceability graph (1)** is, in his framing, the mechanism
that makes corpus-level completeness *queryable* — this ties directly to the "completeness thread"
this document already identified as both mentors' shared top strategic risk (see the Synthesis
section, "The completeness thread," below). The **change-impact graph (2)** is what a delta-scoped
regeneration capability would run against — this ties directly to his re-run/token-cost answer
(below): "regenerate only what changed" needs a graph that knows what a change actually touches.

**Reclassification.** No longer `clarify-with-mentor`. The existing KG subsystem (ADR-0023,
Accepted, live) is confirmed as the asset/catalog graph, already built — that finding stands
unchanged. What's newly real: **traceability** and **change-impact** graphs are distinct, not-yet-
built capabilities, each independently motivated by Nitin's own examples, and each connected to a
separate existing thread in this document (completeness; re-run cost). Moved to
**surface-as-own-design-task** (real design item, graph-DB-vs-bespoke and traceability-vs-
change-impact sequencing both open questions for that task) — **not build-now**; the "no graph DB
required today" note narrows the design task's own first question but does not answer it.

**GRAPHS DESIGN SURFACED (2026-08-12) — a design-surfacing task (build nothing), resolving the
extend-vs-separate question above against the real ADR-0023 code and the platform's real artifact
chain.**

*Pre-flight.* Clean tree, `main`, tip `ff60c01`. `make lint` clean. `make test`: 5756 passed,
unchanged. This note adds text only to this document; nothing else touched.

**The ADR-0023 graph's real shape, read directly.** `requirement_intelligence/knowledge_graph/`
(~35 files) is a governed, typed graph substrate: `KnowledgeNode`/`KnowledgeEdge` models carry a
governed `KnowledgeNodeType`/`KnowledgeEdgeType` `StrEnum` vocabulary (9 node types, 9 edge types
today, `models/enums.py`), a `DeterministicKnowledgeGraphEngine` that is a thin pipeline
orchestrator over independent collaborators (`NodeProjector` → `EdgeProjector` →
`SubgraphDetector` → `ObservationEngine` → `FindingEngine` → `SummaryBuilder`/`MetricsBuilder` →
`ResultBuilder`), and a governed `KnowledgeGraphRuleCatalog` (22 rules: 7 NODE, 9 EDGE, 6
STRUCTURAL) that policy-gates which types are emitted. Two collaborators are genuinely
**type-agnostic, general graph algorithms**: `SubgraphDetector` (connected-component BFS) and the
cycle-detector inside `FindingEngine` operate on whatever `KnowledgeNode`/`KnowledgeEdge` instances
they're given — unchanged by new node/edge types. But `NodeProjector`/`EdgeProjector`
(`engine/projection/`) are **not** generic rule-interpreters — each is hard-coded against one
fixed, 8-field `HistoricalExecutionRecord` dataclass (`engine/historical_dataset.py`:
`execution_id`, `requirement_id`, `recommendation_id`, `finding_id`, `capability_id`,
`document_id`, plus ordinal/dependency flags), with an explicit `if`/`_add`/`_link` call per
field. The rule catalog only toggles an already-wired type on/off; it does not add a new type's
wiring by itself.

**A second, load-bearing finding: today's data source is synthetic, not real.**
`KnowledgeGraphService.build` takes exactly one input, `HistoricalDatasetReference` (D2/
Recommendation 1/Recommendation 9 — **mandatory, frozen**: Knowledge Graph "never imports a Layer
1 subsystem," never consumes "a Layer 1 runtime contract directly," never an Execution Package
artifact). No real, multi-execution Historical Dataset exists (ADR-0021 §Stage 6, still Proposed —
the same prerequisite the completeness sub-part above is blocked on). The shipped default,
`DeterministicHistoricalDatasetProvider`, synthesizes every id — including the **requirement id**
— via SHA-256 digest of the reference's own provenance fields (`f"{dataset_id}-req-{ordinal}"`),
never the real `TestableRequirement` id this run actually produced. Live today (CAP-084C) the
reference itself is a single-execution stand-in (`first_execution_id == last_execution_id == this
run's own execution_id`, `execution_count=1`). So the live Knowledge Graph in production emits a
small, real-shaped but **referentially synthetic** graph — not one tied to this platform's actual
requirement/scenario/step/page-object corpus.

**The extend-vs-separate answer: neither pure CASE A nor pure CASE B — split by layer.**
- *Model/vocabulary/analysis layer: CASE-A-flavored.* The `StrEnum` vocabulary is designed to grow
  additively ("a future edge type is added by an additive `StrEnum` member, never by relaxing the
  field to a plain string," Recommendation 3), and the connected-component/cycle-detection analysis
  is genuinely type-agnostic. Adding `BEHAVIOR`/`SCENARIO`/`STEP`/`PAGE_OBJECT`/
  `EXECUTION_RESULT` node types and a trace edge (reusing or extending `TRACEABLE_TO`) is
  structurally cheap and precedented.
- *Projection layer: real new code, not config.* `NodeProjector`/`EdgeProjector` would need new
  fields on a new record shape and new hard-coded `_add`/`_link` wiring — a rule-catalog entry
  alone does not make a new type project itself.
- *Service/runtime boundary: CASE B — the deciding constraint.* `KnowledgeGraphService.build`
  is frozen to consume Historical Truth only (D2, Recommendation 9: "must never blur" the Truth
  Hierarchy). Traceability's real source data — `TestableRequirementSet` (L1), `.feature`
  scenario/step ids (L2/L3), generated step-def call sites and page-object classes (L3) — is
  exactly the per-run **Runtime Truth**/Execution-Package-shaped data this boundary forbids the
  existing service from consuming directly. Routing it through instead would require first
  building the real multi-execution Historical Dataset (ADR-0021 §Stage 6) — the same heavy
  prerequisite already blocking this item's own completeness sub-part — and is a poor fit anyway:
  traceability needs *this run's* own fresh artifacts, not accumulated cross-execution history.
  **Verdict: reuse the ADR-0023 *pattern* (typed nodes/edges, deterministic pipeline, governed
  rule-gated catalog) for a new, sibling service with its own entry point reading Runtime
  Truth/Execution-Package artifacts directly — do not extend `KnowledgeGraphService.build`
  itself.** This mirrors the platform's own precedent: Continuous Improvement and Knowledge Graph
  are already two independent Layer 2 peers, neither importing the other (D1/Recommendation 1); a
  Traceability/Change-Impact service would be a third peer, not a graft onto the second.

**Data availability — TRACEABILITY (requirement → behavior → scenario → step → page-object →
execution-result).**
- Requirement (L1, `TestableRequirementSet`) ✓ real, structured, versioned.
- Behavior/scenario/step (L2 `.feature` files ADR-0043, L3 generated step-defs) ✓ real, structured
  Gherkin + parsed Java.
- Page-object ✓ **method-level**, real: `automation_engineering/generation/
  page_object_reference_derivation.py` deterministically derives, from the generated step-def's own
  call site (`javalang`-parsed, no LLM), exactly which page-object class + method + params + return
  type each step calls (`DerivedPageObjectRequest`/`DerivedPageObjectMethodCall`). Caveat: produced
  only when page-object generation actually runs, and per `[[cap-page-object-live-wiring-decision]]`
  it is **not live-wired into `handle_analyze` by default** — real today via the script harness, not
  yet in every ordinary live run.
- Execution-result ✗ **BLOCKED.** L5 (`test_execution`, stage 17,
  `requirement_intelligence/run_state/stages.py`) carries `governing_citation="none yet"` —
  genuinely unbuilt, confirmed directly. No execution outcome of any kind exists anywhere in the
  platform today.
- **Conclusion:** the requirement→...→page-object chain is buildable now (with the page-object
  live-wiring caveat above); only the final execution-result hop waits on L5. Crucially,
  requirement→scenario/step linkage alone already answers the **completeness** question this item
  exists for — "requirements with no test, behaviors never covered" is queryable without execution
  results at all. Most of the completeness payoff does not wait on L5.

**Data availability — CHANGE-IMPACT (code/pages → elements → steps → scenarios).**
- Step → page-object **method** ✓ real, same `page_object_reference_derivation.py` data as above —
  a change to which method a step calls is already capturable.
- Page-object **element/selector** → method ✗ **not captured**. Locators/selectors live inside
  opaque, LLM-generated Java source; no structured locator model exists anywhere in the generation
  pipeline. Nitin's own example — "a selector change should let you identify the 8 affected tests"
  — needs exactly this finer mapping, and it is a real, separate, unbuilt prerequisite, not
  something the existing call-site-derivation data already provides.
- **Conclusion:** change-impact is buildable now only at method-level granularity (page-object
  method → its calling steps/scenarios); Nitin's own literal selector-level example is gated on a
  real, separate piece of work (either a structured locator model added to page-object generation,
  or a deterministic post-hoc parse of generated Java for locator declarations, mirroring the same
  javalang-based approach already proven for call-site derivation).

**Options + blast radius.**
- **TRACEABILITY** — new sibling service, ADR-0023's pattern (typed nodes/edges, StrEnum vocab,
  rule-gated deterministic pipeline), own entry point reading L1-L3 Runtime Truth/Execution-Package
  artifacts directly (not `HistoricalDatasetReference`); scope: requirement→behavior→scenario→
  step→page-object now, execution-result hop deferred to L5. Size: comparable to standing up a new
  `knowledge_graph`-shaped package (~30+ files by precedent) — not small, but additive, no ADR
  conflict found (reads already-emitted Layer 1-3 runtime contracts/artifacts, does not reimplement
  their reasoning, mirroring the completeness sub-part's own "arm's-length Layer 2+ consumer"
  framing). **Highest strategic value on this list** — both mentors' independently-named #1 risk;
  this is literally the mechanism the completeness thread has been waiting for.
- **CHANGE-IMPACT** — same sibling-service pattern; method-level scope buildable now from existing
  call-site-derivation data (today transient/internal to the generation pipeline — would need to be
  persisted as its own artifact to be graph-queryable across a run). Element/selector-level scope —
  the part that actually delivers Nitin's own "8 affected tests, not hundreds" example — is
  **dependent on** a new locator-model or post-hoc-parse prerequisite; without it, change-impact
  only ever answers "which steps call this method," a real but smaller win. Payoff validated by
  today's token-distribution data (Item 1's own re-run-token-cost clarification notes, above — no
  single dominant generation stage; a change-impact graph is what would let regeneration skip
  untouched scenarios instead of the current all-or-nothing shape).
- Asset/catalog (ADR-0023 as-is) — unchanged, remains. State/flow — Nitin named it but did not
  prioritize it; deferred, not scoped here.

**The completeness convergence.** The traceability graph is the concrete mechanism the
"completeness thread" (this document's own Synthesis section, below, and both mentors'
independently-named #1 risk) has been missing since this item's own earlier assessment:
requirement→scenario/step queryability turns "is the corpus incomplete" from a qualitative worry
into a queryable answer, mostly buildable now, without L5. Building traceability *is* addressing
completeness — the two are not separate future tasks, they are the same work read from two angles.
This also connects forward to the L1 as-built LLD and mentor item #3-completeness — same
underlying work, not duplicated effort.

**Recommendation.** Build **traceability first** — highest strategic value, mostly buildable now
(module the execution-result hop to L5), and it is the completeness mechanism both mentors already
flagged as the top risk. Approach: a new sibling service reusing ADR-0023's *pattern* (typed
nodes/edges, governed `StrEnum` vocabulary, deterministic rule-gated pipeline, type-agnostic
subgraph/cycle analysis) with its own entry point over L1-L3 Runtime Truth/Execution-Package
artifacts — do not extend `KnowledgeGraphService.build` itself (blocked by its frozen
Historical-Truth-only boundary). Defer: the execution-result hop to L5's own future design;
change-impact's element/selector-level dependency (its own small prerequisite, worth naming as a
distinct next question); state/flow (not prioritized by Nitin). Change-impact can follow
traceability, starting at the method-level scope that's already buildable, with element-level as an
explicit, separately-scoped follow-on.

**Clarify-with-mentor nuance, flagged.** Nitin confirmed the four graph types and the
traceability+change-impact priority, but did not weigh in on the specific service-boundary
question this note resolves (new sibling service vs. extending the existing one) — that question
didn't exist in a form he was asked about. The recommendation above is this note's own reading of
the ADR-0023 code, not something Nitin confirmed; worth a lightweight check before committing
engineering time, the same way item #5's Option B was flagged for a narrow follow-up question.

**Nothing built by this note.** No new package, no new node/edge type, no ADR, no register entry.
This surfaces the extend-vs-separate answer, the real data-availability picture per graph, and a
sequenced recommendation; building either graph remains a future, separate task.

**MINIMAL TRACEABILITY GRAPH BUILT (2026-08-12) — the first #3 piece, following the recommendation
above.** `requirement_intelligence/traceability_graph/` is a new, standalone package: typed
`TraceabilityNode`/`TraceabilityEdge`/`TraceabilityGraph` models (deterministic SHA-256 identity,
mirroring ADR-0023's identity pattern), a directed-adjacency BFS traversal helper (mirroring
`SubgraphDetector`'s own pattern), a deterministic projector
(`project_traceability_graph`) that joins two real, already-produced artifacts —
`TestableRequirementSet` (L1) and `FeatureEngineeringPackage` (L2), re-parsing each `.feature` file
with the same parser `traceability.json` already uses — into `requirement -> scenario -> step`
nodes/edges, and a completeness evaluator (`evaluate_completeness`) that traverses the graph to
answer exactly the question this item exists for: which requirements have no full test chain, and
why (`no_scenario` vs. `scenario_without_steps`). Report-only: `CompletenessReport`'s shape (counts,
coverage %, the untested list) is gate-ready, but no threshold, gate, or fail logic exists anywhere
in this package — scores-first, as scoped. 15 new deterministic tests (fixture-based, no LLM, no
live run), including a containment test proving no import of `knowledge_graph/` anywhere in the new
package — the extend-vs-separate verdict above (CASE B at the service boundary) held in the actual
build, not just the design. `make lint`/`make test` green (5771, +15, 0 regressions); mypy on the
new code clean, whole-repo count unchanged (432, pre-existing).

**Scope held exactly as recommended.** `requirement -> scenario -> step` only — no page-object hop
(deferred; the arc exists per the data-availability finding above but was not added here), no
execution-result hop (blocked on L5, unchanged), no change-impact, no state/flow. The existing
ADR-0023 `knowledge_graph/` package is untouched — not imported, not modified. Not wired into any
execution pipeline (`scripts/run_requirement_analysis.py`, `PlatformContext`) — architecture-plus-
implementation only, mirroring ADR-0023's own CAP-084A/B milestones before its CAP-084C runtime
integration; wiring it live is a deliberate, separately-scoped follow-up.

**Governance flag — an ADR likely belongs here, not yet written.** Every prior Layer-2 peer
(Continuous Improvement, ADR-0022; Knowledge Graph, ADR-0023) got its own architecture-freeze ADR
before or alongside its implementation. This build inverted that order deliberately (scores-first,
per this task's own explicit framing) to get real completeness numbers fast rather than spend a
design cycle on ceremony for a slice this small. Recommend a short capability ADR before any further
extension (the page-object hop, the execution-result hop once L5 exists, change-impact, or live
wiring) — documenting the pattern-reuse decision this note already made, the node/edge vocabulary,
and the deliberate avoidance of ADR-0023's Historical-Truth-only boundary — but not as a blocker on
this already-built, already-tested minimal slice itself.

**Remaining #3 work, unchanged by this build:** the page-object hop, the execution-result hop
(blocked on L5), change-impact (both graphs per the options above), state/flow (deferred, not
prioritized by Nitin), and gating on top of `CompletenessReport` (a deliberate, separate future
decision — this build only surfaces the numbers).

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

**NITIN'S CLARIFICATION (2026-08-12) — neither reading above; a third meaning, more specific than
both.** Nitin does not mean the current Gherkin/call-site-derivation chain (already-done, above), and
he does not mean CAP-087's canonical-domain-model-as-source-of-truth idea either. He means
**branch-scoped vertical slices**: a small vertical feature (UI + service/API + DB, together) built
on its own branch, tied to one requirement slice — e.g. his own "Reschedule Patient Appointment"
example. The **branch spec is the contract** for everything generated on that branch. Tests are built
in the same branch, as the definition of done. Critically, page-object (and other artifact) changes
are **limited to what that feature actually touches** — his example again: only the related UI,
service, DB, tests, and page objects change; the unrelated appointment/billing/pharmacy flows are
*not* regenerated just because they share a domain. His stated rationale: cheaper, reviewable, and a
contained blast radius. He is explicit that the canonical domain model **is** still useful — for
system-engineering completeness and as "the map" — but it is not meant to be the *per-run generation
context*; each branch is meant to work from the relevant slice of that map only, not the whole thing.

**This connects to a separate answer, not a coincidence.** Nitin's own framing ties this directly to
his re-run/token-cost answer (see the "RE-RUN TOKEN COST" clarification, below, under the Item 1
cross-cutting sub-items): branch-scoped slicing is what makes delta-scoped regeneration possible in
the first place — if a branch's spec already bounds what may change, regeneration has a natural,
pre-declared blast-radius boundary to check itself against, not just a graph-derived one.

**Reclassification.** #4 is no longer `clarify-with-mentor` (now resolved) and is no longer
"already-partly-done" in the sense the block above concluded — the existing Gherkin/call-site chain
answers "is generation driven by a structured spec," which is true, but not "is each generation run
scoped to a branch-bounded slice of the requirement corpus with a contained blast radius," which is
the actual ask and is not built. Moved to **surface-as-own-design-task** (real design item, not a
build item yet) — the open question for that future task is how a branch spec is represented/
enforced as a boundary on what a generation run is allowed to touch, and how it composes with the
existing `TestableRequirementSet`/`.feature`/call-site-derivation chain rather than replacing it.
**Nothing designed here — recorded only.**

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

**DESIGN DECISION SURFACED (2026-08-11), a design-surfacing task (build nothing) — this note
resolves the (a)/(b) choice above into a recommendation and adds a hierarchy-level finding this
block did not yet have.**

**What's new since the block above:** a direct read of STD-000's own text (not just its status
fields) surfaces a structural fact that sharpens the (a)/(b) choice beyond "which one avoids an
ADR-0038 amendment." STD-000 §6 states plainly that it does **not** occupy HB-001 §5's
"Platform Constitution" tier — that tier is realized by the constitutional-tier ADRs themselves
(0020/0021/0024–0026/0028). STD-000 occupies the lower **Standards** tier, as "the Standards
family's own constitutional member." §7.1 makes the consequence explicit: STD-000 is inherited as
an authority dependency by Capabilities/Runtime/Certification documents, but **never by
Architecture or Governance** — "neither may cite STD-000 as the source of its own legitimacy,"
because HB-001 §13's dependency matrix permits no authority dependency from ADR onto STD in either
direction. Every deterministic gate checked (`requirement_intelligence/cp1/criteria/engineering_input_availability.py`,
`automation_engineering/cp3/gate.py`) is governed by an ADR at the Architecture tier, cited in its
own module docstring (e.g. "governed by ADR-0013 (Accepted)"). So if the mentor's "every gate
cites its article" means the gate's *governing ADR* treats the constitution as its authority
(reading (ii), below), **Option A structurally cannot deliver that** — promoting STD-000 into
Track A would make it a normative Track-A *Standards* document, not a Platform-Constitution-tier
one, and HB-001's own matrix still forbids an ADR from citing it as authority. Only a document that
itself sits at the Architecture tier — i.e., Option B's new Track-A ADR — can be cited as authority
by the gates' own governing ADRs without contradicting HB-001 §13.

**The citation mechanism, checked directly, not assumed:** two readings exist, and only one is
built. (i) *Documentation mapping* — already pervasive and strong: every checked criterion/gate
names its governing ADR (and often a specific decision letter, e.g. "ADR-0013 §D2") in its own
module docstring. (ii) *Runtime/code citation* — not built. `CP1CriterionMetadata` (`requirement_intelligence/cp1/framework/criterion_metadata.py`)
carries a `documentation_reference` field, but its own docstring labels it "Reserved... has no
behaviour today" — anticipated, never populated, and no criterion sets it. If the mentor pictures
(ii) — a citation visible in gate *output*, not just in source comments — that is new, small,
additive work (populate the existing reserved field) layered on top of whichever of (a)/(b) is
chosen; it does not change the (a)/(b) decision itself.

**Recommendation, sharpened: Option B — a new, short, Track-A "Engineering Constitution" ADR.**
Reasons, in order of weight: (1) it is the only option structurally compatible with HB-001 §13's
dependency matrix if gates' own governing ADRs are meant to cite it as authority; (2) it lets the
same act formally resolve 0021/0024/0025/0026/0028's live governance-consistency gap (Accepted,
live capabilities standing on foundations that are themselves still Proposed) — Option A does not
touch this at all, since STD-000 restates philosophy, not the ADR lineage's own status; (3) it can
still draw on STD-000 as raw material (observationally, per §7.1 — an ADR may reference STD-000 for
reader convenience) without requiring STD-000 itself to move tracks. **Option A is not wrong, only
narrower than it first appears** — promoting STD-000 is a legitimate, smaller act (ratify one
existing Standards-tier document), but it resolves neither the constitutional-tier ADR
lineage's unratified status nor the gate-citation structural requirement, so it would likely need
to be *followed by* something like Option B anyway. **Option C (thin index/view over existing
ADRs+gates, no new normative authority)** is the cheapest and lowest-risk of the three, and is
worth naming as a fallback if the reconciliation-ADR route (B) is judged too heavy for a first
cut — it makes today's already-real doc-level citations (i) explicit and browsable without
creating a ninth normative document — but it does not, by itself, resolve the 0021/0024–0026/0028
unratified-status gap either, and may under-deliver against a mentor picturing genuinely new
normative articles rather than a catalog of existing ones.

**Clarify-with-mentor nuance, flagged though #5 was scored independent-of-Nitin's-pending-answers:**
the (a)/(b)/(c) choice hinges partly on which citation reading (i vs. ii) and which authority shape
(new ADR vs. promoted Standard vs. index) the mentor actually pictures when he says "every gate
cites its article" — the scoping block above did not have this granularity because it had not yet
read STD-000's own §6/§7.1 text. This is a narrow, cheap question to put to the mentor (a
one-round clarification, not a blocker) before committing to Option B's write-up, since B is real
authoring work even though it is "cheap relative to its consensus value."

**Nothing built by this note.** No ADR written, no STD-000 edit, no ADR-0038 amendment, no gate
code touched. This note surfaces the (a)/(b)/(c) decision with its blast radius and a sharpened
recommendation; writing the constitution (or the ADR-0038 amendment, or the thin index) remains a
future, separate task once the approach is confirmed.

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
- ~~**#4 (spec-based development)** — the call-site-is-the-spec design (ADR-0044 D4) is close to a
  literal match already.~~ **Reclassified (2026-08-12), see item #4's own NITIN'S CLARIFICATION
  note above.** Nitin's actual meaning (branch-scoped vertical slices, the branch spec as the
  generation-run's contract, contained blast radius) is a different question than the one this
  bullet answered. Moved out of this group; see "Reclassified after mentor clarification
  (2026-08-12)" below.
- ~~**#3's own Knowledge Graph sub-part** — a real, Accepted, live KG subsystem already exists; it
  answers a different question than "Neo4j for requirement completeness," so this needs
  clarification even though something real is already there.~~ **Reclassified (2026-08-12), see
  item #3's own NITIN'S CLARIFICATION note above.** Nitin named four specific graph types
  (traceability, change-impact, state/flow, asset/catalog) and confirmed the existing KG is the
  asset/catalog graph only. Moved out of this group; see below.
- ~~Nitin's eval-harness point and re-run-token-loss point — both substantially already-solved by
  existing mechanisms (the golden-baseline regression harness; `RunStateManager.should_skip`).~~
  **Reclassified (2026-08-12), see the eval-harness and re-run-token-cost NITIN'S CLARIFICATION
  notes under Item 1 above.** Both are real, more specific asks than the mechanisms that were
  thought to already cover them. Moved out of this group; see below.

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

**Reclassified after mentor clarification (2026-08-12):**
- **#4 (spec-based development)** — no longer group (b). Nitin's clarification (item #4's own
  note, above) is branch-scoped vertical slices with the branch spec as generation-run contract,
  not the already-done Gherkin/call-site chain and not CAP-087's canonical-domain-model idea
  either. No frozen-layer conflict found (it composes with, rather than touches, the existing
  `TestableRequirementSet`/`.feature`/call-site chain). **surface-as-own-design-task.**
- **#3's Knowledge Graph sub-part (traceability + change-impact graphs)** — no longer group (b).
  Nitin's clarification (item #3's own note, above) separates four graph types; the existing
  Accepted, live KG remains confirmed as the asset/catalog graph (unchanged finding), but
  traceability and change-impact are distinct, unbuilt capabilities, each tied to a separate
  existing thread (completeness; re-run cost). No new ADR conflict found beyond the completeness
  sub-part's own already-documented ADR-0032 tension (see Conflicts table, below — that tension
  belongs to completeness, not to the graph types themselves). **surface-as-own-design-task.**
- **Nitin's eval-harness point** — no longer group (b). His clarification (Item 1's own note,
  above) confirms this means LLM-output quality-grading (curated eval sets, tracked scores, a CI
  drift gate), not the existing golden-baseline structural-regression harness. No ADR conflict
  found — additive to the existing harness. **real build item.**
- **Nitin's re-run-token-cost point** — no longer group (b). His clarification (Item 1's own note,
  above) is a finer grain than the stage-level `should_skip` finding: artifact-level
  content-addressed caching, delta-scoped regeneration (via the change-impact graph, item #3),
  deterministic/LLM separation, explicit pinning, and — his own "Critically" — token-consumption
  instrumentation by stage and run. No ADR conflict found. **real, multi-part build item**; token
  instrumentation is the cheap first slice if this is ever sequenced.

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

**Sharpened by Nitin's clarification (2026-08-12).** Nitin's own graph taxonomy (item #3's KG
clarification, above) names the mechanism that would make this thread concrete: the
**traceability/coverage graph** (requirement → behavior → scenario → step → page-object →
execution-result) is what turns "is the corpus incomplete" from a qualitative worry into a
queryable question — requirements with no test, behaviors never covered. This does not change the
thread's own size or status (still group c, still unbuilt, still gated on the same ADR-0032/
Historical-Dataset prerequisites) — it names, for the first time in this document, the concrete
graph type that thread would need if pursued.

### Conflicts with Accepted ADRs (need the additive-amendment treatment, never a silent adopt)

| Item | Conflicts with | Nature of conflict |
| --- | --- | --- |
| #3 (completeness/subset) | **ADR-0032** (Layer 1 freeze, Accepted) | New Layer 1 reasoning is not covered by any of the freeze's 5 carve-outs; needs a freeze-lift or an arm's-length Layer 2+ scoping (recommended). |
| #5 (constitution) | **ADR-0038** (Track A/B governance, Accepted) | Ratifying/promoting `STD-000` into Track A requires amending ADR-0038's own declaration; a fresh Track-A document instead needs to explicitly reconcile, not silently orphan, the existing 0020/0021/0024–0026/0028/STD-000 lineage. |
| Nitin's Playwright point | **ADR-0041** (Java stack, Accepted, locks Selenium) | Only if added directly to the current baseline — avoidable by using CAP-087's own already-designed `RendererRegistry` extension point instead (recommended). |
| #2, #6, #7, #8 | *(none found)* | Each either affirms existing Accepted architecture or is additive to a layer that does not exist yet. |

**Updated by Nitin's clarification (2026-08-12):** #4 and #3's KG sub-part no longer belong in the
"none found" row above at their old descriptions — their *content* changed, not their conflict
status. **#4 is now branch-scoped vertical slicing** (not the already-done Gherkin/call-site chain,
not CAP-087's canonical-domain-model idea) — still *(none found)*: it composes with, rather than
touches, the existing `TestableRequirementSet`/`.feature`/call-site chain. **#3's KG sub-part is now
specifically traceability + change-impact graphs** (not "a KG" generically, and not Neo4j) — also
*(none found)*: both are new, additive Layer 2+-style consumers of existing structural data, distinct
from the completeness sub-part's own real ADR-0032 tension in the row above. Nitin's eval-harness and
re-run-token-cost clarifications (Item 1) likewise surface no new ADR conflict.

### Suggested sequence (a recommendation, not a lock)

1. **#5 — resolve the reconciliation question, then write.** Cheap relative to its consensus value;
   the raw material already exists.
2. **Clarify with the mentor:** ~~#2,~~ ~~#4, and #3's own KG sub-part, plus Nitin's eval-harness and
   token-loss points~~ — confirm what specifically is still wanted once the "already-done" state is
   shown, before spending any build effort here. (#2 struck 2026-08-11; #4, #3's KG sub-part,
   eval-harness, and token-loss struck 2026-08-12 — **all four now resolved, see the NITIN'S
   CLARIFICATION notes under items #4, #3, and Item 1's eval-harness/re-run-token-cost sub-items,
   above.** Nothing left to clarify in this step; each moves to its own step below.)
2a. **#2's own dedicated design-surfacing task (added 2026-08-11)** — resolve the re-framing-vs-
    re-architecture sizing question (item #2's own note, above) by reading the real generator/
    orchestrator structure against what a genuine skill catalog would require. No ADR conflict, no
    frozen layer — buildable whenever prioritized, size unknown until this task runs.
2b. **#4's own dedicated design-surfacing task (added 2026-08-12)** — resolve how a branch spec is
    represented and enforced as a boundary on what a generation run may touch, and how it composes
    with the existing `TestableRequirementSet`/`.feature`/call-site chain (item #4's own note,
    above). Connects to 2d below (re-run/delta-scoping) by Nitin's own framing.
2c. **#3's traceability + change-impact graph design-surfacing task — DONE (2026-08-12), see
    "GRAPHS DESIGN SURFACED" under item #3, above.** Sequencing resolved: traceability first
    (highest strategic value, mostly buildable now, feeds the completeness thread directly);
    change-impact's method-level scope can follow, with its own element/selector-level mapping
    flagged as a separate prerequisite. Extend-vs-separate resolved: reuse ADR-0023's pattern
    (typed nodes/edges, deterministic pipeline) in a new sibling service with its own entry point
    over Runtime Truth — do not extend `KnowledgeGraphService.build` itself (frozen to Historical
    Truth only). The existing asset/catalog KG (ADR-0023) is unaffected. Nothing built.
2d. **Nitin's eval-harness build item (added 2026-08-12)** — curated eval sets per generator/skill,
    a tracked score, a CI drift gate; additive to the existing golden-baseline structural-regression
    harness, not a replacement for it (Item 1's own note, above).
2e. **Nitin's re-run/token-cost build item (added 2026-08-12)** — start with token-consumption
    instrumentation by stage and run (his own "Critically"-flagged, cheapest, no-architecture-change
    first step); artifact-level caching, delta-scoped regeneration (depends on 2c's change-impact
    graph), deterministic/LLM separation, and pinning follow (Item 1's own note, above).
3. **#3's own dedicated design-surfacing task (completeness/subset)** — specifically to answer the
   one question that determines this item's real size: can completeness be scoped as an
   arm's-length Layer 2+ consumer (small-ish), or does it genuinely require lifting ADR-0032
   (large)? Given both mentors' independent agreement this is the top strategic risk, this
   deserves the next big investment after the cheap items above are cleared. Connects to 2c above
   (the traceability graph is the mechanism that would make this thread queryable).
4. **#8 — build once a vendor/license decision is made.** Purely a scheduling question at that
   point; the engineering pattern is proven.
5. **Nitin's catalog-hygiene and pass-bias points** — small, standalone, low-risk; can slot in
   alongside anything else above without blocking or being blocked by it.
6. **Playwright** — defer to CAP-087's own resolution; do not fast-track ahead of that ADR.
7. **#6 and #7** — defer; bake in as founding design constraints whenever Layer 6 and Layer 7
   respectively get their own architecture-freeze ADRs.

**Note on interconnection (2026-08-12):** steps 2b–2e above are not independent — see "THE
THROUGH-LINE" note under Item 1, above, which records Nitin's own framing that spec-slicing (2b),
the change-impact graph (2c), caching-plus-pinning (2e), and the traceability graph (2c, feeding
into 3) form one coherent architecture aimed at containing bias and token cost. This note records
the interconnection; it does not resolve a build order among 2b–2e beyond what is already stated.

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
