# Layer 4 — CP5: Suite-Integration Governance (Design Proposal)

| Field | Value |
|---|---|
| Status | Proposed — design only. **Not approved, not frozen.** |
| Type | Design Proposal (original design, not a deck transcription — no source deck exists for this document) |
| Layer / Control Point | Layer 4 (ADR-0031, "Suite Quality Governance"); CP5, per ADR-0040 Decision 3 and ADR-0044's confirmation, resolving the CP5/CP6 naming conflict `docs/proposals/layer-4-quality-governance-lld.md`'s Finding 0 raised against the `Quality_Governance_Layer.pptx` deck's own (mislabeled) CP5/CP6 |
| Depends on | ADR-0040 Decision 3 (CP5's definition); ADR-0044 (Layer 3 freeze — the catalog, reuse engine, CP3/CP4 shapes CP5 wraps); ADR-0045 (per-asset promotion — the mechanism CP5 wraps directly) |
| Governs | Nothing yet. Informs a future Layer 4 architecture-freeze ADR. This document does not freeze an ADR and does not authorize any build. |

---

## 0. What CP5 must fulfill — the Accepted spec

ADR-0040 Decision 3 defines Layer 4's remit — restated here as this document's own binding
target, quoted exactly:

> "Layer 4 (Suite Quality Governance) is **not** a Gherkin-lint or per-artifact quality stage —
> those responsibilities belong to CP2 and CP3 respectively (Decision 1). Layer 4 performs
> **suite-level integration governance**: checks no single generating layer can make on its own.
>
> - every `SCN-*` has a bound step definition
> - every step definition resolves to at least one scenario (no orphaned glue)
> - no near-duplicate step definitions across the suite
> - the assembled suite compiles
> - aggregate policy gate and the release decision on the suite as a whole"

ADR-0044 confirms this list is specifically CP5's, twice: *"those are Layer 4's suite-level
integration governance (ADR-0040 Decision 3) and Layer 5's execution concern, respectively"*
(re: CP5/CP6), and in Ownership: *"CP5 and CP6 (Layer 4's and Layer 5's own control points
respectively)."* ADR-0045 D1 confirms the list is still fully reserved, untouched by the
per-asset promotion it pulled forward:

> "orphaned-glue detection... cross-suite near-duplicate analysis... the aggregate release
> gate... All three remain Layer 4's, unchanged from ADR-0040 Decision 3, and are not built,
> specified, or authorized by this ADR."

This document designs those four items (the first bullet — bound-step-definition coverage —
is already CP3's own step-coverage criterion, ADR-0044 D5, restated at suite scope by the
"aggregate" bullet below; it is not a fifth, separate component). It does not design the
deck's mislabeled "CP5"/"CP6" (whole-suite Sonar, execution-readiness — real content, wrong
labels per Finding 0 of the LLD review) — see §5.

## 1. What CP5 wraps — the built machinery, as it actually exists today

### 1.1 Per-asset promotion (ADR-0045) — the mechanism CP5 sits on top of

`automation_engineering/promotion/gate.py::evaluate_promotion(candidate, gates,
baseline_catalog) -> Promoted | NotPromotable` is a pure, per-candidate decision: CP2/CP3/CP4
pass (decomposed per-asset since the 2026-08-06 additive note) and the candidate's
content-hash is not already in the baseline catalog. `evaluate_escalated_promotion` re-homes
an already-escalated reuse decision into `PromotionEscalated`, unedited — the same shared
review queue every escalation in this platform already joins (ADR-0045 D3, Recommendation 2).

`automation_engineering/promotion/mechanism.py` is the git-visible half: `apply_promotion`
writes `Promoted.candidate.java_source` verbatim to
`baseline_root / JAVA_SOURCE_SUBPATH / candidate.relative_path`; `stage_promoted_assets` runs
`git add` and **never** `git commit` (ADR-0045 D5, resolved 2026-08-02). The promoted files sit
staged-but-uncommitted after a run.

