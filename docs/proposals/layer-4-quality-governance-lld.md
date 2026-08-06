# Layer 4 — Quality Governance Layer (LLD)

| Field | Value |
|---|---|
| Status | Submitted — under review. **Not approved.** |
| Type | Low-Level Design |
| Layer | Layer 4 — named "Suite Quality Governance" by ADR-0031; this deck calls itself "Quality Governance Layer" |
| Source artifact | `Quality_Governance_Layer.pptx` (21 slides), authored outside this repository. **Not committed to this repository** — unlike the Layer 2 and Layer 3 decks (`Feature Engineering Layer.pptx`, `layer-3-automation-engineering-lld.pptx`, both present in `docs/proposals/`), no copy of this deck exists in this session or repository. This transcription is built from the structured, slide-by-slide review already conducted outside this document (component list, CP5/CP6 design, the Generate→Govern→Approve→Execute principle, HITL conditions, task breakdown, DoD, and the 18 PD estimate), not from a direct re-read of the file. Where layer-2/3's transcriptions reproduce verbatim JSON examples and exact rule tables from slide images, this document does not — those slide-level artifacts are not available in this session, and are not invented here. |
| Transcribed | 2026-08-06 |
| Governs | Nothing yet. Informs a future Layer 4 architecture-freeze ADR. |

---

## Reviewer's note — scope, conflicts, and pending items

This document is committed as the **record of what was proposed**, not as approved design.
The body below reflects the deck's content as reviewed and has **not** been edited to reflect
later decisions. Do not implement from this document without reading this note first.

### Finding 0 — the deck's CP5/CP6 numbering conflicts with two Accepted ADRs; the ADRs win

This is the most consequential finding in this review, and it overrides the framing this
proposal was scoped under. Two Accepted ADRs already assign the labels "CP5" and "CP6" to
specific, different content than this deck uses them for:

- **ADR-0040 Decision 3** redefines Layer 4 as suite-level integration governance: every
  `SCN-*` has a bound step definition, every step definition resolves to at least one scenario
  (no orphaned glue), no near-duplicate step definitions across the suite, the assembled suite
  compiles, and the aggregate policy gate / release decision on the suite as a whole.
- **ADR-0044** (Layer 3 Automation Engineering Architecture Freeze, Accepted 2026-07-29) states
  this explicitly and twice: *"It does not define CP5 or CP6 — those are Layer 4's suite-level
  integration governance (ADR-0040 Decision 3) and Layer 5's execution concern, respectively"*
  (§Problem), and in Ownership: *"What Layer 3 does not own: ... CP5 and CP6 (Layer 4's and
  Layer 5's own control points respectively — LLD Reviewer's note item S7)"*, and again:
  *"Does not own: Layer 4's suite-level integration governance or CP5 (ADR-0040 Decision 3);
  Layer 5's execution, tag selection, live-DOM validation, or CP6."*

Read together, **CP5 is already Accepted-ADR-assigned to Layer 4's suite-integration
governance** — orphaned-glue detection, the cross-suite near-duplicate sweep, suite
compilation, and the aggregate release gate, i.e. exactly the "missing half" (b) this review
was scoped to flag as design-work-to-come (Finding 1, below) — and **CP6 is already
Accepted-ADR-assigned to Layer 5's execution control point**, not split between Layer 4 and
Layer 5.

This deck instead uses "CP5" for whole-suite Sonar/code-quality governance and "CP6" for
execution-readiness (which this review's own working framing, per the original task brief,
proposed splitting into a static Layer 4 half and a dynamic Layer 5 half — see S1/S2, below).
That framing is **superseded by ADR-0040/ADR-0044** wherever it conflicts, per this review's
own governing instruction that an Accepted ADR wins over this proposal. Concretely:

- The deck's CP5 (whole-suite Sonar) and CP6 (execution-readiness) content is real and
  relevant to Layer 4's remit (Layer 4 is, after all, named "Suite Quality Governance"), but it
  **cannot be labeled CP5/CP6 as the deck labels it** — those two labels are already spoken for,
  by name, in Accepted governing documents, for different content.
