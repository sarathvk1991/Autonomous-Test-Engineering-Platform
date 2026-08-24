# Mentor Feedback — Scoping Document

| Attribute | Value |
| --- | --- |
| Document type | Decision-support analysis (not an ADR, not governance) |
| Status | Analysis only — no code, no ADR, no register entry produced by this document |
| Scope | Nitin's 8 original feedback items, plus his own later reply and clarifications, assessed against the platform's real, current architecture |
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

Nitin's reply is not one item — it is eight compact points that partly overlap his own original
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
already identified (Synthesis, below) as Nitin's own top strategic risk. Recorded here as
one coherent architecture, not four isolated features — **no sequencing or design decision is made
by this note**; that remains for each item's own future design-surfacing task.

**DELTA-SCOPED-REGENERATION CLUSTER SURFACED (2026-08-13) — a design-surfacing task (build
nothing), now possible because item #3's change-impact graph (2c) is built
(`[[cap-change-impact-graph-built]]`), the exact dependency the synthesis section (below) already
named for this item ("delta-scoped regeneration (depends on 2c's change-impact graph)").**

*Pre-flight.* Clean tree, `main`, tip `684fa98` (method-level change-impact committed). `make lint`
clean. `make test`: 5796 passed, unchanged. This note adds text only to this document; nothing else
touched.

**What-exists map, verified against real code, not assumed from the earlier notes above.**