**The one property CP5's design leans on hardest:** `scanner.reconcile()`'s own docstring — and
the loop-closing proof (`tests/unit/test_automation_engineering_promotion_loop.py`) — establish
that reconciliation "reads the WORKING TREE directly, not git's index or commit history, so a
staged-but-uncommitted promoted asset is already visible to the very next run's catalog
reconciliation." This is not specific to "the next run" — it is true of **any** reconciliation
called after staging, including one called moments later, in the same process, before any
commit happens. §2.3 designs CP5's wrap order around exactly this property.

### 1.2 The catalog (`automation_engineering/catalog/scanner.py`) — the substrate every component reads

`reconcile(baseline_root) -> AssetCatalog` scans `baseline_root/src/test/java` and returns
`step_definitions`, `page_objects`, `utilities` tuples plus `unparsed_files`. Deterministic,
side-effect-free, no live dependency. Each `StepDefinitionAsset` carries `pattern` (the literal
Cucumber-annotation string), `content_hash`, `semantic_tags`, and `signature_alignment`
(capture ↔ parameter correlation) — all already computed, nothing CP5 needs to re-derive.

Current real scale (this repository's own tracked baseline, checked directly for this design):
**34 files carrying step-definition annotations, 1 tracked `.feature` file.** Small enough that
none of §2's cost concerns are live problems today; recorded so a future implementer does not
over-engineer for a scale that does not yet exist.

### 1.3 The reuse engine's semantic matching — the machinery CP5's near-dup sweep must reuse, not duplicate

The `SemanticMatcher` Protocol (`automation_engineering/reuse/matcher.py`) is need-vs-catalog
shaped: `match(need: GherkinStepNeed, catalog) -> candidates`. `LiveSemanticMatcher`
(`reuse/live_matcher.py`) is the live implementation, and it is **narrowly scoped**, by its own
docstring: *"Only step definitions are matched... this matcher only ever considers
`catalog.step_definitions`."* Page objects and utilities have no comparable embedding-text
derivation anywhere in this codebase today.

**This scoping happens to match ADR-0040 Decision 3's own literal text exactly** — the
near-duplicate bullet reads "no near-duplicate step definitions across the suite," not
page objects or utilities. CP5's near-dup sweep (§2.2) can therefore reuse the existing
step-definition-only embedding machinery as-is, with no new embedding-text derivation for
other asset kinds required — a fortunate alignment, not a coincidence to silently expand
without first amending ADR-0040 Decision 3's own text.

The actual API `LiveSemanticMatcher` sits on: `EmbeddingProvider.embed(texts: Sequence[str]) ->
tuple[vector, ...]` (`reuse/embeddings.py`) — **one batched call for many texts, same order in
as out.** `LiveSemanticMatcher.prime()` already demonstrates the pattern CP5 needs: embed every
relevant text once, in one call, then do all further comparison in memory against the cached
vectors. `_cosine_similarity` and `_embedding_text` are currently **private** to
`live_matcher.py` — CP5 needs the same "promote to public, don't duplicate" treatment this
codebase already gave `method_shape_fits` (originally private to `reuse/engine.py`, promoted to
public specifically so `generation/method_fit.py` could reuse the identical shape-compatibility
rule rather than hand-maintain a second copy). §2.2 designs against this precedent.

**Real calibration data already established** (`reuse/engine.py`'s own `DEFAULT_GENERATE_FLOOR`/
`DEFAULT_CONFIDENCE_THRESHOLD` docstrings, from a live run against this model family):
unrelated text scores `[0.5196, 0.6688]`; a full paraphrase of an existing pattern scored
`0.8980`; an exact-text match scored `0.9843`. `DEFAULT_GENERATE_FLOOR = 0.70` sits at the
midpoint of the unrelated/relevant gap; `DEFAULT_CONFIDENCE_THRESHOLD = 0.75` is Layer 3's own
trust floor. §2.2 reuses this same calibration rather than inventing a second one.

### 1.4 Gherkin-needs derivation (`automation_engineering/stage/gherkin_needs.py`) — the inverse relationship CP5's orphan check needs

`derive_feature_step_needs(content, file_path) -> FeatureStepNeeds` parses one `.feature`
file's text into its own ordered `GherkinStepNeed` tuple, via the same Gherkin parser CP2/CP3
already use. `derive_unique_step_needs(per_feature) -> tuple[GherkinStepNeed, ...]` dedupes by
step text, first-seen order, across every feature handed to it.

**Wired today only for the current run's own new features** (Layer 3's stage 15 orchestration).
CP5's orphan check (§2.1) needs needs derived from **every currently-tracked `.feature` file in
the suite**, not just this run's new ones — this is new wiring (point `derive_feature_step_needs`
at every file under `test-suite-baseline/src/test/resources/features/`, not just this run's
workspace output), reusing the exact same derivation functions unchanged.

