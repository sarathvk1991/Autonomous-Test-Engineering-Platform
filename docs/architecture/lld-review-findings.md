# LLD Review Findings — `docs/proposals/`

| Field | Value |
|---|---|
| Type | Review-only findings document. No LLD, code, ADR, or register was edited to produce this. |
| Scope | All Layer 1–7 LLD artifacts in `docs/proposals/` (PPTX and Markdown), assessed against real code (built layers) or current ADRs/decisions (unbuilt layers). |
| Date | 2026-08-11 |
| Gate | `make lint`: clean. `make test`: 5736 passed. Tree clean, `main`, tracking `origin/main` even. |

---

## 0. The headline reframe

The task brief that motivated this review assumed L2–L4's Markdown LLDs are **"maintained living
docs"** that track current code, needing periodic reconciliation the way a README does. That
assumption does not hold, and it changes the right disposition for almost every item below.

**What the L2/L3/L4 Markdown files actually are:** a faithful, unedited transcription of the
original PPTX deck, frozen at a single "Transcribed" date, plus a **Reviewer's note** section that
flags what the deck got wrong or what's since been superseded — explicitly marked `Status:
Submitted — under review. Not approved.` They are not updated as the build progresses. They exist
to feed a future (now-Accepted) architecture-freeze ADR, and once that ADR lands, the ADR +
`docs/architecture/architecture-baseline-v2.md` — not the LLD — become the living record.

This pattern is now complete for L2, L3, and L4:

| Layer | Proposal doc(s) | Froze into | ADR status |
|---|---|---|---|
| L2 | `layer-2-feature-engineering-lld.md` (+ pptx) | ADR-0043 | Accepted |
| L3 | `layer-3-automation-engineering-lld.md` (+ pptx) | ADR-0044 | Accepted |
| L4 | `layer-4-quality-governance-lld.md` | ADR-0046 | Accepted |
| L4 | `layer-4-cp5-suite-integration-governance-design.md` | ADR-0046 | Accepted |
| L4 | `layer-4-cp7-cp8-design.md` | ADR-0047 | Accepted |

So the operative question for a built layer's Markdown LLD is **not** "does this match today's
code" (it was never meant to) but **"is the Reviewer's note still an accurate snapshot of what was
superseded, and has the freeze ADR fully absorbed it?"** — checked below, layer by layer. On that
question, L2/L3/L4's markdown is in good shape: each Reviewer's note remains accurate, and each
freeze ADR explicitly locks the content the note flagged. **No markdown fix is needed for L2, L3,
or L4.** This reverses the task brief's working hypothesis that drifted L2–L4 markdown would be
the main "fix-now" candidate.

L1 is the exception precisely because it never got this treatment — no transcription, no
Reviewer's note, no freeze ADR that absorbs the deck's content the way ADR-0043/0044/0046/0047 did
for L2–L4. That gap, not "the PPT is stale" per se, is L1's real finding (§2).

---

## 1. Inventory — confirmed vs. the stated premise, with corrections

```
docs/proposals/
  layer-1-requirement-intelligence-layer-lld.pptx          (L1, built)
  layer-2-feature-engineering-lld.md                       (L2, built)
  layer-2-feature-engineering-lld.pptx                     (L2, built)
  layer-3-automation-engineering-lld.md                    (L3, built)
  layer-3-automation-engineering-lld.pptx                  (L3, built)
  layer-4-cp5-suite-integration-governance-design.md       (L4, built)
  layer-4-cp7-cp8-design.md                                (L4, built)
  layer-4-quality-governance-lld.md                        (L4, built)
  layer-5-execution-layer-lld.pptx                         (L5, unbuilt)
  layer-6-failure-intelligence-&-self-healing-layer-lld.pptx (L6, unbuilt)
  layer-7-governance-dashboard-layer-lld.pptx              (L7, unbuilt)
  + 13 other proposal docs, not per-layer LLDs (§7, out of scope)