- The genuine Accepted CP5 — orphaned-glue detection, cross-suite near-duplicate sweep, suite
  compiles, aggregate release gate — is **not mentioned anywhere in this deck** (see S5, below).
  This is not a second, separate gap on top of the deck's CP5/CP6 content; it is the actual,
  already-named CP5, and the deck simply never reaches it.
- What this deck calls "CP5" (Sonar) and "CP6" (readiness) needs new, non-colliding
  provisional names at a future freeze (e.g. "suite Sonar gate" / "readiness gate," or
  renumbered CP7/CP8 once Layer 5's own CP6 is built) — **not decided here**; renumbering is
  design work, out of scope for a transcription + review.

This finding does not remove any of this deck's content from Layer 4's eventual remit — Layer 4
is legitimately the layer where whole-suite Sonar governance and suite execution-readiness
governance belong. It only invalidates the deck's own CP5/CP6 labels for that content, and it
means the "two-half scope" this review was asked to record (Finding 1) is better understood as:
**one half already has an Accepted name and definition (CP5, ADR-0040 Decision 3) and is
completely unaddressed by this deck; the other half (this deck's actual content) has real
substance but no Accepted control-point number of its own yet.**

### Finding 0a — a second, unrelated name collision: "Quality Governance" already exists elsewhere

`docs/proposals/quality-governance-framework.md` (Accepted, governed by ADR-0017, capability
CAP-080) is a **live, fully implemented, currently-wired-into-the-runtime** subsystem also
named "Quality Governance" — but it is not this layer. CAP-080's Quality Governance sits
immediately after CP1 in the Requirement Intelligence pipeline (Layer 1) and renders the
release decision from `GroundingResult` + `ValidationResult` + `CP1Result`; it has nothing to
do with Layers 2–4, SonarQube, Gherkin, or generated automation code. This deck's "Quality
Governance Layer" (Layer 4, ADR-0031) is a distinct, unbuilt subsystem that happens to share
the same English name. Any future Layer 4 freeze ADR should name this collision explicitly
(the same disambiguation discipline ADR-0031 D5 already requires for layer numbers) so a reader
does not assume CAP-080's existing, live "Quality Governance" is what Layer 4's freeze is
building. No functional conflict exists — the two subsystems' scopes do not overlap — but the
identical name is a standing source of confusion this note records for the future freeze ADR to
resolve (e.g., by renaming one of the two in prose, without touching CAP-080's frozen code).

### Finding 1 — the two-half scope, and the missing half's evidentiary basis

Layer 4 (ADR-0031: "Suite Quality Governance") has two genuinely distinct halves:

**(a) CP5/CP6-labeled code-quality and execution-readiness governance** — this deck's actual
content (whole-suite Sonar governance, execution-readiness checks), subject to Finding 0's
renaming caveat.

**(b) Suite-integration governance** — orphaned-glue detection, cross-suite near-duplicate
sweep, promotion-wrapping, and aggregate-release cohesion. This is **entirely missing** from
this deck, and per Finding 0 it is not a second gap alongside (a) — it is the Accepted CP5
(ADR-0040 Decision 3) itself.

ADR-0045 D1 (Scoped Asset Promotion, Accepted 2026-07-30) is the direct evidence that half (b)
is real, load-bearing, and deliberately reserved for Layer 4 — not invented by this review.
ADR-0045 pulled only the per-asset promotion decision forward into Layer 3's own capstone,
and said so in these words:

> "This ADR resolves **only** promotion — the workspace → tracked-baseline transition ADR-0037
> named. It does **not** pull forward any of Layer 4's other suite-level integration governance
> (ADR-0040 Decision 3):
> - orphaned-glue detection ("every step definition resolves to at least one scenario")
> - cross-suite near-duplicate analysis — i.e., "no near-duplicate step definitions across the
>   suite" as a *whole-suite* sweep, which is a broader check than D2(b)'s promotion-time
>   anti-duplicate gate below (D2(b) checks one candidate asset against the tracked baseline;
>   Layer 4's check sweeps the entire assembled suite for near-duplicates regardless of
>   promotion history)
> - the aggregate release gate ("aggregate policy gate and the release decision on the suite as
>   a whole")
>
> All three remain Layer 4's, unchanged from ADR-0040 Decision 3, and are not built, specified,
> or authorized by this ADR."

And, on the relationship between the per-asset promotion just built and Layer 4's eventual
governance:

> "**This is designed to be wrapped, not replaced.** Layer 4, once built, may wrap this
> promotion decision in richer suite-level governance — for example, folding a promotion event
> into its own aggregate release gate, or extending its cross-suite near-duplicate sweep to also
> re-verify recently-promoted assets. Nothing in this ADR forecloses that."

### Finding 2 — the missing half (b), and its connections to what already exists

This half needs its own design — a future task, not this one. Recorded here so that future
design work starts from what already exists rather than from nothing:

- **Orphaned-glue detection.** Baseline step definitions with no feature referencing them —
  dead automation. This is the *inverse* of the catalog + Gherkin-needs derivation Layer 3
  already built (ADR-0044 D3's persistent, tracked-baseline-reconciled catalog, and the
  Gherkin-needs-to-catalog matching the reuse engine already performs): where Layer 3 asks
  "does a need have a catalogued asset," orphaned-glue detection asks "does a catalogued asset
  have any need pointing at it."
- **Cross-suite near-duplicate sweep.** The suite-wide version of promotion's per-asset
  non-duplicate check (ADR-0045 D2(b)). D2(b) checks one candidate against the tracked baseline
  at promotion time; this sweep instead looks for near-duplicate **clusters** across the
  *entire* assembled suite — asset pairs or groups that each individually passed their own
  per-asset promotion check but are collectively redundant. Reuses the reuse engine's semantic
  matching machinery (ADR-0044 D3/D4) at suite scale rather than at single-candidate scale.
- **Promotion-wrapping.** The ADR-0045 capstone's own stated hook: a **suite-level gate on top
  of** the per-asset promotion mechanism already built (`automation_engineering/promotion/`,
  ADR-0045 D1–D5, closed end-to-end 2026-08-02). An asset that passes per-asset promotion can
  still be rejected at suite level — it orphans glue elsewhere, creates a near-duplicate cluster
  once combined with other recently-promoted assets, or breaks suite cohesion in some way no
  single-asset check can see.
- **Aggregate-release cohesion.** Whether the assembled suite — the tracked baseline plus
  everything newly promoted this run — compiles and coheres as a whole, beyond each individual
  asset passing its own gates. This is the "aggregate policy gate and the release decision on
  the suite as a whole" ADR-0040 Decision 3 names directly.

This is where the real Layer 4 design energy goes at the next freeze. It is the Accepted CP5
(Finding 0); this deck does not touch it.

### S1–S6 — the deck's-half (a) boundary fixes

| Item | Deck's content | Fix / caveat |
|---|---|---|
| S1 | CP5 = whole-suite Sonar governance, distinct from CP3's per-generation-batch Sonar gate (ADR-0044 D5) | **Distinction confirmed, label conflicts.** The *distinction* is sound — CP5 governs what the SUITE has become (the entire accumulated baseline), CP3 gates what a single RUN produced (ADR-0044 D5's hard per-batch quality-gate scan). Without this distinction, a suite-level Sonar gate is a redundant CP3 re-run. But per Finding 0, the label "CP5" for this content conflicts with ADR-0040/ADR-0044's own CP5 (suite-integration governance). The distinction survives; the number does not. |
| S2 | CP6 = execution-readiness, and this review's own working brief proposed splitting it: static readiness (assets present, deps resolvable, `pom.xml`/Cucumber/Selenium/env config valid, well-formed) → Layer 4; dynamic checks (build succeeds, smoke test passes) → Layer 5 | **Split confirmed as the correct static/live boundary, label conflicts.** The static/dynamic split mirrors the exact boundary CP4 already drew for locator health (ADR-0044 D6: static locator health in Layer 3/CP4, live-DOM validation in Layer 5) — the same "no running-browser or SUT dependency" discipline applies here: readiness-of-configuration is a Layer 4 concern, readiness-in-execution is Layer 5's, confirmed by the user that Layer 5 is where test execution happens. But per Finding 0, ADR-0044 already assigns the whole of CP6 to Layer 5, not split. If this static/dynamic split is adopted at a future freeze, the static half needs a label that is not "CP6" (which is already Layer 5's, undivided) — for example, folded into the renamed CP5-successor from S1, or a new number. |
| S3 | CP5's security dimension: gate on SonarQube security ratings/hotspots for generated Java | **Scope down honestly, per the CP3 precedent.** This must inherit CP3's own honest Sonar closure (ADR-0044 D5/D6 and the `customqa:*` arc): SonarQube performs *generic* quality analysis; this platform's own architectural rules (`direct-webdriver-action`, `long-method`, etc.) are STATIC checks precisely because Sonar could not express them natively. The same honesty applies to security: Sonar's security ratings/hotspots are largely designed for production service code and are mostly inapplicable to test-automation code — a Selenium test suite has a very different, mostly-irrelevant security profile compared to a production service. A future CP5-successor should not gate meaningfully on Sonar security ratings that do not mean much for test code; if a security dimension is wanted, it likely needs the same "static check Layer 4 writes itself" treatment CP3 already gave `direct-webdriver-action`. |
| S4 | Slide 13 — a Governance Dashboard | **Drop — Layer 7's job.** ADR-0031 names Layer 7 (Governance Dashboard) as the layer that renders leadership-facing insight across the pipeline. Layer 4 (like Layer 2 and Layer 3 before it) *produces* CP5/CP6-successor reports; it does not *consolidate* them into a dashboard. This slide's content belongs to a future Layer 7 LLD, not this one. |
| S5 | The deck never mentions promotion, the asset catalog, or the tracked baseline at all | **Symptom of the missing half.** This absence is exactly what Finding 1/2 describe: the deck's silence on promotion/catalog/baseline is consistent with it never addressing the Accepted CP5 (suite-integration governance), which is where promotion-wrapping and the catalog's suite-wide view actually live. Cross-referenced, not re-argued, here. |
| S6 | SonarQube Community Edition is assumed to support CP5's claimed features (security hotspots, quality-gate specifics) | **To-verify-before-building, not resolved here.** Sonar Community Edition has materially reduced security-analysis and quality-gate capability compared to paid editions. This platform's existing CP3 build already exercises the "verify the tool does what the slide claims" discipline once (the `customqa:*` arc, discovering that Sonar's rule engine cannot natively express caller-role constraints like `direct-webdriver-action`, resolved by a static Layer 3 check instead). The same discipline applies here, unresolved by this review: confirm what this repository's actual Sonar edition supports before any CP5-successor design assumes hotspot/quality-gate features it may not have. |

### CP3/CP4-honesty inheritance

Layer 4's eventual Sonar use (the S1/S3 content) is not a fresh Sonar story — it extends CP3's
already-honest one (ADR-0044 D5) to suite scale. Everything CP3 already learned carries
forward: Sonar performs generic-only analysis; anything Sonar's rule engine cannot express
natively (caller-role constraints, method-size thresholds tied to this platform's own
conventions) is a static check this platform writes itself, not a Sonar rule; and the actual
capabilities of the Sonar edition/profile in use must be verified against the real server, not
assumed from a slide (S6). A future CP5-successor design that treats Sonar-at-suite-scale as a
brand-new integration, rather than an extension of CP3's own established profile/scope
realities, has not read CP3's own freeze closely enough.

---

## 1. Purpose

The Quality Governance Layer validates the accumulated, suite-wide state of the automation
codebase — as distinct from any single run's output — and determines whether the suite is
execution-ready.

**Responsibilities, as described in the deck:**

- Whole-suite SonarQube quality governance
- Suite-wide quality metrics aggregation
- Execution-readiness analysis (static configuration/dependency validation)
- Jenkins readiness validation
- Governance reporting across the accumulated suite

**Output:** Governed, execution-ready suite, plus governance reports.

> Per Finding 0/1, this Purpose statement describes only half of Layer 4's eventual remit
> (deck's-half (a)). Suite-level integration governance (orphaned-glue detection, cross-suite
> near-duplicate sweep, promotion-wrapping, aggregate cohesion — half (b), the Accepted CP5)
> is not addressed by this deck and is not part of this Purpose statement as transcribed.

## 2. Inputs

**Primary Input:** Validated Automation Package

**Produced by:** Automation Engineering Layer (Layer 3)

**Contains** (per Layer 3's own output list, ADR-0044/§21 of the Layer 3 LLD): Step
Definitions, Page Objects, Automation Scripts, Utilities, Automation Coverage Report, CP3
Validation Report, CP4 Validation Report, Sonar Analysis Report, Traceability Report.

## 3. Outputs

| | Work product |
|---|---|
| Work Product 1 | Whole-Suite Quality Metrics Report |
| Work Product 2 | CP5-labeled Validation Report (Sonar/code-quality; see Finding 0 on the label) |
| Work Product 3 | Execution Readiness Report |
| Work Product 4 | Jenkins Readiness Report |
| Work Product 5 | CP6-labeled Validation Report (execution-readiness; see Finding 0 on the label) |
| Final Output | Governed, execution-ready suite + governance report set |

## 4. High Level Flow

Validated Automation Package → Quality Metrics Engine (whole-suite aggregation) → SonarQube
Integration (whole-suite scan) → CP5-labeled Validation Engine → Execution Readiness Analyzer
(static config/dependency checks) → Jenkins Readiness Validator → CP6-labeled Validation Engine
→ Governance Reporting → Governed, execution-ready suite.

> Reconstructed from the reviewed component list and the deck's own stated
> Generate→Govern→Approve→Execute principle (§5, below), not from a slide flowchart image —
> unlike layer-3's §4, no flowchart image is available in this session (see the Source artifact
> caveat at the top of this document).

## 5. Key Design Principle

**Generate → Govern → Approve → Execute.**

Every suite must pass through whole-suite governance and an explicit approval step before it
is handed to execution — mirroring the same generate → validate → repair discipline each prior
layer's own in-layer control point already applies (ADR-0040 Decision 1), but at suite scale
rather than single-artifact or single-run scale.

## 6. Components

| Component | Purpose |
|---|---|
| SonarQube Integration | Whole-suite Sonar scan and quality-gate evaluation |
| Quality Metrics Engine | Aggregates code-quality metrics across the accumulated suite |
| CP5 Validation Engine (label per Finding 0) | Suite-wide code-quality gate |
| Execution Readiness Analyzer | Static checks: assets present, dependencies resolvable, config well-formed |
| Jenkins Readiness Validator | Validates Jenkins-specific execution prerequisites |
| CP6 Validation Engine (label per Finding 0) | Execution-readiness gate |
| Governance Reporting | Produces the suite-level governance report set |

## 7. SonarQube Integration

Runs a whole-suite Sonar scan against the accumulated tracked baseline (not a single run's
newly generated code, which is CP3's own scope — ADR-0044 D5). Inherits CP3's `customqa:*`
profile and the same generic-quality/static-check split (S1, S3, and the CP3/CP4-honesty
inheritance section, above).

## 8. Quality Metrics Engine

Aggregates code-quality metrics across the whole accumulated suite: code smells,
maintainability, duplication, and coverage — the same metric families CP3 already computes per
run (Layer 3 LLD §18), rolled up to suite scope.

## 9. CP5 Validation Engine (label per Finding 0)

**Purpose, as described in the deck:** gate the whole-suite Sonar scan's quality-gate result.
Per Finding 0, this label conflicts with the Accepted CP5 (ADR-0040 Decision 3 / ADR-0044) and
needs a non-colliding name at a future freeze; the content itself — a suite-scoped Sonar gate,
distinct from CP3's per-run gate — is not in question (S1).

## 10. Execution Readiness Analyzer

**Purpose, as described in the deck:** validate that the suite is statically ready to execute —
assets present, dependencies resolvable, `pom.xml`/Cucumber/Selenium/environment configuration
valid and well-formed. Per S2, this is the static half of what the deck calls CP6; the dynamic
half (build succeeds, smoke test passes) belongs to Layer 5, not this layer.

## 11. Jenkins Readiness Validator

**Purpose, as described in the deck:** validate Jenkins-specific execution prerequisites ahead
of a Layer 5 handoff. Depends on ADR-0039 (Execution Backend and CI/CD), which is **Proposed,
not Accepted** — nothing in this component may be built against Jenkins specifics until
ADR-0039 is Accepted (mirroring the caveat the architecture baseline register already carries
for ADR-0039).

## 12. CP6 Validation Engine (label per Finding 0)

**Purpose, as described in the deck:** gate execution-readiness (both the static
Execution Readiness Analyzer and the Jenkins Readiness Validator's output). Per Finding 0, this
label conflicts with the Accepted CP6 (Layer 5's own execution control point, per ADR-0044).
Per S2, the dynamic portion of what this deck calls CP6 (build succeeds, smoke test passes) is
Layer 5's job outright, not this layer's, regardless of labeling.

## 13. Governance Reporting

Produces the suite-level governance report set: whole-suite quality metrics, the CP5-labeled
and CP6-labeled validation reports, and a consolidated governance summary — consumed
downstream by execution (Layer 5) and, per S4, **not** itself a dashboard.

## 14. Governance Dashboard (slide 13) — out of scope

The deck's slide 13 describes a governance dashboard. Per S4, this is Layer 7's job
(ADR-0031): Layer 4 produces reports; Layer 7 consolidates them into a leadership-facing
dashboard. Transcribed here for completeness, not adopted into this layer's scope.

## 15. Human-in-the-Loop Conditions

Review required when (as described in the deck):

- Suite-wide Sonar quality gate fails
- Execution readiness checks fail (missing assets, unresolved dependencies, malformed config)
- Jenkins readiness validation fails
- Suite-wide quality metrics fall below threshold

## 16. Work Product / Handover Artifacts

| Artifact | Consumed By |
|---|---|
| Whole-Suite Quality Metrics Report | Governance Reporting |
| CP5-labeled Validation Report | Governance Reporting; downstream release decision |
| Execution Readiness Report | Jenkins Readiness Validator; Layer 5 |
| Jenkins Readiness Report | Layer 5 (execution handoff) |
| CP6-labeled Validation Report | Governance Reporting; Layer 5 |
| Governance Report Set | Layer 7 (Governance Dashboard, per S4) |

## 17. Implementation Task Breakdown

> The deck's own per-task breakdown table (if one exists on a dedicated slide, as layer-2's §20
> and layer-3's §26 each had) is not available in this session — see the Source artifact
> caveat. The table below is reconstructed at the granularity of this deck's own named
> components (§6), not fabricated at finer detail than the review actually captured.

| Task | Output |
|---|---|
| Build SonarQube Integration (whole-suite scan) | Whole-suite Sonar scan result |
| Build Quality Metrics Engine | Whole-suite quality metrics report |
| Build CP5-labeled Validation Engine (label per Finding 0) | CP5-labeled validation report |
| Build Execution Readiness Analyzer (static checks) | Execution readiness report |
| Build Jenkins Readiness Validator | Jenkins readiness report |
| Build CP6-labeled Validation Engine (label per Finding 0) | CP6-labeled validation report |
| Build Governance Reporting | Consolidated governance report set |
| Unit tests for each engine | Test results |
| End-to-end dry run against a real accumulated suite | Governed, execution-ready suite |

## 18. Definition of Done

The Quality Governance Layer (deck's-half (a) only — see Finding 1/2 for half (b), out of
this deck's scope entirely) is considered complete when:

**Suite-wide Sonar governance**

- Whole-suite Sonar scan executes successfully against the accumulated tracked baseline.
- CP5-labeled quality gate result is available (label pending resolution, Finding 0).
- Code smells, maintainability, and duplication metrics are generated at suite scope.

**Execution readiness**

- Static readiness checks execute successfully (assets present, dependencies resolvable,
  config well-formed).
- Jenkins readiness validation executes successfully.
- CP6-labeled validation report is generated (label pending resolution, Finding 0).

**Governance**

- Consolidated governance report set is generated.
- Reports are consumable by Layer 5 (execution) and Layer 7 (dashboard, per S4).

**Final Acceptance**

- Suite-wide Sonar quality gate = PASSED.
- Execution readiness = PASSED.
- Suite successfully handed off to Layer 5.

## 19. Estimated Effort Summary

**Total: 18 PD**, as given in the deck.

> The deck's own per-workstream effort breakdown (mirroring layer-2's §22 and layer-3's §26
> tables) is not available in this session — see the Source artifact caveat. Inventing a
> workstream-by-workstream split that sums to 18 PD would fabricate detail the review did not
> actually capture, so none is given here. The 18 PD total covers deck's-half (a) only (§1's
> caveat) — it does not include half (b)'s suite-integration governance (Finding 1/2), which
> has no effort estimate yet because it has no design yet.