---

## 2. The four CP5 components

### 2.1 Orphaned-glue detection

| | |
|---|---|
| **Checks** | Every step-definition asset in the reconciled catalog is referenced by at least one step in the **current, whole tracked feature corpus** — not just this run's newly generated features. |
| **Operates on** | `AssetCatalog.step_definitions` (§1.2) × `derive_unique_step_needs` over **every** tracked `.feature` file (§1.4, extended scope). |
| **Uses existing machinery** | The catalog scan and the needs-derivation functions, unchanged. Reused, not reimplemented. |
| **Produces** | A list of `(asset_id, class_name, pattern)` tuples for every step definition with zero matching needs, plus (per the recommendation below) the matching mechanism's own confidence, if semantic matching is used as a secondary signal. |

**Real decision 1 — referenced by which feature set.** "Orphaned" means referenced by none of
the **current, whole suite's** tracked features (§1.4) — not merely this run's new ones. A step
definition unreferenced by this run's own features but still bound to an older, still-tracked
feature elsewhere in the baseline is not orphaned; only a suite-wide needs-derivation answers
this correctly, which is why this is a Layer 4 (suite-scope) check and structurally could not
be a Layer 3 (per-run-scope) one.

**Real decision 2 — "no need matches": exact-pattern or semantic — recommend exact/deterministic
as primary, semantic as advisory only.** This is the sharper question, and this document departs
from treating it as a straight semantic-vs-exact choice: **Cucumber itself resolves glue at
runtime by matching a step's literal text against a step-definition's own pattern (a Cucumber
Expression or regex), never by semantic similarity.** An asset that is a *semantic* near-match
to some current need but whose actual pattern never matches that need's literal text is truly
dead code from Cucumber's own point of view — it will never fire at execution time regardless
of how "similar" its intent reads. Conversely, using the LiveSemanticMatcher's embeddings for
this check would be answering the wrong question (fuzzy intent-similarity) when a precise,
deterministic one (does this pattern actually match this text) already exists and is
computable with no live/embedding dependency at all: the catalog already records each asset's
raw `pattern`; the parser already produces each need's raw `text`; what is missing is a pattern
↔ literal-text matching evaluator (a Cucumber Expression / regex evaluator over the two), which
is new work but purely deterministic — no model, no live call.

**This also matters for ADR-0040 Decision 2's own discipline** ("control-point gates evaluate
only deterministic evidence... LLM-generated assessments are advisory only... never gate"):
a pattern-match evaluator keeps orphan detection a genuine, deterministic PASS/FAIL contributor
to CP5's own gate. Recommended design: **primary orphan determination is deterministic
pattern-vs-text matching** (new: a Cucumber Expression/regex evaluator, reusing the existing
`pattern`/`text` fields, no embeddings). A **secondary, advisory** semantic check — is a
pattern-orphaned asset semantically close to some current need anyway (candidate for "this
looks like a broken regex, not dead code" review) — may be layered on top using the same
step-definition embeddings §2.2 already computes, but must never itself decide orphan status,
only flag it for a human's attention (§3).

**Real decision 3 — the action on a detected orphan.** **Flag for review, never auto-remove.**
Deleting glue code is destructive and Cucumber-runtime-irreversible in a way promotion's own
additive, staged git changes are not; an orphan detector with a false positive (e.g., a step
referenced only by a `.feature` file the scan missed, or a pattern-matcher bug) that
auto-deletes would silently break a still-wanted binding with no staged diff for a human to
catch before it lands. This mirrors this platform's own promotion review posture (ADR-0045 D3:
auto-act only on what is provably safe by construction; escalate everything else to the one
shared human queue) — orphan detection has no equivalent "provably safe" case, so it never
auto-acts.