```

| Layer | PPT | MD | Built? | git-last-edit (content) | Note |
|---|---|---|---|---|---|
| L1 | yes | **none** | Yes (heavily — 142/252 commits, ADR-0032) | Content new to repo 2026-08-11 (never committed before today) | Confirms user's premise: PPT-only, no markdown |
| L2 | yes | yes | Yes | pptx content 2026-07-24; md 2026-07-24 | Confirms premise. Both are provenance for ADR-0043, not living docs |
| L3 | yes | yes | Yes | both 2026-07-29 | Confirms premise. Both are provenance for ADR-0044 |
| L4 | **none** | **yes, three files** | Yes | all three md 2026-08-06 | **Deviates from premise** — no PPT was ever committed (documented reason: the deck was reviewed but never checked in, unlike L2/L3); three MDs instead of one, only one of which is a deck transcription |
| L5 | yes | none | No | content new to repo 2026-08-11 | Confirms premise |
| L6 | yes | none | No | content new to repo 2026-08-11 | Confirms premise |
| L7 | yes | none | No | content new to repo 2026-08-11 | Confirms premise |

**Two corrections to the stated premise:**

1. **L4 has no PPT at all**, not a PPT+MD pair like L2/L3. This isn't an oversight to fix — the
   L4 quality-governance-lld.md's own header states it directly: the deck was reviewed slide-by-slide
   outside this repo but never committed here, "unlike the Layer 2 and Layer 3 decks." L4 also has
   **three** markdown documents, not one: one deck transcription
   (`layer-4-quality-governance-lld.md`) and two **original, born-digital design docs** with no
   source deck at all (`layer-4-cp5-suite-integration-governance-design.md`,
   `layer-4-cp7-cp8-design.md`) — these two were written directly against live-verified real
   systems (e.g. a real `docker ps`/Sonar Community Edition check), not transcribed from slides.

2. **L1, L5, L6, and L7's PPTX files were not in version control until today's commit**
   (`80672af`, "adding remaining llds for reference"). L2's pptx was already tracked (since
   2026-07-24, just renamed today); L3's has been tracked since 2026-07-29. So while the "PPT
   only, no markdown" shape the user described is correct for L1/L5/L6/L7, these four files are
   brand-new additions to this repository as of this session — they did not silently drift
   untracked; they simply weren't here to drift.

Build state (confirmed via `requirement_intelligence/run_state/stages.py`, `STAGE_DEFINITIONS`):
L1 (stages 1–13), L2 (stage 14, ADR-0043), L3 (stage 15, ADR-0044) are live; L4 (stage 16) is
built and wired (CP5/CP7/CP8, ADR-0046/0047) though its `governing_citation` field reads "none
yet" (a label gap in that one field, not a build-state gap — worth a one-line fix separately, but
outside this review's LLD scope). L5 (stage 17), L6 (stage 18), L7 (stage 19) are all
`governing_citation="none yet"` and genuinely unbuilt — confirms the user's built/unbuilt premise
exactly.

---

## 2. L1 — Requirement Intelligence (built, PPT-only) — the special case

**Verdict: the proposal is comprehensively stale — nearly every concrete claim in it is
contradicted by the real, built code — and L1 is the one built layer with no reconciliation
record of any kind.**

Verified directly against `requirement_intelligence/` (file:line citations from a live grep/read
pass, not inferred):

| Deck claim | Reality | Verdict |
|---|---|---|
| Sources: HP ALM Trial, OWASP ZAP, SonarQube | `config/source-registry.json:14-40` — **JIRA**, ZAP, SonarQube. No HP ALM connector exists anywhere. Real connectors: `connectors/jira/connector.py`, `connectors/zap/connector.py`, `connectors/sonarqube/connector.py` | **Contradicted** — ADR-0031 (Accepted) names JIRA/SonarQube/ZAP as the frozen three sources; the deck's HP ALM has no ADR basis at all |
| Enrichment via Azure OpenAI | `llm/provider_registry.py:22-23` defaults `LLM_PROVIDER="gemini"`; `llm/providers/gemini_provider.py:163` is the live implementation. `llm/providers/azure_openai_provider.py:1-62` is an explicit **stub** — "Licensing status: NOT YET AVAILABLE," every method `raise NotImplementedError` | **Contradicted** |
| Consolidation groups by module/feature-intent/functional-similarity/security-relevance/quality-relevance/risk-level (implying semantic/AI grouping) | `consolidation/consolidation_rules.py:8-16` — deterministic, rule-based: component → shared tag → endpoint → risk level, explicitly documented as "no AI... no semantic similarity" | **Partially contradicted** — grouping exists but is deliberately non-semantic, the opposite of what the deck implies |
| Named output files (`raw-records.json`, `canonical-requirements.json`, `consolidated-requirements.json`, `requirement-analysis-report.json`, `cp1-validation-report.json`, `validated-requirement-model.json`) | None of these filenames exist anywhere in the repo. Real output machinery is `execution_package/` (`execution_writer.py`, `manifest_builder.py`, `cp1_report_builder.py`, `validation_report_builder.py`, `baseline_metrics_builder.py`, `review_builder.py`, `engineering_context_artifact.py`) | **Contradicted** — different concept ("Execution Package"), different structure |
| CP1's 7 named rules (Mandatory Field / Ambiguity / Acceptance Criteria / Traceability / Risk Coverage / Duplicate / Confidence Check) | None of these seven exist. Real CP1 (`cp1/engine/cp1_engine.py`) runs exactly **one** criterion today, `EngineeringInputAvailabilityCriterion` (CP1-0001, "≥1 pooled requirement exists"). Real multi-rule validation lives in a completely different taxonomy: `validation/rules/` (11 rules) and `requirement_quality_governance/rules/quality_rule_builder.py` (17 rules, `QG-*` ids) | **Contradicted** |
| Generic "source registry + connector interface" extensibility pattern | `config/source-registry.json` + `registry/connector_registry.py` + `connectors/base.py` — the pattern **matches**, plus an `EXECUTION_MODE=FILE\|API` toggle the deck never anticipated | **Matches** (the one item that survives intact) |

**Built with zero mention in the deck at all:** `grounding/` (49 files), `requirement_quality_governance/`
(rule catalog + decision engine), a full governed **Prompt Registry** subsystem (`prompts/`,
ADR-0014, SHA-256-fingerprinted versions, Draft→Production→Archived lifecycle),
`context_orchestration/`, `knowledge_graph/`, `learning/`, `organizational_memory/`,
`continuous_improvement/`, `recommendation/`, `enhancement/`, `testable_requirement/`,
`run_state/`. Per ADR-0031 D3, several of these are entire redesignated sub-capabilities (CAP-083
through CAP-086) with their own multi-milestone ADR arcs — none of it existed as a concept when
the deck was written.

**The key finding, restated per the task brief's own framing:** this isn't just "the PPT is
stale" — every other built layer (L2, L3, L4) got a committed transcription + Reviewer's note that
explicitly reconciles the deck against later decisions, feeding a freeze ADR. **L1 never got that
treatment.** It has ADR-0032 (Layer 1 Capability Freeze), but that ADR is a policy freeze
document — it bounds *future* growth, it does not describe L1's *current* architecture the way
L2/L3/L4's reviewed transcriptions describe theirs.

**Recommendation:** create a markdown LLD for L1 that captures L1 **as-built** — mirroring the
L2/L3/L4 pattern (either a transcription-plus-Reviewer's-note of the existing deck, or a from-code
description; from-code is the more honest choice here given how little of the deck survives). Do
**not** re-edit the stale PPTX deck slide-by-slide — the deck is now source-historical only, the
same disposition every other built layer's original deck has.

**Timing — this is the one judgment call in this review.** Mentor item #3 (corpus-level
requirement completeness) is confirmed to land squarely on Layer 1 (`docs/architecture/mentor-feedback-scoping.md`,
Item 3): it is currently scoped as "surface-as-own-design-task," not adopted, specifically because
it may require either an ADR-0032 freeze-lift or a careful arm's-length Layer 2+ scoping — either
path changes what L1 *is* documented as owning. Writing L1's as-built markdown now would need a
second pass once #3 resolves; writing it after #3 resolves means describing L1 once, correctly.
**Lean: create-with-#3**, not create-now — same posture already adopted for the other
"adopt-when-building" mentor items (§5). If the user wants L1 documentation sooner regardless (e.g.
as a stopgap onboarding aid), that's a legitimate reason to override this lean, but it should be
labeled explicitly as a stopgap that will need a second pass.

---

## 3. L2 — Feature Engineering (built, PPT+MD)

**The Markdown (`layer-2-feature-engineering-lld.md`):** current and accurate — as what it is,
a point-in-time transcription-plus-review, not a from-code description. Its Reviewer's note
(top of file) already flags every major supersession an as-of-today re-check would find:

- Azure OpenAI → provider-agnostic `llm_factory`, Gemini in use (spot-checked against L1's live
  finding above — still accurate; Gemini remains the active provider platform-wide).
- Untyped criteria arrays → `TestableRequirement`/`TestableRequirementSet` (ADR-0034).
- A new Layer-2-local Prompt Registry → the existing governed registry (ADR-0014), which is
  correct — `prompts/` is a platform-wide, Layer-1-owned service, not Layer-2-local.
  (Cross-checked against CAP-075's prompt-runtime-integration work: the registry is confirmed the
  live runtime prompt source.)
  Same registry, `prompts/versions/manifest.json`.
- CP2 LLM-judged gating → deterministic-only gating (ADR-0040) — matches ADR-0040's own text
  exactly.

No new drift found beyond what the note already records. **No fix needed.**

**The PPTX:** superseded by the md + ADR-0043 (Accepted, "Layer 2 Feature Engineering
Architecture Freeze"). **Recommend: mark superseded/historical, do not re-edit.**

---

## 4. L3 — Automation Engineering (built, PPT+MD)

**The Markdown (`layer-3-automation-engineering-lld.md`):** same pattern as L2, same verdict.
Its Reviewer's note is unusually thorough — three superseded/corrected items (S1–S2, S7), four
locked pre-freeze decisions (Q1–Q4) with full rationale, and six explicitly underspecified items
(S3/S4/S6, deferred to freeze or implementation). ADR-0044 (Accepted) locks Q1–Q4 exactly as
recorded. The note is explicit that later build work (the page-object arc, class-collision fix,
CP7 rating-gating — baseline-v2 items 28–40) is **out of this document's scope by design**; it
governs the pre-freeze proposal, not ongoing implementation. Checked against baseline-v2: nothing
in the note is contradicted by subsequent build state. **No fix needed.**

**The PPTX:** superseded by the md + ADR-0044 (Accepted). Its own slide-23 task breakdown is
literally L2's task list pasted in verbatim — already caught and flagged as S2 in the md's own
Reviewer's note. **Recommend: mark superseded/historical, do not re-edit.**

---

## 5. L4 — Suite Quality Governance (built, MD-only — no PPT)

All three L4 documents follow the same disposition, more emphatically than L2/L3 — each was
**frozen into an Accepted ADR** (table in §0) and each pre-emptively resolves the exact kind of
ADR conflict this review looks for, inside its own text, before the review ever started:

- `layer-4-quality-governance-lld.md`'s **Finding 0** identifies, on its own, that the source
  deck's "CP5"/"CP6" labels collide with ADR-0040 Decision 3 and ADR-0044's already-Accepted
  assignments, states "the ADRs win," and defers renumbering to a future freeze — which
  ADR-0046 then did (CP5 kept for suite-integration governance; the deck's mislabeled content
  renumbered CP7/CP8).
- `layer-4-cp5-suite-integration-governance-design.md` designs exactly the four items ADR-0040
  Decision 3 names as CP5's remit, quoting the ADR as its own binding target.
- `layer-4-cp7-cp8-design.md` designs CP7/CP8 under ADR-0046 D8's naming, live-verifying the real
  Sonar Community Edition server before proposing anything (not assumed).

All three are now fully absorbed by ADR-0046 and ADR-0047 (both Accepted), which per
architecture-baseline-v2.md items 33–34 lock this design "in full." **No fix needed on any of the
three.**

No PPT to assess (never committed — documented, not a gap; see §1).

---

## 6. L5/L6/L7 — unbuilt layers (PPT-only, forward design)

All three decks share the same base-layer staleness: HP ALM and Azure OpenAI appear throughout
(L5's external-systems slide, L6's RCA engine, L7's dashboard adapters) — the same provider/source
pivot documented as stale for L1 (§2) applies here too, though with lower cost, since none of this
is built yet; whoever designs these layers will re-derive the real sources/provider at design
time regardless.

**A more consequential, ADR-specific conflict, distinct from L1's:** L5 and L6 both use a **CP7**
label for content unrelated to what CP7 now means. L5 slide 22 hands its output to "CP7 Failure
Analysis Layer"; L6 slide 15 defines its own "CP7 Validation Engine" (failure-lifecycle
validation). **ADR-0047 (Accepted) has since assigned CP7 to Layer 4's suite-wide Sonar
governance** — a different control point entirely. This is the same *kind* of mislabeling
Finding 0 caught and resolved for the L4 deck's CP5/CP6 (§5), but for L5/L6 it is **still live and
unresolved** — nothing has renumbered L5/L6's CP7 usage yet, because neither layer has reached a
review pass. **The ADR wins**; a future L5/L6 design pass needs the same renumbering treatment
L4's Finding 0 already modeled. L7's own aggregation slide (inputs: "CP5 Report," "CP6 Report,"
"CP7 Report" from "Quality Governance Layer" and "Failure Intelligence Layer" respectively)
inherits the same stale numbering by extension.

**Mentor-program intersections — both confirmed directly against `mentor-feedback-scoping.md`:**

- **L6 vs. the human-gate item (mentor item #6).** Confirmed via `stages.py` (`layer="L6"`,
  `governing_citation="none yet"`) and the scoping doc: "genuinely blocked on Layer 6... Genuinely
  not built — there is nothing today for this principle to gate." L6's deck (§ "Diagnose → Fix →
  Validate → Re-Execute," an "Auto Remediation Engine" that "applies eligible fixes"
  automatically) reads as more autonomous than the platform's own established pattern for AI-fix
  loops — ADR-0040's "bounded at 2 LLM attempts, then human-in-the-loop," with a real production
  instance on record (the Live Feature Remediator's one escalation, where the model claimed a fix
  it hadn't made and the platform's own tag-preservation check caught it). Mentor item #6's
  recommendation is **adopt-when-building-that-layer**: bake the human-gate principle in as a
  founding constraint of L6's own future architecture-freeze ADR, not retrofit it. This review
  concurs — flag, don't fix now.
- **L7 vs. BI-tools (mentor item #7).** Confirmed via `stages.py` (`layer="L7"`,
  `governing_citation="none yet"`) and the scoping doc: genuinely blocked on Layer 7, and further
  blocked on ADR-0036 §D5 (below) resolving first. Mentor item #7's own recommendation: resolve
  the D5 shape question before choosing a BI-tool integration shape, since the two decisions are
  coupled. This review concurs.
- **A third, ADR-native intersection not from the mentor docs:** ADR-0036 D5 records, as an
  explicitly open question, whether Layer 7 (Governance Dashboard) is really a per-run pipeline
  stage at all, or a separate continuously-running service reading completed runs —
  "not resolved... recorded as an open question in `docs/architecture/architecture-baseline-v2.md`."
  L7's own deck assumes the per-run pipeline-stage shape throughout (a stage in a `CP1–CP7`
  sequence). Whichever way D5 resolves will reshape more of L7's deck than the CP-numbering
  fix alone.
- **L5 vs. ADR-0039 (Jenkins, Proposed — not Accepted).** L5's deck assumes Jenkins as settled
  infrastructure throughout ("Jenkins Orchestrator," a component list built entirely around it).
  ADR-0039 (Execution Backend and CI/CD), which would ratify that choice, is explicitly
  **PROPOSED — NOT ACCEPTED**, with its own status line stating "no component may be built against
  this ADR until it is ratified." This isn't staleness so much as a live dependency: L5's design
  cannot be finalized ahead of ADR-0039's own ratification, which is itself a separate governance
  action.

**Recommendation:** all three remain forward-design inputs, worth keeping, but none should be
treated as ready-to-implement as written. **Defer** a full reconciliation pass on L6 and L7 until
their respective mentor items (#6, #7) and ADR-0036 D5 resolve — reconciling now risks a second
pass once those land. L5 additionally waits on ADR-0039's own ratification. The HP-ALM/Azure/CP7
staleness is cheap to note now (as this document does) but not worth a dedicated fix-the-deck task
before those blocking decisions land.

---

## 7. Out of scope, and why

`docs/proposals/` contains 13 other documents beyond the seven per-layer LLDs
(`capability-contract-standard-*`, `continuous-improvement-framework.md`,
`cross-source-consolidation-and-selection.md`, `evidence-grounding-and-traceability.md`,
`executable-specification-engineering.md`, `governance-review-lifecycle-*.md`,
`knowledge-graph-framework.md`, `learning-framework.md`, `organizational-memory-framework.md`,
`quality-governance-framework.md`, `recommendation-framework.md`,
`repository-governance-reorganization-proposal.md`, `requirement-enhancement-framework.md`).
These are cross-cutting Layer-1-sub-capability proposals (CAP-08x arcs, governed by ADR-0021–0030
and others), not per-layer pipeline LLDs, and the task brief scoped this review to "ALL the layer
LLDs" — read as the L1–L7 pipeline set. Flagged here, not reviewed, since the brief's own
per-layer structure (built-vs-code, unbuilt-vs-ADR) doesn't map cleanly onto them; several already
carry their own "Runtime Integration"-stamped currency per their most recent commits (e.g.
`continuous-improvement-framework.md`'s 2026-07-15 "CAP-083C — Continuous Improvement Runtime
Integration" tag) and would need a differently-shaped review.

`stages.py`'s `governing_citation="none yet"` label on L4 itself (stage 16) — noticed while
confirming build state, not part of this review's LLD scope, but worth a one-line follow-up since
L4 is in fact built and governed by ADR-0040/0044/0045/0046/0047; the field just doesn't cite any
of them.

---

## 8. Synthesis — disposition groups

**(a) L2–L4 markdown needing a code-alignment fix:** **none.** Contrary to the task brief's
working hypothesis, all five L2/L3/L4 markdown documents remain accurate as point-in-time
transcription-plus-review records; their own Reviewer's notes already did the staleness-flagging
work, and each has since been absorbed by an Accepted freeze ADR (ADR-0043/0044/0046/0047).

**(b) L1 — the gap.** Recommend **creating** a markdown LLD describing L1 as-built (mirroring the
L2/L3/L4 transcription-plus-Reviewer's-note pattern, or a direct from-code description — the
latter is more honest given how little of the existing deck survives contact with the real code).
Do not re-edit the stale PPTX. **Timing: lean create-with-#3** (the corpus-completeness mentor
item, which may reshape what L1 owns), not create-now — see §2 for the full reasoning and the
override condition if the user wants a stopgap sooner.

**(c) Built-layer PPTs (L1–L3; L4 has none).** All superseded by their respective markdown +
freeze ADR (L1's markdown doesn't exist yet, but once created, its PPT is superseded the same
way). **Recommend: mark as historical/superseded via a short note, not slide-by-slide re-editing**
— consistent with how L2/L3's own PPTs are already treated (kept as committed provenance,
untouched, with the md carrying the current record).

**(d) Unbuilt-layer PPTs (L5, L6, L7).** Forward design, worth keeping, not ready to implement as
written. Base-layer staleness (HP ALM, Azure OpenAI, stale CP7 labeling) is cheap to note (done in
§6) but not worth a dedicated fix task. **Defer** full reconciliation: L6 on mentor item #6 +
its own future architecture-freeze ADR; L7 on mentor item #7 + ADR-0036 D5; L5 on ADR-0039's own
ratification.

**(e) Mostly-accurate, leave as-is:** L2 md, L3 md, all three L4 md documents.

---

## 9. Suggested sequence (a recommendation, not a lock)

1. **Now, cheap:** none — there is no drifted L2–L4 markdown to fix. (This step existed in the
   original brief's hypothesis; this review found it empty.)
2. **L1:** decide create-now vs. create-with-#3. This review's lean is **create-with-#3**, since
   item #3 is already scoped as a design-task that may reshape L1, and writing L1's as-built
   record twice is worse than writing it once, correctly, after #3 resolves.
3. **Mark L1–L3's PPTs (and L1's future markdown once written) as historical/superseded** — a
   short note per file, not a rewrite. Low cost, can happen independently of (2).
4. **Defer L5/L6/L7** reconciliation until their respective blocking decisions land (ADR-0039
   ratification for L5; mentor item #6 + a future freeze ADR for L6; mentor item #7 + ADR-0036 D5
   for L7).
5. **Optional, low-priority, out of this review's own scope:** fix `stages.py`'s
   `governing_citation="none yet"` label on the L4 stage entry (§7).

---

## 10. Confirmation

Review only. No LLD, code, ADR, or register file was edited or created by this task, other than
this findings document itself. `make lint` and `make test` (5736 passed) were re-confirmed green
before this document was written and were not re-run after (no code changed). Anything beyond
scope is listed in §7 and was not reviewed in depth.