| Nitin's part | Status | Real evidence |
| --- | --- | --- |
| (1) Content-addressed caching, artifact-level | **Absent** (a real but coarser cousin exists) | `RunStateManager.should_skip` (ADR-0036, `requirement_intelligence/run_state/run_state_manager.py`) hashes whole `input_artifacts` files (`_hash_artifacts`: sha256 over sorted (path, content-sha256) pairs) keyed by `stage_id` — but `stage_id` must be one of the 19 fixed `STAGE_DEFINITIONS`; `_find` raises `ValueError` on an unknown id. **Not reusable as-is** for a per-requirement or per-generated-class cache entry — the *pattern* (`_hash_artifacts`'s own content-hash shape) is directly reusable, the *class* is architecturally closed to the fixed stage catalogue. |
| (2) Delta-scoped regeneration | **Absent as an action; its input is now ready** | `change_impact_for_method`/`build_change_impact_report` (`requirement_intelligence/traceability_graph/change_impact.py`, built the same day) answer "which scenarios are affected by this method" — nothing yet consumes that answer to skip or scope a regeneration. |
| (3) Deterministic/LLM split | **Absent, confirmed directly, not inferred** | Every generator checked (`LiveStepDefinitionGenerator.generate`, and its `LivePageObjectGenerator`/`LiveFeatureContentGenerator`/`LiveTestDataGenerator` siblings) is one prompt → one LLM call → the ENTIRE artifact's Java/feature/data text as output. No scaffold-deterministically/fill-with-LLM split exists anywhere in the generation package — the least-present of the four parts, as the surfacing prompt itself anticipated. |
| (4) Model/prompt pinning | **Partial, more precisely than previously stated** | Real and strong at the *source*: `PromptRegistry` enforces unique `(prompt_id, version)` pairs, immutable after `seal()`, and `PromptDefinition.metadata.sha256` is the verified content-hash of the prompt's own text (`shared/prompts/models/prompt_definition.py`) — a genuine content-addressable prompt identity already exists. `LLMResponse.model`/`.provider` (`requirement_intelligence/llm/llm_models.py`) are captured at every call site. Model selection is explicit and readable (`GEMINI_MODEL`, `STEP_DEF_GEMINI_MODEL` env vars, `scripts/run_requirement_analysis.py`) — but the env var names a hosted model, never a content hash of its own behavior, a structural limitation caching can pin around but never fully close. **The real, verified gap:** this identity is captured but mostly discarded before it reaches a persisted artifact record — exactly the same shape of gap the token-instrumentation build (piece (c), already closed) found and fixed for token counts. Only `TestableRequirementSetProvenance` (L1, `contracts/testable_requirement.py`) actually persists `prompt_id`/`prompt_version`/`prompt_sha256`/`provider`/`model` — once per run, for the requirement set as a whole. `FeatureRecord`/`FeatureEngineeringPackage` (L2) and `AssetRecord`/`AutomationEngineeringPackage` (L3) carry **no** prompt/model provenance field at all, confirmed by reading both dataclasses in full. |
| Source-snapshot | **Absent for raw evidence; a serviceable proxy already exists one layer downstream** | No hash of the raw ingested JIRA/SonarQube/ZAP evidence exists anywhere (`EngineeringContext`'s own model carries no content-hash field; a repository-wide search for an evidence/source-snapshot hash returns nothing). But `TestableRequirement`'s own `REQ-*`/`AC-*`/`RSK-*` ids are already sha256-derived from each requirement's own normalized content (ADR-0042) — a real, existing content-address one hop downstream of the raw evidence, usable as a practical spec-slice-and-source-snapshot proxy without waiting for a true pre-analysis evidence hash. |
| Spec-slice (Nitin's #4) | **Not built — a separate, larger, unresolved mentor item** | Item #4's own "branch-scoped vertical slice" design (a whole branch-per-feature workflow) is unbuilt and unscoped as a concrete artifact; treating it as a hard prerequisite for caching would block this cluster indefinitely (see the sequencing recommendation below). |
| Token instrumentation (Nitin's own "Critically") | **Built** (`TOKEN INSTRUMENTATION BUILT`, above) | The measurement instrument this whole cluster's own payoff should be judged against. |

**Dependency structure, mapped against the real evidence above, not just Nitin's own stated
ordering.**

- **Pinning (4) is the foundation for caching's key — confirmed both by Nitin's own words
  ("caching... needs pinning... to have a meaningful, invalidatable key," THE THROUGH-LINE note,
  above) and by the code: the raw identity (`prompt_sha256`, `model`) already exists at the call
  site, exactly parallel to how token counts already existed at the provider before the
  instrumentation build threaded them through. Pinning's own remaining work is that same threading
  move, not new invention.**
- **A cache key needs pinning (4) + a slice identity + a source identity.** The slice/source
  identity does not need to wait for spec-slice (#4, unbuilt) or a true raw-evidence hash (absent)
  — `TestableRequirement.requirement_id`'s own content-derived `REQ-*` id (already real, already
  content-addressed) is a serviceable first-cut key component for both roles simultaneously. This
  is a genuine, load-bearing finding: **the caching key does not have a hard, blocking dependency
  on either the unbuilt spec-slice item or a new raw-evidence hash** — it can start now, refined
  later as those mature.
- **Delta-scoped regeneration (2) depends on change-impact (built, ready) AND some notion of "what
  changed."** Nitin's own framing (THE THROUGH-LINE, above) casts the artifact-level cache itself
  as that staleness signal ("the cache tells you an artifact is stale; the change-impact graph
  tells you... which downstream artifacts that staleness actually reaches") — under his own model,
  (2) sits on top of (1), not beside it. A narrower, cheaper first slice is visible in the data,
  though: for the literal "a page-object method's source changed" trigger (Nitin's own selector
  example), a simple content-hash diff of the TRACKED BASELINE's page-object files — much smaller
  than the full artifact-level LLM-output cache (1) — is enough to name "this method changed" and
  feed `change_impact_for_method` directly, without waiting for (1)'s own, larger, re-run-efficiency
  cache. These are two related but distinct triggers for the same underlying capability (Nitin's
  own re-run-cost concern vs. "something in the corpus changed"), both worth naming, neither
  designed here.
- **The deterministic/LLM split (3) shapes scope, it does not gate the other three.** It determines
  *how much* ever needs a cache entry (a fully-deterministic scaffold needs none — it is trivially
  reproducible) but building (1)/(2)/(4) does not require (3) to exist first; it is a parallel-track
  refactor of the generators themselves (each of the ~7 LLM call sites), genuinely the largest, most
  invasive of the four parts, and — per the surfacing prompt's own expectation — the least-present
  today.

**The first build, recommended, in order:**

1. **Thread the already-captured pinning identity into L2/L3 artifact records** (`FeatureRecord`,
   `AssetRecord`) the same additive way `TestableRequirementSetProvenance` already does for L1, and
   the same shape the token-instrumentation build already proved out for token counts ("capture was
   already present... but discarded by every caller"). Small, precedented, no new derivation logic
   — the data already exists at the call site (`LLMResponse.model`, `PromptDefinition.metadata.
   sha256`); this only stops discarding it.
2. **Build the artifact-level cache itself**, keyed on `(requirement_id/REQ-* content hash,
   prompt_sha256, model)` — buildable immediately after (1), using the existing `REQ-*` content
   address as the slice/source-snapshot proxy rather than waiting on spec-slice (#4) or a new raw-
   evidence hash. Reuses `_hash_artifacts`'s own content-hash pattern; does not reuse
   `RunStateManager` itself (architecturally closed to the fixed stage catalogue, above) — a new,
   small, sibling store.
3. **Build delta-scoped regeneration on top**, consuming both the new cache (staleness) and the
   already-built change-impact graph (blast radius) — Nitin's own combined model, now fully
   unblocked (both of its own named inputs exist).
4. **Sequence the deterministic/LLM split (3) independently, in parallel or after** — the largest,
   most invasive part, and the one that narrows what (1)/(2) even need to cover over time; not a
   blocker for 1-3.

**Measurability, not just architecture.** The token instrumentation (already built) is this
cluster's own scorecard: a live run's `token_usage.json` today (the `run-20260812T064317663150Z-
a20b0cc2` measurement, above) is the pre-cluster baseline; the same live run repeated after each of
the four build steps above would show the savings directly, call-type by call-type — recommended as
the verification method for whichever of these steps is eventually built, not designed here.

**Clarify-with-mentor nuance, flagged.** Nitin's own four-part framing and his "cache tells you
stale, change-impact tells you the reach" model are his own words, cited directly above. The
specific sequencing recommendation (pin-then-cache-then-regen, with the deterministic/LLM split run
in parallel, and the `REQ-*` id as an interim spec-slice/source-snapshot proxy) is this note's own
reading of the real code and dependency shape, not something he weighed in on — the same caveat
already flagged for the traceability and change-impact extend-vs-separate calls, above.

**Nothing built by this note.** No cache, no delta-regen logic, no pinning field added to any
artifact record, no deterministic/LLM refactor. This surfaces the what-exists map (corrected in two
places against the earlier, coarser notes above: pinning is more partial-but-precise than "unbuilt,"
and the caching key's spec-slice/source-snapshot dependency is softer than it first appears), the
dependency structure, and a recommended build order; building any of it remains a future, separate
task.

**PINNING FOUNDATION BUILT (2026-08-13) — the first recommended build step above, built exactly as
scoped: purely additive persistence, mirroring the token-instrumentation build's own precedent
("identity already captured at the call site, discarded before persistence — thread it, don't
re-derive it").** New module `requirement_intelligence/llm/generation_identity.py`:
`GenerationIdentity` (`prompt_id`/`prompt_version`/`prompt_sha256`/`provider`/`model`), mirroring
`TestableRequirementSetProvenance`'s own field shape exactly, generalized from "once per run" (L1)
to "once per generated artifact" (L2/L3). All six L2/L3 generators
(`LiveStepDefinitionGenerator`/`LivePageObjectGenerator`/`LiveUtilityGenerator`/
`LiveTestDataGenerator`/`LiveFeatureContentGenerator`/`LiveFeatureRemediator`) gained a
`last_identity` property, set at the exact point each already calls
`self._usage_recorder.record(...)` — from the SAME already-captured `LLMResponse.model`/`.provider`
and `PromptDefinition.metadata` the platform already had, never re-derived. Threaded outward through
four outcome dataclasses (`GeneratedStepDefinition`, `GeneratedTestDataClass`, `GeneratedFeature`,
`RemediationResult`) via `getattr(generator, "last_identity", None)` at each orchestrator/assembler
call site (`orchestrate_step_definition`, `generate_test_data_class`, `generate_feature_file`,
`run_cp2_remediation`) — duck-typed and optional, so `StubStepDefinitionGenerator`/
`StubFeatureContentGenerator`/every other stub (no `last_identity` attribute) degrades to `None`,
never an `AttributeError`. Finally threaded onto `AssetRecord`/`FeatureRecord` (both gained an
additive `generation_identity: GenerationIdentity | None = None` field, `to_json`/`from_json`
updated) at every construction site that corresponds to an outcome an LLM call actually produced —
the SAME "identity exists only where a real generation happened" scoping `workspace_path` already
uses; a `"bound"`/reused or `"escalated"` record carries `None`, by design, not omission.

**A real bug found and fixed by this build's own tests, not merely a clean pass.** The runner-level
threading test (`AssetRecord.generation_identity` surviving the FULL stage, not just the
orchestrator) initially FAILED: `automation_engineering/stage/runner.py::_with_promotion` — the
helper that reconstructs an `AssetRecord` after promotion, adding `promotion_status`/
`promoted_path` — explicitly listed every field of the record it was rebuilding EXCEPT
`generation_identity`, silently resetting it to `None` for every promoted asset. Fixed by adding
the one missing line (`generation_identity=record.generation_identity`). This is exactly the class
of bug an additive-field build risks — a reconstruction site that lists fields explicitly rather
than copying the object wholesale — and exactly why the runner-level (not just generator-level)
proof mattered.

**Proof, deterministic, no live LLM call anywhere.** Generator-level: all six generators gained a
`TestGenerationIdentityCapture` test class (mirrors each generator's own `TestTokenUsageRecording`
class where one exists) proving identity is `None` before any call, populated correctly after a
successful call (via each file's own hand-written `FakeProvider`), and left unset after a failed
call. Orchestrator-level: `orchestrate_step_definition`/`generate_test_data_class` proven against a
minimal hand-written `_IdentityCapturingGenerator` double (exposing only `.generate`/
`.last_identity`) — the generated outcome carries the double's own identity; the pre-existing stub
generator (no `last_identity` attribute) yields `None`, not a crash. `generate_feature_file`/
`run_cp2_remediation` proven the same way against the real `LiveFeatureContentGenerator`/
`LiveFeatureRemediator`. Runner-level (the bug-catching layer): a full `run_automation_engineering_
stage` call with an identity-capturing step-def generator proves every resulting `AssetRecord`
(including PROMOTED ones, after the fix) carries the generator's own identity. Additive both ways,
proven not assumed: `make test` — **5832 passed** (5796 + 36 new: `TestGenerationIdentityCapture`/
`TestGenerationIdentityThreading` classes across the six generator test files plus the orchestrator/
test-data-orchestrator files, one runner-level test class, and a new
`requirement_intelligence/tests/unit/test_generation_identity.py`) — every pre-existing test in
every touched file passes byte-for-byte unchanged, proving no generation behavior changed (the
generated Java/feature text is identical; only the new metadata is now persisted alongside it).
`make lint`: clean. `mypy`: whole-repo error count unchanged (432, pre-existing baseline); zero new
errors in any touched file.

**Cache-ready, confirmed against Nitin's own key, not assumed.** His key: spec-slice + prompt-version
+ model-version + source-snapshot. This build supplies exactly the prompt-version
(`prompt_id`/`prompt_version`/`prompt_sha256`) and model-version (`provider`/`model`) components —
deliberately not spec-slice or source-snapshot, which belong to the requirement/artifact this
identity is attached to, not to the identity object itself (the design-surfacing note's own finding:
`TestableRequirement`'s `REQ-*` content-hash already serves as an interim proxy for both, no new
work needed here for that piece).

**Scope held exactly as recommended.** Identity persisted only — no cache, no cache key assembly, no
delta-scoped regeneration, no deterministic/LLM split, no invalidation logic, no live-wiring beyond
what already threads `usage_recorder` through today's live paths (this build's own six generators
gain identity capture symmetrically with where they already gain token-usage capture — including
`LivePageObjectGenerator`/`LiveUtilityGenerator`, not live-constructed by default, exactly mirroring
the token-instrumentation build's own choice to instrument all seven call sites uniformly regardless
of live-wiring status). This build unblocks the next recommended step (the artifact-level cache
itself); it does not build it.

**ARTIFACT-LEVEL CACHE DESIGN SURFACED (2026-08-14) — the second recommended build step above, a
design-surfacing task (build nothing), now possible because pinning
(`PINNING FOUNDATION BUILT`, above) supplies prompt-version + model-version on every L2/L3
outcome.**

*Pre-flight.* Clean tree, `main`, tip `506b552` (pinning foundation committed). `make lint` clean.
`make test`: 5832 passed, unchanged. This note adds text only to this document; nothing else
touched.

**Available key components, confirmed against real code, not the prior note's summary.**
`GenerationIdentity` (`prompt_id`/`prompt_version`/`prompt_sha256`/`provider`/`model`) is real on
every `AssetRecord`/`FeatureRecord` an LLM call produced. All five fields are, in fact, knowable
*before* the LLM call, not only after: `prompt_sha256` comes from the registry at generator
construction (`self._definition.metadata.sha256`, set in `__init__`); `model`/`provider` are
already fixed at provider construction (`GeminiProvider.__init__` sets `self._model_name` once and
echoes it verbatim into every `LLMResponse.model`, confirmed by reading `gemini_provider.py:366,
450` — the response never reports a model the provider wasn't already going to use). Today,
`last_identity` is populated only *after* a call returns, because it reads the identity off the
*response*, not off the generator's own already-fixed construction-time state — a small, real gap
for a cache that must decide hit/miss *before* calling (Lookup point, below), not a hard blocker.

**Pipeline call path, traced per LLM-driven generator — where the call is made, what determines
the output, where a cache could intercept.**

| Generator | Input type | `_build_prompt` serializes | LLM call site | Intercept point |
| --- | --- | --- | --- | --- |
| `LiveStepDefinitionGenerator` | `StepDefinitionGenerationContext` | step text, step_type, captures, target_package, page_object_interface, utility_interface, customqa_constraints (`json.dumps(..., sort_keys=True)`) | `.generate(context)` | `StepDefinitionGenerator` Protocol boundary, called once from `orchestrate_step_definition` (`orchestrator.py:259`) |
| `LivePageObjectGenerator` | `PageObjectGenerationContext` | class_name, need(s), return_type(s), parameters, target_package, customqa_constraints (incl. `additional_method_needs` batch) | `.generate(context)` | `PageObjectGenerator` Protocol boundary, `page_object_orchestrator.py` |
| `LiveUtilityGenerator` | `UtilityGenerationContext` | action_text, captures, class_name, target_package, customqa_constraints | `.generate(context)` | `UtilityGenerator` Protocol boundary, `utility_orchestrator.py` |
| `LiveTestDataGenerator` | `TestDataGenerationContext` | specification fields, target_class_name/package, customqa_constraints | `.generate(context)` | `TestDataGenerator` Protocol boundary, `generate_test_data_class` |
| `LiveFeatureContentGenerator` | `TestableRequirement` | title, narrative, component, acceptance_criteria (ac_id/statement/polarity_hints) | `.generate(requirement)` | `FeatureContentGenerator` Protocol boundary, `generate_feature_file` |
| `LiveFeatureRemediator` | `(content: str, violations)` | the feature text under repair + its lint violations | `.remediate(content, violations)` | different shape (repair, not first-generation) — weak caching candidate, flagged not recommended (below) |

Every one of the five generation call sites (excluding the remediator) has the identical shape:
constructor-injected provider (never selected inside the generator), one `generate`-like method,
one `_build_prompt` that deterministically serializes a **complete, already-assembled JSON payload**
before the call, one LLM call, one response. That JSON payload is the exact interception seam: it
already exists, fully built, in memory, at the moment right before `self._provider.generate(request)`
is called — nothing new needs deriving to hash it.

**Output flow a hit must reproduce.** `generator.generate(...)` returns a plain `str` (Java source
or feature text). The orchestrator wraps that string into an outcome dataclass
(`GeneratedStepDefinition`, etc.) carrying `generation_identity=getattr(generator, "last_identity",
None)`, which `automation_engineering/stage/runner.py` then writes to disk
(`_write_generated_java`) and records as `AssetRecord(outcome="generated", ...,
generation_identity=...)` — the same record shape `FeatureRecord` mirrors for L2. **A cache hit
therefore only has to produce the same `str` the live call would have returned** — everything
downstream (file-write, class-merge, `AssetRecord`/`FeatureRecord` construction, CP1-5 validation,
promotion) is unchanged and already oblivious to whether the string came from a fresh call or a
cache, exactly because those sites already consume `generator.generate(...)`/`.last_identity`
through a Protocol/`getattr`, not a concrete class. This is confirmed, not assumed: the pinning
build's own choice to thread `last_identity` via `getattr(generator, "last_identity", None)` —
duck-typed, because stub generators don't have it — is the same shape a caching decorator needs,
and was already proven safe at the runner level.

**(A) Store shape.** On-disk, content-addressed — cross-run reuse is the entire point (an in-run
dict cache would only save duplicate calls within one run, which the reuse-first orchestration and
per-need dedup already mostly prevent; it would not touch Nitin's actual complaint, re-run cost
across invocations). Recommend mirroring two already-proven platform patterns rather than inventing
a third: `atomic_write.py`'s atomic JSON writer (durability — the same primitive `RunStateManager`
already uses) and `_hash_artifacts`'s sha256-over-sorted-content pattern (the content-hash shape,
not the class — `RunStateManager` itself is architecturally closed to the fixed 19-entry
`STAGE_DEFINITIONS` catalogue, confirmed unusable as-is by the prior note). Shape: one file per
cache entry, path derived from the key hash (`<cache_dir>/<hash[:2]>/<hash>.json`, avoiding one huge
flat directory), storing `{generated_text, generation_identity, key_components (for diagnosis),
created_at}`. Where `<cache_dir>` lives (a new env var/CLI flag, sibling to how run/workspace
directories are already configured) is a small config decision, not designed here.

**(B) The key — and the correctness crux.** The prior note's recommended key,
`(REQ-* content hash, prompt_sha256, model)`, is **incomplete once checked against the actual
`_build_prompt` code**, in two distinct ways:

1. **For L2 (`LiveFeatureContentGenerator`), `REQ-*` under-covers its own generator's input.**
   `generate_requirement_id` (`contracts/id_generation.py`) hashes only `normalize(title) +
   source_external_ids` — but `_build_prompt` serializes `title`, `narrative`, `component`, *and*
   `acceptance_criteria` (`ac_id`, `statement`, `polarity_hints`) into the actual prompt.
   `generate_acceptance_criterion_id` is ordinal-based (`AC-<REQ short>-NN`), not content-hashed
   either — so an edited `narrative`, `component`, or acceptance-criterion `statement`, with the
   `title` unchanged, changes the generator's real output but **leaves `REQ-*` identical**. A cache
   keyed on `REQ-*` would return a stale hit here — silently, with no signal anything was wrong.
2. **For all four L3 generators, `REQ-*` is not even applicable.** Their inputs are
   `StepDefinitionGenerationContext`/`PageObjectGenerationContext`/`UtilityGenerationContext`/
   `TestDataGenerationContext` — step-need text, captures, target package, interface names,
   `customqa` constraints, specifications — none of which carries or derives from a `REQ-*` id at
   all (confirmed by reading all four context dataclasses; no field references it).

**The corrected key:** hash the generator's **own already-assembled input payload** — the exact
JSON string each `_build_prompt` already builds via `json.dumps(..., sort_keys=True)` right before
the call — combined with `prompt_id` + `prompt_version` + `prompt_sha256` + `provider` + `model`.
This is strictly more correct than a `REQ-*`/id-based proxy, and costs nothing new: the payload is
already deterministically serialized in memory at the exact interception point (above), for the
prompt itself — hashing it *is* hashing "what actually varies the output," by construction, not an
approximation of it. `REQ-*`/`AC-*`/`method_name`/`step_text` remain valuable as a **human-readable
label** on the cache entry (for diagnosis, or a future "invalidate everything touching REQ-1234"
tool) — just not as the correctness-bearing hash component. **Two residual, flagged risks, not
solved here:** (a) the key's completeness is only as good as each `_build_prompt`'s own
serialization completeness — if a context dataclass ever grows a field a generator forgets to
include in `input_payload`, the prompt and the cache key silently diverge together (a pre-existing
correctness obligation these generators already carry for the LLM call itself, not a new one this
design invents); (b) `temperature` (constant `0.0` platform-wide today, per `LLMRequest`'s own
default) is not in `GenerationIdentity` or any context — harmless while it stays a hardcoded
constant, but must join the key the moment it becomes configurable. Separately, and inherent to any
LLM cache, not a defect of this design: hosted-model APIs do not guarantee bit-identical output
across calls even at `temperature=0.0` — a perfect key guarantees "this was a genuine prior output
for these exact inputs," never "identical to what a fresh call would produce today." The existing
downstream gates (CP1-5, promotion) are the safety net for that residual gap, unchanged whether an
artifact arrived via cache or a fresh call.

**(C) Lookup point + hit consumption.** The five live generators (excluding the remediator) span
**five different Protocols** with different input shapes (`StepDefinitionGenerator`,
`PageObjectGenerator`, `UtilityGenerator`, `TestDataGenerator`, `FeatureContentGenerator`) — so
there is no single universal wrapper class, but the *pattern* is identical across all five: one
small `Caching<X>Generator` decorator per Protocol, each implementing that Protocol, each
constructor-wrapping any inner generator conforming to it (mirroring exactly how
`LiveStepDefinitionGenerator`/`StubStepDefinitionGenerator` are already peers behind the same
seam) — and all five decorators delegate their actual key/get/put logic to **one shared, generic
store module** (new, e.g. `requirement_intelligence/llm/generation_cache.py`), so the store/key
logic itself is written once. This is the option-(ii) shape the surfacing prompt anticipated,
correctly adapted to this platform's actual seam shape (per-Protocol, not per-call-site,
and not one universal class — five Protocols really do differ). Rejected: (i) inline-per-generator
(duplicates cache logic into the six *live*, LLM-calling classes themselves, mixing concerns those
classes currently keep clean — each one's whole job today is "render prompt, call provider, wrap
response"); (iii) at the orchestrator (there are 4+ distinct call sites —
`orchestrate_step_definition`, `orchestrate_page_object_method`, `orchestrate_utility_method`,
`generate_test_data_class`, `generate_feature_file` — wrapping there duplicates the same logic
across all of them, the identical problem as (i) one level up).

Each decorator's `generate`: compute the key from the wrapped generator's known-in-advance identity
(prompt_id/version/sha256 from its `_definition`, model/provider from its `_provider` — today
private; a small additive public accessor, or constructor-supplied identity prefix, closes the gap
noted under (A) above) plus a hash of the context/requirement it was just handed → **HIT**: return
the stored text, and set its own `last_identity` from the **stored** `GenerationIdentity` (not a
fresh one) — this is what keeps `AssetRecord`/`FeatureRecord.generation_identity` populated exactly
as today for a reused artifact, since every downstream site already reads `last_identity` via
`getattr`, oblivious to cache involvement → **MISS**: delegate to the wrapped generator, store the
result + its `last_identity` under the key, return it unchanged.

**Token-scorecard integration, a real gap to flag, not solved here.** A hit must show as the
measurable saving Nitin's own instrumentation exists to surface — but `TokenUsageTracker.record(
call_type, usage)` today treats `usage=None` as **unmeasured** (an incomplete-run signal,
`unmeasured_call_count`), not **zero-cost-verified**. Recording a hit as `record(call_type, None)`
would make a cache hit look like a broken measurement, the opposite of the intended signal.
`TokenUsageTotals` needs a small additive third bucket (e.g. `cache_hit_count`, distinct from both
measured and unmeasured) before hits can be trusted in the scorecard — a small, precedented
extension (same shape as the `unmeasured_call_count` field already is), not designed here.

**(D) Correctness summary.** The key is sound *if and only if* it captures every input that
determines the output: `prompt_sha256` (the template), `provider`+`model` (which model), and a hash
of the generator's own fully-serialized context payload (the per-artifact content) — this is
strictly stronger than the prior note's `REQ-*`-based proxy (B, above), reuses no derivation logic
that doesn't already exist for the prompt itself, and degrades exactly as gracefully as the prompt
construction it mirrors: if `_build_prompt` is complete, the key is complete. The two flagged
residual risks (context-field drift between a generator's `input_payload` and its actual template
placeholders; provider-level non-determinism even at fixed inputs) are real but bounded — the first
is a pre-existing generator-authoring discipline, not a new one; the second is caught by the
platform's existing downstream validation gates regardless of artifact provenance.

**Blast radius.** Contained. New code only: one store module + five small decorator classes.
Zero changes to `orchestrator.py`, `page_object_orchestrator.py`, `utility_orchestrator.py`,
`runner.py`, or any `AssetRecord`/`FeatureRecord` construction site — all already consume
`generator.generate(...)`/`.last_identity` through a Protocol/`getattr`, unaware of the concrete
class. The only touch points are generator-*construction* sites (wherever `LiveStepDefinitionGenerator(
provider, ...)` etc. is built today, e.g. the CLI's live-wiring path) — swap the live generator for
a cache-wrapped one. This confirms, concretely, that the pinning build's duck-typed
`getattr(generator, "last_identity", None)` choice (rather than a required interface field) was the
right foresight for exactly this: it is what keeps this wrap low-blast-radius today.

**Governance verdict.** No ADR names this. Searched every ADR for "cache"/"caching": only
ADR-0044 mentions it, and only for the semantic-matcher's *embedding* cache (catalog-lookup
MATCH, an unrelated, narrower, already-different concept from an LLM-generation artifact cache) —
confirmed not overlapping scope. Nitin's re-run cluster itself is not ADR'd anywhere. An
artifact-generation cache is a real, standalone capability — new store, new key scheme, a new
hit-consumption contract threaded through five generator seams — the same class of decision the
traceability graph got its own ADR for (ADR-0048). **Recommend an ADR before building**, per this
platform's established discipline (ADR-first for a new named capability, not additive infra riding
inside an existing frozen layer).

**First build, recommended.** The store + key + **one** decorator, on **one** generator — not the
full five-generator wrap. Recommend `LiveStepDefinitionGenerator` specifically: highest recent
iteration/re-run volume among the six (the live-regen defect-fixing line of work —
`[[cap-page-object-live-regen-findings]]`, `[[cap-step-def-non-lite-model-scoping]]`,
`[[cap-classname-collision-fix]]` — has repeatedly re-run step-def generation over the same corpus),
and it already has the most measurement infrastructure built around it. Measure via the existing
token-usage scorecard: run the same live corpus twice — the first run populates the cache, the
second should show `step_definition_generation`'s call-type totals collapse toward the new
`cache_hit_count` bucket rather than fresh `prompt_tokens`/`completion_tokens` — proving the saving
before extending to the other four generators, mirroring the same scores-first, prove-then-extend
discipline the mentor-clarification items themselves recommend.

**Remediator excluded from this design.** `LiveFeatureRemediator.remediate(content, violations)` is
a repair operation, not first-generation — its input already encodes a prior attempt's own failure,
live remediation is independently known to be rare (`[[cap-live-feature-remediator]]`: "live model
rarely fails CP2 naturally"), and re-running the identical `(content, violations)` pair twice is a
much rarer event than re-running the same generation twice across corpus re-runs. Weak ROI; not
recommended as a caching target even after the five-generator wrap, unless evidence changes.

**Dependencies, explicit.** Spec-slice (Nitin's #4, branch-scoped vertical slices) remains
genuinely deferred and is **not** a blocker — this design does not use `REQ-*` as the
source-snapshot proxy at all (the corrected key, B above, hashes each generator's own payload
directly), so it needs neither #4 nor a new raw-evidence hash to start. Delta-scoped regeneration
(item 3 of the original four-part cluster) is the next piece after this cache is built — it would
consume this cache as its own staleness signal, exactly as Nitin's own model casts it ("the cache
tells you an artifact is stale; the change-impact graph tells you which downstream artifacts that
staleness actually reaches"), with `change_impact_for_method`/`build_change_impact_report`
(`[[cap-change-impact-graph-built]]`) already built and ready as its other input.

**Nothing built by this note.** No store, no key module, no decorator, no ADR, no wiring change, no
`TokenUsageTracker` extension. This surfaces the store shape, the corrected key (with the
`REQ-*`-incompleteness finding as its own load-bearing correction to the prior note), the lookup
point, hit consumption (with the token-scorecard gap flagged), blast radius, governance verdict, and
a recommended first build; building any of it remains a future, separate task.

Gate: `make lint` clean; `make test` 5832 unchanged. Tree modified only in this document.

**ARTIFACT-LEVEL CACHE ADR + FIRST INCREMENT BUILT (2026-08-14) — ADR-first, then the first build
step, both same-day, in that order (not the traceability graph's own scores-first inversion).**

`docs/adr/0050-artifact-level-generation-cache.md` was written BEFORE any code, recording the
corrected payload-hash key (the surfacing's own centerpiece finding, above) plus the store,
interception, hit-consumption, and correctness decisions, Status `Proposed`. The same day, the
first increment its own D5 named was built directly against it: `requirement_intelligence/llm/
generation_cache.py` (`compute_cache_key`, `GenerationCacheEntry`, `GenerationCacheStore`) and
`automation_engineering/generation/caching_step_definition_generator.py`
(`CachingStepDefinitionGenerator`), wrapping `LiveStepDefinitionGenerator` only. Both D3 gaps
closed: `resolve_step_definition_identity`/`build_step_definition_payload`
(`live_step_definition_generator.py`, Gap 1 — pre-call identity, plus the single shared payload
definition that closes D1's own "serialization drift" residual risk) and
`TokenUsageTotals.cache_hit_count`/`TokenUsageTracker.record_cache_hit` (`token_usage.py`, Gap 2 —
the zero-cost-verified bucket, distinct from `unmeasured_call_count`).

**Proven two ways.** Deterministically (33 new tests: a payload field a naive `REQ-*`/id-only key
would have missed changes the corrected key with `need.text` held fixed; a HIT skips the wrapped
generator and returns the identical artifact; a changed input MISSES, never stales; a HIT replays
the STORED identity across independent decorator/provider instances sharing only the on-disk
store; a HIT records the new cache-hit bucket, never `unmeasured`; every pre-existing
`LiveStepDefinitionGenerator` test still passes unchanged, proving the `_build_prompt` extraction
is behavior-preserving; a genuine identity mismatch on a MISS raises rather than silently caching
under the wrong key). And live: a standalone, uncommitted harness (mirroring `CAP-088`'s own
first-measurement precedent) ran 3 realistic step-definition contexts against the real Gemini API
twice — pass 1: 3 real calls, 7003 total tokens; pass 2 (fresh decorator + fresh provider instance,
same on-disk cache): 0 new calls, 0 new tokens, 3 hits, byte-identical artifacts.
`gemini-3.5-flash` (the platform default for this generator) returned transient `503` "high
demand" at measurement time, confirmed model-specific by direct probe (`gemini-2.5-flash` and the
platform's `GEMINI_MODEL` default both succeeded immediately) — the measurement ran on
`gemini-2.5-flash` instead, a harness-only substitution; the cache key already includes `model`,
so this has no bearing on the mechanism's own correctness.

**ADR-0050 updated same-day, additively** (not a silent rewrite): Status `Proposed` → `Accepted`
for this first increment's own scope, an "Implementation Note" section recording exactly what was
built/proven, and the Consequences/Governance closing lines updated to match — mirroring how
ADR-0044/ADR-0046/ADR-0047 each carry their own additive amendment notes rather than being
re-authored. Accepted status is scoped explicitly to `LiveStepDefinitionGenerator` alone; the
other four generators, the remediator, delta-scoped regeneration, and the deterministic/LLM split
remain untouched, exactly as D5 sequenced.

**Scope held.** Only the step-def generator wrapped. `scripts/run_requirement_analysis.py` still
constructs `LiveStepDefinitionGenerator` directly, unwrapped — not live-wired, per D5. Governance
follow-ons (a `CAP-089` matrix row, now recommended `Accepted`/`Implementation` rather than the
ADR's original `Proposed`/`Architecture` framing, plus a register entry) remain flagged, not
performed, mirroring ADR-0048's own deferred-entry pattern.

Gate: `make lint` clean; `make test` 5865 passed (5832 + 33 new, itemized above); `mypy`: zero new
errors in any touched or new file (whole-repo count fluctuates 432→434 on the unmodified baseline
tree itself, confirmed by direct `git stash` comparison — not attributable to this build). Tree:
3 new modules, 1 new ADR (already committed), 3 modified files (`live_step_definition_generator.py`,
`token_usage.py`, `test_token_usage.py`), 1 new test file plus one new test module.

**ARTIFACT-LEVEL CACHE — SECOND INCREMENT BUILT (2026-08-14, same day) — `LiveFeatureContentGenerator`,
the distribution's biggest sink.** ADR-0050 D5 named extension to the remaining four generators as
future work, one at a time, measured; this is that next step, on
`LiveFeatureContentGenerator` (`feature_content_generation`, 22,383 tokens / 45.4% of the 20-call
distribution sample, above — the largest single call type, ahead of `test_data_generation` at
43.4%). Pre-flight confirmed the step-def pattern transfers DIRECTLY, no wrinkles: the generator
already builds a deterministic `json.dumps(..., sort_keys=True)` payload immediately before its LLM
call (the same shape D1 already named for this generator); its identity is knowable pre-call the
same way; its Protocol boundary (`FeatureContentGenerator.generate(requirement) -> str`) wraps with
zero downstream changes; and the cache-hit token bucket needed no change at all — Gap 2's own build
was already call-type-parameterized, not step-def-specific.

Built: `feature_engineering/generation/caching_feature_content_generator.py`
(`CachingFeatureContentGenerator`), reusing `generation_cache.py`'s store/key unmodified;
`live_content_generator.py` gained `resolve_feature_content_identity`/`build_feature_content_payload`
(the same Gap 1/serialization-drift closure, this generator's own version). The one adaptation:
`GenerationCacheIdentityMismatchError` is a new class here (not a shared import) because
`feature_engineering.generation.errors.TransportFailureError` and
`automation_engineering.errors.TransportFailureError` are distinct per-package hierarchies.

**Proven two ways**, mirroring the first increment exactly. Deterministically (13 new tests): a
`narrative`/acceptance-criterion-`statement` change with `title` held fixed MISSES (this
generator's own version of the naive-key defect D1 found); a HIT skips the wrapped generator and
returns the identical artifact; a changed input MISSES, never stales; a HIT replays the STORED
identity across independent instances sharing only the on-disk store; a HIT records the cache-hit
bucket under `feature_content_generation`, never `unmeasured`; a MISS is byte-identical to an
unwrapped `LiveFeatureContentGenerator` call; a genuine identity mismatch on a MISS raises rather
than silently caching under the wrong key. And live: the same standalone, uncommitted harness
pattern ran 3 realistic `TestableRequirement`s (password reset, shipping-address update,
search-filter) against the real Gemini API twice — pass 1: 3 real calls, 3702 total tokens (3195
prompt + 507 completion); pass 2 (fresh decorator + fresh provider instance, same on-disk cache): 0
new calls, 0 new tokens, 3 hits, byte-identical artifacts. No model substitution was needed this
time — the platform's own `GEMINI_MODEL` default (`gemini-3.1-flash-lite`) succeeded on every call
on the first attempt.

**ADR-0050 updated same-day, additively, again**: both Implementation Notes now coexist (step-def's
own, unchanged; a new one for feature-content); the header Runtime status, Consequences, and
Ownership/governance closing lines all updated to name both wrapped generators rather than one.
Accepted status now covers `LiveStepDefinitionGenerator` AND `LiveFeatureContentGenerator`
specifically; the remaining three generators, the remediator, delta-scoped regeneration, and the
deterministic/LLM split remain untouched, exactly as D5 sequenced.

**Scope held.** Only the feature-content generator added to the wrapped set this pass.
`scripts/run_requirement_analysis.py` still constructs `LiveFeatureContentGenerator` directly,
unwrapped — not live-wired, per D5. `test_data_generation`, the other near-equal sink, is flagged
as the natural next candidate, not performed here. Governance follow-ons (`CAP-089` matrix row,
register entry) remain flagged, not performed, unchanged from the first increment's own note.

Gate: `make lint` clean; `make test` 5878 passed (5865 + 13 new, itemized above); `mypy`: whole-repo
count 434 (unmodified baseline, confirmed by `git stash -u`) → 435 with this change — exactly one
new instance, and it is the identical `**dict[str, str]` keyword-unpacking pattern
`resolve_step_definition_identity`'s own test call site already carries in the first increment
(confirmed: that call site independently reproduces the same error in isolation) — not a new class
of type error, the same accepted pattern repeated at a second call site. Tree: 2 new modules, 1
modified file (`live_content_generator.py`), 1 new test file, this ADR amended further.

**ARTIFACT-LEVEL CACHE — THIRD INCREMENT BUILT (2026-08-14, same day) — `LiveTestDataGenerator`,
the other co-dominant sink.** `test_data_generation` (21,387 tokens / 43.4% of the same 20-call
distribution sample, above) was wrapped the same day — the third repeat of the identical pattern,
the cleanest transfer of the three: `LiveTestDataGenerator` lives in the SAME package as
`LiveStepDefinitionGenerator` (`automation_engineering.generation`), uses the same governed
system/user template contract, and shares the same `TransportFailureError` hierarchy, so this
increment's identity-mismatch error is REUSED from the step-def caching module rather than defined
a third time. Pre-flight confirmed no wrinkles: `_build_prompt` already built a deterministic
`json.dumps(..., sort_keys=True)` payload before its LLM call; identity is knowable pre-call the
same way; the `TestDataGenerator` Protocol wraps with zero downstream changes; `test_data_generation`
was already a registered call type, so `record_cache_hit` needed no change.

Built: `automation_engineering/generation/caching_test_data_generator.py`
(`CachingTestDataGenerator`), reusing `generation_cache.py`'s store/key AND
`caching_step_definition_generator.py`'s `GenerationCacheIdentityMismatchError` unmodified;
`live_test_data_generator.py` gained `resolve_test_data_identity`/`build_test_data_payload`.

**Proven two ways**, mirroring both prior increments. Deterministically (13 new tests): a `fields`
change with `requirement_id` held fixed MISSES (this generator's own version of the naive-key
defect); a HIT skips the wrapped generator and returns the identical artifact; a changed
`customqa_constraints`/`class_name` MISSES; a HIT replays the STORED identity across independent
instances sharing only the on-disk store; a HIT records the cache-hit bucket under
`test_data_generation`, never `unmeasured`; a MISS is byte-identical to an unwrapped
`LiveTestDataGenerator` call; a genuine identity mismatch on a MISS raises. And live: the same
standalone, uncommitted harness pattern ran 3 realistic `TestDataGenerationContext`s (checkout
credentials, shipping-address postal code, search-filter category) against the real Gemini API
twice — pass 1: 3 real calls, 3402 total tokens (3065 prompt + 337 completion); pass 2 (fresh
decorator + fresh provider instance, same on-disk cache): 0 new calls, 0 new tokens, 3 hits,
byte-identical artifacts. No model substitution was needed — the platform's own `GEMINI_MODEL`
default (`gemini-3.1-flash-lite`) succeeded on every call on the first attempt, as it did for
feature-content.

**The ~89% correction, stated precisely (the artifacts win over any looser paraphrase).**
Feature-content (45.4%) and test-data (43.4%) together already accounted for ~89% of that one
measured run's own token total BY THEMSELVES — `step_definition_generation` recorded ZERO tokens in
that specific run (30 of 60 step-def needs were reuse hits, the other 30 escalated before reaching
the generator; a real, already-documented finding above, nothing to do with this cache). This
increment caches BOTH of that run's dominant call types, alongside step-def (first increment, whose
own savings depend on a colder catalog in some future run). `page_object_generation`/
`utility_generation` remain both uncached AND absent from this same distribution entirely (not
live-constructed in `handle_analyze` at measurement time) — their real share is unmeasured, not
small.

**ADR-0050 updated same-day, additively, a third time**: a third Implementation Note added; header
Runtime status, Consequences, and Ownership/governance lines updated to name all three wrapped
generators and to state the ~89%/zero-step-def finding precisely rather than the looser "three
biggest sinks" phrasing an earlier draft of this note briefly used and this same session corrected
before it left the ADR. Accepted status now covers `LiveStepDefinitionGenerator`,
`LiveFeatureContentGenerator`, AND `LiveTestDataGenerator`; `LivePageObjectGenerator`/
`LiveUtilityGenerator`, the remediator, delta-scoped regeneration, and the deterministic/LLM split
remain untouched, exactly as D5 sequenced.

**Scope held.** Only the test-data generator added to the wrapped set this pass.
`scripts/run_requirement_analysis.py` still constructs `LiveTestDataGenerator` directly, unwrapped —
not live-wired, per D5. Governance follow-ons (`CAP-089` matrix row, register entry) remain flagged,
not performed, unchanged from the first two increments' own notes.

Gate: `make lint` clean; `make test` 5891 passed (5878 + 13 new, itemized above); `mypy`: whole-repo
count 435 (confirmed baseline before this change) → 436 with this change — exactly one new instance,
the identical `**dict[str, str]` keyword-unpacking pattern already carried at two prior call sites
(step-def's own test, feature-content's own test) — a third occurrence of the same accepted pattern,
not a new class of type error. Tree: 2 new modules, 1 modified file
(`live_test_data_generator.py`), 1 new test file, this ADR amended further.

**DELTA-SCOPED REGENERATION — THE CRUX SURFACED (2026-08-14, same day) — a design-surfacing task,
nothing built.** Item 3 in the recommended build order above ("build delta-scoped regeneration on
top, consuming both the new cache (staleness) and the already-built change-impact graph (blast
radius)") is now attemptable — both its own named inputs exist: the artifact cache (three
generators, above) and `change_impact_for_method`/`build_change_impact_report`
(`requirement_intelligence/traceability_graph/change_impact.py`, built earlier). Before building
anything, the real question Nitin's own model poses ("the cache tells you an artifact is stale; the
change-impact graph tells you... which downstream artifacts that staleness actually reaches") needs
an honest answer: does the cache already deliver "regenerate only what changed," or is there a real
gap change-impact fills?

*Pre-flight.* Clean tree, `main`, tip `8b47323` (test-data cache committed). `make lint` clean.
`make test`: 5891 passed, unchanged. This note adds text only; nothing else touched.

**What the cache already delivers, confirmed by re-reading all three wrapped generators' own
payloads.** Each `Caching<X>Generator`'s key is `compute_cache_key(identity, payload)`, and
`payload` is EXACTLY the generator's own `build_*_payload` — its real, direct determining input,
per ADR-0050 D1. So on a re-run: requirement R's `narrative` changes → `build_feature_content_payload`
changes → R's feature-content MISSES and regenerates; every OTHER requirement's feature-content
payload is byte-identical → HIT, reused, zero tokens. The same holds for test-data (a `fields`/
`required_variants` change) and step-def (a `need.text`/`customqa_constraints` change). **This IS
"only regenerate what changed" at the direct-input level — already proven, not merely designed**:
all three Implementation Notes above show exactly this (a changed field → MISS; unchanged → HIT;
never a stale hit on a real edit).

**The transitive-dependency trace — walking each generator's real dependency chain, not assuming
one.**

- **Feature-content has no generation-time dependency on anything downstream.** Its payload
  (`title`/`narrative`/`component`/`acceptance_criteria`) is read straight off `TestableRequirement`
  — Layer 1's own emission. Feature-content generation is the SOURCE of scenarios, not a consumer of
  anything Layer 2/3 produces. No transitive gap is possible here — there is nothing upstream of it
  in the generation DAG for the cache to miss.
- **Test-data depends on the SAME Layer-1/2 fields feature-content does, never on generated feature
  TEXT.** `TestDataSpecification` (`contracts/test_data_specification.py`) is derived from
  `AcceptanceCriterion.data_fields`/`.polarity_hints` directly (`feature_engineering.stage.
  test_data_spec`), never from the assembled `.feature` file's own prose. If only an AC's
  `statement` (narrative wording) changes — not its `data_fields`/`polarity_hints` — feature-content
  MISSES (statement is in its payload) while test-data correctly HITS (statement is not in test-data's
  own dependency set at all). **Not a gap** — a narrower, correct dependency, not a stale hit.
- **Step-def is where a real gap lives.** `StepDefinitionGenerationContext.page_object_interface`/
  `.utility_interface` are, verbatim, "bare hint fields (a fully-qualified class name the generated
  code MAY reference)" (`step_definition_generator.py`'s own docstring) — NOT the page-object's/
  utility's actual method signature, parameter shape, or generated body. `build_step_definition_
  payload` hashes only that bare class-name string. So: if a page-object class (say `LoginPage`)
  gets a NEW or RENAMED method added in a later run — a real, already-built platform behavior, not
  hypothetical: `orchestrate_page_object_class` (`page_object_orchestrator.py`) explicitly BATCHES
  every NO_MATCH method-need for the SAME class into one generation call, and `derive_page_object_
  class_name` derives the class name from the step's own action text, a stable semantic domain (e.g.
  "log in" → `LoginPage`) that stays constant across runs even as new steps needing new methods on
  that same page accumulate — a step-def's cache key (`need.text` + `page_object_interface=
  "LoginPage"` + `customqa_constraints`) is COMPLETELY UNCHANGED by that page-object edit. **A cache
  HIT reuses a step-def that calls a method whose current shape the cache never observed.** This is
  the EXACT trigger Nitin's own clarification names as his selector example ("a page-object method's
  source changed," THE THROUGH-LINE / NITIN'S CLARIFICATION notes, above) — not a scenario invented
  for this note. `utility_interface` carries the identical bare-hint shape, so the same gap applies
  symmetrically to utility bindings.

**Does this cross ADR-0050 D4's own bar ("a cache that returns a wrong artifact is worse than no
cache")? No — checked, not assumed.** A stale step-def calling a page-object method that no longer
exists (or whose signature changed) does not silently produce a passing artifact — it fails to
compile. `suite_quality_governance/cp5/compile_check.py` (`LiveCompileChecker`, real `mvn
test-compile`, no `test` phase — compiles, never runs) is ALREADY built and live-wired into stage 16
(`scripts/run_requirement_analysis.py`, behind the existing `--with-suite-quality-governance` flag,
confirmed at the CLI construction site: `compile_checker=LiveCompileChecker()`). A staleness of this
kind is a DETECTABLE, loud compile failure downstream — not a silent wrong artifact. D4's bar is not
crossed; the failure mode is "wasted effort discovered at CP5," not "a wrong artifact shipped
undetected."

**Is this gap live TODAY?** Not yet, and for a specific, checkable reason: `LivePageObjectGenerator`/
`LiveUtilityGenerator` are the two generators this cluster has NOT wrapped (the two remaining, per
ADR-0050 D5) — page-object/utility generation is not itself cached, so there is no FROZEN prior
page-object artifact for a step-def's cache entry to go stale against yet; every run regenerates
page objects fresh regardless. The risk becomes live the moment page-object/utility generation ARE
cached — the natural next step in this same cluster.

**THE VERDICT: mixed, precisely bounded.** (a) For all three currently-wrapped generators' own
DIRECT inputs, the cache already delivers accurate, measured, correct delta-scoped regeneration —
confirmed, not designed. (b) There is exactly ONE real transitive gap, narrow and named: step-def
(and, symmetrically, the not-yet-built utility caching) depends on page-object/utility SHAPE via a
bare class-name hint the cache key cannot see past. It is not silent (CP5 catches it) and not yet
live (page-object/utility aren't cached).

**THE OPTIONS.**

1. **A change-impact-driven invalidation pipeline** (what Nitin's own words most directly suggest):
   consume `build_change_impact_report`'s method → affected-scenario map to force-miss the affected
   step-def cache entries whenever a page-object method's own generation changes. Rejected as the
   RECOMMENDED fix, for a structural reason, not a taste preference: `project_change_impact`'s own
   `STEP → PAGE_OBJECT_METHOD` edges are built POST-HOC, by parsing ALREADY-GENERATED step-def Java
   source (`derive_page_object_requests` over `workspace_dir / record.workspace_path`) — the graph
   cannot exist until AFTER a run has already generated the Java it describes. A PRE-generation
   cache-hit/miss decision needs to know the dependency BEFORE calling the generator; the
   change-impact graph, as built, is definitionally too late to consult at that decision point in
   the SAME run, and consulting a PRIOR run's graph introduces its own staleness question (was that
   prior graph itself still accurate?). Its real, proven value is as a POST-HOC, HUMAN-facing
   reporting/impact-analysis tool ("I am about to hand-edit `LoginPage.enterUsername`, show me every
   scenario that reaches it") — genuinely useful on its own terms, already scoped that way by its own
   module docstring ("this module never gates and never regenerates anything").
2. **Widen the step-def (and future utility) payload itself — recommended.** Fold the transitive
   dependency into D1's own key-construction discipline directly, the same way D1 already treats
   `prompt_sha256`/`model` as first-class key components rather than bolting on a second
   invalidation mechanism: when page-object/utility generation get their own artifact cache (the
   natural next two increments), change `page_object_interface`/`utility_interface` from a bare class
   name to a value that also captures the underlying page-object/utility artifact's own identity
   (its own cache key, or a content-hash of its generated source) — so a page-object regeneration
   that changes shape under the same class name PRODUCES a different step-def payload, and D1's
   existing machinery (unmodified) does the rest. No new invalidation pipeline, no graph traversal at
   cache-decision time, no second mechanism to keep in sync with the first — this is D1's own
   "serialization drift... a code-review-time discipline for future context-field additions" residual
   risk (already named in the ADR), applied to exactly the field this note identifies.
3. **No build at all, right now — the actual recommendation.** The gap is real but currently
   dormant (page-object/utility uncached), non-silent (CP5), and narrow (one field, two generators).
   Building either option 1 or 2 today would be built against a dependency (page-object/utility
   caching) that does not exist yet — premature. The right trigger for option 2 is "when page-object/
   utility caching is built," not now.

**Connecting to the token payoff, honestly.** The cache's own token savings are ALREADY measured and
delivered (three real runs, above) — that is Nitin's primary "save token-maxxing costs" goal,
substantially met without any further build. A change-impact-driven regen mechanism's INCREMENTAL
value beyond the cache is confined to the one narrow transitive case above — and even there, option 2
(a payload-widening fix, folded into the existing key) captures the same correctness benefit more
cheaply than a graph-traversal-driven invalidation pipeline would, when the time comes. The
INCREMENTAL value of building change-impact-driven regeneration specifically, as its own mechanism,
is therefore assessed as LOW today and likely LOW even later (option 2 pre-empts most of its would-be
value). Change-impact's OWN value is real and unrelated to this verdict — impact-analysis reporting
for humans, unaffected either way.

**RECOMMENDATION.** No delta-scoped-regeneration build now. Document that content-addressed,
per-artifact caching (built, three generators) IS delta-scoped regeneration at the level Nitin's own
"only regenerate what changed" goal targets for direct inputs — a good outcome, not a gap. Flag the
one real transitive gap (step-def/utility ↔ page-object/utility, bare-class-name hint) as a NAMED,
DEFERRED follow-on, to be closed by widening the dependent generators' payload (option 2) at the
SAME time page-object/utility generation get their own artifact cache — not before, not as a
separate change-impact-driven pipeline. Change-impact graph's scope stays exactly what it already
is: a post-hoc, human-facing query/reporting tool, not a regeneration driver.

**Clarify-with-mentor nuance, flagged.** Nitin's own words ("the cache tells you an artifact is
stale; the change-impact graph tells you... which downstream artifacts that staleness actually
reaches") and his own selector example ("a page-object method's source changed") are cited directly
above and are the literal grounding for the one real gap this note finds. The specific verdict that
this gap is narrow/dormant/non-silent, and that a payload-widening fix beats a change-impact-driven
pipeline, is this note's own reading of the real code — not something Nitin weighed in on directly,
the same caveat flagged for every prior design-surfacing note in this item.

**Nothing built by this note.** No cache-invalidation logic, no payload widening, no change to
`change_impact.py`'s own scope. `make lint`/`make test` unchanged (5891, confirmed above). Recorded
here per the surfacing task's own instruction; CAP-089's matrix/register follow-ons remain flagged,
unperformed, unchanged from the third increment's own note.

**EVAL HARNESS DESIGN SURFACED (2026-08-17) — the last major unbuilt Item-1 sub-item, a
design-surfacing task (build nothing).** Nitin's own model, restated precisely from his
clarification above: treat every skill/agent as a software component with a curated eval set
(expected outputs or rubrics), a score tracked over time, so a model/prompt/framework change that
causes silent quality drift is caught in CI before adoption — not discovered later. His own
example: a model swap that silently starts missing allergy validation or insurance-eligibility
rules should be caught by CI, not by a person noticing downstream. He is explicit both mechanisms
are needed together: structural regression (shape/consistency — already built) plus quality
grading (new).

*Pre-flight.* Clean tree, `main`, tip `a64e3d6` (CAP-089 closure committed). `make lint` clean.
`make test`: 5891 passed, unchanged. This note adds text only to this document; nothing else
touched.

**What already exists (1) — the golden-baseline structural harness, read directly, not
assumed.** `tests/productization/test_golden_baseline.py` / `docs/productization/golden-baseline.md`
(CAP-070) is a **release regression baseline**: one hand-authored dataset (9 source artifacts, all
`component="authentication"`) driven through the full pipeline against a **fixed, hand-written
stub LLM response** (`GoldenStubProvider`, `GOLDEN_LLM_RESPONSE_TEXT` — no real model call, ever).
It checks: every governed subsystem executes in the governed order; every governed artifact is
produced; manifest checksums/byte-counts/cross-references agree with disk; Validation and CP1
evaluate as expected; and two runs on the same input produce byte-identical findings/verdicts
(excluding provenance). Its own document is explicit about its own boundary, quoted verbatim: *"It
deliberately does not validate prompt quality: the LLM response is a fixed, deterministic stub, so
this baseline asserts nothing about how good a real model's answer would be"* (golden-baseline.md
§Overview). §12's own ownership table scopes it to *"verification of the completed architecture"*
and lists Normalization/Analysis/Connectors/Prompt Engineering as things it **consumes, never
judges**. This is a real, live, 70-test harness — but by its own governance contract it structurally
cannot be the seam Nitin is asking for; it never calls a real model and never grades a real
generated artifact. Quality-grading is additive to this, not a duplicate or an extension of it — a
different subject entirely (LLM output quality vs. pipeline shape/determinism), confirmed by
reading its own frozen ownership boundary, not inferred.

**What already exists (2) — the generators ARE the "skills/agents."** Item #2's own finding
(above) already established there is no agent/tool-loop architecture on this platform — every LLM
call is a single-shot, Protocol-bound generator class. That finding is the mapping Nitin's model
needs: a "skill/agent," here, is one **generator + its governed prompt**. Seven real call sites
exist across three layers: L1 `RequirementAnalysisService` (one call/run); L2
`LiveFeatureContentGenerator` + `LiveFeatureRemediator`; L3 `LiveStepDefinitionGenerator` /
`LivePageObjectGenerator` / `LiveUtilityGenerator` / `LiveTestDataGenerator`. Each already carries
a governed, versioned, content-hashed prompt identity (`PromptRegistry`, ADR-0014,
`(prompt_id, version)` unique and sealed, `PromptDefinition.metadata.sha256`) and, since the
pinning build (`[[cap-pinning-foundation-built]]`), a per-call `GenerationIdentity`
(`prompt_id`/`version`/`sha256`/`provider`/`model`) captured at every L2/L3 outcome. **This is
precisely the per-component identity a per-component eval score needs to key against** — it
already exists, built for caching, directly reusable here as the eval harness's own scoring key.
Each of the seven call sites is a candidate eval-set owner.

**What already exists (3) — seed data, checked, not assumed usable.**
`tests/productization/fixtures/golden_dataset.py` is **not** usable as eval-set seed material as-is:
it is one hand-built input paired with one hand-built, fixed stub *response* — by construction
there is no real generation to grade, and its own two planned siblings (`Golden Validation FAIL`,
`Golden CP1 FAIL`, both unimplemented) are aimed at exercising Validation/CP1 failure paths, not
grading quality either. Curation is **not** starting from zero, though: this arc's own ad hoc
live-regen work already produced genuine, human-verified expected-outcome data —
`[[cap-page-object-live-regen-findings]]` (32/32 generated, 3 defects hand-diagnosed and named) and
`[[cap-compile-gap-closed]]` (17 `gemini-2.5-flash` generations, each hand-classified clean/defective
with a named defect type) are exactly the shape of curated, labeled examples Nitin's ask requires —
just recorded as prose in a memory file and a scoping-doc note, never packaged as a structured,
re-runnable fixture. Real curation raw material exists; it needs packaging, not invention from
scratch.

**THE HARD QUESTION — how to grade generation quality stably enough for CI.**

- **Expected-outputs (golden text).** Rejected as the primary mechanism, for a reason this
  platform has already documented about itself, not a generic LLM caveat: ADR-0050 D2's own
  residual-risk note states plainly that *"hosted-model APIs do not guarantee bit-identical output
  across calls even at temperature=0.0."* An exact-match golden artifact would false-fail on every
  regrade with zero real regression — the opposite of CI-stable. Approximate/similarity matching
  pushes the problem down a level (what threshold? scored by what?) without actually detecting the
  real historical defects below, which were small, discrete textual faults (a wrong import token, a
  fenced block) that a similarity score could easily average away as "close enough."
- **Rubrics scored by a human.** Not CI-automatable by definition — useful for periodic audit
  (mirrors the "pass-bias meaning-check" recommendation already made elsewhere in this document),
  not for gating a model swap before adoption.
- **LLM-judge.** The standard modern answer for holistic/semantic quality (e.g., "does this
  generated step correctly implement the intended business rule," which no syntax check can see).
  Real problems, honestly stated: cost (a second LLM call per graded artifact, minimum), and a
  second model that itself needs pinning/versioning and its own reliability calibration — the exact
  silent-drift risk this whole harness exists to catch, now recursively applied to the judge. Not
  rejected, but not the first layer: it needs the deterministic layer's own discipline (identity
  pinning, a tracked baseline score) applied to itself before it can be trusted as a CI gate.
- **Property/assertion checks.** Deterministic, checkable without a judge, and — the load-bearing
  finding below — **this platform already has a live, proven instance of exactly this pattern**:
  `suite_quality_governance/cp5/` (`compile_check.py`'s `LiveCompileChecker`, real `mvn
  test-compile`; `cohesion.py`'s `no_ambiguous_glue`; `orphaned_glue.py`; `near_duplicate_sweep.py`)
  is a deterministic, CI-stable, no-judge-required property-check suite, already live-wired into
  stage 16 — just scoped at the whole-suite level (does the generated corpus cohere), not curated
  per-generator as a versioned, scored eval set compared across model/prompt versions over time.
  Cheap, stable, but bounded: it only catches properties someone thought to name in advance, never
  holistic "is this good."

**THE GEMINI-2.5-FLASH DEFECT AS THE TEST CASE — traced against real data, not hypothesized.**
`[[cap-compile-gap-closed]]` recorded the actual defect breakdown across 17 real
`gemini-2.5-flash` step-definition generations (76% defective): wrong Cucumber import package
(`io.cucumber.java.When` vs. the correct `io.cucumber.java.en.When`, 8/17); a markdown code fence
despite an explicit no-markdown prompt contract (2/17); an inline/duplicate page-object class
fabricated in the same file instead of referencing the external one (3–4/17). **All three are
deterministically checkable, with zero judge call, and largely already caught by mechanisms this
platform already runs**: the wrong-import defect is exactly what `mvn clean test-compile`
(CP5's `compile_check.py`, already live) fails on; the fabricated-duplicate-class defect is a
structural check `near_duplicate_sweep.py` is already adjacent to; the markdown-fence defect is a
literal string check with no existing analog for L3 Java text (L1's `ResponseNormalizer` enforces
the equivalent contract for JSON, not yet mirrored for generated Java) but is trivial to add. **The
property/assertion layer would have caught this real defect automatically — not the rubric layer,
not an LLM-judge.** The actual gap was never detection capability; `mvn clean test-compile` already
existed and already would have failed. The gap was that this detection ran **once, manually, ad
hoc, discovered by a human reading a live-regen transcript after the fact** — not as a curated,
versioned eval set with a tracked score, run automatically in CI the moment `STEP_DEF_GEMINI_MODEL`
changed, before that change shipped. That is the actual, narrow, honest shape of Nitin's ask
against this platform's own history: not "build a detector," but "curate, wire, and score what
already exists so it runs before adoption, not after."

**A necessary caveat, not overclaimed.** Nitin's own motivating example — a model silently missing
an allergy-validation or insurance-eligibility rule — is a *different* defect shape than the real
one traced above: not a syntax fault, but a semantic omission where the generated artifact is
syntactically clean and still wrong. Two sub-cases exist, with different answers: if the omission
shows up as a **coverage gap** (an acceptance criterion with no corresponding generated
scenario/step at all), that is a deterministic, judge-free property check — and this platform
already has the exact mechanism for it, unused for this purpose: the traceability graph
(`[[cap-traceability-graph-minimal-build]]`, `CompletenessReport`, CAP-088) already answers
"does every requirement/AC have a corresponding scenario/step," and could feed the property-check
layer directly, no new coverage logic required. If instead the criterion IS covered but the
generated logic **implements it incorrectly** (present, but wrong), no deterministic check can see
that without a rubric of what "correct" means — genuine rubric/judge territory. The honest
conclusion: property checks are more load-bearing here than they first appear (they cover both the
real historical defect and the coverage-shaped half of the hypothetical one), but they do not
close the whole gap.

**THE RECOMMENDED APPROACH — layered, deterministic-first.** Build the property/assertion layer
first: a curated eval set per generator (not one golden case — a small, labeled corpus of real
generation contexts, seeded from the already-produced `[[cap-page-object-live-regen-findings]]` /
`[[cap-compile-gap-closed]]` corpora, each paired with named, checkable properties, not full
expected text), scored as a pass-rate over deterministic assertions, persisted keyed on the
generator's own `GenerationIdentity` (prompt_id/version/sha256/provider/model — the same identity
the cache already threads, a second consumer of the same mechanism, not a new one). This is
CI-stable by construction: no LLM-judge variance, no false alarms from hosted-model
non-determinism at the property level (a correct import statement is correct regardless of exact
wording), cheap relative to a judge (several checks are static analysis; the compile check is
already run today). Rubric/LLM-judge grading is real, additive, later work for the semantic-only
half the caveat above names — deferred, not rejected, and only after the deterministic layer's own
identity-pinning discipline is proven, so the judge itself doesn't become a second source of the
exact silent-drift problem being solved.

**FIRST-BUILD SCOPE, recommended, not performed.** One generator:
`LiveStepDefinitionGenerator` — the same generator ADR-0050's own first-increment reasoning
already picked (highest recent iteration/defect volume this arc, most measurement infrastructure
already wrapped around it: `GenerationIdentity`, token-usage recording, and the existing
`CachingStepDefinitionGenerator` all already instrument this exact class), and, concretely, the
literal generator where the real, traced defect above occurred. Mechanism: a curated fixture (10–20
real `StepDefinitionGenerationContext` examples, drawn from the already-produced corpus, hand-
labeled clean/defective) + a small `Cp5`-style property-check runner (reusing the
`compile_check`/`near_duplicate_sweep`/`orphaned_glue` pattern, adding "correct Cucumber import
package," "no markdown fence," "no fabricated BasePage/page-object helper reference") + a score
(pass-rate, persisted per `GenerationIdentity`) comparable across model/prompt versions over time.
**Open, unresolved design question, flagged not answered here:** whether CI makes a real, live LLM
call per run (cost/quota-bound — `[[cap-compile-gap-closed]]`'s own finding that
`gemini-2.5-flash`'s free tier caps at 20 requests/day is a real, already-measured constraint on
this exact idea) or replays a pinned, cached response set (reusing the generation cache itself,
ADR-0050) — this determines whether the harness runs on every PR or on a scheduled/gated cadence,
and is not resolved by this note.

**GOVERNANCE.** A new capability, not an extension of CAP-070: different subject (LLM output
quality vs. pipeline architecture/determinism), and CAP-070's own frozen ownership boundary (§12,
above) explicitly excludes prompt/generation quality from its scope — extending it would violate
its own governance contract freeze (§13), not merely be inconvenient. Recommend **ADR-first**,
per this arc's own corrected lesson: ADR-0050 (artifact cache) was written before any code and is
cited elsewhere in this document as the right order, in explicit contrast to the traceability
graph's own build-then-ADR inversion (`[[cap-traceability-graph-adr]]`), later named as debt.
Likely lands as its own capability (next available CAP number after CAP-089), sibling to CAP-088
(traceability graph) and CAP-089 (artifact cache) — both similarly new-subsystem-plus-own-ADR
precedents from this same arc.

**DEPENDENCIES, explicit.** **#8 (per-stage LLM assignment)** — the eval harness is the literal
mechanism that would let a future #8 model/provider swap be gated rather than merely permitted;
Nitin's own words tie them together directly ("a model, prompt, or framework change... caught in
CI before it is adopted"). #8 remains the cheapest item on this list to build engineering-wise, but
today nothing would catch a bad swap before it ships — the eval harness is what closes that.
**Pinning/caching (`[[cap-pinning-foundation-built]]`, ADR-0050)** — the eval harness's own scoring
key reuses `GenerationIdentity` verbatim, a second consumer of an identity built for caching; this
also fulfills Item 1's own earlier re-run-token-cost note that pinning "lets an eval-harness
trigger target exactly what changed," now traceable to a concrete mechanism rather than a forward
reference. **Traceability graph (CAP-088)** — the property-check layer's coverage-shaped checks
(the caveat above) consume `CompletenessReport` directly, no new logic.

**Nothing built by this note.** No eval set, no property-check runner, no score store, no ADR, no
CI wiring, no fixture. This surfaces what exists (structural harness, generators-as-skills mapping,
seed-data assessment), the grading-option tradeoffs, the traced verdict on the real
`gemini-2.5-flash` defect (property checks would have caught it; the gap was curation/CI-wiring,
not detection), the recommended layered approach, a first-build scope, the governance verdict
(new capability, ADR-first), and the #8/pinning/traceability-graph dependencies; building any of it
remains a future, separate task.

Gate: `make lint` clean; `make test` 5891 unchanged. Tree modified only in this document.

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

**Consensus signal:** high — Nitin's own follow-up ("agent/re-run token loss") reiterates the same
theme from his original list.

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

**SIZING RESOLVED (2026-08-23) — MIXED, and the re-architecture half has no live use case today.
Nothing built.** One mentor throughout (Nitin).

**Pre-flight.** Clean tree, `main`, tip `26982a2` (the grounding-docstring fix). `make lint` clean,
`make test` 6106 passed, unchanged.

**The generators, read directly, are already close to a uniform "skill" shape.** All six —
`LiveStepDefinitionGenerator`, `LivePageObjectGenerator`, `LiveTestDataGenerator`,
`LiveUtilityGenerator`, `LiveFeatureContentGenerator`, `LiveFeatureRemediator` — each sit behind
their own dedicated `Protocol` (`StepDefinitionGenerator`, `PageObjectGenerator`,
`TestDataGenerator`, `UtilityGenerator`, `FeatureContentGenerator`, `FeatureRemediator`), each with a
single narrow method (`generate(context) -> str`, or for the remediator,
`remediate(content, violations) -> str`), each with a matching `Stub*` deterministic test double, each
raising its own `LiveGenerationError(TransportFailureError)`. This is exactly the shape of a
discrete, single-purpose, independently-testable skill — just six separately-named Protocols, not one
common interface, and not exposed anywhere as a catalog.

**The gates are, if anything, even more skill-shaped than the generators.** CP4/CP5/CP7/CP8
(`evaluate_cp4`, `evaluate_promotion_wrap`, `evaluate_rating_gate`, `evaluate_static_readiness`) are
plain, deterministic, single-purpose functions — no LLM, trivially unit-testable in isolation, a
closer literal match to Nitin's own "a linting/quality-check skill" example than the generators are.
They are composed by three flat, hardcoded function calls in
`suite_quality_governance/stage/runner.py::run_suite_quality_governance_stage`, in fixed order — no
registry, no selection logic, same invocation shape as the generators (see below).

**The orchestrator invokes everything by constructor-injected parameter, in a fixed loop — there is
no selection/routing layer anywhere.** `run_automation_engineering_stage` and
`run_feature_engineering_stage` both take their generators as plain typed parameters
(`step_definition_generator: StepDefinitionGenerator`, `content_generator: FeatureContentGenerator`,
etc.) and call them inside an ordinary `for need in unique_needs` / `for requirement in
requirement_set.requirements` loop. Which generator handles which need is decided entirely by
**need-kind, statically, in Python control flow** (an `if page_object_generation_enabled:` branch,
not a dynamic lookup) — there is no place today where the platform chooses among interchangeable
skills, or between a skill and an agent, at runtime. The `EngineeringContextOrchestrator`
(CAP-076D)'s own policy-selection mechanism (`create_orchestration_policy` vs
`create_legacy_selection_policy`) is the platform's one real precedent for "selection," and it
selects among context-assembly *policies*, not generation *skills* — not the same axis.

**A registry/catalog pattern already exists, repeatedly, in this codebase — this is the strongest
re-framing evidence.** Six independent registries already ship: `PromptRegistry` (the one the
original note names as the shape to mirror — register/seal/lookup by `(id, version)`, sourced from
`shared/prompts/framework/prompt_registry.py`), plus `provider_registry.py`, `connector_registry.py`,
`validation_registry.py`, `criterion_registry.py`, and `normalization_registry.py`. A "skill catalog"
naming and registering the six generation Protocols (and, if extended, the gate functions) is not a
new pattern this platform would need to invent — it is the sixth-or-seventh instance of a pattern
already proven cheap here.

**Surprising finding, bearing directly on the value question: the caching decorators exist and are
tested, but are not constructed anywhere live.** `CachingStepDefinitionGenerator`,
`CachingFeatureContentGenerator`, `CachingTestDataGenerator`, `CachingPageObjectGenerator`, and
`CachingUtilityGenerator` all exist (per-Protocol decorators, ADR-0050) and each has its own unit
test file — but grepped directly, none is ever constructed inside `scripts/run_requirement_analysis.py`
or anywhere else outside a test file. The decorator pattern that would make "wrap any skill in a
cache" mechanical already exists; nothing wires it live yet. This is a real, pre-existing gap
independent of #2, worth its own future note, but it also means: a skill catalog would not, by
itself, close this — the caching wiring gap is a separate, already-latent finding, not something
adopting #2 would fix or that blocks #2.

**Testability, the value a catalog might otherwise chiefly buy, is already delivered a different way.**
`eval_harness/` already evaluates each generator independently — `feature_content_{eval_set,
properties, runner}.py`, `step_definition_{eval_set, properties}.py`, `test_data_*`, `page_object_*`,
`utility_*` — five parallel per-generator eval surfaces (ADR-0051), the same "test each skill in
isolation" value a skill catalog would otherwise be the mechanism to unlock. It already exists,
achieved by file-naming convention rather than a central registry object.

**Sizing determination: MIXED, decomposed.**

| Part of #2 | Size | Evidence |
| --- | --- | --- |
| Naming the six generator classes + gate functions as first-class, named "skills" | **Re-framing** | They already are Protocol-bounded, single-method, independently stubbed and eval'd; only the label is missing. |
| A registry/catalog exposing them uniformly | **Re-framing** | Mirrors an existing, cheap, six-times-proven pattern (`PromptRegistry` and siblings) — mechanical, not novel. |
| A uniform cross-skill invocation interface | **Re-framing, mostly** | Five of six already share `generate(context) -> str`; the remediator's `remediate(content, violations) -> str` is the one real shape mismatch a common interface would have to paper over or exclude. |
| A skill-selection/routing layer choosing among skills at runtime | **Re-architecture, but with no live use case** | No current need is ambiguous about which generator should handle it — need-kind to generator is a fixed, static 1:1 mapping today. There is nothing for a routing layer to route. |
| Agent-vs-skill routing decided per step | **Re-architecture, and entirely hypothetical today** | See the agent question below — zero current code is agent-shaped; there is no "step" anywhere that would need this decision made. |

**The honest verdict: the cheap, valuable half (catalog + naming) is real and precedented; the
expensive half (selection/routing, agent-vs-skill-per-step) has no current problem to solve.**
Building the routing layer now would be architecture in search of a use case, not a response to a
measured need — the same shape this arc has already declined for utility wiring and the eval judge
layer.

**The value question, grounded in Nitin's own rationale, not abstract architecture-goodness.** Item
2's own opening framing ties this to token minimization and predictability — already fully achieved
(no agent/tool-loop exists; per-stage model scoping and the water-filled evidence budget are the real
token-cost mechanisms, both already live). The separate "bias and token cost" through-line Nitin names
(spec-slicing, the change-impact graph, caching-plus-pinning, the traceability graph) is a different
cluster, already built (`[[cap-pinning-foundation-built]]`, `[[cap-artifact-cache-adr]]`,
`[[cap-traceability-graph-adr]]`) — a skill catalog does not feed that cluster; conflating the two
would overstate #2's own value. What a catalog would concretely buy: **discoverability and governance
visibility** — a single, named, versioned inventory of "what LLM-backed and deterministic capabilities
this platform has," the same role `PromptRegistry` plays for prompts. That is real but modest value
(this session's own read-only repo audit had to re-derive that inventory by reading six separate
files; a catalog would have made that a lookup) — not a reuse, composability, or token-cost win, since
none of those are currently constrained by the catalog's absence.

**The agent question: bounded to one hypothetical, unbuilt place.** Grepped and register-confirmed:
no agent/tool-loop architecture exists anywhere in this platform today (reaffirming the original,
pre-clarification finding above). The one place something agent-shaped could plausibly first appear
is Layer 6 (Failure Intelligence & Self-Healing) — confirmed still UNBUILT, `governing_citation="none
yet"` in `stages.py`, per the 2026-08-23 repo audit. There is no current code, current generator, or
current gate that would benefit from agent-autonomy instead of a skill call — the "agents where
genuinely needed" half of Nitin's framing is entirely a future-L6 question, not a present one.

**Honest current-need check: no measured pain today.** No duplicated capability was found (each
generator/gate has exactly one live implementation), no reuse blocker (constructor injection already
lets any stage swap implementations freely — the `Stub*`/`Live*` pairing already proves this), and no
testing gap (the eval harness already tests each generator independently). This is the same
"surfaced, no measured need now, defer with a named trigger" pattern this session already applied to
page-object activation, utility wiring, #8, and the eval judge layer — not a special case.

**Options.** (A) **Re-frame now**: build a lightweight skill registry (mirroring `PromptRegistry`'s
own register/seal/lookup shape) cataloguing the six generation Protocols and, optionally, the CP4/5/7/8
gate functions, under consistent naming — small, mechanical, no behavior change, a few days at most.
(B) **Re-architect**: additionally build a genuine skill-selection/routing layer and an agent-vs-skill
decision point per step — large, and today would have nothing real to select among or route, since
need-kind already statically determines the generator. (C) **Defer**: record the direction (re-frame,
not re-architect, if ever done) and wait for a concrete trigger — a new (7th+) generator joining the
roster where a catalog would make onboarding it mechanical, Layer 6's agent loop actually getting
built (making the skill-vs-agent distinction load-bearing for the first time), or a recurring external
need to enumerate the platform's capabilities (this audit's own experience is a soft data point, not
yet a real recurring need).

**Recommendation: Option C, with Option A's direction recorded for whenever a trigger appears.** The
re-framing half is cheap and precedented but has no measured pain to relieve today (reusability,
composability, and per-skill testability are already achieved by other means); the re-architecture
half has no live use case to justify it (routing is already static and correct). Building either now
would be forward-looking reorganization, not a response to a real gap — consistent with this session's
own pattern for every other "surfaced, no consumer yet" item. If Layer 6 is ever designed, revisit
#2's re-architecture half specifically then, since that is the one place the skill-vs-agent decision
would become real. Nothing built, wired, or changed by this note — investigation only. Gate: `make
lint` clean; `make test` 6106 passed, unchanged.

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
   The corpus-level question — the one Nitin is actually worried about — is genuinely new.
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

**Consensus signal: highest of all eight items.** Nitin flags this repeatedly, in both rounds of his
own feedback (his reply's "house of cards"/input-quality framing, and his original list's
completeness + KG framing) — this is squarely Nitin's own #1 strategic risk, even though it is also
the heaviest single item on this list.

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
this document already identified as Nitin's own top strategic risk (see the Synthesis
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
  framing). **Highest strategic value on this list** — Nitin's own consistently-named #1 risk;
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
"completeness thread" (this document's own Synthesis section, below, and Nitin's own
consistently-named #1 risk) has been missing since this item's own earlier assessment:
requirement→scenario/step queryability turns "is the corpus incomplete" from a qualitative worry
into a queryable answer, mostly buildable now, without L5. Building traceability *is* addressing
completeness — the two are not separate future tasks, they are the same work read from two angles.
This also connects forward to the L1 as-built LLD and mentor item #3-completeness — same
underlying work, not duplicated effort.

**Recommendation.** Build **traceability first** — highest strategic value, mostly buildable now
(module the execution-result hop to L5), and it is the completeness mechanism Nitin already
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

**REAL COMPLETENESS MEASURED (2026-08-12) — Nitin's #1 concern answered with real numbers, on the
real corpus (not the synthetic ADR-0023 provider).** Ran the projector + `evaluate_completeness`
against the most recent real live run's own artifacts
(`output/executions/run-20260812T064317663150Z-a20b0cc2/` — the same 20-requirement, real-Gemini
run the token-instrumentation measurement used) via a thin, uncommitted scratch harness (mirrors the
page-object script-harness pattern; not wired into the pipeline, not a repo artifact) — loading the
real `testable_requirement_set.json` and `feature_engineering_package.json`, re-parsing the real
on-disk `.feature` files under the run's own `workspace/src/test/resources/features/`. **Result: 20
requirements, 20 scenarios, 67 steps, 100% coverage — every requirement has a full
requirement→scenario→step chain. Zero uncovered requirements.** The corpus is Gherkin-complete at
this minimal slice.

**The honest caveat this result demands — "complete" here means "has a test chain," not "has a
passing test."** Cross-referencing the SAME run's `cp3_report.json` and
`automation_engineering_package.json` shows a real, separate gap this graph's own minimal scope
cannot see: CP3 reports 34 of these exact same 67 steps have no step-definition binding at all
("34/67 steps unmapped, 49.3% step coverage," `overallVerdict: fail`) — consistent with the
automation-engineering package's own step-definition-need outcomes (60 unique step-definition needs
after dedup, 30 `bound` / 30 `escalated`, an exact 50/50 split). **This is not a contradiction — it
is two different, both-real layers of completeness, measured honestly:** Gherkin-authoring
completeness (this graph, 100%) and step-definition-binding completeness (CP3, ~49–50%) are
distinct questions, and this graph's own deliberately-deferred page-object/step-definition hop is
exactly the gap between them. A requirement counted "covered" by this report has a scenario and
steps written; it does not yet have a proven, working generated test — that is precisely the future
hop this build already flagged as deferred, now given a concrete number.

**Scope-specific, not a general claim.** This is the real completeness picture for this specific,
current saucedemo-based 20-requirement corpus, not a claim about corpus completeness in general —
a different or larger corpus could show real requirement-level gaps this minimal slice is fully
built to detect (the fixture tests already prove the `no_scenario`/`scenario_without_steps`
detection works; this corpus simply doesn't happen to exercise it).

**CAPABILITY ADR WRITTEN (2026-08-12) — closes the scores-first governance debt this build itself
flagged.** `docs/adr/0048-traceability-graph.md` — **Accepted**, recommended id `CAP-088` (not yet
entered in `docs/governance/platform-capability-matrix.md` — flagged as a follow-on, not performed).
Records the capability, the CASE-B decision (reuse ADR-0023's pattern, not its frozen
Historical-Truth-only service), the minimal-slice scope + named deferred hops, the scores-first
report-only posture, and D5's own real measurement above as the capability's first recorded data
point. **A genuine placement nuance surfaced while writing it, not previously stated this
precisely:** this capability consumes Runtime Truth directly (`TestableRequirementSet`,
`FeatureEngineeringPackage`) — exactly why it could not extend `KnowledgeGraphService` — which means
it does not satisfy ADR-0021's own strict Layer-2 Historical-Truth-only definition. The ADR records
this honestly (its own D2) and leaves precise layer placement an explicitly open question for a
future ADR-0020/ADR-0031 amendment, mirroring `CAP-087`'s own still-open placement (ADR-0042
Decision 7) rather than silently asserting "Layer 2" where the constitution does not actually fit.
ADR-0023 itself is referenced, not edited — additive only. `make lint`/`make test`: 5771 passed,
unchanged; only the new ADR file added.

**STEP-DEFINITION-BINDING HOP BUILT (2026-08-12) — closes the exact gap this section's own
"honest caveat" named, within ADR-0048's already-named scope, no ADR amendment needed.**
Pre-flight read ADR-0048 D4's canonical deferred-hops list (page-object, execution-result,
change-impact, state/flow) against D5's own later text, above, which names the SAME deferred item
as **"the deferred page-object/step-definition hop"** — a single bundled hop, not two. D4 itself
only ever describes the page-object *call-site* linkage (`page_object_reference_derivation.py`),
never the step→step-definition existence question CP3 answers; but D5's own compound name, written
by this ADR's own author when tying the CP3 finding back to D4, is direct textual evidence the
binding question was already folded into that one named hop, not silently omitted. Verdict:
**in-scope — built, no ADR-0048 amendment required.**

Added a companion, not a replacement: `BindingCompletenessReport`/`UnboundStep`
(`traceability_graph/models.py`) and `evaluate_binding_completeness`
(`traceability_graph/completeness.py`), joining each STEP node's own `label` (the raw Gherkin text
`project_traceability_graph` already carries) against `AutomationEngineeringPackage`'s
`need_kind == "step_definition"` records (`automation_engineering.stage.models` — the same
structured artifact this section's own real measurement, above, already cited; a clean,
already-established peer dependency, mirroring the existing `feature_engineering.stage.models`
import in `projection.py`). A step is bound iff a matching record exists and is not `escalated`.
**Shape chosen: annotation, not a step-definition node layer** — an escalated need's own
`class_name` is `null` (no identity yet), which would violate `TraceabilityNode.referenced_id`'s
`min_length=1` invariant if modeled as a node; a lightweight report mirrors `CompletenessReport`
instead, no change to the existing node/edge shape.

**Re-run against the same real run's artifacts this section already measured
(`run-20260812T064317663150Z-a20b0cc2`): 67 STEP nodes, 33 bound / 34 unbound, 49.25% —
reproducing CP3's own "34/67 steps unmapped (49.3% step coverage)" exactly**, all 34 unbound for
reason `"escalated"` (zero `"no_step_definition_need"` cases — every step's text matched a real
automation-package need, as expected for a same-run artifact set). The two-layer picture above
(100% authoring, ~50% binding) is now one graph's own two reports, not a manual cross-reference.
Scope discipline held: the step-definition's own internal call sites into page objects (the other
half of D4's named hop), the execution-result hop, change-impact, and state/flow all remain
deferred, untouched. `make lint`: clean. `make test`: **5780 passed** (5771 + 9 new, fixture-based,
`tests/unit/test_traceability_graph.py`). `mypy` on the touched packages: clean, no new errors.
Report-only, unchanged posture: no gate, no threshold on either completeness layer. Not wired into
any execution pipeline — same as the rest of this capability. Neither `docs/adr/0048-traceability-graph.md`
nor the `CAP-088` row in `docs/governance/platform-capability-matrix.md` needed a status change: the
binding hop was governed *within* ADR-0048's existing text before this build, not amended by it —
this entry is the additive record of the build, mirroring how "CAPABILITY ADR WRITTEN" above records
the ADR without retro-editing it.

**CHANGE-IMPACT GRAPH DESIGN SURFACED (2026-08-13) — a design-surfacing task (build nothing),
resolving Nitin's second-prioritized graph (change-impact: "code/pages → elements → steps →
scenarios... a selector change should let you identify the 8 affected tests, not rerun hundreds")
against the real substrate, correcting one stale finding from the 2026-08-12 note above.**

*Pre-flight.* Clean tree, `main`, tip `caceba2` (the Engineering Constitution's governance loop
closed). `make lint` clean. `make test`: 5780 passed, unchanged. This note adds text only to this
document; nothing else touched.

**The pattern reused.** `requirement_intelligence/traceability_graph/` (built above) is the
template: frozen, camelCase, reference-not-copy `TraceabilityNode`/`TraceabilityEdge`/
`TraceabilityGraph` models (`models.py`) with a governed `StrEnum` node/edge vocabulary; SHA-256
deterministic identity (`identity.py`); a type-agnostic directed-adjacency BFS traversal
(`traversal.py`, forward-only today — `build_directed_adjacency`/`reachable_from`); a deterministic
projector re-parsing real, already-produced artifacts directly, never a synthetic stand-in
(`projection.py`); a report-only completeness layer with no gate, no threshold
(`completeness.py`). Change-impact reuses every one of these exactly, as an **extension of this
same package**, not a new sibling — see Architecture, below.

**Correcting the 2026-08-12 finding: locator/element data is not "genuinely absent" — it is
real, but incomplete for this purpose.** The prior note above ("element/selector-level mapping is
NOT captured anywhere — no structured locator model exists anywhere in the generation pipeline")
was accurate *as of that date* but is now stale: `automation_engineering/cp4/extraction.py`
(governed by ADR-0044 D6, built after that note) deterministically extracts exactly this —
`Cp4Locator(class_name, field_name, strategy, value)` — from generated page-object Java, both the
platform's own `private final By field = By.id(...)`/`.xpath`/`.cssSelector`/... convention and
the `@FindBy(...)` annotation shape, via the same `javalang` technique
`page_object_reference_derivation.py` already uses. **What CP4 does NOT do, confirmed by reading
its own gate** (`automation_engineering/cp4/gate.py`): all four of its criteria
(`locator_uniqueness`, `duplicate_locators`, `dynamic_xpath`, `well_formedness`) reason about
locator *fields* only — uniqueness and fragility of the (strategy, value) pair itself — never
which *method(s)* on the page object reference a given field. The genuinely missing piece is
narrower than previously stated: not "locator data," but **the field → method usage link**
(walking each method's own body for references to a declared locator field, the same
`javalang`-statement-walk CP4's own extraction and `page_object_reference_derivation.py`'s own
call-site derivation already use — a small, precedented addition, not a new kind of problem).
**A second, separate caveat, unrelated to the data model:** CP4 itself is currently wired
vacuously in the live runner — `automation_engineering/stage/runner.py:507`:
`cp4_result: Cp4Result = evaluate_cp4(())`, because page-object generation is not live-wired by
default (the same root cause `[[cap-page-object-live-wiring-decision]]` already recorded) — so
today CP4's real extraction code runs only over real generated page objects when the script-harness
path is used, not in an ordinary live run.

**The buildable-now (method-level) chain, verified link by link, all real, all already built:**
- STEP → SCENARIO (reverse direction). The traceability graph's own `STEP` node id
  (`f"{scn_id}::step-{ordinal:03d}"`, `projection.py`) already embeds its owning scenario — each
  `STEP` node has exactly one `HAS_STEP` edge into it, from exactly one `SCENARIO` node (steps are
  not deduplicated across scenarios in this graph's own model). Only `traversal.py`'s own
  adjacency builder is forward-only; a reverse-adjacency variant (swap `source`/`target` when
  building the map) is a small, type-agnostic, purely additive function — the same shape as the
  existing one, not a new algorithm.
- STEP → STEP-DEFINITION. Already built and already joined: `completeness.py::
  evaluate_binding_completeness` matches a `STEP` node's own `label` (raw Gherkin text) against
  `AutomationEngineeringPackage`'s `need_kind == "step_definition"` records, giving the bound
  step-definition's `class_name` (when not escalated).
- STEP-DEFINITION → PAGE-OBJECT METHOD(S). Already built, real, tested:
  `automation_engineering/generation/page_object_reference_derivation.py::
  derive_page_object_requests(java_source)` deterministically parses a **generated** step-def's own
  Java source (on disk in the run's workspace) and returns exactly which page-object class and
  method(s) (with resolved parameter/return-type shape) that step-def's body calls. This function
  is not persisted as an artifact today (`AssetRecord`, `automation_engineering/stage/models.py`,
  carries no page-object-call-site field — confirmed by its own docstring: "no page-object/utility
  `AssetRecord` is ever produced here") — but it needs no new derivation logic, only a new call
  site: a change-impact projector re-parses the same on-disk generated `.java` files
  `derive_page_object_requests` already knows how to read, exactly mirroring how
  `project_traceability_graph` itself re-parses `.feature` files from disk rather than reading a
  summary artifact.
- **Net: PAGE-OBJECT METHOD → (reverse) STEP-DEFINITION → (existing join) STEP → (new reverse
  adjacency) SCENARIO is buildable now, by composing three already-existing, already-tested,
  deterministic functions plus one small, type-agnostic reverse-traversal helper. No LLM, no new
  heuristic, no open research question.**

**The blocked (element-level) chain — one real, bounded prerequisite, not an open-ended gap.**
Nitin's own headline example is element-level: a locator's *value* changes (a selector, not a
method signature) and the question is which tests that specific field touches. That needs exactly
one new function: `field_name → {method_name, ...}` — which method bodies reference a given
locator field, via the identical `javalang` method-body walk CP4's own extraction and
`page_object_reference_derivation.py`'s own call-site derivation already use twice over. Once that
one link exists, element-level change-impact is: locator field change → (new link) → affected
method(s) → (existing, reversed) affected step-definition(s) → (existing) affected `STEP`
node(s) → (new reverse adjacency) affected `SCENARIO`(s) — the exact "8 affected tests" shape,
composed entirely from precedented, already-proven extraction techniques.

**The value question: is method-level alone worth building, before element-level exists?**
Answered directly. Method-level change-impact answers a coarser question than Nitin's own example
— "if this page-object *method*'s behavior/signature changes, which scenarios are affected,"
not "if this exact selector changes" — but a locator-value-only edit (no method signature change)
that has no linked change-impact data at all would, absent any granularity, force treating the
*whole class* as changed, and every method on it (and therefore every scenario calling any of
them) as potentially affected — already a real narrowing from "rerun the whole suite" down to "the
scenarios touching this one page object," even before method- or element-level precision exists.
Method-level narrows that further, to "the scenarios touching the specific method(s) that
changed." Each granularity tier is a strict refinement of the one before it (class → method →
element), so building method-level now creates no rework when element-level is added later — the
element-level link only makes an existing method-level edge more precise, it does not replace the
graph shape. **Verdict: method-level is a real, substantial, immediately buildable delta-regen
increment, reusing ~90% already-built machinery — worth building now, not gated on element-level.**
This is also consistent with today's own token-distribution data (Item 1's re-run-cost note,
above): generation cost is not concentrated in one stage, so a change-impact graph that lets
regeneration skip *any* untouched scenario — even at method granularity — is real leverage, not a
marginal one.

**Architecture: an extension of `traceability_graph/`, not a new sibling service** — differing
from how *traceability itself* related to `knowledge_graph/` (D2's frozen-service-boundary CASE B,
above). No equivalent boundary conflict exists here: change-impact would add exactly one new node
type (`PAGE_OBJECT_METHOD`) and one new edge type (e.g. `CALLS_METHOD`, `STEP → PAGE_OBJECT_METHOD`)
onto the *same* `TraceabilityGraph` model, projected by the *same* package, reading the *same*
class of Runtime Truth artifacts (`traceability_graph/` already established its own D2 placement —
Runtime Truth consumption, not ADR-0021's strict Historical-Truth-only Layer 2 shape — extending it
does not newly cross that boundary, it is already on this side of it) — plus a new, report-only
`evaluate_change_impact(graph, changed_method) -> ChangeImpactReport`-shaped query, mirroring
`evaluate_completeness`'s/`evaluate_binding_completeness`'s own report-only posture exactly (no
gate, no threshold). The element-level link (above) would be a further, additive edge annotation
on the same `PAGE_OBJECT_METHOD` node (or a sibling `LOCATOR` node/edge pair), not a redesign.

**Governance verdict: already in ADR-0048's own named scope — no new ADR, no amendment,
confirmed by re-reading its actual text, not assumed.** ADR-0048 §D4 ("The minimal slice, and the
named deferred hops") names, verbatim: *"**Change-impact graph** (code/pages → elements → steps →
scenarios) — a distinct capability the scoping doc's own design-surfacing task separately scoped;
method-level linkage is buildable from the same page-object call-site data above, but
element/selector-level mapping... has no structured source anywhere yet."* This is the identical
governance shape the step-definition-binding hop already used successfully (D5's own "governed
*within* ADR-0048's existing text... not amended by it"): change-impact — both the method-level
slice and its element-level follow-on — is already named, deferred future scope of this same,
Accepted ADR. Building it (a future task, not this one) requires no status change to ADR-0048 and
no new ADR; it would be recorded the same additive way the binding hop was. **One nuance worth
flagging honestly:** D4's own heading calls every deferred item a "hop," but individually labels
two of the four "hop" (page-object, execution-result) and two "graph" (change-impact, state/flow)
— an inconsistency in ADR-0048's own text, not a substantive ambiguity about scope; both readings
place change-impact inside ADR-0048's already-governed deferred set.

**Options + recommendation.**
- **Method-level now** — buildable today (chain verified above), real delta-regen value, reuses
  the traceability pattern as an extension, already in ADR-0048's named scope. **Recommended.**
- **Element-level as a named follow-on** — needs exactly one new, small, precedented extraction
  (field → method usage, the same `javalang` technique used twice already in this codebase); not
  blocked on anything else once that one function exists. Named explicitly, not silently deferred,
  mirroring D4's own already-deferred framing.
- **Defer everything until element-level exists** — considered and rejected: method-level's own
  value does not gate on element-level (Value question, above), and delaying it would leave the
  real, already-buildable delta-regen win unbuilt for no architectural reason.

**The delta-regen dependency, named, not designed.** Change-impact is the direct input Item 1's
own re-run/token-cost cluster (`[[cap-mentor-clarification-prep]]`'s delta-scoped regeneration
answer, and Nitin's own "regenerate only what changed" framing) needs to know *what a change
actually reaches* — this note is a prerequisite for that later work, not that work itself; no
caching, pinning, or regeneration logic is designed or built here.

**Clarify-with-mentor nuance, flagged.** Nitin confirmed change-impact as his second-prioritized
graph type and gave the selector-level example himself, but did not weigh in on the specific
method-vs-element sequencing or the extend-vs-sibling architecture question this note resolves —
those are this note's own reading of the real code, the same caveat already flagged for
traceability's own extend-vs-separate call, above.

**Nothing built by this note.** No new node/edge type, no new projector, no new reverse-traversal
function, no ADR, no register entry, no capability-matrix row. This surfaces the buildable-now vs.
blocked scope, corrects the stale "no locator data exists" finding against the real CP4 code, and
recommends method-level change-impact as the next build (a future, separate task) reusing
`traceability_graph/`'s own pattern as an extension.

**METHOD-LEVEL CHANGE-IMPACT BUILT (2026-08-13) — the buildable-now half of the design-surfacing
note above, built exactly as scoped: an extension of `traceability_graph/`, method-level only.**
Two additions to the SAME `TraceabilityGraph` model, never a new sibling: `PAGE_OBJECT_METHOD`
(`TraceabilityNodeType`) and `CALLS_METHOD` (`TraceabilityEdgeType`, `STEP -> PAGE_OBJECT_METHOD`).
A new module, `requirement_intelligence/traceability_graph/change_impact.py`:
`project_change_impact(graph, automation_package, workspace_dir=...)` extends an already-projected
graph by joining each `STEP` node's own text against `AutomationEngineeringPackage`'s
`step_definition` records (the SAME join `evaluate_binding_completeness` already uses), reading the
matched **`"generated"`** record's own real Java source off disk
(`workspace_dir / record.workspace_path`) and deriving its page-object call sites via the platform's
own, already-built, already-tested `automation_engineering.generation.
page_object_reference_derivation.derive_page_object_requests` — no new derivation logic, only a new
call site, exactly as the design-surfacing note predicted. `traversal.py` gained one small, pure,
type-agnostic addition, `build_reverse_directed_adjacency` (swap source/target; `reachable_from`
itself, already generic, needed no change) — proven directly to walk `CALLS_METHOD -> HAS_STEP ->
HAS_SCENARIO` backward from a changed method to every ancestor STEP/SCENARIO/REQUIREMENT in one BFS.
Two new query functions answer the delta-scoping question: `change_impact_for_method(graph,
class_name, method_name) -> MethodImpact | None` (one method's own affected-scenario set) and
`build_change_impact_report(graph) -> ChangeImpactReport` (the full method -> affected-scenarios
map, the shape a future delta-scoped-regeneration capability would consume). Both report-only —
`ChangeImpactReport`/`MethodImpact` carry no `passed`/`verdict`/`gate_status` field anywhere, proven
structurally in the same style the binding-hop's own report-ready-but-no-gating test already used,
not merely by never failing.

**Proof, fixture-based, no LLM, no live run.** A two-scenario-share-one-step-text, one-scenario-
distinct-text fixture (mirroring `derive_unique_step_needs`'s own dedup-by-text rule): scenarios
`SCN-S1`/`SCN-S2` both use the literal step "user logs in," bound to a **generated**
`LoginSteps.java` whose body calls `LoginPage.clickLogin()`; `SCN-S3` uses "user logs out," bound to
a **generated** `LogoutSteps.java` calling `DashboardPage.logout()`. `change_impact_for_method`
returns exactly `{SCN-S1, SCN-S2}` for `LoginPage.clickLogin` and exactly `{SCN-S3}` for
`DashboardPage.logout` — proving the delta-scoping narrowing precisely, never over- or
under-inclusive. `build_change_impact_report` reproduces both entries as one map. Determinism
proven directly (two `project_change_impact` calls over identical input produce an identical
graph). **The scope boundary held, proven not assumed:** a `"bound"` record (no `workspace_path`)
and an `"escalated"` record each contribute nothing (`extended == graph`, no exception); a
`workspace_path` naming a file that does not exist on disk is skipped silently, mirroring
`project_traceability_graph`'s own "absence is a signal, never a crash" discipline for `.feature`
files, applied here for generated Java. **Non-corruption of the existing layers, proven directly:**
`evaluate_completeness`/`evaluate_binding_completeness` return byte-identical results computed over
the base graph vs. the SAME graph after `project_change_impact` extended it — adding new node/edge
types does not perturb the existing traversal-based reports, confirmed by equality assertion, not
argued from code reading alone.

**Scope held exactly as recommended.** Method-level only — no element/locator-level change-impact
(the field -> method usage link remains the named follow-on), no gating, no delta-regen action (this
graph *identifies* the affected set; *acting* on it — regenerating only those scenarios — is
Nitin's own future caching cluster, untouched here), no live wiring (`PlatformContext` gains no new
method, mirroring how the completeness/binding layers are also not wired into any execution
pipeline). The containment invariant holds unchanged — `TestScopeDiscipline`'s own AST-walking test
already globs every `*.py` file in the package, so the new `change_impact.py` module is covered
without a test change, and it imports no `knowledge_graph` module.

**Governance: no ADR-0048 amendment, additive record only — the identical determination the
binding hop already made.** ADR-0048 §D4 already named "change-impact graph" as deferred scope,
verbatim, including the exact method-level/element-level split this build's own design-surfacing
note quoted — this entry is that named scope's own build record, not a new decision. Neither
`docs/adr/0048-traceability-graph.md` nor the `CAP-088` row in
`docs/governance/platform-capability-matrix.md` needed a status change, mirroring exactly how the
step-definition-binding hop's own entry, above, reached the identical conclusion.

`make lint`: clean. `make test`: **5796 passed** (5780 + 16 new: `tests/unit/
test_traceability_graph.py` gained `TestChangeImpactProjection` (6 tests), `TestChangeImpactQuery`
(6 tests), two `TestModelInvariants` validator tests, one `TestIdentityAndTraversal` reverse-adjacency
test, and one `TestSerialization` renderer test). One unrelated pre-existing flaky thread-safety
test (`test_cp1_engine.py::TestThreadSafety::test_concurrent_runs_are_independent`) failed once
under full-suite load and passed on immediate rerun in isolation and in the full suite — not caused
by this build, confirmed by its own unrelated file and by the rerun. `mypy`: whole-repo count
unchanged (432, pre-existing); zero errors in `traceability_graph/` or the new
`change_impact.py` module. **The delta-regen dependency, now genuinely unblocked, not merely
named:** Nitin's own delta-scoped-regeneration cluster (`[[cap-mentor-clarification-prep]]`) can now
consume a real `ChangeImpactReport` instead of a design note — this build is that cluster's
prerequisite, not that cluster itself; no caching, pinning, or regeneration logic exists anywhere in
this package.

---

**#3a DESIGN-SURFACING SURFACED (2026-08-24) — the heaviest remaining mentor item, both mentors'
independently-named #1 strategic risk. Decision-support only: build nothing, change nothing.**

*Pre-flight.* Clean tree, `main`, HEAD `4219d82`. `make lint` clean. `make test`: **6106 passed**,
unchanged. This note adds text only to this document; nothing else touched.

**What #3a is, precisely, now that #3b (graphs) is built.** Item 3's original "Already-partly-done?"
list (above) had three parts: (1) subset-not-everything (ingestion volume), (2) completeness, (3)
Knowledge Graph. Part 3 is done — the traceability graph (ADR-0048) shipped, governed, and is now
answering real numbers (D5/D5-binding above: 100% Gherkin-authoring coverage, ~50% step-definition-
binding coverage, on the real 20-requirement corpus). **#3a is what's left: parts 1 and 2 — subset-
not-everything and corpus/input completeness — the mentor-program tracking label the repo audit
(`[[cap-repo-audit-2026-08-23]]`) already uses for this remaining pair.** This note resolves the
buildable-vs-blocked question that memory entry flagged as still open.

**The distinction, made precise.** `evaluate_completeness`/`evaluate_binding_completeness`
(`traceability_graph/completeness.py`, read directly, both confirmed by direct reading this session)
answer: *given the `TestableRequirement` nodes that already exist in this run's `TestableRequirementSet`,
does each one reach a full scenario→step chain, and is each step bound to a step-definition?* Both
traverse a graph built **from** the requirement set — neither ever asks whether the requirement set
itself is missing a requirement. **This is coverage-completeness (BUILT). #3a is input/corpus
completeness — are the requirements themselves a complete picture of what should be tested — a
different, still-open question**, exactly the "house of cards" framing: coverage-completeness is
complete *relative to* whatever the corpus already contains; if the corpus is short a requirement,
coverage-completeness reports 100% over an incomplete set and never flags it.

**What #3a encompasses — both sub-questions, read from the original item-3 text and Nitin's own
follow-up, not merely assumed:** (a) **corpus-set internal completeness** — are there missing
requirements, inferred from the existing set or from history (the KG/inference angle); (b)
**subset-not-everything** — feeding a relevant subset rather than the whole corpus, for token/
hallucination control. These are related (both are about the *input* side of the pipeline, both
were named together as one item) but not identical: (a) is a completeness question, (b) is a
volume/relevance question. Confirmed via direct code reading, `TestableRequirement`
(`contracts/testable_requirement.py`) carries **no cross-requirement relationship field** —
`traces_to` links out to external `SourceRef`s (JIRA/doc), `supersedes` links to a prior version of
the *same* requirement's own lineage — there is no field linking one requirement to another sibling
requirement it might imply, depend on, or duplicate. This matters directly for the verdict below: a
within-run, requirements-only internal-consistency check has almost no relational data to reason
over today.

**What it touches — ADR-0032, confirmed by reading its actual freeze text, not inferred.** Both
sub-questions are new Layer 1 judgment: (a) inferring a missing requirement from the existing set or
from history, and (b) intelligently prioritizing which requirements matter most for a subset, are
each a new reasoning capability over `requirement_intelligence/`'s own domain, not a bugfix,
contract-emission, or orchestration carve-out. Checked against ADR-0032 §"Permitted carve-outs"
(the five: `TestableRequirement` emission, run/stage-state integration, ADR-0033 renames, bugfixes,
tests) — **neither sub-question fits any of the five.** Building either directly into Layer 1 (new
extraction/inference logic *inside* `requirement_intelligence/`'s own governed pipeline, e.g. new
CP1/enhancement/grounding rules) requires the freeze lifted first, per ADR-0032's own three-part
procedure: (1) Layer 2 (Feature Engineering) must have reached Runtime Integration, (2) Architecture
Review Board approval, (3) the lifting ADR names the specific new CAP number(s) — general lifts are
out of policy.

**A genuinely new finding this session: precondition (1) is now factually met, but that does not
mean the freeze is lifted.** `[[cap-repo-audit-2026-08-23]]` and this session's own re-check both
confirm Layer 2 (Feature Engineering, stage 14) is BUILT and live — Runtime Integration reached, the
same milestone ADR-0032 §"How the freeze is lifted" names as its exit condition. ADR-0032's own
2026-07-25 resolution note already anticipated this exact question and answered it directly for
ADR-0043 ("Layer 2's own Architecture Freeze... is stage 1... not stage 4 [Runtime Integration]...
this freeze is not lifted by it") — at that time Layer 2 hadn't reached Runtime Integration yet. It
has now. **Precondition 1 is satisfied today; preconditions 2 and 3 are not — no Architecture Review
Board action has been taken, and no ADR names a specific Layer 1 CAP number for this capability.**
The freeze is not lifted by anything that has already happened; the *first* of its three gates has
simply stopped being the blocking one. This narrows a hypothetical freeze-lift path's remaining
work, but lifting the freeze is still a deliberate governance act requiring the other two steps —
not something a design-surfacing note performs or assumes on the user's behalf.

**What it depends on — the unbuilt Historical Dataset, confirmed by reading the code, not the
prose.** Read `requirement_intelligence/knowledge_graph/engine/historical_dataset.py` directly:
`DeterministicHistoricalDatasetProvider.resolve` synthesizes every field —
`execution_id`/`requirement_id`/`recommendation_id`/`finding_id`/`capability_id`/`document_id` — as
a pure SHA-256 digest of the reference's own provenance fields (`dataset_id`, ordinal), never real
requirement data from any actual past execution. Its own docstring says so plainly: "No Historical
Dataset storage implementation exists yet (ADR-0021 §Stage 6)... A future milestone replaces this
with a provider backed by a real Historical Dataset implementation." Grepped for any other
implementation anywhere in the repo — none exists; every hit is this same synthetic provider
(Knowledge Graph's copy) or its Continuous Improvement sibling, same pattern, same absence. ADR-0021
itself: **Status now reads "Accepted (ratified by ADR-0049)"** — but ADR-0049 §D2 is explicit that
ratification covers only "the lineage's substantive constitutional content — the Truth Hierarchy,
Historical Dataset Resolution Principle..." and explicitly **does not** ratify "ADR-0021–0029's
runtime contracts" (there are none to ratify — none were ever built). Ratifying the constitution is
not building the service it describes. **Corpus/input completeness genuinely depends on this,
because "is a requirement missing" is not answerable from one execution's own data alone** — it
requires comparing this run's requirement set against a pattern established across many prior runs
(what a given component/functional_tag usually yields, what recurs across executions) — exactly the
Historical Truth layer ADR-0021 defines and nothing has built.

**The KG connection — boundary-blocked, same shape as the #3b graphs finding, re-confirmed.**
ADR-0023's `KnowledgeGraphService.build` is frozen (D2/Recommendation 9, quoted above in the #3b
notes) to consume `HistoricalDatasetReference` only — never a Layer 1 runtime contract, never an
Execution Package artifact, directly. This is the identical boundary that forced traceability/
change-impact to become a new sibling service rather than an extension of `knowledge_graph/`. For
completeness inference, the KG's frozen boundary is not fatal in principle — completeness genuinely
*is* a Historical-Truth-shaped question (per the paragraph above), unlike traceability/change-impact
which needed per-run Runtime Truth the KG boundary correctly forbids it from touching. **But today
the KG cannot host it either way**, because the Historical Truth it would need to consume doesn't
exist — only the synthetic stand-in. Once a real Historical Dataset exists, the KG (or a sibling
built the same way) becomes the *architecturally correct* home for this reasoning; today it is
simply empty of anything real to reason over.

**THE VERDICT — mostly BLOCKED, with one narrow buildable-now slice named honestly as a lesser
proxy, not equated with the real question.**

- **Sub-question (a), corpus-set completeness (missing requirements):** **BLOCKED**, on two real
  prerequisites — the unbuilt Historical Dataset (ADR-0021 §Stage 6) for any inference that compares
  against history, and the ADR-0032 freeze-lift (precondition 1 met, 2/3 not) for any inference
  built as new judgment logic *inside* Layer 1 itself. A within-run-only version (reasoning purely
  over the current `TestableRequirementSet`, no history) has near-zero relational data to work with
  today — `TestableRequirement` carries no cross-requirement links (confirmed above) — so even
  waiving both prerequisites, there is little for it to detect beyond trivial duplicate-content-hash
  checks. Not a real answer to "are we missing requirements."
- **Sub-question (b), subset-not-everything (intelligent prioritization):** **BLOCKED** on the same
  freeze question. ADR-0032's own text names this exact case: "If the platform genuinely needs
  Layer 1 itself to change (e.g., ingestion-time prioritization), the freeze-lift path is real,
  slower work" — this is that case, verbatim.
- **One buildable-now slice, real but narrower than either sub-question: ingestion-funnel
  visibility.** The JIRA connector already computes two real, already-available numbers per run —
  issues fetched under `_max_issues`'s pagination cap, and the final `TestableRequirementSet` count
  after enhancement/grounding/CP1 — but nothing today reports the *drop-off* between them (how many
  fetched issues never became a `TestableRequirement`, and whether the pagination cap itself was hit,
  meaning issues beyond it were never even fetched). Reporting this pair of counts needs no new
  Layer 1 judgment (it aggregates numbers each already-governed stage already produces), no
  freeze-lift, and no Historical Dataset — a Layer 2+ consumer (or even a Layer 1 reporting-only
  carve-out, arguably bugfix-adjacent instrumentation) could emit it. **Named honestly: this is
  visibility into "how much of the source did we see and keep," not "are we missing a requirement
  a human would expect to exist."** It answers a real, smaller, adjacent question — worth naming,
  not worth conflating with #3a's actual ask.

**The prerequisite sequence, if #3a is taken on later.** Historical Dataset service (ADR-0021 §Stage
6, real build — the same prerequisite every completeness-adjacent thread in this document converges
on: the #3b graphs note above, the Knowledge Graph's own synthetic-provider caveat, and now this)
→ (in parallel, independent of the Dataset) ADR-0032 freeze-lift, if corpus-completeness needs new
judgment *inside* Layer 1 rather than as an arm's-length consumer (precondition 1 already met;
precondition 2/3 remain a deliberate governance act) → the completeness/subsetting capability itself,
built as a new Layer 2+ consumer of Historical Truth (mirroring how traceability/change-impact
already avoided the freeze entirely by consuming Runtime Truth as an arm's-length Layer 2+ peer,
never touching Layer 1's frozen internals) — the same "arm's-length Layer 2+ consumer" framing this
item's own original recommendation (above) already named as the cheapest real path, now confirmed
concretely against ADR-0021/0023/0032's real text rather than argued abstractly.

**Options.**
- **OPTION A — build the buildable slice now (ingestion-funnel visibility).** Real, cheap,
  unblocked, but answers a narrower question than #3a's own ask — a proxy, not a substitute.
- **OPTION B — defer #3a, blocked.** Both real sub-questions need prerequisites that don't exist yet
  (Historical Dataset built; freeze-lift enacted, not just precondition-1-eligible). Honest verdict,
  not a dead end — the prerequisite chain above is now concrete, not vague.
- **OPTION C — surface the Historical Dataset service (ADR-0021 §Stage 6) as the actual next
  actionable step.** It is the shared prerequisite for #3a's deeper half, and this session confirms
  (again) that it is the same recurring blocker the #3b graphs note, the Knowledge Graph's own
  built-on-a-stand-in status, and this note all converge on independently.

**Recommendation.** **Option C, with Option A as a cheap, honest side-build if visibility is wanted
now.** #3a itself — both mentors' #1 strategic risk — is genuinely blocked, not dodged: real
corpus-completeness inference needs history that does not exist yet, and intelligent subsetting
needs Layer 1 judgment the platform has deliberately frozen pending Layer 2+ proof (a freeze this
session confirms is now one precondition closer to liftable, not fully liftable). The highest-
leverage next action toward #3a is not #3a itself — it is scoping the Historical Dataset service,
the same unblocker three independent threads in this document now point to. Building the ingestion-
funnel visibility slice (Option A) is optional, cheap, and honest about what it is — it does not
substitute for, or reduce the size of, the real prerequisite chain above.

**Nothing built by this note.** No new package, no new field, no ADR, no freeze-lift, no register
entry, no capability-matrix row. This resolves the buildable-vs-blocked question
`[[cap-repo-audit-2026-08-23]]` left open, distinguishes coverage-completeness (built) from
input/corpus completeness (#3a, still open), and names a concrete, evidence-grounded prerequisite
chain and a narrow honest buildable-now slice; building any of it remains a future, separate task.

---

**HISTORICAL DATASET SERVICE SURFACED (2026-08-24) — the shared prerequisite #3a named, resolved
against ADR-0021's actual text and the real on-disk data. Decision-support only: build nothing,
change nothing.**

*Pre-flight.* Clean tree, `main`, HEAD `af1b4db` (the #3a note above, already committed by the
user). `make lint` clean. `make test`: **6106 passed**, unchanged. This note adds text only to this
document; nothing else touched.

**The convergence, checked, one correction.** The #3a note above and the KG synthetic-provider
caveat (#3b's "GRAPHS DESIGN SURFACED" note) both genuinely name the Historical Dataset as a real,
current blocker: #3a's corpus-completeness inference needs cross-run comparison data that doesn't
exist; the Knowledge Graph runs live today (CAP-084C) but only ever over
`DeterministicHistoricalDatasetProvider`'s synthetic SHA-256 output, never real requirement data —
both true, re-confirmed this session. **The change-impact graph's inclusion needs a correction: it
does not depend on the Historical Dataset.** Re-reading its own design note precisely (line ~1512
above): Historical Dataset is named there only to explain why *extending* `KnowledgeGraphService`
was **rejected** as change-impact's architecture — the verdict was a new sibling service reading
Runtime Truth directly, built and shipped with **zero** Historical Dataset dependency. The real,
current convergence is two threads, not three: **#3a (completeness) and the Knowledge Graph's own
live synthetic-data problem.** Traceability/change-impact are relevant here only as the *precedent*
for how a Layer 2+ capability avoids needing the Historical Dataset at all — not as a third blocked
thread.

**What ADR-0021 §Stage 6 specifies.** Read in full this session (not re-derived): the Historical
Dataset is "the canonical owner of historical executions" — it owns ordering, lineage, retention,
indexing, search, and organization of a corpus Stage 5 requires to be append-only and permanent.
Stage 7 is the load-bearing rule for sizing: **"Historical datasets are constructed exclusively from
runtime contracts... Never from reports, Markdown, manifests, logs, or execution artifacts
generally."** Stage 7 names the source contracts explicitly: `EngineeringContext`, `AnalysisResult`,
`RequirementEnhancementResult`, `GroundingResult`, `ValidationResult`, `CP1Result`,
`QualityGovernanceResult`, `RecommendationResult`. Consumers, per Stage 10/11: "Continuous Learning
consumes Historical Datasets" (owns learning), and every later stage (Feature Engineering,
Prediction, ...) consumes Continuous Learning's output, never the Dataset directly — Stage 6's own
text forbids anything "reaching past the Historical Dataset to read `manifest.json` or a
`*_report.md` file directly." In today's actual codebase the two live consumers of the *reference*
(not yet a real dataset) are Continuous Improvement and Knowledge Graph, both minting/consuming it
directly rather than through a "Continuous Learning" intermediary — a naming/placement gap already
flagged, unchanged by this note (`[[cap-mentor-item3-graphs-design]]`'s own open-placement finding).

**Governance state — no new ADR is strictly required to start, but the platform's own practice
argues for one anyway.** ADR-0021's header now reads "Status: Accepted (ratified by ADR-0049)," but
its own closing "Governance" line (§ bottom) and Stage 15 point 10 still read "Proposed... becomes
Accepted as CAP-083A" — the same stale-inconsistent-status-line shape the #3a note already found
elsewhere in this ADR, not a new discovery, re-confirmed by direct reading. Substantively: ADR-0049
§D2 ratifies ADR-0021's **constitutional content** (Truth Hierarchy, Stage 6 ownership, the
Stage-7/10/11 rules) but explicitly does **not** ratify "runtime contracts" — there are none, because
nothing implementing Stage 6 has ever been built. **Net: ADR-0021 already constitutionally
authorizes building the Historical Dataset service — no freeze-lift, no ADR-0032 conflict (checked:
the frozen range is `CAP-001…073` + the Layer-1-sub-capability range `CAP-081…086`; a new Historical
Dataset capability would take the next id in the separate, open-ended `CAP-060…` block
`docs/governance/platform-capability-matrix.md` §3.1 already uses for CAP-088/089/090 — confirmed
directly, next unused id is CAP-091, no freeze territory).** What the ADR-0021 text does not supply
is an implementation-level capability ADR of its own (schema, storage mechanism, provider contract)
— every prior Layer 2 peer (Continuous Improvement/ADR-0022, Knowledge Graph/ADR-0023) got one
before or alongside its build; the traceability graph (ADR-0048) proved a "scores-first, ADR-after"
sequence is also an accepted pattern in this repo. Either order is available; not a blocker either
way.

**What the synthetic stand-in does today, read directly (a second time, now for its consumers and
contract, not just its mechanism).** `DeterministicHistoricalDatasetProvider.resolve` (both copies —
`knowledge_graph/engine/historical_dataset.py`, `continuous_improvement/engine.py`, byte-identical
pattern) is a pure function of `HistoricalDatasetReference`'s own provenance fields
(`dataset_id`, ordinal) via SHA-256 digest — it never reads a file, a database, or any prior
execution's real output. **Its contract, which any real provider must satisfy (drop-in, per the
`HistoricalDatasetProvider(ABC)` boundary both engines already depend on, never the concrete
class):** `resolve(HistoricalDatasetReference) -> HistoricalDataset`, where `HistoricalDataset` is
`{dataset_id, executions: tuple[HistoricalExecutionRecord, ...]}` and each
`HistoricalExecutionRecord` is exactly 8 fields, **one scalar value each** — `execution_id`,
`ordinal`, `requirement_id`, `recommendation_id`, `finding_id`, `capability_id`, `document_id`,
`depends_on_previous`. **Live consumers, confirmed by direct grep, both wired in
`scripts/run_requirement_analysis.py` (`_historical_dataset_reference_for_execution`,
`_knowledge_graph_historical_dataset_reference_for_execution`):** every live analysis run mints and
consumes this reference for both Continuous Improvement and Knowledge Graph — **real, live call
sites, not dormant code** — but every mint today is deliberately single-execution
(`dataset_id=f"single-execution:{execution_id}"`, `execution_count=1`, `history_window=1`,
`generated_at=result.completed_at`), so the "real" consumers run every time, but only ever over one
execution's worth of synthesized, not real, data.

**A real model-shape gap, found by reading the record, not assumed.** `HistoricalExecutionRecord`
carries `requirement_id: str` — **one** requirement per execution. A real execution's
`TestableRequirementSet` carries **many** requirements (the real corpus measured earlier in this
document: 20). The current record shape was built to exercise the deterministic engine end to end
(per its own docstring — "solely so the deterministic engine can be exercised end to end"), never to
represent a real execution's actual multiplicity. **This means a real provider cannot simply swap
the synthetic function for a real lookup and be done** — either the record shape needs extending
(e.g. `requirement_ids: tuple[str, ...]`) or the projection needs to denormalize one row per
requirement per execution — a real, small design decision a full implementation must make, not
merely plumbing.

**The data question — mostly already emitted, one concrete gap, confirmed by listing a real run's
own directory, not assumed.** `output/executions/` holds **5 real prior runs** on this machine
today. Listed one in full
(`run-20260812T064317663150Z-a20b0cc2/`, the same run this document's own D5/CP4 measurements
already used): it contains real JSON for 7 of Stage 7's 8 named runtime contracts —
`analysis_result.json`, `requirement_enhancement_result.json`, `grounding_result.json`,
`validation_result.json`, `quality_governance_result.json`, `recommendation_result.json`, and
`engineering_context.json` (plus `testable_requirement_set.json`, the L1→L2 export ADR-0032's own
carve-out #1 already authorizes). **One real, specific, confirmed gap: `CP1Result` is persisted only
as `cp1_report.md`** — grepped `execution_package/*.py` directly: `execution_writer.py` writes
`cp1_report.md` from a supplied `CP1Result`, but no `cp1_result.json` is ever written anywhere. Per
Stage 7's own rule ("never from reports... execution artifacts remain projections only"), CP1Result
is **not** recoverable as Runtime Truth from today's execution package — only its Markdown
projection exists. Closing this is small and additive (persisting an already-computed, already-
governed result as JSON — the same shape every sibling contract already gets, not new judgment
logic) — real, but the *only* concrete emission gap found; **this is not "runs must start emitting
data they don't produce today"** — 7 of 8 contracts already are, in exactly the shape Stage 7
requires.

**The storage question — no technology mandated, but the existing location is disqualifying for
"permanent."** ADR-0021 deliberately reserves the storage mechanism (Stage 6: "no storage, no
schema, no query surface" — CAP-084A's own scope note says the same). Confirmed: `output/` is
listed in `.gitignore` (`output/`, line in `.gitignore`) — untracked, per-machine, no retention
guarantee. Stage 5's own permanence requirement ("once appended, an entry is never deleted,
archived-and-forgotten") is **not satisfiable by reading `output/executions/` as-is** — it could be
cleared by any `git clean`, a fresh checkout, or normal disk hygiene, none of which this repository
treats as a destructive operation against tracked state. **Two separable questions, not one:** (a)
does the *shape* of the data a Historical Dataset needs already exist? Yes, confirmed above. (b) does
it live somewhere *durable*? No — and that is a deliberate scope/ops decision (a committed/archived
directory outside `.gitignore`, or real storage infra), not something more code resolves on its own.

**Blast radius + effort, grounded in the above, not estimated abstractly.**
- **Additive, standalone, no ADR-0032 conflict** — confirmed above (open `CAP-060…` numbering,
  next id CAP-091; no Layer 1 internals touched; reads only already-emitted, already-governed L1
  JSON output, mirroring the traceability graph's own precedent).
- **Not one build, three separable pieces of real but bounded size:** (1) close the CP1Result JSON
  gap — small, additive, no design question. (2) Build a real `HistoricalDatasetProvider` — a
  file-based reader/indexer over `output/executions/` (no new infra required for the read path
  itself; the *shape* of a real, multi-execution provider is a genuinely new module, comparable in
  size to the traceability graph's own projector, not to a full new subsystem) — but must first
  resolve the record-shape mismatch above (extend `HistoricalExecutionRecord` or denormalize).
  (3) Decide durable storage location — a scope/ops decision, not sized in engineering terms, and the
  one piece this note cannot size because it isn't a code question.
- **Not large in the way the completeness capability itself is large.** The heaviest-looking risk
  named for #3a — "a genuine multi-execution Historical Dataset... a real prerequisite" — turns out,
  on direct inspection, to be mostly an aggregation/indexing layer over data the platform already
  produces, plus one small missing artifact and one deliberate storage decision — not a new
  emission-instrumentation project across every layer.

**Its own prerequisites — real, but small, not another blocked chain.** (1) CP1Result JSON — no
prerequisite, buildable immediately. (2) The record-shape decision — no prerequisite, a design call
this note surfaces but does not make. (3) Durable storage location — the one item genuinely
outside pure engineering scope; everything else is buildable standalone, now.

**THE VERDICT — buildable-slice-now, not fully blocked and not a clean single build-now either.**
Unlike #3a itself (genuinely blocked on this service), the Historical Dataset service is **not**
blocked on anything external — its two code prerequisites (CP1Result JSON, record-shape decision)
are both small and resolvable within this same effort, and its one non-code prerequisite (durable
storage location) does not need to be resolved to start: a first real provider can read
`output/executions/` exactly as it stands today, honestly named as "real data, not yet durable
storage," mirroring how the traceability graph itself shipped "scores-first" against real data
before its own wiring/durability questions were settled.

**An honest limit on what this unblocks.** A first real provider built against today's scalar
`HistoricalExecutionRecord` contract (one representative id per field per execution) would replace
Continuous Improvement's and Knowledge Graph's synthetic inputs with real ones — real value, a
direct fix to the KG's own live synthetic-data problem. **It would not, by itself, unblock #3a.**
Corpus-completeness inference needs each historical execution's **full** requirement set (to compare
against the current run's own set for gaps), not one representative requirement id per execution —
exactly the record-shape mismatch named above. Reaching #3a specifically requires the shape
extension, not merely a real (vs. synthetic) resolution of today's shape.

**Options.**
- **OPTION A — build the real service now, full scope (CP1Result JSON + shape extension + a
  file-based provider over `output/executions/`).** Directly reaches #3a's own data need. Real,
  bounded effort (three small-to-medium pieces, not a new subsystem), no external blocker. Durability
  named but not required to start.
- **OPTION B — build a narrower slice first: a real provider against TODAY's scalar contract only
  (skip the shape extension), fixing the Knowledge Graph's live synthetic-data problem immediately,
  deferring the shape work (and therefore #3a's own unblock) to a named follow-on.** Cheaper, real
  value, but explicitly does not reach #3a.
- **OPTION C — defer, durability-first.** Treat "not durable" as disqualifying before writing any
  provider, on the theory that building against `output/`'s ephemeral corpus produces a service that
  looks real but silently violates Stage 5's own permanence rule. Considered and not favored: this
  repo's own precedent (traceability graph) already shipped real-data-but-not-yet-durably-placed
  work and named the gap honestly rather than waiting on it; nothing in ADR-0021 requires durability
  to be settled before a first implementation exists to *validate* the shape against.

**Recommendation.** **Option A**, scoped exactly as sized above — this is the first real,
standalone, unblocked build in the completeness/truth-frontier arc, not another surfacing-only stop.
Order: (1) CP1Result JSON persistence (small, no design question, unblocks nothing by itself but
removes the one real emission gap while it's already been found); (2) resolve the record-shape
question (extend `HistoricalExecutionRecord` to carry the real per-execution collections its
consumers actually need, or denormalize — a real but bounded decision); (3) a file-based
`HistoricalDatasetProvider` reading `output/executions/`, behind the existing `HistoricalDatasetProvider`
ABC (drop-in for both Continuous Improvement and Knowledge Graph, no call-site change required).
Name durable storage location as an explicit, separate, later decision — not a blocker, exactly the
same "scores-first" governance debt pattern the traceability graph ADR (ADR-0048) already used and
recorded honestly rather than gated on. Once built, #3a's own corpus-completeness capability becomes
a genuinely new, arm's-length Layer 2+ consumer of this real dataset — buildable next, no longer
blocked on an unbuilt prerequisite, only on the deliberate freeze-lift question if it turns out to
need judgment *inside* Layer 1 rather than as a consumer (the #3a note's own still-open branch,
unchanged by this note).

**Nothing built by this note.** No new module, no schema, no provider implementation, no CP1Result
JSON persistence, no ADR, no register entry, no capability-matrix row. This surfaces §Stage 6's real
spec, corrects the change-impact convergence claim, and grounds the buildable-slice-vs-blocked
verdict in the real on-disk corpus and the real record contract; building any of it remains a
future, separate task.

---

**HISTORICAL DATASET ARC, PIECE 1 BUILT (2026-08-24) — CP1Result JSON emission, closing the one
emission gap the architecture surfacing found.** Real code this time, scoped exactly as sized above:
CP1Result additively serialized as `cp1_result.json`, alongside the existing `cp1_report.md`
(unchanged). Mirrors the `ValidationResult` precedent exactly (direct `model_dump(mode="json",
by_alias=True)` in `execution_writer.py`, no new serializer class — CP1 has no metrics.md sibling,
the same shape as Validation, not the 3-artifact Grounding/QualityGovernance pattern). Manifest gets
one new key, `cp1ResultArtifact` = `"cp1_result.json"`, alongside the existing `cp1Executed`/
`cp1Report`/`cp1Verdict` — package metadata only, the artifact already appears in
`generatedArtifacts` via the same checksum mechanism as every other file.

**All 8 of ADR-0021 §Stage 7's named runtime contracts are now JSON-persisted** — the piece-2
precondition this arc's own prior note named is met. Verified via the golden productization suite
(`_CP1_ARTIFACTS` extended to `{cp1_report.md, cp1_result.json}`; new `test_cp1_result_json_parseable`,
`test_cp1_result_json_matches_manifest_verdict`) and unit tests (`test_run_requirement_analysis.py`:
`test_execution_package_serializes_cp1_result_object`, `test_cp1_result_json_matches_contract`,
`test_cp1_pass_manifest_updated` extended, determinism test extended) — 6109 passed (6106 + 3 net
new), `make lint` clean, mypy unchanged at 436 (confirmed against a `git stash`-isolated pre-edit
baseline — the 436 is the real current whole-repo count, not the "432" an earlier session's note
cited; this build added zero new mypy errors either way).

**Two pre-existing regression tests had to change, honestly, not just newly-written ones.**
`test_run_requirement_analysis.py` carried a test explicitly named
`test_execution_package_transports_cp1_result_object` asserting `not (tmp_path /
"cp1_result.json").exists()` — a deliberate CAP-067B-era lock-in of the OLD "transported, never
serialised" behavior. Renamed to `test_execution_package_serializes_cp1_result_object` and inverted,
with the old intent recorded in the docstring rather than silently deleted. A second test,
`test_existing_artifacts_unchanged_when_cp1_present`, asserted the exhaustive set of new files was
exactly `{cp1_report.md}`; extended to `{cp1_report.md, cp1_result.json}`. Both are expected,
intentional consequences of this piece's own purpose — not collateral damage.

**A real finding, surfaced not forced (per this task's own instruction).** `CP1Result` nests
`CP1Input` → `ValidationResult`/`NormalizationResult` → `AnalysisResult`/`ParsedResponse`, and some
of those already-shipped nested fields (`LLMResponse.execution_status`, the normalization
`parsed_response` shape) are loosely typed enough that `CP1Result.model_validate(json_dump)` does
**not** reconstruct to full Python-object equality with the original in-memory result (an enum stays
a string, a typed sub-model stays a plain dict) — confirmed by writing and then relaxing the
round-trip assertion in `test_cp1_result_json_matches_contract`. **This is not a CP1Result
serialization defect** — the JSON emission itself is exact (`data ==
cp1_result.model_dump(mode="json", by_alias=True)` holds, and the JSON-level round-trip,
`model_validate(data).model_dump(...) == data`, also holds) — it is a pre-existing looseness in
nested contracts CP1Result was always going to inherit the moment any of them got serialized
together, not something introduced by or blocking this piece. Named for whoever builds piece 2: the
provider reading this JSON back should compare at the JSON/dict level (as this task's own tests now
do), not assume full Python-object round-trip identity through `model_validate`.

**The backfill question, answered plainly: going-forward-only, not migrated.** The 5 real runs
already on disk in `output/executions/` (measured by the architecture-surfacing note above) do
**not** get a `cp1_result.json` retroactively — no migration script was written, deliberately out of
this piece's own scope (`cp1_report.md`-to-JSON backfill is new functionality, not "emit CP1Result as
JSON" for new runs). **What this means for piece 2:** a real `HistoricalDatasetProvider` built next
must tolerate execution directories with 7 of 8 contracts (the 5 existing runs) alongside newer ones
with all 8 — or those 5 runs must be re-run to backfill, which regenerates every artifact fresh
rather than patching one file in place, consistent with ADR-0021 Stage 4's own "corrections create
new executions, never edit an old one" rule. Named as piece 2's own first real input, not decided
here.

**ADR agreement check (per this task's own instruction — where this prompt and an Accepted ADR
disagree, the ADR wins).** No disagreement found: ADR-0021 §Stage 7 names `CP1Result` as one of the
eight runtime contracts a Historical Dataset must be built from, and specifies no shape or field
constraint beyond "the runtime contracts themselves... never a report" — a direct `model_dump` of the
real `CP1Result` (its existing, already-governed 1.1 shape, `cp1_result.py`) satisfies that exactly,
with no shape decision required at this piece. The prompt's own instruction to "serialize the
CP1Result CONTRACT per ADR-0021... NOT the markdown report's prose" is exactly what was built.

**Nothing beyond CP1Result JSON emission touched.** No provider, no `HistoricalDatasetProvider`
change, no `HistoricalExecutionRecord` shape extension (piece 3), no durable-storage decision. Piece
2 (a real file-based provider over `output/executions/`) and piece 3 (the record-shape extension) are
both still future, separate work.

---

**HISTORICAL DATASET ARC, PIECE 2 BUILT (2026-08-24) — `FileHistoricalDatasetProvider`, a real,
file-based `HistoricalDatasetProvider`, drop-in behind the existing ABC.** New module
`requirement_intelligence/knowledge_graph/engine/file_historical_dataset_provider.py`. Reads
`output/executions/<run>/manifest.json`, `testable_requirement_set.json`,
`recommendation_result.json`, and `cp1_result.json` (piece 1) as plain JSON — dict-level only, never
`model_validate` (carries piece 1's own finding forward: nested contracts like `CP1Result` do not
round-trip to full Python-object equality). Never fabricates: a run missing `manifest.json`, an
`executionId`, `testable_requirement_set.json`, or a non-empty `requirements` list is skipped, not
padded — proven directly against dry-run and interrupted-run shapes actually present in the real
corpus, not just the anticipated missing-CP1-JSON case. Keeps `HistoricalExecutionRecord`'s existing
scalar shape unchanged: one record per qualifying execution, `requirement_id` = the first requirement
in that execution's own set (a deterministic representative, execution-granularity not
requirement-granularity — piece 3's own future work); `capability_id`/`document_id` always `None`,
documented as a genuine absence in today's Layer 1 data model, not an oversight.

**20 new unit tests** (`tests/unit/test_file_historical_dataset_provider.py`), all against tiny,
self-built `tmp_path` corpora (never the real, gitignored `output/executions/` directory, matching
how every other test in this suite avoids depending on real local run output) — contract/ABC checks,
single- and multi-execution window resolution, reversed/capped windows, six tolerance cases (missing
manifest, missing/empty `testable_requirement_set.json`, malformed JSON, missing `cp1_result.json`,
mixed 7-of-8/8-of-8 runs in one window), two dict-level nested-contract reads, two scalar-shape-honesty
checks, one determinism check. **6129 passed** (6109 + 20), `make lint` clean, mypy unchanged at 436
(re-verified via `git stash -u`-isolated baseline).

**A one-off verification, not a committed test, proved two things beyond the unit suite:**
(1) A **genuine, machine-generated** `cp1_result.json` — a real `CP1Result` object (reusing piece 1's
own test helper, `_cp1_result`) through the real `ExecutionWriter`, not a hand-shaped stand-in —
is read correctly at the dict level: the provider's resolved `finding_id` matched the real object's
`findings[0].finding_id` exactly. (2) Run against the **actual real corpus** on this machine
(`output/executions/`): **22 of 26 directories index cleanly** (not "5" — the #3a/architecture
surfacing sessions' own `ls | tail -5` undercounted the real corpus; corrected here). The 4 excluded
are honestly, gracefully skipped, not crashed on: 3 dry runs (`executionId: null`) and 1 run with no
`manifest.json` at all (an interrupted run) — real, messy, previously-unseen shapes the tolerance
logic handled correctly without being specifically written for them. The most recent real execution
resolved to a real record (`execution_id=2ca6862f-...`, `requirement_id=REQ-f90f23fa`,
`recommendation_id=rc-ad5d22c0641f`, `finding_id=None` — no `cp1_result.json` exists for any
pre-piece-1 run, exactly as documented). A full-corpus window resolved 13 of the 22 indexed
executions as qualifying (the other 9 lack `testable_requirement_set.json` — genuinely older/
rehearsal runs that predate ADR-0032's carve-out).

**The consumer, confirmed.** `DeterministicKnowledgeGraphService.__init__(*, policy, rule_catalog,
provider=None)` → `DeterministicKnowledgeGraphEngine.__init__` defaults `provider` to
`DeterministicHistoricalDatasetProvider()` when `None`. `PlatformContext.create_knowledge_graph_service`
is the composition root and today passes no `provider=` at all — the synthetic default flows through
untouched. `FileHistoricalDatasetProvider` satisfies the identical `HistoricalDatasetProvider` ABC, so
swapping it in is a one-line constructor-injection change at that single composition-root call site —
mirroring exactly how this platform's other live/stub swaps work — **not yet made** (see the finding
below for why).

**THE LOAD-BEARING FINDING — the "consumer win" this task promised is not yet reachable through the
LIVE call path, for a reason outside piece 2's own scope, confirmed by reading the CLI's real
ordering, not assumed.** `scripts/run_requirement_analysis.py`: `run_knowledge_graph_phase` (and
`run_continuous_improvement_phase`) execute at lines ~1499–1532, strictly **before**
`ExecutionWriter().write(...)` at line 1632. Both phases' own reference-minting helpers
(`_historical_dataset_reference_for_execution`, `_knowledge_graph_historical_dataset_reference_for_
execution`) mint a **self-referential, single-execution** reference — `first_execution_id ==
last_execution_id == this run's own execution_id`, `execution_count == 1` — always, today, with no
other minting path. **The consequence: at the moment the live Knowledge Graph phase calls `build`,
the current run's own `output/executions/<dir>/` does not exist on disk yet** — the Execution Package
that would create it hasn't run. A real, file-based provider asked to resolve THAT specific live
reference will therefore correctly, honestly resolve to **zero records**, every single time, for
every live run — not because the provider is wrong (`test_unfound_execution_resolves_to_empty_not_
fabricated` proves this is exactly the intended, honest behavior for an execution not found on disk),
but because the live reference, as currently minted, can never name an execution the provider can
find. **This is not a piece 2 defect and not fixable within piece 2's own scope** (build the reader,
not change minting or phase ordering) — it is a real, pre-existing architectural fact this task's own
framing ("the KG starts running on real historical data... fixing the KG's synthetic-data problem")
did not anticipate.

**What this means concretely, stated plainly.** If `PlatformContext.create_knowledge_graph_service`
were changed today to inject `FileHistoricalDatasetProvider` by default, every live run's Knowledge
Graph phase would go from building a small, **fake-but-populated** graph (today's synthetic SHA-256
data) to building a **real-but-empty** one (zero nodes, zero edges, since the live reference resolves
to no records) — an honest result, arguably more correct in spirit (never fabricate), but a visible
behavior change this task's own "first consumer win" framing did not anticipate and this note will
not make unilaterally.

**What the provider DOES deliver, real and proven, right now:** correct resolution against any
reference naming an execution that already exists on disk — which is exactly what an OFFLINE/
out-of-band Knowledge Graph build (or, eventually, piece 3's completeness work) would use; not the
in-flight live CLI call as currently wired. The 22-of-26-real-executions verification above is genuine
evidence this works, just not yet reachable through `scripts/run_requirement_analysis.py`'s live path
without also changing minting or phase order — both explicitly out of piece 2's scope.

**Two real prerequisites for the LIVE consumer win specifically (not piece 2's own build), named, not
built:** (a) minting logic that references a **prior**, already-completed execution instead of the
current in-flight one (a real design question: which prior execution — the immediately preceding run,
a fixed window? — not answered here); or (b) reordering the Knowledge Graph phase to run **after**
`ExecutionWriter().write(...)`, so the current run's own directory exists by the time `build` is
called (own consequence: KG could no longer contribute anything for the Execution Package to persist
about the current run, since it would run after the package is already written — a real trade-off,
not free). Neither is small, both are genuine follow-on design questions, and neither was in scope
here.

**Options, and the call this note does NOT make unilaterally.**
- **Wire it live now, accept real-but-empty.** Honest, matches this platform's own
  never-fabricate discipline, and removes the SHA-256 stand-in from the live path entirely — but
  every live KG run produces an empty graph until (a) or (b) above is separately built, a visible
  regression in apparent (if not honest) behavior from today's fake-but-populated graph.
- **Hold the live wiring; build+prove only.** Matches this whole arc's own repeated pattern
  (traceability graph, change-impact graph, page-object/utility generation — built and tested, wiring
  left a deliberate, separate decision). The provider is available (`FileHistoricalDatasetProvider`,
  exported from `knowledge_graph`/`knowledge_graph.engine`), fully correct, fully tested against both
  synthetic fixtures and the real corpus — just not the live default yet.
- **Build prerequisite (a) or (b) first, then wire.** The actual path to the promised live consumer
  win — but a separate, real, unscoped design task either way.

**Recommendation.** Hold the live wiring (Option 2) — this mirrors the codebase's own established,
repeatedly-successful pattern for exactly this shape of situation, and flipping the default today
would trade one honest-but-limited state (synthetic-fake) for another (real-but-empty) without
actually reaching the win this task promised. Piece 3 (`HistoricalExecutionRecord`'s shape extension,
for #3a's requirement-granularity need) does not depend on this wiring decision either way and can
proceed once the user calls it.

**Nothing else changed.** No `PlatformContext` change, no live wiring flip, no ADR, no register entry,
no capability-matrix row, no touch to `HistoricalExecutionRecord`'s shape (piece 3) or #3a itself.

---

**HISTORICAL DATASET ARC, KG-LIVE-WIN PREREQUISITE SURFACED (2026-08-24) — decision-support only,
resolving piece 2's own two named candidate fixes.** Piece 2 found that wiring
`FileHistoricalDatasetProvider` live today would trade fake-but-populated for real-but-empty and
named two unbuilt candidate fixes without comparing them. This surfacing reads the real code and the
governing ADRs to compare them; it builds, reorders, and wires nothing.

**The ordering, re-confirmed verbatim against the current code (`scripts/run_requirement_analysis.py`)
— piece 2's claim holds exactly.** The live phase sequence is: Recommendation → Continuous Improvement
(lines 1492–1509) → Knowledge Graph (lines 1523–1541) → Organizational Memory → Learning →
`ExecutionWriter().write(target_dir, data)` (line 1632). All four Layer 2 phases run and complete
**before** the current run's own `output/executions/<dir>/` is ever written to disk.

**The minting, re-confirmed against the real code.**
`_knowledge_graph_historical_dataset_reference_for_execution` (lines 808–831) builds a
`HistoricalDatasetReference` with `first_execution_id=result.execution_id` and
`last_execution_id=result.execution_id` — both name the run **currently in flight**, the same run
whose directory does not exist yet. Confirmed self-referential, not merely asserted.

**The consequence, re-confirmed by reading `FileHistoricalDatasetProvider._select_window`
directly, not assumed.** When `first_execution_id == last_execution_id`, the provider looks up that
one id in its chronological index of `output/executions/`; the current run's id is never in that
index yet (its directory doesn't exist), so the window resolves to `[]` and `resolve()` returns zero
records. This is the provider's real, tested, honest behavior (`test_unfound_execution_resolves_to_
empty_not_fabricated`) — not a bug in piece 2, a structural consequence of what the CLI hands it.

**What the Knowledge Graph semantically needs — grounded in ADR-0021/0022/0023, not inferred.**
ADR-0021 §Stage 6 defines the Historical Dataset as "the canonical owner of historical
**executions**" — an indexed, multi-execution corpus a learning capability reads from, explicitly
never scoped to one execution (Layer 1 contracts are "scoped to exactly one execution"; the
Historical Dataset is the thing that spans many). More directly: ADR-0023 §D12, Recommendation 20
(frozen permanently) already anticipates and licenses this exact swap: *"A future Historical Dataset
implementation — and a future `HistoricalDatasetProvider` backed by it — may replace the
single-execution reference this milestone reuses without requiring any change to the CLI, the
serializer, the Execution Package, or `KnowledgeGraphResult`."* The self-reference was always
understood as a temporary placeholder for "no real Historical Dataset exists yet" — never the
intended long-run shape. This settles the semantic question before comparing implementations: the KG
is a cross-run, historical-truth consumer by design; referencing prior executions is not a
workaround, it is what the architecture already says the reference should eventually name.

**CANDIDATE A — prior-execution minting.**
- *What it touches:* only `_knowledge_graph_historical_dataset_reference_for_execution` (and its
  Continuous Improvement twin, same shape, out of this task's scope but noted for completeness). It
  would need to enumerate prior, already-qualifying execution ids from `output/executions/` — the
  same root `FileHistoricalDatasetProvider._index_chronologically` already reads — and set
  `first_execution_id`/`last_execution_id` to a chronological window ending at the most recent prior
  run (never the current one). **No provider change is needed**: `_select_window` already handles a
  `first != last` chronological range; this is unexercised-but-existing code, not new surface.
- *Blast radius:* contained to the minting helper. No change to the CLI's phase order, the
  `KnowledgeGraphService`/`DeterministicKnowledgeGraphEngine` call shape, the serializer, the
  Execution Package, or `KnowledgeGraphResult` — exactly the boundary ADR-0023 Recommendation 20
  already promises stays untouched.
- *Correct-by-design, not a workaround:* confirmed above against ADR-0021 §Stage 6 and ADR-0023
  Recommendation 20. Self-reference never had real data even in principle (the synthetic provider's
  populated look was always fabricated); prior-reference is what "historical" was always defined to
  mean.
- *Cold start:* `HistoricalDatasetReference` requires `first_execution_id`/`last_execution_id`
  (`min_length=1`) and `execution_count` (`ge=1`) — the type cannot represent "zero prior
  executions," so a corpus with no qualifying prior runs (the very first live run, or any run
  before one qualifying prior exists) needs an explicit fallback. The honest fallback is today's
  existing self-referential mint, which — proven above — already resolves to zero records through
  the real provider. That is not a new failure mode; it is today's live behavior, narrowed from
  "every run" to "only the cold-start case."

**CANDIDATE B — phase reordering.**
- *What it would take:* move `ExecutionWriter().write(...)` (or at least the current run's directory
  persistence) to before the Continuous Improvement/Knowledge Graph phases.
- *What it touches — the real structural problem, not just risk-in-the-abstract:* `ExecutionData`
  (lines 1599–1625) bundles `continuous_improvement_result`, `knowledge_graph_result`,
  `organizational_memory_result`, and `learning_result` into the **same** `ExecutionWriter().write()`
  call that would need to move earlier. Moving the write before KG runs means the write can no longer
  include this run's own CI/KG/OM/Learning results — the exact thing the current, frozen ordering
  guarantees gets persisted into this run's own Execution Package. A partial-then-final write would
  mean splitting `ExecutionWriter` into two passes, real restructuring of a currently single,
  self-contained write call, not a reorder of two lines.
- *ADR conflict:* both ADR-0022 §D11 and ADR-0023 §D12 state, verbatim, "**Activation and execution
  order (frozen)**" for exactly this sequence (`... → Continuous Improvement → Knowledge Graph → ...
  → Execution Package`). Reordering would contradict two ADRs' explicitly frozen recommendations,
  requiring a governance amendment before any code change — not a mechanical move.
- *Semantic question:* even if built, B only makes the **current** run's own data readable to KG.
  Per the grounding above, the KG's own architecture wants historical (prior-run) truth, not
  necessarily this run's own truth about itself — so B, even fully built, doesn't obviously answer
  the question A already answers correctly.

**Comparison and recommendation.** A is contained (one helper, zero change to the
CLI/serializer/Execution Package/runtime-contract boundary, explicitly pre-licensed by ADR-0023
Recommendation 20) and correct-by-design (ADR-0021 §Stage 6's own definition of what "historical"
means). B is structurally invasive (splits an atomic write call), conflicts with two ADRs' frozen
ordering decisions, and — even if built — doesn't clearly deliver a more-correct KG than A already
would. **Recommend A** — prior-execution minting — as the fix that actually delivers the live
"Knowledge Graph on real, populated data" win with the least risk and the most architectural
justification. Cold-start caveat carries forward unchanged: the first qualifying live run (or any run
before a prior one qualifies) legitimately falls back to today's self-referential, zero-record mint —
an honest empty result for a genuinely history-less run, not a defect.

**Nothing built, reordered, or wired by this surfacing.** No `PlatformContext` change, no minting
code change, no phase-order change, no ADR amendment, no register entry, no capability-matrix row.
The decision to build Candidate A (and then, separately, whether to wire the live provider) remains
the user's to make.

---

**HISTORICAL DATASET ARC, KG-LIVE-WIN BUILT (2026-08-24) — Candidate A + live provider wiring, both
executed.** The user decided: build the recommended fix and wire the real provider live. Two-part
change, exactly as scoped above.

**Part 1 — prior-execution minting.** `_knowledge_graph_historical_dataset_reference_for_execution`
(`scripts/run_requirement_analysis.py`) now takes an `executions_root: Path` parameter and mints a
reference naming the most recent PRIOR execution already on disk — found by a new, contained sibling
helper, `_most_recent_prior_execution_id`, which reads only `manifest.json`'s `executionId`/
`executionCompletedTimestamp` (the same two fields real historical-dataset resolution already indexes
by), never a fuller reconstruction. Falls back to today's original self-referential mint only when no
prior execution qualifies (cold start). The call site passes `output_base` — the same base directory
the current run itself is being saved under (respects `--output-dir`), already in scope at the call
site. No provider change was needed: `FileHistoricalDatasetProvider._select_window` already resolved
a `first != last` range; this mint keeps `execution_count=1`/`history_window=1` (still exactly
CAP-083C's single-execution shape) and only changes *which* execution the one slot names. Confirmed
live and real: the current, in-flight run's own directory has no `manifest.json` yet at KG-phase time
(it's a `write()`-generated artifact, appended to `output_paths` only after `write_result` returns),
so no explicit "exclude the current run" logic was needed — the manifest-presence check alone excludes
it, for the same reason piece 2's provider does.

**Part 2 — live provider wiring.** `PlatformContext.create_knowledge_graph_service` gained an optional
`provider: HistoricalDatasetProvider | None = None` parameter, defaulting to
`FileHistoricalDatasetProvider()` when omitted — the live default flip. The bare CLI call site
(`context.create_knowledge_graph_service()`, unchanged) now gets the real provider automatically.

**A real ripple the pre-licensing didn't cover, found and resolved — reported, not silently
absorbed.** ADR-0023 §D12 Recommendation 20 licenses this swap "without any change to the CLI, the
serializer, the Execution Package, or `KnowledgeGraphResult`" — honored; none of those four changed.
But two *other* real consequences surfaced during the build, outside that named list:
1. **Golden/productization hermeticity.** `tests/productization/conftest.py`'s golden pipeline fixture
   also calls `context.create_knowledge_graph_service()` bare, with its own hardcoded self-referential
   reference (never on real disk). Once the live default became the real provider, this fixture would
   resolve to the real, ambient `output/executions/` corpus — non-deterministic across machines (and
   empty on a fresh CI clone, where that gitignored directory doesn't exist at all) — breaking the
   golden dataset's structurally-bounded node/edge-count assertions
   (`3 <= len(nodes) <= 7`, etc., pinned to the synthetic SHA-256 provider's specific behavior).
   **Fixed:** the golden fixture, and the two determinism tests that independently rebuild a second
   `KnowledgeGraphResult` from the same reference (`test_knowledge_graph_execution_integration.py`,
   `test_golden_baseline.py::test_determinism_knowledge_graph_result_content`), now pass
   `provider=DeterministicHistoricalDatasetProvider()` explicitly — pinning the exact prior behavior,
   unchanged. This is the "explicit synthetic injection" escape hatch, applied for real.
2. **A frozen provider-containment test.** `HistoricalDatasetProvider` (KG's, and — via the identical
   generic name — Continuous Improvement's own copy) was frozen private to its own package:
   `test_knowledge_graph_result_freeze.py` / `test_continuous_improvement_result_freeze.py` each assert
   *zero* other modules anywhere in `requirement_intelligence/` may even name the string
   `"HistoricalDatasetProvider"`. `PlatformContext` naming it (to accept the override and construct the
   real default) trips both. **Resolved, not bypassed:** both tests' `permitted` allowlist now includes
   `platform/platform_context.py` explicitly, with a docstring explaining why — the composition root is
   the one place in the platform whose entire purpose is making exactly this kind of concrete wiring
   decision (its own module docstring: "keeps wiring in one place"). This is a deliberate, narrow,
   documented exception, not a weakened guard: it still catches any *other* accidental leak.

**Also updated, coherently, not silently:** `test_cli_reuses_the_cap_083c_minting_strategy_not_a_second_one`
previously asserted byte-identical minting text between the CI and KG helpers — necessarily false now
that they name different executions by design. Rewritten to assert the invariant that actually still
holds (the shared single-execution *shape*, `execution_count=1`/`history_window=1` in each helper)
instead of literal self-reference text. The old single minting-helper unit test
(`test_minting_helper_produces_a_valid_single_execution_reference`) is replaced by three: cold-start
fallback, prior-execution reference, and malformed/incomplete-manifest skip — direct coverage of the
new behavior, not just text-scanning.

**Verified live, against the real, unmodified `output/executions/` corpus (read-only,
never written to):**
- **Minting is real:** the helper, called with the real executions root, minted
  `first_execution_id == last_execution_id == "2ca6862f-cc6b-483d-935d-d29e689a2522"` — the real,
  most-recently-completed qualifying execution on disk (`run-20260812T064317663150Z-a20b0cc2`) — never
  the simulated current run's own id.
- **The win, precisely measured:** building the KG through the now-default real provider on that
  minted reference produced **4 nodes** (`dataset`, `execution`, `requirement`, `recommendation`),
  **3 edges**, **1 subgraph**, **0 findings** — real content, traced to that run's own
  `manifest.json`/`testable_requirement_set.json`/`recommendation_result.json`.
- **The exact pre-fix shape, reproduced and precisely characterized (not just asserted):** resolving a
  self-referential reference (today's old shape) through the same real provider yields exactly
  **1 node**, and only of type `dataset` — the engine's own `NodeProjector` unconditionally projects a
  `dataset` identity node from the reference itself regardless of whether any execution backs it (real
  code, `node_projector.py`), so "real-but-empty" precisely means "the dataset identity node alone,
  zero execution-derived nodes" — a sharper, code-grounded correction of the surfacing's own looser
  "zero records" framing.
- **Synthetic provider unaffected:** the same self-referential reference through an explicitly-pinned
  `DeterministicHistoricalDatasetProvider()` still yields its own fake-but-populated shape, unchanged.
- **Cold start, live-checked:** an empty executions root yields the self-referential fallback mint, and
  resolving it returns zero `HistoricalExecutionRecord`s — no crash, an honest empty history.
- **Piece 2's findings hold live:** of 22 really-indexed executions, 13 genuinely qualify (have a
  non-empty `testable_requirement_set.json`) — new, more precise data than piece 2's own memory
  recorded. Resolving the oldest qualifying (pre-piece-1) run succeeded without crashing, with
  `finding_id = None` — an honest reflection of a run that predates `cp1_result.json` emission, not an
  error.

**Gate.** `make lint`: clean. `make test`: **6131 passed** (6129 baseline + 2 net new, from replacing
one minting test with three). mypy: **436**, unchanged from baseline — the only mypy delta introduced
during the build (a `ModuleType`-vs-inferred-`object` annotation on a new test helper) was caught and
fixed before landing. Tree left with exactly this arc's 8 changed files; nothing else touched.

**Piece 3 (record-shape extension for #3a's requirement-granularity need) remains unbuilt and out of
this task's scope**, unaffected by this wiring — see [[cap-real-completeness-measured]] and
[[cap-mentor-item3a-completeness-surfaced]].

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

**SPEC-SLICE VALUE ASSESSED (2026-08-20) — the "surface-as-own-design-task" note above, resolved
into a verdict. Largely already delivered; the genuine residual is workflow, not generation
architecture. Nothing built.** One mentor throughout (Nitin).

**Pre-flight.** Clean tree, `main`, tip `7c84096` (the judge-layer surfacing). `make lint`/`make
test` clean, 5982 unchanged.

**What the pipeline already does, checked directly, not assumed.** Generation is already
slice-scoped, at a finer grain than Nitin's own example: `run_feature_engineering_stage` iterates
`for requirement in requirement_set.requirements`, and `build_feature_content_payload` serializes
only that ONE requirement's own `title`/`narrative`/`component`/`acceptance_criteria` — no
cross-requirement data ever enters the call. Layer 3 generation is finer still — per Gherkin STEP
NEED (`for need in unique_needs`, `automation_engineering/stage/runner.py`), each generator call
scoped to one need's own text and interface. Nothing in this pipeline's own generation code can see
or touch another requirement's data — not because it is forbidden, but because the payload never
carries it. **The canonical model ("the map") exists, exactly as Nitin describes it, but is 0%
implemented:** ADR-0030/CAP-087A froze a real canonical domain model (`SpecificationPlan`/
`BusinessFeature`/`BusinessScenario`/etc., Gherkin as one Renderer among several) as pure
architecture — "No code is written... nothing is wired into a pipeline" (ADR-0030's own Runtime
status). It is not used as per-run context today because it does not run at all yet — consistent
with, not contradicting, Nitin's own "map, not context" framing.

**The decisive finding: Nitin's own STATED rationale (cheaper, reviewable, contained blast radius)
splits into two independent values, and one of them is already fully delivered.**
`[[cap-delta-regen-crux-surfaced]]` (this arc's own prior design-surfacing task) already answered
the efficiency half directly: "the cache already delivers correct per-artifact delta-regen for all
three wrapped generators' DIRECT inputs, proven by 3 real measured runs" — feature-content and
test-data have ZERO transitive gap; step-def has exactly one small, dormant, non-urgent gap (a
bare-class-name cache-key hint), already recommended-fixed by widening the payload, not by a
branch/change-impact mechanism. **This is Nitin's own rationale, delivered — a re-run today
already only regenerates what changed, corpus-wide, without any branch structure at all.** The
change-impact graph (`[[cap-change-impact-graph-built]]`) was explicitly found NOT to be a regen
driver — "report-only... a human-facing reporting/impact-analysis tool," confirming the blast-
radius VALUE comes from the cache's content-addressed key, not from a graph or a declared spec
boundary.

**Each part of #4, mapped:**

| Part of #4 | Status |
| --- | --- |
| Per-requirement/slice generation scope | **Already exists** — confirmed above, finer-grained than his own example (per-need, not just per-requirement). |
| Blast-radius containment (regenerate only what the feature touches) | **Already delivered by the cache** (`[[cap-delta-regen-crux-surfaced]]`) — Nitin's own stated rationale, achieved by a different mechanism (content-addressed payload hashing) than the one he proposed (a declared branch-spec boundary), same result. |
| DoD-in-branch (tests built with the feature) | **Already the shape, minus the branch container** — a requirement's `.feature` scenarios and its step-defs/page-objects/test-data are generated together, in the same run, from the same `TestableRequirement`, traceable end-to-end via the `@REQ-*`/`@AC-*`/`@SCN-*` tag chain CAP-088's own traceability graph already verifies. |
| Page-object changes limited to the feature | **Partially blocked, but not by #4** — page-object/utility generation is not yet cache-wrapped at all (CAP-089's own 3-of-5 scope); once it is, `[[cap-delta-regen-crux-surfaced]]` already names the exact fix (payload widening), not a branch structure. |
| Branch-as-unit + branch-spec-as-CONTRACT (an explicit, enforced boundary on what a run may touch) | **Genuinely new — and moot as an enforcement mechanism.** No git-branch concept exists anywhere in this pipeline's production code (grepped, zero hits) — promotion (`automation_engineering/promotion/mechanism.py`) `git add`s every promoted asset into ONE shared tracked-baseline working tree per run, not a per-feature branch. But "enforcement" has nothing real to prevent: the generation payloads already cannot leak across requirements BY CONSTRUCTION (above) — there is no cross-slice violation this platform's own code could commit for a spec-as-contract to guard against. |
| Reviewability (a human reviewing one feature's own diff, not the whole run's) | **The one genuine, undelivered value** — today a promotion stages every changed asset from the whole run together; there is no mechanism to scope a review action to one requirement/feature's own changes. This is the part of #4 the cache does NOT deliver. |

**The crux, answered directly.** Is this a generation-architecture change, or a workflow/CI
practice layered on what already exists? **Workflow, not architecture — decisively.** The
generation code is already per-slice; the cache already contains blast radius; nothing about
"branches" requires the generator classes, the payload contracts, or the orchestration to change
at all. A branch-per-requirement git practice (checkout a branch named after the requirement,
run the pipeline, review that branch's own diff, merge) is fully expressible TODAY, on top of the
existing pipeline, with zero code changes — the only genuinely missing piece is a thin
promotion/review-tooling enhancement (e.g., partition the `git add` staging or the promotion
report by requirement/feature so a reviewer sees one feature's own diff, not the whole run's).
That is a small, real, additive tooling item — not a re-architecture of generation.

**VERDICT: (b) largely-already-delivered.** Nitin's own stated rationale (cheaper, reviewable,
contained blast radius) is already achieved for the efficiency half by the cache
(`[[cap-delta-regen-crux-surfaced]]`), and the generation architecture is already slice-scoped,
finer-grained than his own example. The one genuine residual — reviewability, a diff scoped to one
feature at a time — is a promotion/review-tooling addition, small and workflow-shaped, not the
branch-scoped generation re-architecture the original ask described. **Restructuring generation
into branch-bounded units to chase a blast-radius value the cache already delivers would be
questionable restructuring — the same shape this arc already declined once for the deterministic
split.** Recommended, if ever prioritized: the small reviewability tooling addition, not a
generation re-architecture. Not designed here.

**Connections and Nitin's own intent.** Connects directly to the cache (ADR-0050, delivers the
efficiency half) and to CAP-087 (the "map," frozen architecture, 0% implemented, consistent with
his own "not per-run context" framing). Page-object live-wiring blocks one small part (already
named, already has its own fix recommended, unrelated to branches). **Nitin's own words** name the
outcome he wants ("cheaper, reviewable, a contained blast radius") — re-reading his rationale
against what this platform actually measured, the efficiency outcome is already real, proven by
three live-measured cache runs; only the reviewability outcome remains open, and it does not
require the branch-scoped generation architecture he described to get it.

**PAGE-OBJECT PRODUCTION-ACTIVATION DECISION SURFACED (2026-08-21) — the "page-object live-wiring
blocks one small part" note above is now stale; that blocker closed same-day
([[cap-page-object-live-wiring-decision]]), and cache + eval were extended to the page-object
generator the same day this note was written (`20c7a8b`, `11d916e`).** Activation at the
`scripts/run_requirement_analysis.py` stage-15 call site is now purely a two-parameter flip
(`LivePageObjectSemanticMatcher(GeminiEmbeddingProvider())` + a page-object generator) — nothing
else is missing: wiring, matcher, generator, `GenerationIdentity`, cache, and eval Layer 1 are all
built and tested. Real per-run cost if flipped: live LLM generation calls (Gemini, 12/min pacing)
plus live embedding calls (90/min pacing) on every `--with-automation-engineering` run — the one
real prior full-corpus measurement was 32 page objects generated in 145.8s with zero throttling
([[cap-page-object-live-regen-findings]]). The historical pattern held here too: that same live run
surfaced 3 real defects only live generation exposed (method-name conveyance, DI constructor
mismatch, fictional `BasePage` helpers) — all 3 are now fixed and the tracked baseline compiles
clean (`mvn clean test-compile` exit 0, committed `4db1ea2`,
[[cap-compile-gap-closed]]); the new page-object eval (`eval_harness/page_object_*.py`) exists
specifically to catch a regression of those 3 shapes automatically. **Decision: DEFER, not
activate-now or validate-first** — `--with-automation-engineering` is off by default and every live
page-object run to date has been a manual, investigative session (no CI wiring, no scheduled/
production runs found anywhere in this repo). Activating would add real per-run cost for a saving
and an eval that nothing currently consumes — the same "no consumer" reasoning already applied to
runtime-citation and the eval judge layer. If a concrete need appears (a new AUT, or a decision to
start measuring the cache saving live), the low-risk path is Option B (a scoped validation run
through the real call site) before flipping it on for every run, not a blind Option A. Nothing
built, changed, or activated by this note — investigation only.

**UTILITY STAGE-15 WIRING DECISION SURFACED (2026-08-22) — a sibling question to the page-object
note above, with a different answer.** `LiveUtilityGenerator` is fully built (this same week: identity
threading, `CachingUtilityGenerator`, and `eval_harness/utility_*.py`'s Layer 1 eval all landed), but
unlike page objects it is not one flip away from live — it is not even plumbed that far.

- **What utility generation is for.** A generated utility (e.g. `ConfigReader`) is a stateless helper
  a step definition's own body calls. Consumption is identical in shape to page objects: reuse-first
  (`orchestrate_utility_method`), generate on `NoMatch`. The generator and orchestrator are fully
  built and unit-tested (mirroring `page_object_orchestrator.py` deliberately, including the precise
  method-fit discharge — `utility_orchestrator.py`'s own module docstring investigates and confirms
  the risk is real, sharper even than for page objects, citing `ConfigReader`'s own `env`/`data`
  same-shape-different-meaning accessors).
- **No derivation feeds it — this is the real gap, not activation.** Page objects get their live
  requests from `page_object_reference_derivation.py`, which parses a freshly generated step-def's
  own body for field call sites. That module's own docstring states plainly: "utilities remain out
  of scope, mirroring every prior page-object-before-utilities build," and explicitly excludes
  utility-typed fields from its traversal. No equivalent `derive_utility_requests` exists anywhere.
  `UtilityBindingRequest`/`utility_request` is a real, tested, optional parameter on
  `orchestrate_step_definition` (`automation_engineering/generation/orchestrator.py`) — but nothing
  outside a unit test ever constructs one. Confirmed by reading the actual plumbing: unlike page
  objects, which at least reached `page_object_matcher`/`page_object_generator` as optional
  parameters on both `run_automation_engineering_stage` and `execute_automation_engineering_stage`
  (`automation_engineering/stage/runner.py`), **no `utility_matcher`/`utility_generator` parameter
  exists at either level.** Utility wiring is one full layer further back than page-object activation
  was — it needs the derivation module built first, not just a two-parameter flip at the CLI.
- **The real corpus generates zero utility demand.** The entire tracked baseline (33 step-def
  classes, 33 page-object classes, the real saucedemo 20-req/33-need corpus) contains exactly one
  committed utility class, `ConfigReader` — hand-authored baseline infrastructure that predates the
  `com.automation.utils` convention (it lives in `com.automation.base`, confirmed by
  `utility_orchestrator.py`'s own docstring and `eval_harness/utility_eval_set.py`'s own "hybrid
  seed" note), never something the pipeline generated. Grepped directly: zero of the 33 real,
  committed step-def classes reference `ConfigReader` or any other utility-typed field. The corpus
  that exercises this platform's own generation pipeline end-to-end has never once asked for a
  utility.
- **No CP gate depends on it.** CP4 (`automation_engineering/cp4/gate.py`) is exclusively locator
  health — four criteria, all defined over page-object field locators. A utility has no locators by
  construction (`eval_harness/utility_eval_set.py`'s own framing: "no locators, no `BasePage`").
  Wiring utility would not activate a dormant gate the way page-object activation would have for
  CP4 — there is no utility-specific gate sitting idle waiting for live utility assets. Promotion
  outcome types (`GeneratedUtility`/`BoundUtilityMethod`/`EscalatedUtilityMethodNeed`) exist and are
  wired into `automation_engineering/promotion/outcomes.py` identically to page objects, so a
  utility asset that did arrive would flow through promotion correctly — that much is real.
- **Value vs. effort.** Cost to wire: build the missing derivation (utility-typed-field call-site
  parsing, mirroring `page_object_reference_derivation.py`'s own shape but for a class kind that
  never had a derivation attempt made against it), then plumb `utility_matcher`/`utility_generator`
  through both stage-runner levels, then the CLI flip — strictly more work than page-object
  activation, which was already fully built. Payoff if built: the dormant identity/cache/eval assets
  become live-exercised — but against a corpus that has generated zero real utility need in every
  run to date, so "live-exercised" would mean exercised by a fixture, not a real demand.
- **This is the same "no consumer" pattern as page-object activation, runtime citation, the eval
  judge layer, and #8 — but one step earlier.** Those items had everything built and just needed
  activating, and were deferred for lack of a live consumer. Utility does not even have everything
  built (the derivation is missing) and *also* has no live consumer (zero real corpus demand) — a
  stronger case for deferring than any of the four prior "no consumer" items, since here there is
  additionally no proof the missing derivation would ever fire.

**Options.** (A) Wire utility into stage 15 — build the derivation, plumb both stage-runner levels,
flip the CLI: real effort (a new module, not a flag flip) for a payoff nothing in this platform's own
corpus currently demands. (B) Defer, leave wired-ready-but-dormant like page-object activation — but
utility is not actually wired-ready; deferring here means leaving a known, scoped, unbuilt gap
documented rather than an armed-and-idle capability. (C) Accept utility as a permanently
harness/standalone capability (eval + cache prove the generator seam works in isolation; the derivation
that would make it a live pipeline consumer may simply never be worth building if no AUT this platform
targets ever needs more than `ConfigReader`-shaped helpers).

**Recommendation: Option C, with Option B's language for the record.** Wiring utility now (Option A)
would be speculative engineering against zero measured demand, worse than the "no consumer" items
already deferred this session because part of the wiring (the derivation) doesn't exist yet either —
there is nothing today asking for it and no reason to believe that will change absent a new AUT with a
richer helper surface than saucedemo's. Treat utility generation as proven-standalone
(generator/orchestrator/identity/cache/eval all real and tested) but not a pipeline consumer, and
revisit only if a concrete generated step-def or page-object is observed needing a helper
`derive_page_object_requests`'s own page-object-only scope cannot supply. Nothing built, wired, or
changed by this note — investigation only. Gate: `make lint` clean; `make test` 6106 passed,
unchanged.

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

**Consensus signal: high** — Nitin raises this in both his original list and his later reply.

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

**Nitin confirmation (2026-08-20) — the clarify-with-mentor nuance above is now CONFIRMED, not
pending.** Asked directly, Nitin confirmed both halves: the citation reading is (i) doc-level
mapping, not (ii) runtime citation; the authority shape is reconcile the existing
0020/0021/0024–0026/0028/STD-000 lineage (what ADR-0049 built, Option B, ratifying rather than
orphaning it), not a clean-slate replacement. Both match what was already written to. Additive
confirmation only — the (a)/(b)/(c) analysis above is not re-opened.

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

**Consensus signal: high** — Nitin raises this consistently across his feedback.

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

**Consensus signal:** raised in Nitin's original list, not clearly repeated in his own reply points.

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

**LICENSING DECISION SURFACED (2026-08-22) — decision-support only, nothing built, configured, or
changed.** *Pre-flight.* Clean tree, `main`, tip `0b2ad3b`. `make lint` clean. `make test`: 6106
passed, unchanged. This note adds text only to this document; nothing else touched.

**What the mechanism supports today, verified against the real construction sites, not the prior
note's summary.** `scripts/run_requirement_analysis.py`'s live-wiring (`handle_analyze`) constructs
exactly **two** provider instances per run, not five: a shared `provider` (`context.create_provider
(args.provider, args.model)`, resolving `GEMINI_MODEL`/`args.model`) handed to
`LiveFeatureContentGenerator`, `LiveFeatureRemediator`, and `LiveTestDataGenerator` alike (three
generators, one model), and a second, separately-constructed `step_definition_provider`
(`_step_definition_model()`, resolving `STEP_DEF_GEMINI_MODEL`) for `LiveStepDefinitionGenerator`
alone. `LivePageObjectGenerator`/`LiveUtilityGenerator` are not constructed anywhere in this file at
all — confirmed by grep, zero matches — so they have no live model assignment today, scoped or
otherwise (the pre-existing, already-recorded `[[cap-page-object-live-wiring-decision]]` DEFER).
**The real granularity is per-carve-out, not per-stage:** the mechanism *can* scope any generator
individually (each is a constructor-injected `LLMProvider`, per `llm_factory.create_provider`'s own
"no other change required anywhere in the platform" contract for adding a provider or a caller-side
override) — but only one such override has ever been built (`STEP_DEF_GEMINI_MODEL`). Three
generators still share one undifferentiated model; two more have no live model at all. "Per-stage
model scoping exists" is accurate as a *capability*; "per-stage model assignment exists" is not yet
true as a *configuration*.

**What's configured today, read from the actual live `.env` (gitignored), not `.env.example`'s
documented default.** `GEMINI_MODEL=gemini-3.1-flash-lite` — this, not `gemini_provider.py`'s own
code-level fallback (`gemini-2.5-pro`) or `.env.example`'s committed illustration
(`gemini-2.5-pro`), is what `requirement_analysis`, `feature_content_generation`,
`feature_remediation`, and `test_data_generation` actually run on. `STEP_DEF_GEMINI_MODEL` is unset
in this `.env`, so `step_definition_generation` falls through to `_DEFAULT_STEP_DEFINITION_MODEL`,
`gemini-3.5-flash`. `page_object_generation`/`utility_generation`: not configured, because not
live-constructed. `AZURE_OPENAI_*` entries exist in `.env` but hold placeholder values
(`https://your-resource.openai.azure.com/`, `your_azure_openai_api_key_here`) — confirming the
provider is unlicensed here too, not merely unimplemented in code.

**Nitin's pinning ask: name-only, confirmed a real, already-flagged gap, not newly discovered.**
`GenerationIdentity` (`requirement_intelligence/llm/generation_identity.py`) has `model: str` and
`provider: str` fields — the hosted model's *name* (e.g. `"gemini-3.1-flash-lite"`), never a version
or content-hash of that model's own behavior. This is the identical gap ADR-0050's own design note
already named verbatim: "the env var names a hosted model, never a content hash of its own
behavior, a structural limitation caching can pin around but never fully close." By contrast,
prompt pinning is genuinely name+version+content-hash (`prompt_id`/`prompt_version`/`prompt_sha256`,
`PromptRegistry`-enforced, immutable after `seal()`). **So: model pinning is partial** — a caller
can pin *which named model* a stage uses (already true, via env var, for the one carve-out), but not
*which version of that model's behavior* a hosted provider serves under that name — a gap this
platform cannot close unilaterally (it depends on the provider publishing dated/pinned model
snapshots, which neither Gemini's `GEMINI_MODEL` env-var shape nor this platform's own
`GenerationIdentity` schema currently captures). This connects #8 directly to the artifact-cache
work's own residual risk (ADR-0050, above) rather than opening a new one.

**The real choice-space, grounded in the measured token distribution
(`[[cap-artifact-cache-first-increment-built]]`'s own 2026-08-12 run,
`run-20260812T064317663150Z-a20b0cc2`).** `feature_content_generation` (45.4%, 20 calls) and
`test_data_generation` (43.4%, 20 calls) are the two token-heavy generation stages — together ~89%
of measured spend — and both, today, already run on the cheapest configured model
(`gemini-3.1-flash-lite`, the shared default). `step_definition_generation` recorded **zero** tokens
in that run (reuse hits + pre-generation escalation absorbed all 60 needs) but is the one stage with
a **measured, real defect history** at the model-choice level (`gemini-2.5-flash`'s 76% defect rate,
corrected to `gemini-3.5-flash`) — already acted on, already the one existing carve-out. No
comparable defect measurement exists for `feature_content_generation` or `test_data_generation` on
`gemini-3.1-flash-lite`: this same live run recorded feature generation CP2-clean for all 20
requirements on the first pass, and the `gemini-model-evaluation.md` benchmark (a different,
L1-`requirement_analysis`-scoped comparison, not L2/L3, but the only controlled multi-model
Gemini-family comparison this platform has run) shows `gemini-3.1-flash-lite` matching
`gemini-2.5-flash`'s completeness and determinism at 8.4x the speed and lowest token cost —
`gemini-3-flash-preview` scored highest completeness but was non-deterministic and ~200x slower.
`page_object_generation`/`utility_generation` are absent from the token distribution entirely
(unwired, per above) — the earlier-recorded live-regen defect line
(`[[cap-page-object-live-regen-findings]]`) is a real, separate quality concern for those two
generators specifically, orthogonal to this item's licensing question and already tracked under the
page-object work, not this one.

**Complexity map, verified against real code, not assumed from the mentor's own framing.** Every
stage that calls an LLM at all is a **generation** stage — `requirement_analysis` (L1, one call),
`feature_content_generation`/`feature_remediation` (L2), `step_definition_generation`/
`page_object_generation`/`utility_generation`/`test_data_generation` (L3): six generators, one
`LLMProvider` call each, "one prompt in, one artifact out" — the exact shape the artifact-cache
design note already characterized in full. **Every governance stage checked
(`suite_quality_governance`'s CP1–CP8) is deterministic, confirmed directly, not inferred:**
`suite_quality_governance/cp5/pattern_matching.py`'s own docstring states its comparison is "never
[an] LLM-generated assessment," and CAP-080A's own frozen pipeline
(`RuleEvaluator`→`AssessmentEngine`→`DecisionEngine`→`GovernanceService`) is rule-based throughout —
no governance stage in this platform calls an LLM today. **The mentor's own three-way split
("generation" / "structural governance" / "semantic governance") therefore only has a real target
for its first leg.** "Structural governance → Haiku" and "semantic governance → OpenAI" both
presuppose an LLM-driven governance stage that does not exist yet — CP1–CP8 are already
deterministic-and-cheap (zero token cost, not merely a low-cost model), so there is nothing today
for either leg to route. The platform's one existing "semantic" LLM-adjacent use is
`GeminiEmbeddingProvider` (`automation_engineering/reuse/embeddings.py`, its own
`EMBEDDING_MODEL` env var) — catalog reuse-matching, a semantic **match**, not a governance
**gate** — a different concern from what "semantic governance" names, and already independently
model-scoped (its own env var, mirroring the same pattern).

**What the licensing decision actually requires, concretely.** Only `gemini` is a real, live
provider. `azure_openai` is a genuine `NotImplementedError` stub (every method raises), and this
environment's own `.env` confirms it is unlicensed in practice, not just unbuilt (placeholder
endpoint/key/deployment values). No Anthropic (Sonnet/Haiku) provider exists in any form — not even
a stub — `_PROVIDER_REGISTRY` (`llm_factory.py`) lists exactly `{"gemini", "azure_openai"}`. So:
**(a) if only Gemini is ever licensed,** the real choice-space is Gemini-internal
(`flash-lite`/`flash`/`flash-preview`/`pro`), and the mentor's cross-provider routing does not apply
at all. **(b) if Sonnet/Haiku/OpenAI licensing lands,** the engineering seam to add them is proven
(mirror `AzureOpenAIProvider`'s shape for a new `AnthropicProvider`, register it, then reuse
`STEP_DEF_GEMINI_MODEL`'s own env-scoped pattern per generator) — but the "structural/semantic
governance" legs of the mentor's specific routing still have no LLM-driven consumer to attach to
until/unless a governance stage becomes LLM-driven, which is a separate, unproposed design change,
not a licensing question.

**Cost/quality tradeoff, per stage, grounded in the two real measurements this platform actually
has.** For the two token-heavy stages (`feature_content_generation`, `test_data_generation`): both
already run on the cheapest available model, and no defect measurement exists to justify paying for
a stronger one — moving them to a costlier model would spend more with no measured quality
justification, the inverse of the step-def case. For `step_definition_generation`: the one stage
with a real, measured, resolved model-quality incident — already on its corrected model
(`gemini-3.5-flash`), already isolated from the shared default via the existing carve-out. There is,
today, **no second stage with a comparable measured defect signal** to justify extending the
carve-out pattern further.

**Options assessed.**
- **Option A (decide Gemini-only routing now):** buildable immediately (seam exists), but nothing in
  the measured evidence names a stage that would benefit — the two heavy stages are already on the
  cheap model with no defect signal, and the one stage with a defect signal already has its own
  carve-out. Would be a configuration change made without a measured reason.
- **Option B (defer for provider licensing):** the mentor's actual "Sonnet / Haiku / OpenAI" routing
  is blocked here regardless of Option A — no Anthropic provider exists in any form, and Azure
  OpenAI is a confirmed-unlicensed stub in this environment. This leg is a procurement decision, not
  an engineering one, exactly as the mentor's own framing already says.
- **Option C (status quo):** the current shape — one shared default plus the one measured-need
  carve-out — already matches every measured signal this platform has. The token instrumentation
  that would detect a *new* need (a defect on `gemini-3.1-flash-lite` for feature-content or
  test-data, or a cost spike worth trading for a cheaper/faster model) exists and keeps running on
  every live invocation; it has not, so far, surfaced one.

**Recommendation: Option C (status quo) now; Option A is available but not measured-justified;
Option B is blocked on procurement, not engineering.** The mentor's multi-provider vision is real and
the seam is proven, but it is gated entirely on a licensing decision this document cannot make. Within
what's actually licensed today (Gemini only), the existing shared-default-plus-one-carve-out
allocation already reflects every measured cost/quality signal on record — extending per-stage
routing further, absent a new measured defect or cost pressure, would be the premature optimization
this platform's own discipline elsewhere (`[[cap-step-def-non-lite-model-scoping]]`'s own "correct
and simple now, refine later if warranted") already argues against. If a future live run's token
scorecard or a CP2/compile-gate regression flags `feature_content_generation` or
`test_data_generation` specifically, that would be the concrete trigger to revisit Option A for that
stage — named here as the condition to watch for, not acted on.

**Nothing built, configured, or changed by this note.** No provider added, no env var set, no
generator rewired, no ADR opened. This surfaces the mechanism's real granularity (per-carve-out, not
uniformly per-stage), what's actually configured (`.env`, not the code default or `.env.example`),
the pinning gap (name-only, already flagged by ADR-0050, not new), the token-distribution-plus-
complexity grounding for the choice-space, the licensing reality (Gemini live, Azure OpenAI a
confirmed-unlicensed stub, no Anthropic provider at all), and the recommendation; adopting any option
remains a future, separate decision.

Gate: `make lint` clean; `make test` 6106 passed, unchanged. Tree modified only in this document.

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
  `TestableRequirementSet`/`.feature`/call-site chain). **surface-as-own-design-task — DONE
  (2026-08-20), see "SPEC-SLICE VALUE ASSESSED" under item #4: largely-already-delivered (the
  cache already contains blast radius); the residual is review tooling, not architecture.**
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

Nitin's own #1 strategic risk appears under two names across his two rounds of feedback: his "house
of cards" / input-quality framing (his reply), and his own completeness + Knowledge Graph framing
(his original list), both pointing at the same underlying question — **does this platform know when
its own requirement corpus is incomplete, not just whether the requirements it has are individually
well-formed?** Verified: no corpus-level completeness check exists anywhere today (only
per-requirement completeness, in `enhancement/`/`grounding/`). This is simultaneously the heaviest
item on this list (group c) and, by Nitin's own repeated framing, the single highest-strategic-value
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
2b. **#4's own dedicated design-surfacing task — DONE (2026-08-20), see "SPEC-SLICE VALUE ASSESSED"
    under item #4, above.** Verdict: largely-already-delivered, not a generation-architecture
    change. Generation is already per-requirement/per-need slice-scoped, finer-grained than
    Nitin's own example; the blast-radius/efficiency rationale he stated is already delivered by
    the artifact cache (`[[cap-delta-regen-crux-surfaced]]`, proven by three live-measured runs);
    the one genuine residual (reviewability — a diff scoped to one feature, not the whole run) is a
    small promotion/review-tooling addition, workflow-shaped, not a branch-scoped generation
    re-architecture. Nothing built.
2c. **#3's traceability + change-impact graph design-surfacing task — DONE (2026-08-12), see
    "GRAPHS DESIGN SURFACED" under item #3, above.** Sequencing resolved: traceability first
    (highest strategic value, mostly buildable now, feeds the completeness thread directly);
    change-impact's method-level scope can follow, with its own element/selector-level mapping
    flagged as a separate prerequisite. Extend-vs-separate resolved: reuse ADR-0023's pattern
    (typed nodes/edges, deterministic pipeline) in a new sibling service with its own entry point
    over Runtime Truth — do not extend `KnowledgeGraphService.build` itself (frozen to Historical
    Truth only). The existing asset/catalog KG (ADR-0023) is unaffected. Nothing built.
2d. **Nitin's eval-harness build item (added 2026-08-12) — design-surfacing DONE (2026-08-17), see
    "EVAL HARNESS DESIGN SURFACED" under Item 1, above; ADR-0051 WRITTEN (2026-08-17), then Layer 1
    BUILT the same day (ADR-0051 now Accepted for `LiveStepDefinitionGenerator` only — see
    ADR-0051's own Implementation Note).** Curated eval sets per generator/skill, a tracked score,
    a regression gate; additive to the existing golden-baseline structural-regression harness, not
    a replacement for it (confirmed: CAP-070's own frozen ownership boundary excludes
    prompt/generation quality). Built: `eval_harness/` — a curated eval set seeded from the real
    tracked-baseline corpus, three deterministic property checks composed from CP5's own check
    class (one per real `gemini-2.5-flash` defect shape — wrong Cucumber import, markdown fence,
    fabricated duplicate class), scored per generator keyed by `GenerationIdentity`, gated by
    REGRESSION against a stored baseline (never an absolute threshold — proven relative, not
    absolute, by dedicated tests). Proven, deterministically (34 new tests, no live LLM call): each
    check catches its own real defect shape on a fixture reproducing it; the full arc (baseline
    established on a clean run, a worse-model-standing-in generator caught as a regression) works
    end to end via `StubStepDefinitionGenerator`. The judge layer (silently-wrong-logic) remains
    deferred, not designed, per ADR-0051 D5. CAP-090 (recommended) matrix/register entries were
    subsequently entered the same day (§5.13 / `architecture-baseline-v2.md` §3), closing that
    follow-on — this note's own "remain flagged" wording is a point-in-time snapshot, superseded by
    that same-day closure, not retro-edited here. Not CI-wired, not live-wired — the "live vs.
    cached LLM in CI" question ADR-0051 D2 flagged stays open, deliberately not resolved by this
    build.
2f. **Second generator extended (2026-08-20) — `LiveFeatureContentGenerator`, ADR-0051's own D5
    "extend to other generators" next step.** (Relabeled 2e → 2f, additive: the original `2e` below
    is a pre-existing, differently-numbered item — Nitin's re-run/token-cost build item — this
    note's own label collided with it when first added; only the label moved, no content changed.)
    Same proven Layer 1 pattern repeated, with feature-content's OWN defect shapes established
    first, not copied from step-def's: six deterministic checks composed from
    `feature_engineering.generation.assembler.generate_feature_file`'s own already-real
    tag-contract validation (five) plus the governed `generate_feature` prompt's own
    no-markdown-fence clause (one) — grounded in the real, already-enforced CONTRACT, since (unlike
    step-def) no known real historical feature-content defect exists on record (the live E2E run
    scored 15/15 clean, 0 escalations). A seventh real `assembler.py` block (tagged-`Background:`)
    was investigated and deliberately not ported, verified empirically that it is structurally
    unreachable (a tag before `Background:` is always a hard Gherkin parse error, already caught by
    the Gherkin-structure check). `models.py`, `scoring.py`'s `score_eval_set`, and
    `baseline_store.py` reused verbatim, unchanged — proving D2's generator-agnostic design
    directly. Proven end to end (32 new tests, no live LLM call): baseline established, a
    worse-model stand-in (a stray `@REQ-*` tag, the prompt's single most explicitly forbidden
    defect shape) caught as REGRESSED, a clean re-run PASSED. CAP-090 now covers 2 of 7 target
    generators (matrix §5.13, ADR-0051, `architecture-baseline-v2.md` §3 all updated additively the
    same day). Five generators/skills and the judge layer remain future, separate work. One mentor
    throughout (Nitin).
2g. **Third generator extended (2026-08-20, same day) — `LiveTestDataGenerator` — completes eval
    coverage of all THREE of ADR-0050's own measured/cached token sinks (step-def, feature-content,
    test-data).** A THIRD artifact type: Java, like step-def's, but governed by ADR-0037 D3's
    SUT-binding boundary, not Cucumber's grammar. Two checks DIRECTLY compose already-real,
    already-enforced mechanisms — the strongest grounding found in this arc yet:
    `check_no_env_binding` ports `test_data_orchestrator._check_no_env_binding`'s own regex
    verbatim (a live, always-on orchestration guard, not a design aspiration);
    `check_no_long_method` calls CP3's real, PUBLIC `evaluate_long_method` directly, no port
    needed. Three checks are contract-grounded, no known incident (like feature-content) —
    `check_no_markdown_fence`, `check_class_name_matches`, `check_no_webdriver_reference` — the
    last closing a REAL, previously-unenforced gap (CP3's own `direct_webdriver_action` criterion
    explicitly excludes test-data's package). One check (field-variant coverage) considered and
    honestly NOT built: every real `TestDataSpecification` this platform has ever emitted carries
    `fields=()` — no real case to ground it against. `models.py`/`scoring.py`'s
    `score_eval_set`/`baseline_store.py` reused verbatim a THIRD time;
    `feature_content_coverage.check_requirement_covered` reused verbatim too, no new coverage
    module. Proven end to end (25 new tests, no live LLM call): baseline established, a worse-model
    stand-in (`ConfigReader.env(...)`, the real guard's own violation shape) caught as REGRESSED, a
    clean re-run PASSED; `check_no_long_method` proven to actually fire on a real 45-line method.
    CAP-090 now covers 3 of 7 target generators. Four generators/skills and the judge layer remain
    future, separate work. One mentor throughout (Nitin).
2h. **The judge layer (eval-harness Layer 2) INVESTIGATED (2026-08-20, same day) — NOT WORTH
    BUILDING NOW, as a CI gate or in any minimal/non-gating form either; the deferral confirmed
    correct, not merely re-asserted.** Full analysis recorded in ADR-0051's own new "Investigation
    Note" (2026-08-20). Summary: (A) silently-wrong-logic (the judge's only real residual scope,
    once Layer 1 + CAP-088 are subtracted) is **unobserved** across every real corpus this arc has
    produced — the one real historical defect (`gemini-2.5-flash`, 76% defective) is 100%
    structural, already Layer-1-catchable; feature-content and test-data are both clean of any
    incident. (B) an LLM judge's own reliability is unproven and uncalibratable without ground
    truth this platform does not have — calibration requires exactly the human-scored-rubric
    approach already rejected as not CI-automatable. (C) the five open questions worked through:
    pinning is cheap and already solved (`GenerationIdentity` reuses verbatim); which judge, whose
    rubric, calibration, and cost remain genuinely open, with a real, already-existing precedent on
    this platform of the identical category (CP2's own "Business readability"/"Step reusability"
    LLM-judged advisory checks) being named once and never built, at no recorded cost. (D) the
    proven-safe regression gate (`check_regression`, exact/relative) does not transfer to a noisy
    judge score without undesigned machinery. (E) a NEW, decisive finding beyond ADR-0051's own
    original five questions: ADR-0049's Engineering Constitution, Article VII ("Deterministic Gates
    Decide" — an LLM-authored assessment is advisory only and never gates) means a judge could
    never GATE on this platform at all, by its own now-Accepted constitution, regardless of how
    well (B)-(D) were ever solved — only ever advisory, mirroring `CP2AdvisorySignals`'s own
    dormant slot. **Connection to #8/Nitin's intent:** a judge would validate a future #8
    model-swap semantically, but #8 itself remains unbuilt (no live consumer yet, the same shape
    `[[cap-runtime-citation-not-built]]` found for runtime citation); Nitin's own words name
    "rubrics" as an acceptable mechanism, not an LLM judge specifically, and his one concrete,
    real example (the gemini incident) is now fully covered by Layer 1 without any judge at all —
    his hypothetical healthcare example splits per D3, with only its unobserved semantic-
    implementation half needing a judge. **The trigger to reopen, named not scheduled:** a REAL
    observed instance of silently-wrong-logic in this platform's own generated output. Nothing
    built — surfacing only. One mentor throughout (Nitin).
2e. **Nitin's re-run/token-cost build item (added 2026-08-12)** — start with token-consumption
    instrumentation by stage and run (his own "Critically"-flagged, cheapest, no-architecture-change
    first step); artifact-level caching, delta-scoped regeneration (depends on 2c's change-impact
    graph), deterministic/LLM separation, and pinning follow (Item 1's own note, above).
3. **#3's own dedicated design-surfacing task (completeness/subset)** — specifically to answer the
   one question that determines this item's real size: can completeness be scoped as an
   arm's-length Layer 2+ consumer (small-ish), or does it genuinely require lifting ADR-0032
   (large)? Given Nitin's own repeated emphasis that this is the top strategic risk, this
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