### 2.2 Cross-suite near-duplicate sweep

| | |
|---|---|
| **Checks** | The reconciled catalog's step definitions for **semantically near-duplicate clusters** — assets that individually passed ADR-0045 D2(b)'s exact content-hash check (so they are byte-distinct) but express near-identical intent, likely accumulated because different runs' independent generation solved the same need slightly differently. |
| **Operates on** | `AssetCatalog.step_definitions` only (§1.3's scope alignment with ADR-0040 Decision 3's own text). |
| **Uses existing machinery** | `EmbeddingProvider.embed()` (§1.3) for one batched embed call over every step-definition's `_embedding_text`; the same cosine-similarity formula `live_matcher.py` already computes, promoted to a shared/public location rather than duplicated (the `method_shape_fits` precedent, §1.3). |
| **Produces** | A set of near-duplicate clusters (each cluster: 2+ `asset_id`s plus their pairwise similarity scores), for human consolidation review. |

**Real decision 1 — the distinction from D2(b), stated precisely.** ADR-0045 D2(b) is an
**exact, content-hash** duplicate check, performed **per candidate, at promotion time**, against
the tracked baseline (`AssetCatalog.by_content_hash`) — it catches byte-identical re-promotion,
nothing else. This sweep is **semantic, suite-wide, and retrospective** — it catches assets that
are each individually unique by content-hash (so D2(b) correctly let each one promote on its
own run) but that, once the suite is viewed as a whole, do near-identical work: two or three step
definitions, promoted across different runs, each writing a slightly different implementation of
"user submits valid credentials." D2(b) cannot see this because it never compares two already-
promoted assets against **each other** — only a new candidate against the existing baseline.

**Real decision 2 — the similarity threshold, reused from real calibration, not invented.** The
task framing that motivated this design suggested "~0.90+," and that lines up closely with data
this platform has already measured (§1.3): a full paraphrase of an existing pattern scored
`0.8980` against the SAME embedding model this sweep would reuse. Recommend anchoring the
near-dup cluster threshold near that already-observed paraphrase floor (e.g. `0.90`, a small,
explicit margin above the measured `0.8980`) rather than picking an independent number — cosine
similarity between two texts is symmetric regardless of which one is labeled "need" and which is
labeled "catalog asset," so the existing need-vs-asset calibration is valid evidence for an
asset-vs-asset comparison using the identical model and identical `_embedding_text` shaping.
This is a **lean, not a lock** — real calibration against actual near-duplicate pairs (which
this platform has never yet observed, unlike the paraphrase/exact bands, which come from a real
live run) should confirm or adjust it before this becomes a frozen threshold.

**Real decision 3 — the action.** **Flag the cluster for human consolidation review; never
auto-merge.** Auto-merging automation code requires deciding which implementation is canonical,
rewriting every current Gherkin binding that depended on the discarded copy's exact pattern, and
verifying no subtle Cucumber Expression semantics differ between the "duplicates" — a
consequential, code-editing decision no deterministic gate should make unattended. This mirrors
the same posture as the orphan action (§2.1) and, again, ADR-0045 D3's own discipline: automate
only what is provably safe (nothing here is), escalate everything else.

**Cost, reported honestly.** The embedding **API cost is O(1) batched calls, not O(n)** —
exactly what `LiveSemanticMatcher.prime()`/`_embed_and_cache` already prove for the reuse
engine's own need-vs-catalog matching: one `embed()` call carries every step-definition's text
at once (deduplicated), regardless of catalog size. The **O(n²) cost is purely in-memory cosine-
similarity arithmetic** over the already-fetched vectors — cheap, no network, no additional
API quota consumed. At this repository's real current scale (34 step-definition-bearing files,
§1.2) this is a non-issue outright. If the catalog grows into the thousands, pure O(n²) pairwise
comparison could become a real compute cost (not an API-quota cost) — a future implementer could
bucket by `semantic_tags` first and only compare within a bucket, but this is **noted as a future
optimization trigger, not built or required now.**

**Scope boundary, restated.** This sweep does not extend to page objects or utilities — see
§1.3's scope-alignment note. Extending it would require both new embedding-text derivation for
those asset kinds (none exists today) and an amendment to ADR-0040 Decision 3's own literal
text, which currently names step definitions only. Not decided here.

### 2.3 Promotion-wrapping

| | |
|---|---|
| **Checks** | Whether the state ADR-0045's per-asset promotion just staged (git-added, uncommitted) is safe to become a durable, committed change to the tracked baseline. |
| **Operates on** | A fresh `reconcile()` of the baseline root, called **after** per-asset promotion has run and staged its candidates. |
| **Uses existing machinery** | `scanner.reconcile()`'s own working-tree read (§1.1) — no new file-reading mechanism needed; §2.1's orphan check and §2.2's near-dup sweep, run against this post-staging catalog. |
| **Produces** | A suite-level PASS (staged change may proceed to commit/merge) or a suite-level REJECT-FOR-REVIEW (the staged, uncommitted change is left exactly as staged, flagged for human review — never auto-reverted). |

**The wrap order, and why.** CP5 runs **after** per-asset promotion has staged its candidates
(`git add`, no commit — ADR-0045 D5) and **before** whatever turns a staged change into a
commit. This is not a new mechanism bolted on top — it directly exploits the property §1.1
already establishes: `reconcile()` reads the working tree, not git history, so a second
reconciliation called moments after staging already sees the assembled state (tracked baseline
+ newly staged assets) with zero new plumbing. ADR-0045 D5's own text anticipates exactly this
shape: *"An implementation may... stage the change for a separate CI gate to merge."* CP5 is
that separate gate. The alternative — CP5 evaluating a hypothetical pre-staging state via an
in-memory or scratch-copy simulation — was considered and rejected here: it requires new
machinery to simulate a merge that staging + a second `reconcile()` already gives for free, and
it diverges from the stage-then-review flow ADR-0045 D5 already locked.

**Composition with an individually-clean asset.** An asset that passed §1.1's per-asset gate
(CP2+CP3+CP4, non-duplicate) can still cause a suite-level REJECT — it orphans existing glue
(unlikely for a newly-promoted asset by construction, but a suite-level near-dup cluster or a
compile collision is entirely possible), or its addition creates or joins a near-dup cluster
(§2.2), or it breaks compile/ambiguous-glue cohesion (§2.4). **Recommended composition: route
this the same way every other escalation in this platform already routes** — into the ONE
shared human-in-the-loop review queue ADR-0045 D3 already established (*"Promotion escalation
and reuse escalation are the same review, not two separate ones"*, Recommendation 2). A CP5
suite-level rejection of an individually-clean asset is, structurally, the same shape: a
human must decide what to do with something no deterministic per-asset check could catch. This
document recommends CP5 extend that one queue rather than open a third, CP5-specific one — an
open decision for a future freeze to confirm, not locked here.

**What CP5 never does to the staged change on reject:** it does not `git restore`/unstage, and
it does not force a decision. A REJECT leaves the staged diff exactly as promotion left it —
visible, diffable, unresolved — for the same human review the orphan/near-dup findings already
route to. This preserves ADR-0045 D5's "a human has eyes on a tracked-baseline change before it
lands" posture rather than re-deciding it.

### 2.4 Aggregate-release cohesion

| | |
|---|---|
| **Checks** | Whether the assembled suite (tracked baseline + newly staged promotions) coheres as a whole: compiles, and has no Cucumber-ambiguous glue across classes. |
| **Operates on** | The same post-staging state §2.3 reconciles, plus the actual Java source tree on disk (for a compile check) and the catalog's `pattern` fields (for ambiguous-glue). |
| **Uses existing machinery** | The tracked baseline's own `test-suite-baseline/pom.xml` (confirmed present, §1.2) for a Maven-driven compile; the catalog's already-recorded `pattern` strings for glue-collision detection — no new asset-shape needed. |
| **Produces** | A structural PASS/FAIL (compiles or not; no exact-pattern collision across distinct classes or not). |

**The compile-boundary question, resolved by the same static/live line CP3/CP4 already drew.**
CP3 already establishes that a Layer 3/4-owned gate MAY depend on live *tooling infrastructure*
(a running SonarQube server) without crossing into Layer 5's territory — the boundary CP4 (and
this deck's own S2 finding) actually draws is **SUT/browser** dependency, not *any* live
dependency whatsoever (ADR-0044 D6: *"No running browser and no SUT are consulted... Live-DOM
validation... is explicitly not CP4's job. That is Layer 5's runtime concern."*). Invoking a
JDK/Maven toolchain to compile (`mvn compile` or equivalent) is structurally the same kind of
dependency as CP3's Sonar server — a build-time tool call, not a SUT or browser — so it sits
consistently on Layer 4's side of that boundary. **Recommended: "does it compile" is Layer 4/CP5's
own check.** "Does it then successfully RUN" (a smoke test passing, per the L4 LLD review's own
S2 finding) remains Layer 5's, unchanged.

**Ambiguous-glue-across-classes, scoped to an achievable first version.** Cucumber itself raises
an "Ambiguous step definitions" runtime error when two step-definition methods (in different
classes) both match the same literal step text. A precise version of this check needs a full
Cucumber Expression/regex overlap analysis (two syntactically different patterns can still both
match some literal text — a harder problem than string equality). **Recommended MVP: exact
pattern-string collision across distinct classes** — comparing each `StepDefinitionAsset.pattern`
against every other's, flagging exact string matches owned by different `class_name`s. This is
deterministic, cheap (string equality, not embeddings), and reuses only the catalog's
already-recorded `pattern` field — no new machinery. **Full expression-overlap detection (two
different-looking patterns that could still collide) is flagged as a stretch goal, not designed
or committed to here** — it would need a real Cucumber Expression engine this platform does not
currently have a dependency on.

---

## 3. CP5's control-point discipline — deterministic vs. advisory composition

ADR-0040 Decision 2 is unambiguous: *"All control-point gates evaluate only deterministic
evidence... LLM-generated assessments are advisory only... they may never gate a control
point."* CP5's four components do not compose uniformly against this rule, and this document
records the split explicitly rather than letting it stay implicit:

| Component | Nature | Composition |
|---|---|---|
| Orphaned-glue (primary check) | Deterministic (pattern-vs-text match, §2.1) | Contributes to CP5's PASS/FAIL |
| Orphaned-glue (secondary semantic hint) | Advisory (embedding similarity) | Review-trigger only, never gates |
| Cross-suite near-dup sweep | Advisory (embedding similarity, §2.2) | Review-trigger only, never gates — same discipline as the reuse engine's own confidence-based escalation (ADR-0044 D4(a)) |
| Promotion-wrapping reject | Composed from the above | A deterministic-check failure (orphan/compile/ambiguous-glue) may gate; a near-dup-only finding routes to review (§2.3), does not itself flip CP5's verdict |
| Aggregate cohesion (compiles, ambiguous-glue) | Deterministic | Contributes to CP5's PASS/FAIL |

**The practical rule this table encodes:** CP5's own PASS/FAIL verdict is driven only by its
deterministic components (compiles, exact pattern-vs-text orphan detection, exact ambiguous-glue
collision). The embeddings-backed near-dup sweep — and any secondary semantic orphan hint — never
by themselves fail CP5; they produce flagged findings that join the one shared human review
queue (§2.3), exactly as the reuse engine's own confidence-based escalation already does one
layer down. This is the same shape ADR-0040 Decision 2 already required of CP2's LLM-judged
checks ("Business readability"/"Step reusability" — advisory, never gating) and CP1's own
grounding-vs-gate separation (ADR-0016/ADR-0017) — CP5 is not a new exception to this platform's
deterministic-gate discipline, it is another instance of it.

---

## 4. Open decisions surfaced for review (consolidated)

None of these are locked by this document. They are the decisions a future freeze ADR must
make explicitly:

1. **Near-dup cluster similarity threshold** — leaning `~0.90`, anchored to the real `0.8980`
   paraphrase measurement (§2.2), not yet confirmed against real observed near-duplicate pairs.
2. **Orphan/near-dup action** — leaning flag-for-review-only, never auto-remove/auto-merge
   (§2.1, §2.2) — a stronger, more automated stance was considered and rejected here as
   inconsistent with this platform's own escalation-review discipline.
3. **Wrap order** — leaning after-staging/before-commit, exploiting `reconcile()`'s working-tree
   read (§2.3) — an alternative pre-staging dry-run simulation was considered and rejected as
   unnecessary new machinery.
4. **Suite-level-reject-of-a-clean-asset routing** — leaning the same shared human review queue
   ADR-0045 D3 already established, not a third queue (§2.3) — not yet confirmed against a
   future freeze's own review of whether CP5's own findings need a distinguishable review lane.
5. **Compile-boundary** — leaning Layer 4/CP5 owns "does it compile," Layer 5 owns "does it run"
   (§2.4), by analogy to CP3's own live-Sonar-but-not-live-SUT precedent.
6. **Ambiguous-glue detection depth** — leaning exact-pattern-collision as the achievable first
   version; full Cucumber Expression overlap analysis flagged as a stretch goal, unscoped here.
7. **Orphan detection's primary mechanism** — leaning deterministic pattern-vs-text matching
   (new: a Cucumber Expression/regex evaluator) over semantic matching, specifically so orphan
   detection can genuinely gate under ADR-0040 Decision 2's deterministic-only rule (§2.1); this
   evaluator does not exist in this codebase today and would be new build work.
8. **`_cosine_similarity`/`_embedding_text` promotion to a shared location** — leaning yes,
   mirroring the `method_shape_fits` precedent (§1.3), so CP5 never hand-maintains a second copy
   of the reuse engine's own similarity math.

## 5. What CP5 does NOT do

- It is not the deck's mislabeled "CP5" (whole-suite Sonar governance) or "CP6"
  (execution-readiness) — those are real Layer 4 content under different, still-to-be-decided
  labels (`docs/proposals/layer-4-quality-governance-lld.md` Finding 0). This document's CP5 is
  suite-**integration** governance only, per ADR-0040 Decision 3's own text.
- It does not re-litigate ADR-0045's promotable gate or review model (D2/D3) — it wraps them,
  per ADR-0045's own Recommendation 4 ("Layer 4's future architecture-freeze ADR must not
  re-litigate what's promotable or the review model").
- It does not extend near-duplicate detection to page objects or utilities without a future
  amendment to ADR-0040 Decision 3's own literal text (§2.2).
- It does not decide "does the suite run" (smoke test, live execution) — that stays Layer 5's,
  per this document's own compile-boundary lean (§2.4) and the L4 LLD review's own S2 finding.

## 6. Confirmation

This document proposes a design for review. It contains **no code**, freezes **no ADR**, and
authorizes **no build**. The next steps (in order, none performed here) are: review this
design, freeze it into a Layer 4 architecture-freeze ADR (resolving §4's open decisions), then
build against the frozen ADR — the same three-step discipline this platform already applied to
Layers 2 and 3 (LLD → freeze ADR → implementation).
