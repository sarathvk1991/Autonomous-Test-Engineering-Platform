# ADR-0051 — Generation Quality Eval Harness (Layer 1: Deterministic Property Checks)

- **Status:** Accepted (Layer 1, three of seven target generators —
  `LiveStepDefinitionGenerator`, `LiveFeatureContentGenerator`, and `LiveTestDataGenerator` — see
  the "Implementation Note" sections, below; the remaining four generators and the judge layer,
  D5, remain future, separate work). **All three of ADR-0050's own measured/cached token sinks
  now have quality-drift eval coverage** (step-def, feature-content, test-data).
- **Date:** 2026-08-17
- **Supersedes:** nothing. **Amends:** nothing.
- **Governing design:** none — this ADR *is* the governing design. It records the decisions
  reached by a design-surfacing task (`docs/architecture/mentor-feedback-scoping.md`, Item 1's
  eval-harness sub-item, "EVAL HARNESS DESIGN SURFACED," 2026-08-17) rather than a preceding
  `docs/proposals/*.md` document — the surfacing note itself served that role, read in full before
  this ADR was written. This ADR is written **before** any code, fixture, or CI wiring exists —
  ADR-first, matching this platform's standing discipline (ADR-0050's own precedent), explicitly
  **not** the traceability graph's build-then-ADR inversion (ADR-0048 D5, itself named as
  governance debt it closed after the fact).
- **Depends on:** `requirement_intelligence/llm/generation_identity.py` (`GenerationIdentity` —
  the prompt/model identity this ADR's eval-score key reuses verbatim; additive infra, not itself
  ADR'd); ADR-0044 (Layer 3 Automation Engineering Architecture Freeze — governs the four L3
  generator Protocols this harness's first layer targets); ADR-0043 (Layer 2 Feature Engineering
  Architecture Freeze — governs `FeatureContentGenerator`, a future eval-set target); ADR-0048
  (Traceability Graph — `CompletenessReport`, consumed by this harness's coverage-shaped property
  checks, D3, never extended); ADR-0050 (Artifact-Level Generation Cache — sibling precedent for a
  new, focused, ADR-first capability, and the module this harness's own scorecard store shape
  mirrors, D2).
- **Runtime status: Built and tested (Layer 1, three of seven target generators — see the
  "Implementation Note" sections, below).** `eval_harness/` exists: a curated eval set,
  deterministic property checks, scoring/aggregation, CAP-088 coverage consumption, and a
  regression-gated baseline store — for `LiveStepDefinitionGenerator` (first increment),
  `LiveFeatureContentGenerator` (second increment, 2026-08-20), and `LiveTestDataGenerator` (third
  increment, 2026-08-20). **Not CI-wired and not live-wired.** No CI job, no `PlatformContext`
  composition-root method, and no live LLM call anywhere in this package's own test suite — every
  proof runs against a Stub generator seeded with captured/fixture text (D2's own "live-vs-cached"
  open question is left exactly as open as this ADR named it; this build resolves only the eval
  *logic*, deterministically). The remaining four generators and the judge layer (D5) are
  untouched.

## Problem

Nitin's mentor feedback (one mentor throughout) asked for an eval harness: treat every skill/agent
as a software component with its own curated eval set (expected outputs or rubrics), a score
tracked over time, so that a change to a model, prompt, or framework that causes silent quality
drift is caught in CI before it is adopted — not discovered later, by accident, in production. His
own example, healthcare-specific: a model swap that silently starts missing allergy validation or
insurance-eligibility rules should be caught by CI, not by a person noticing downstream. He is
explicit that this is additive to, not a replacement for, structural regression testing — this
platform already has that half (`tests/productization/test_golden_baseline.py`, CAP-070).

The design-surfacing task this ADR follows read the real evidence, rather than assuming a gap
exists where none does. **The reframe, and this ADR's centerpiece:** the platform already
*detects* the shape of defect that actually occurred this arc. The real, measured
`gemini-2.5-flash` 76%-defect-rate regression (`docs/architecture/mentor-feedback-scoping.md`,
Item 1, citing the live-regen corpus) consisted of three defects — a wrong Cucumber import
package, a markdown code fence violating an explicit no-markdown contract, and a fabricated
duplicate page-object class — every one of which is deterministically checkable, and largely
already caught, live, by `suite_quality_governance/cp5/` (`compile_check.py`'s
`LiveCompileChecker`, a real `mvn clean test-compile`; `near_duplicate_sweep.py`). **The gap was
never detection capability.** The gap was that this detection ran exactly once, manually, ad hoc,
by a human reading a live-regen transcript after the model swap had already shipped — not as a
curated, versioned, CI-gated eval set with a score tracked over time, run automatically the moment
`STEP_DEF_GEMINI_MODEL` changed, before that change was adopted. CP5 gates whether one *run's*
generated suite coheres; nothing scores whether one *generator*, at a given prompt/model identity,
still produces the quality it did before — across changes, over time. That distinction is the gap
this ADR closes the first layer of.

Two prerequisites now exist that did not exist when Nitin's clarification was first recorded:
`GenerationIdentity` (pinning, built) supplies the exact per-component key an eval score needs to
be comparable across model/prompt versions; and the traceability graph (CAP-088, built) supplies a
deterministic coverage signal this harness's property-check layer can consume rather than
re-derive. Building an eval harness on top of them, unexamined, without first separating what is
genuinely new (curated, scored, CI-gated *discipline*) from what already exists (deterministic
*detection*, via CP5) would risk duplicating CP5 under a new name, or reaching immediately for an
LLM-judge where a cheaper, more stable mechanism already proves sufficient for the one real defect
on record. This ADR exists to record that separation, and the resulting scope, before any of it is
built.

## Decision

Introduce a new, governed subsystem, **the Generation Quality Eval Harness**
(`eval_harness/`), scoring individual LLM-driven generators — Nitin's "skills/agents," concretely
the seven Protocol-bound generation call sites across L1–L3 — against curated eval sets, on a
tracked score, gating CI. Five decisions, each detailed below:

1. **The reframe** — the eval harness is standing *discipline* around detection this platform
   mostly already has (CP5-class deterministic checks), not a new detection mechanism; it curates,
   versions, scores, and CI-gates what today runs once, manually, ad hoc (D1, the centerpiece).
2. **Layer 1: deterministic property/assertion checks**, scored per generator, keyed by
   `GenerationIdentity`, CI-gated on regression — the only layer this ADR decides to build (D2).
3. **The defect-shape taxonomy** — which layer catches what, and why the boundaries are drawn
   where they are: structural defects → Layer 1 (this ADR); coverage omissions → the existing
   traceability graph, consumed not extended; silently-wrong-logic → a rubric/judge layer,
   explicitly deferred, not designed here (D3).
4. **Relationship to existing subsystems** — a new capability alongside CP5, the golden-baseline
   harness (CAP-070), and the traceability graph (CAP-088), not a duplicate or extension of any of
   them (D4).
5. **Scope and sequence** — one generator's eval set, Layer 1 only, measured, before any
   extension; the judge layer is named as deferred future scope, not designed (D5).

---

## D1 — The reframe (the centerpiece decision)

**Nitin's ask, restated precisely:** curated eval sets, expected outputs or rubrics, a score
tracked over time, CI catches drift before adoption. **What the surfacing found, checked against
real code and a real historical defect, not assumed:** the detection half of this ask is
substantially already built. `suite_quality_governance/cp5/compile_check.py`'s `LiveCompileChecker`
runs a real `mvn clean test-compile` against the generated suite; `cohesion.py`'s
`no_ambiguous_glue`, `near_duplicate_sweep.py`, and `orphaned_glue.py` are further deterministic
structural checks, all live-wired into stage 16 today. The real `gemini-2.5-flash` regression this
arc measured (`docs/architecture/mentor-feedback-scoping.md`, Item 1) — wrong import package,
markdown fencing, a fabricated duplicate class — is exactly the class of defect a compile check and
a duplicate-class sweep already catch. Re-running that same corpus through this platform's own
existing CP5 machinery today would have failed it, loudly, deterministically, before a human ever
had to read the generated Java by hand.

**What is genuinely missing is not a checker — it is a standing, curated, scored, CI-wired
*harness* around checkers this platform already runs at the wrong scope and cadence.** CP5 answers
"does this run's generated suite, as a whole, cohere" — evaluated once, after a full corpus
generation, gating promotion of that run's own output. It does not answer "has
`LiveStepDefinitionGenerator`'s output quality, specifically, changed since the last time I trusted
it" — a question that needs a *curated, representative, small* set of generation cases (not a full
corpus), a *score* comparable across `GenerationIdentity` values (not a single pass/fail for one
run), and a place in CI that runs *before* a model or prompt change is adopted (not after a full
live regeneration has already been paid for). This ADR's Layer 1 is precisely that missing
scaffolding, built to reuse CP5-class checks as its grading mechanism wherever they already exist,
rather than re-implementing detection this platform has already proven.

**Why this reframing matters, concretely, for scope:** it means this ADR does not need to invent
new defect-detection logic for the one real defect class on record — it needs to *curate* a small
eval set of generation contexts, *wrap* CP5-class and generator-specific property checks as scored
assertions, *key* the resulting score by `GenerationIdentity`, and *gate* CI on a regression. Each
of those four is genuinely new; none of them requires a new way of recognizing a bad step-definition
that CP5 does not already recognize.

## D2 — Layer 1: the deterministic property-check design (the only layer this ADR builds)

**Curated eval set.** Per generator, a small (10–20 case), versioned, hand-labeled fixture of real
generation contexts — not full expected output text (rejected, D2 below explains why), but the
generator's real input context paired with the set of named properties that context's output must
satisfy. Seeded from real, already-produced, human-verified material this arc already generated —
the 33-step-def/32-page-object live-regen corpus
(`docs/architecture/mentor-feedback-scoping.md`'s own citations of the live-regen findings) — not
invented from scratch. Versioned independently per generator, the same shape the golden dataset
(`GOLDEN_DATASET_VERSION`) already establishes for structural regression, so the eval set can grow
additively without an ADR amendment for ordinary curation.

**Why not expected-output text (rejected as the primary mechanism).** ADR-0050 D1's own residual
risk, already documented by this platform about itself: hosted-model APIs do not guarantee
bit-identical output across calls even at `temperature=0.0`. An exact golden-text comparison would
false-fail on every regrade with zero real regression — the opposite of CI-stable. Approximate
similarity matching pushes the same instability down one level (what threshold, scored how) without
reliably catching the real defects on record, which were small, discrete, structural faults a
similarity score could easily average away as "close enough."

**Grading: deterministic property/assertion checks, not a judge.** Each check is a pure function
over `(generated_text, context)` returning pass/fail plus a reason — no LLM call, no run-level
state, no similarity threshold. For `LiveStepDefinitionGenerator`, the first target (D5): a valid
Cucumber import package, no markdown code fence (mirroring the no-markdown contract the prompt
already states), no fabricated/duplicate class declared inline where an external reference was
expected, and a reference only to page-object/utility methods actually declared in the target
interface supplied to the generator. Each of these is either a direct reuse of an existing CP5-class
check (compile, near-duplicate) or a small, new, equally deterministic string/AST check of the same
shape — no new category of mechanism, per D1.

**Scoring and key.** A run of the eval set against one generator at one `GenerationIdentity`
(`prompt_id`/`prompt_version`/`prompt_sha256`/`provider`/`model`) produces a pass/fail per case and
an aggregate pass rate, persisted as an eval-run record keyed by `(generator_id, GenerationIdentity,
eval_set_version)`. Store shape mirrors ADR-0050 D2's own precedent (`atomic_write.py`'s durable
writer; an append-only per-generator history, not a content-addressed cache — the store here exists
to keep history for comparison, the opposite goal of the cache's dedup-and-discard shape, so the
pattern is reused, the store is not).

**CI gate.** Regression-relative, not an absolute score threshold: a candidate `GenerationIdentity`
(a prompt or model change under review) is compared against the last-recorded baseline score for the
generator's current production identity; any case that newly fails, or an aggregate pass-rate drop,
fails CI. An absolute threshold is deliberately rejected — this document's own "pass-bias
meaning-check" caution (Item 1, above) already flags the risk of a numeric bar quietly meaning less
than it appears to; a regression comparison against a known-good baseline avoids inventing a new
magic number.

**Open, unresolved design question, named, not answered here.** Whether CI executes a real, live LLM
call against each eval case on every run (cost/quota-bound — `[[cap-compile-gap-closed]]`'s own
measured finding that `gemini-2.5-flash`'s free tier caps at 20 requests/day is a real, already-
observed constraint on exactly this idea) or replays a pinned, cached response set (reusing the
generation cache itself, ADR-0050, as the harness's own input-replay mechanism) determines whether
this gate runs on every PR or on a scheduled/gated cadence. Left to the implementation milestone, not
decided here.

## D3 — The defect-shape taxonomy: what Layer 1 catches, what is deferred, and why

| Defect shape | Example | Catching mechanism | Status |
| --- | --- | --- | --- |
| **Structural** — the artifact is malformed relative to a checkable, nameable rule | Wrong import package, markdown fence, fabricated duplicate class (the real `gemini-2.5-flash` defects) | Deterministic property/assertion checks, largely reusing CP5-class checks | **Layer 1 — this ADR, decided and scoped for build** |
| **Coverage omission** — a required thing (an AC, a scenario) has no corresponding generated artifact at all | An acceptance criterion with no generated step covering it | The traceability graph's `CompletenessReport` (CAP-088, ADR-0048) | **Consumed, not extended.** Layer 1's property-check runner queries `CompletenessReport` as one more deterministic check; no new coverage-computation logic is built by this ADR. |
| **Silently-wrong-logic** — the artifact is structurally clean and nominally covers the right thing, but implements it incorrectly | A generated step that validates the wrong field, or a model that silently drops an allergy-validation rule the AC still nominally covers | No deterministic check can see this without a rubric of "correct" | **Deferred — a future Layer 2 (rubric/LLM-judge), not designed by this ADR (D5).** |

Nitin's own motivating example (a model silently missing allergy validation or insurance
eligibility) does not map cleanly onto one row. If the omission manifests as a coverage gap — the
governing acceptance criterion ends up with no generated scenario or step at all — row 2 already
catches it deterministically, today, via CAP-088, with no new logic. If instead the criterion is
nominally covered but the generated logic implements it incorrectly, only row 3 — deferred — could
catch it. This ADR does not overclaim: Layer 1 covers the real historical defect (row 1) and the
coverage-shaped half of the hypothetical one (row 2, by composition, not new work); it does not
close row 3.

## D4 — Relationship to existing subsystems: new capability, not a duplicate

- **`suite_quality_governance/cp5/` (CP5).** Gates whether one run's *entire generated suite*
  coheres (compiles, no ambiguous glue, no near-duplicates), evaluated once per run, as a promotion
  gate. This harness scores whether one *generator*, at one identity, still produces the quality it
  used to, across changes, over time — a different axis (per-component drift vs. per-run
  cohesion), not a duplicate. Layer 1 reuses CP5's *check logic* as grading material wherever
  directly applicable; it does not reimplement or replace CP5's own run-gating role.
- **The golden-baseline structural harness (CAP-070, `docs/productization/golden-baseline.md`).**
  Its own document states its boundary explicitly: *"It deliberately does not validate prompt
  quality: the LLM response is a fixed, deterministic stub."* Its §12 ownership table freezes it to
  architecture/determinism verification, explicitly excluding prompt/generation quality — extending
  it to grade real generated output would violate its own frozen governance contract (§13), not
  merely be inconvenient. This harness is CAP-070's quality-grading peer, not its replacement or
  extension.
- **The traceability graph (CAP-088, ADR-0048).** Consumed for coverage-shaped property checks
  (D3, row 2), read-only, through its existing `CompletenessReport` output. No change to
  `traceability_graph/`'s own scope, models, or pipeline is made or proposed by this ADR.

## D5 — Scope and sequence: one generator, Layer 1 only, measured before extending; the judge layer deferred

**First build** (a future, separate milestone; not this ADR): the curated eval set (D2) + the
property-check runner (D2) + the score store (D2) + CI wiring, targeting
**`LiveStepDefinitionGenerator`** only — the same generator ADR-0050's own first cache increment
picked (highest recent iteration/defect volume this arc, and the most measurement infrastructure
already wrapped around it: `GenerationIdentity`, token-usage recording, and
`CachingStepDefinitionGenerator` all already instrument this exact class), and, concretely, the
literal generator where the real, traced `gemini-2.5-flash` defect occurred. Measured, scores-first
within this ADR-first capability, the same discipline ADR-0050 D5 established: build against the
curated set, confirm the score correctly regresses on a reintroduction of the known defect (a
negative-control check), before extending to any other generator.

**Explicitly excluded from this ADR's decided scope, named as deferred future work, each with its
own trigger, not designed here:**

- **The remaining six generators' eval sets** (`LivePageObjectGenerator`, `LiveUtilityGenerator`,
  `LiveTestDataGenerator`, `LiveFeatureContentGenerator`, `LiveFeatureRemediator`,
  `RequirementAnalysisService`). Same pattern, applied once step-def's own build proves the
  mechanism — an extension, not a redesign, mirroring exactly how ADR-0050's cache extended from one
  generator to three by repeating its own pattern.
- **The rubric/LLM-judge layer (Layer 2), for silently-wrong-logic (D3, row 3).** Named as future
  scope, not designed here — it is speculative relative to what this ADR can decide with confidence
  today. Open questions, named, not resolved: which model serves as judge, and how is *its own*
  version pinned (the same `GenerationIdentity`-shaped discipline this ADR relies on for Layer 1
  would need to apply recursively to the judge, or the judge becomes a second, unpinned source of the
  exact silent-drift risk this whole harness exists to catch); what is the rubric, and who authors
  and maintains it; what is the judge's own false-positive/false-negative rate, and how would that be
  calibrated without another eval harness one level up; and what is the cost model for a second LLM
  call per graded artifact, at what cadence. None of these are decided by this ADR. Layer 2 is
  recorded as a real, additive, later capability — not rejected, not designed, not scheduled.
- **Rubric grading generally**, including human-scored rubrics (not CI-automatable by construction;
  useful for periodic audit, not a CI gate).

---

## Implementation Note (2026-08-17) — D5's first increment: `LiveStepDefinitionGenerator`, built and tested

The first build D5 names (curated eval set + deterministic property checks + scoring + the
regression-gated baseline store, one generator, measured) was built the same day this ADR was
written. This note records what was actually verified — the decisions above stay decisions; this
is the separate record of what now backs them.

**Built:** a new top-level package, `eval_harness/` (`models.py`, `step_definition_properties.py`,
`step_definition_eval_set.py`, `scoring.py`, `coverage.py`, `baseline_store.py`, `runner.py`), for
`LiveStepDefinitionGenerator` only.

- **The curated eval set (D2).** `STEP_DEFINITION_EVAL_SET` (`step_definition_eval_set.py`),
  independently versioned (`STEP_DEFINITION_EVAL_SET_VERSION`, mirroring `GOLDEN_DATASET_VERSION`'s
  own convention) — three cases seeded directly from the real, currently-tracked, currently-
  compiling `test-suite-baseline/src/test/java/com/automation/steps/LoginSteps.java` (the same
  corpus `[[cap-compile-gap-closed]]`'s real `gemini-2.5-flash` measurement regenerated and found
  76% defective), plus one case with no page-object interface expected, to exercise the
  `NOT_APPLICABLE` path deliberately, not by accident.
- **The deterministic property checks (D2/D3, composed not invented).** `step_definition_
  properties.py`: `check_valid_cucumber_import`, `check_no_markdown_fence`, `check_no_fabricated_
  page_object_class` — one check per real defect shape (`[[cap-compile-gap-closed]]`'s wrong-import,
  markdown-fence, and fabricated-duplicate-class findings, respectively). Each returns `PASSED`,
  `FAILED`, or `NOT_APPLICABLE` (never a vacuous pass when nothing is checkable).
- **Scoring, keyed by `GenerationIdentity` (D2).** `scoring.py`'s `score_case`/`score_eval_set`;
  `models.py`'s `EvalScore` carries `total_checks_applicable`/`total_checks_passed`/`pass_rate`,
  each enforced consistent with its own `case_results` by a `model_validator` (mirroring
  `BindingCompletenessReport._counts_are_consistent`'s own discipline) — a score can never claim an
  arithmetic it did not actually compute.
- **The coverage-shaped check, consumed not extended (D3/D4).** `coverage.py`'s
  `check_step_covered` — a single dictionary lookup against an already-computed CAP-088
  `BindingCompletenessReport.unbound_steps`; proven, by its own test, never to re-derive binding
  completeness itself. Optional, composable, not part of the default check set (the curated,
  isolated eval cases have no real traceability graph to consult by default — D3's own scoping).
- **The regression gate, relative not absolute (D2, the pass-bias-trap avoidance).**
  `baseline_store.py`'s `EvalBaselineStore`/`check_regression` — reuses
  `requirement_intelligence.run_state.atomic_write` verbatim (ADR-0050 D2's own precedent), one
  current baseline `EvalScore` per `generator_id`, explicitly recorded, never auto-promoted. Three
  outcomes: `ESTABLISHED_BASELINE` (no prior baseline — this run IS the measurement), `REGRESSED`
  (candidate pass rate below the baseline's), `PASSED` (stable or improved) — no absolute score
  threshold anywhere in this module.
- **The runner (D5).** `runner.py`'s `run_step_definition_eval` — takes any `StepDefinitionGenerator`
  (Protocol-typed, agnostic to live/stub/cached) plus a caller-supplied `GenerationIdentity`, runs
  the curated set through it, scores the result.

**Proven two ways, both deterministic, no live LLM call anywhere in this package's own test
suite (34 new tests):**

1. **Each property check catches its own real defect shape and passes the real clean corpus text**
   (`test_eval_harness_step_definition_properties.py`) — `check_valid_cucumber_import` against a
   mutation reproducing the real `io.cucumber.java.When` (missing `.en.`) defect; `check_no_
   markdown_fence` against a fenced wrapper; `check_no_fabricated_page_object_class` against an
   inline duplicate `LoginPage` class replacing the real import — all three FAIL on their own
   defect and PASS on the real, unmodified `LoginSteps.java` text.
2. **The full arc — scores-first baseline establishment, then regression detection — end to end**
   (`test_eval_harness_runner.py`), driven entirely by `StubStepDefinitionGenerator` seeded with
   captured/fixture Java text: a clean generator's first run against the curated set has no prior
   baseline (`ESTABLISHED_BASELINE`, not a pass or a fail) and is explicitly recorded as one; a
   second generator standing in for a worse model (the real defect-1 shape reintroduced into every
   case, `_worse_model_java_by_step_text`) is caught (`REGRESSED`) relative to that recorded
   baseline; re-running the same clean generator does not regress (`PASSED`). The regression gate's
   own relativity, not an absolute bar, is proven directly
   (`test_eval_harness_baseline_store.py::TestCheckRegressionIsRelativeNotAbsolute`): a 25%
   baseline compared against a 25% candidate PASSES, and a 100% baseline compared against a 75%
   candidate REGRESSES — either assertion would be reversed under an absolute-threshold gate
   calibrated at any single cutoff, which is exactly the pass-bias-trap D2 named as the reason to
   reject one.

**Scope held exactly as D5 decided.** Only `LiveStepDefinitionGenerator`'s Layer 1 is built. The
remaining six generators' eval sets, the judge layer (D5), rubric grading, and any CI/live wiring
are all untouched by this increment — extending to them, or wiring this into CI, is the next,
separate step D5 already named, not performed here.

Gate: `make lint` clean; `make test` 5925 passed (5891 + 34 new, itemized above); `mypy`:
whole-repo error count unchanged (436, confirmed by `git stash -u` before/after) — the new package
(`eval_harness/`) is itself zero-error under `mypy strict`; the one transient new-code error
surfaced mid-build (a missing return-type annotation on a test helper) was fixed before this count,
not carried forward. Tree: 8 new files under `eval_harness/`, 5 new test files, this ADR amended
further.

---

## Implementation Note (2026-08-20) — D5's second increment: `LiveFeatureContentGenerator`, built and tested

Extends D5's own named next step ("apply the same pattern... once step-def's own build proves the
mechanism") to the second target generator — the one D5 itself named as the biggest measured
token sink (45.4% of one real distribution, `[[cap-artifact-cache-second-increment-built]]`) and
already cache-wrapped (`CachingFeatureContentGenerator`, ADR-0050). One mentor throughout (Nitin).

**Pre-flight.** Clean tree, `main`, tip `40d7942` (the ADR-0049 stale-line fix). `make lint`/`make
test` clean, 5925 unchanged.

**Feature-content's OWN defect shapes established first — not copied from step-def's.**
Feature-content generates raw Gherkin scenario/background text (`LiveFeatureContentGenerator`),
not Java, governed by a different, already-real contract:
`feature_engineering.generation.assembler.generate_feature_file` already deterministically
validates the generator's raw output against six real properties, live, today, before assembly is
ever attempted — raising `FeatureGenerationError` the instant one is violated. Unlike step-def,
there is **no known real historical feature-content defect on record**: the live E2E corpus run
scored 15/15 features clean, 0 escalations (`[[cap-stage14-live-cli-wiring]]`) — these checks are
grounded in the real, already-enforced CONTRACT (`assembler.py` + the governed `generate_feature`
v1.1.0 prompt's own explicit OUTPUT CONTRACT clause forbidding a markdown fence), not a real
historical INCIDENT the way step-def's three checks were.

**One real `assembler.py` validation block investigated and deliberately NOT ported, verified not
assumed.** `assembler.py` also raises when a `Background:` block carries tags. Checked directly
against the real parser (`feature_engineering.gherkin_lint.source.parse_source_text`): a tag
placed immediately before `Background:` is a hard Gherkin **parse error** under the real Cucumber
grammar this platform's own lint port uses — never a valid-but-tagged AST node. That defect shape
is therefore already fully subsumed by `check_valid_gherkin_structure`; porting a separate
tagged-Background check would report a `FAILED` outcome no real input could ever trigger. Left out
on that verified basis, not merely skipped for scope.

**Built:** `eval_harness/feature_content_eval_set.py`, `feature_content_properties.py`,
`feature_content_coverage.py`, `feature_content_runner.py` — reusing `models.py`, `scoring.py`'s
`score_eval_set`, and `baseline_store.py` verbatim, generator-agnostic exactly as D2 designed them
(no changes to any of the three).

- **The curated eval set (D2).** `FEATURE_CONTENT_EVAL_SET` (independently versioned,
  `FEATURE_CONTENT_EVAL_SET_VERSION`) — three cases seeded from three real, currently-tracked
  requirements in `output/latest/testable_requirement_set.json`, the same 20-requirement corpus
  the real, live-regenerated `.feature` files under
  `output/executions/run-20260812T064317663150Z-a20b0cc2/.../features/` were generated from. Every
  real requirement in this corpus carries exactly one acceptance criterion and no
  common-to-every-scenario steps — a real, honest fact about the corpus, not a simplification made
  here.
- **Six deterministic property checks (D2/D3, composed not invented).**
  `feature_content_properties.py`: `check_no_req_tag`, `check_no_markdown_fence`,
  `check_valid_gherkin_structure`, `check_scn_pending_tag_count`, `check_ac_tag_presence`,
  `check_no_unknown_ac_tag` — each a direct, decomposed port of one real `generate_feature_file`
  validation block (five) or the governed prompt's own no-markdown-fence clause (one). Each
  returns `PASSED`, `FAILED`, or `NOT_APPLICABLE`.
- **Scoring, keyed by `GenerationIdentity` (D2).** Reuses `eval_harness.scoring.score_eval_set`
  verbatim — no new scoring logic; `feature_content_runner.py` builds each case's `CaseResult`
  directly from `run_property_checks`, the same one-line composition `scoring.score_case` performs
  for step-def, against a different check set and context type (`TestableRequirement`, not
  `StepDefinitionGenerationContext`).
- **The coverage-shaped check, consumed not extended (D3/D4).**
  `feature_content_coverage.py`'s `check_requirement_covered` — a single dictionary lookup against
  an already-computed CAP-088 `CompletenessReport.untested_requirements`; the same graph
  `check_step_covered` (step-def) consumes, one node level up (REQUIREMENT, not STEP). Optional,
  composable, not part of the default check set — identical reasoning to step-def's own coverage
  check.
- **The regression gate, reused verbatim (D2).** `EvalBaselineStore`/`check_regression` — no
  changes; `generator_id="feature_content_generation"` (`LiveFeatureContentGenerator.CALL_TYPE`)
  stores to its own separate file, no collision with step-def's baseline.
- **The runner (D5).** `feature_content_runner.py`'s `run_feature_content_eval` — takes any
  `FeatureContentGenerator` (Protocol-typed, agnostic to live/stub/cached) plus a caller-supplied
  `GenerationIdentity`, mirroring `run_step_definition_eval`'s own shape exactly.

**Proven two ways, both deterministic, no live LLM call anywhere in this package's own test suite
(32 new tests):**

1. **Each property check catches its own real defect shape and passes the real, reconstructed
   clean corpus text** (`test_eval_harness_feature_content_properties.py`) — the "clean" fixtures
   are reconstructed directly from the real, live-regenerated assembled `.feature` files (tags
   un-hoisted, the real minted `@SCN-*` id replaced with the one true `@SCN-PENDING` placeholder,
   the Feature:/comment lines stripped) — the raw shape the generator itself would have returned.
   All six checks FAIL on a fixture reproducing their own real defect shape and PASS on the clean
   text; `check_valid_gherkin_structure` is also proven to catch the verified-unreachable
   tagged-Background shape directly, since it is what actually fires for that input.
2. **The full arc — scores-first baseline establishment, then regression detection — end to end**
   (`test_eval_harness_feature_content_runner.py`), driven by `StubFeatureContentGenerator` seeded
   with the reconstructed clean text: a clean generator's first run has no prior baseline
   (`ESTABLISHED_BASELINE`) and is explicitly recorded as one; a generator standing in for a worse
   model (a stray `@REQ-*` tag — the prompt's single most explicitly, unconditionally forbidden
   defect shape — reintroduced into every case, since no real historical feature-content defect
   exists to replay) is caught (`REGRESSED`) relative to that baseline; re-running the same clean
   generator does not regress (`PASSED`).

**Scope held exactly as D5 decided.** Two of seven target generators (`LiveStepDefinitionGenerator`,
`LiveFeatureContentGenerator`) are built. The remaining five generators' eval sets, the judge layer
(D5), rubric grading, and any CI/live wiring are all untouched by this increment.

Gate: `make lint` clean; `make test` 5957 passed (5925 + 32 new, itemized above); `mypy`:
whole-repo error count unchanged (436, confirmed) — the seven new/changed files are themselves
zero-error under `mypy strict`. Tree: 4 new files under `eval_harness/`, 3 new test files, this ADR
amended further.

---

## Implementation Note (2026-08-20) — D5's third increment: `LiveTestDataGenerator`, built and tested

Extends D5's own "same pattern, applied once step-def's own build proves the mechanism" claim to a
THIRD generator — the other ~43% measured token sink (`[[cap-artifact-cache-third-increment-built]]`),
already cache-wrapped (`CachingTestDataGenerator`, ADR-0050). **Completes eval coverage of all
THREE of ADR-0050's own measured/cached token sinks** (step-def, feature-content, test-data). One
mentor throughout (Nitin).

**Pre-flight.** Clean tree, `main`, tip `2107cfe` (the feature-content eval increment). `make
lint`/`make test` clean, 5957 unchanged.

**Test-data's OWN defect shapes established first — a THIRD artifact type, not copied from either
prior increment's checks.** `LiveTestDataGenerator` produces Java source (like step-def), but
governed by a different real contract: ADR-0037 D3's SUT-binding boundary (a test-data class is
the DATA side of the platform's SUT binding, never the environment side), not Cucumber's
annotation grammar. **Grounding basis, checked directly, not assumed — mixed, stronger than
feature-content's:**

- **Two checks compose ALREADY-REAL, ALREADY-ENFORCED mechanisms** — the strongest grounding
  found in this arc yet. `check_no_env_binding` ports `automation_engineering.generation.
  test_data_orchestrator._check_no_env_binding`'s own regex verbatim: a live, ALWAYS-ON,
  orchestration-level guard that `generate_test_data_class` runs on every generator's output
  (stub or live) today, raising `TestDataBoundaryError` before ever returning a result — not a
  design aspiration, a real production check. `check_no_long_method` calls CP3's real, PUBLIC
  `evaluate_long_method` (`automation_engineering.cp3.architecture`) directly — no port needed,
  since it is already a pure, in-memory, no-subprocess function — and `customqa:long-method`
  applies to "ANY generated class... no class-role restriction" (that module's own docstring),
  test-data included.
- **Three checks are contract-grounded, no known incident** (like feature-content) —
  `check_no_markdown_fence`, `check_class_name_matches`, `check_no_webdriver_reference`, each
  ported from the governed `generate_test_data` v1.0.0 prompt's own explicit OUTPUT
  CONTRACT/CONSTRAINTS text. No real historical test-data defect exists on record.
- **A real, deeper gap found and closed, not merely a missing incident.** CP3's own
  `direct_webdriver_action` criterion explicitly EXCLUDES test-data's package from evaluation
  (`architecture.py`'s own comment: "page objects, utilities, test data... not evaluated by this
  criterion at all"). `check_no_webdriver_reference` is therefore the FIRST deterministic
  enforcement of that specific prompt constraint anywhere in this platform — not a duplicate of an
  existing check, a genuinely new one closing a real, previously-unenforced gap.

**One check considered and NOT built, reported honestly (mirrors feature-content's own
tagged-Background finding, generalized).** "One static member per required (field_name, variant)
pair" (the OUTPUT CONTRACT's own field-coverage requirement) was considered. Unlike the
Background-tag case, this one is not structurally unreachable — a dropped required variant is a
real, possible defect. Not built because **every real `TestDataSpecification` this platform has
ever emitted carries `fields=()`** — confirmed against all 20 requirements in `output/latest/
test_data_specifications.json`, and stated directly in the contract's own docstring
(`contracts.test_data_specification.TestDataSpecification`: "true of every requirement this
platform has emitted so far"). No real case exists to seed or ground it against; a synthetic-
fields fixture would violate this arc's own "seeded from real generation contexts, not invented"
discipline for the curated set. Named as the next check to add if Layer 2 ever emits a non-empty
specification — not designed further here.

**Built:** `eval_harness/test_data_eval_set.py`, `test_data_properties.py`, `test_data_runner.py`
— reusing `models.py`, `scoring.py`'s `score_eval_set`, `baseline_store.py`, AND
`feature_content_coverage.py`'s `check_requirement_covered` verbatim (the coverage-shaped check is
reused directly across generators — not merely the scaffolding, the actual check, since both
generators trace to the same `TestableRequirement`/`requirement_id`).

- **The curated eval set (D2).** `TEST_DATA_EVAL_SET` (independently versioned,
  `TEST_DATA_EVAL_SET_VERSION`) — three cases built from the SAME three real, currently-tracked
  requirements feature-content's own eval set uses (`REQ-c64bb0f7`/`REQ-f90f23fa`/`REQ-92502735`),
  each with the real, currently-tracked EMPTY `TestDataSpecification` every requirement in this
  corpus actually has. `class_name`/`target_package`/`customqa_constraints` derived via the real
  orchestrator's own functions (`derive_test_data_class_name`,
  `DEFAULT_TEST_DATA_TARGET_PACKAGE`, `DEFAULT_CUSTOMQA_TEST_DATA_CONSTRAINTS`), verified to
  produce the exact class names the real corpus's own tracked `.java` files carry
  (`ReqC64bb0f7TestData`, etc.).
- **Five deterministic property checks (D2/D3, composed not invented).**
  `test_data_properties.py`: `check_no_env_binding`, `check_no_markdown_fence`,
  `check_class_name_matches`, `check_no_webdriver_reference`, `check_no_long_method` — two direct
  reuses of already-real mechanisms, three contract-grounded ports (above). Each returns `PASSED`,
  `FAILED`, or `NOT_APPLICABLE`.
- **Scoring, keyed by `GenerationIdentity` (D2).** Reuses `eval_harness.scoring.score_eval_set`
  verbatim — the THIRD generator to do so unchanged, confirming the design is genuinely
  generator-agnostic, not merely designed to look that way.
- **The coverage-shaped check, reused verbatim, not re-implemented (D3/D4).** No new
  `test_data_coverage.py` module — `feature_content_coverage.check_requirement_covered` is called
  directly (`test_eval_harness_test_data_coverage.py` proves it), since the coverage-shaped
  question ("does this requirement reach a full traceability chain") is identical for both
  generators, both keyed by the same `requirement_id`. Optional, not part of the default check
  set, same reasoning as the other two increments.
- **The regression gate, reused verbatim (D2).** `EvalBaselineStore`/`check_regression` — no
  changes; `generator_id="test_data_generation"` (`LiveTestDataGenerator.CALL_TYPE`) stores to its
  own separate file, no collision with the other two generators' baselines.
- **The runner (D5).** `test_data_runner.py`'s `run_test_data_eval` — takes any `TestDataGenerator`
  (Protocol-typed, agnostic to live/stub/cached) plus a caller-supplied `GenerationIdentity`,
  mirroring the other two runners' own shape exactly.

**Proven three ways, all deterministic, no live LLM call anywhere in this package's own test suite
(25 new tests):**

1. **Each property check catches its own real defect shape and passes the real, currently-tracked
   clean corpus text** (`test_eval_harness_test_data_properties.py`) — unlike feature-content, no
   reconstruction was needed: test-data's raw generator output IS the final Java text (no assembly
   step exists for this artifact type), so the "clean" fixture is the real, currently-tracked
   `ReqC64bb0f7TestData.java` content, verbatim. All five checks FAIL on a fixture reproducing
   their own real defect shape and PASS on the clean text. `check_no_long_method` is additionally
   proven to actually FIRE on a real 45-line method — not structurally unreachable, the lesson
   carried forward from feature-content's own tagged-Background finding.
2. **The full arc — scores-first baseline establishment, then regression detection — end to end**
   (`test_eval_harness_test_data_runner.py`), driven by `StubTestDataGenerator` seeded with the
   real clean text: a clean generator's first run has no prior baseline (`ESTABLISHED_BASELINE`)
   and is explicitly recorded as one; a generator standing in for a worse model (a
   `ConfigReader.env(...)` call — the real, always-on orchestration guard's own SUT-binding
   violation — reintroduced into every case, since no real historical defect exists to replay) is
   caught (`REGRESSED`) relative to that baseline; re-running the same clean generator does not
   regress (`PASSED`).
3. **The coverage-shaped check's reuse is proven, not merely claimed**
   (`test_eval_harness_test_data_coverage.py`) — the SAME `check_requirement_covered` function,
   imported from `feature_content_coverage.py`, correctly PASSES/FAILS against test-data's own
   `requirement_id`, no test-data-specific coverage module written.

**Scope held exactly as D5 decided.** Three of seven target generators
(`LiveStepDefinitionGenerator`, `LiveFeatureContentGenerator`, `LiveTestDataGenerator`) are built —
**all three of ADR-0050's own measured/cached token sinks now have quality-drift eval**. The
remaining four generators' eval sets (`LivePageObjectGenerator`/`LiveUtilityGenerator` — blocked
on live-wiring, ADR-0050's own note; `LiveFeatureRemediator` — excluded per ADR-0050 D5's own
"repairs a prior attempt... independently rare" reasoning, mirrored here; `RequirementAnalysisService`),
the judge layer (D5), rubric grading, and any CI/live wiring are all untouched by this increment.

Gate: `make lint` clean; `make test` 5982 passed (5957 + 25 new, itemized above); `mypy`:
whole-repo error count unchanged (436, confirmed) — the six new/changed files are themselves
zero-error under `mypy strict`. Tree: 3 new files under `eval_harness/`, 3 new test files, this ADR
amended further.

---

## Investigation Note (2026-08-20) — the judge layer (Layer 2) value assessed, not built

A surface-then-build-if-warranted task on D3/D5's own judge-layer deferral, the same discipline
`[[cap-runtime-citation-not-built]]` applied to ADR-0049's runtime-citation deferral: establish
whether the judge is actually worth building before designing or building any of it. **Verdict:
NOT WORTH BUILDING NOW, as a CI gate. Did not build. The deferral was correct — confirmed by
evidence, not merely re-asserted.** One mentor throughout (Nitin).

**Pre-flight.** Clean tree, `main`, tip `4450d72` (the test-data eval increment). `make lint`
clean, `make test`: 5982 unchanged. This note adds text only to this document; nothing else
touched.

**The judge's real, narrow residual scope, established first.** D3's own taxonomy names three
defect shapes; two are already closed without a judge. Structural defects (row 1) are Layer 1's
own scope, now built and proven for three generators (the Implementation Notes, above) — wrong
imports, markdown fences, fabricated classes, SUT-binding violations, oversized methods, all
deterministically checkable. Coverage omissions (row 2) are CAP-088's `CompletenessReport`,
consumed read-only by two of the three built increments (`check_step_covered`/
`check_requirement_covered`) — "does a required thing have no corresponding generated artifact at
all" is fully answered without a judge. **What is left for a judge is exactly row 3, and only
row 3:** an artifact that is structurally clean, references real methods, and nominally covers the
right acceptance criterion, but implements the wrong logic underneath — a defect no deterministic
check can see without a rubric of "correct."

**(A) Does silently-wrong-logic actually occur here? Checked against every real defect corpus
this platform has, not assumed.** No. This platform's ONLY real historical generation-quality
incident — the `gemini-2.5-flash` 76%-defect-rate regression (`[[cap-compile-gap-closed]]`, 17
generations) — is **100% structural**: wrong Cucumber import package (8/17), a markdown code
fence (2/17), a fabricated duplicate page-object class (3-4/17). None of the three is
silently-wrong-logic — every one is deterministically checkable and IS checked today by Layer 1.
The two other generators this arc measured are also clean of any incident: feature-content's real
live E2E corpus scored 15/15, 0 escalations; test-data's real corpus has never even exercised a
non-empty specification. **Zero instances of the row-3 defect shape exist anywhere in this
platform's own recorded history.** Nitin's own motivating example (a model silently missing
allergy validation or insurance eligibility) is illustrative, not observed — a healthcare analogy,
not a finding from this platform's actual domain (a saucedemo-style e-commerce test-automation
corpus). This is a **theoretical**, not an **observed**, defect class here — the same honest
distinction `[[cap-runtime-citation-not-built]]` drew for runtime citation's own "no consumer"
finding.

**(B) Is an LLM judge reliable enough to trust for a CI gate? Reasoned from this platform's own
already-documented facts, not a generic caveat.** No, not without infrastructure this arc has not
built and cannot build today. Three compounding problems:

1. **Non-determinism compounds, it does not merely repeat.** ADR-0050 D1's own residual-risk
   finding, already documented about this platform: "hosted-model APIs do not guarantee
   bit-identical output across calls even at `temperature=0.0`." That is already true of the
   GENERATOR's own output — Layer 1 was deliberately built around property checks, not golden-text
   matching, specifically because of it (ADR-0051 D2). A judge adds a SECOND LLM call, with the
   SAME non-determinism, now applied to SCORING rather than generating — even identical generated
   text could receive a different judge score on a re-run, a second, independent noise source
   stacked on the first.
2. **A false positive is worse than no judge.** A judge that flags good output as bad erodes trust
   in the exact mechanism this whole harness exists to be trusted — the same "pass-bias
   meaning-check" trap D2 already named as the reason Layer 1 rejects an absolute score threshold,
   now recurring one level up: an unreliable judge trains engineers to override or ignore it,
   which is strictly worse than having no judge at all.
3. **Calibration requires ground truth this platform does not have, and cannot cheaply produce.**
   Knowing whether a judge's score correlates with real quality requires labeled examples of known-
   good and known-bad generations. (A) already established this platform has **zero real examples**
   of the row-3 defect the judge would exist to catch — there is nothing to calibrate against.
   Producing that ground truth would require a human expert manually reviewing generations for
   semantic correctness — which is exactly the "Rubrics scored by a human" category the original
   design-surfacing note (Item 1, above) already named and rejected as "not CI-automatable by
   definition... useful for periodic audit, not for gating a model swap." Calibration and the
   human-rubric problem are the same unsolved problem, not two.

**(C) The five open questions, worked through — not answered, but no longer merely named.**

1. **Which judge?** No precedent exists on this platform for a "judge" role specifically. Self-
   grading (same model judges its own output) risks the model's own blind spots recurring in its
   own grading; a different/stronger model adds a second provider dependency and cost. Genuinely
   open, not decidable from this platform's existing evidence.
2. **How pinned?** The one question this platform's own infrastructure already answers. A judge's
   `prompt_id`/`prompt_version`/`prompt_sha256`/`provider`/`model` would reuse `GenerationIdentity`
   verbatim — proven reusable across three unrelated generators already (the Implementation Notes,
   above). Pinning is cheap and solved; it is the OTHER four questions that are not.
3. **Whose rubric?** No existing role or convention on this platform authors or maintains a
   semantic-correctness rubric. The original Layer 2 LLD already named two LLM-judged advisory
   checks ("Business readability," "Step reusability," `CP2AdvisorySignals`) and never built
   either — a live, real precedent, on this exact platform, of the same category of work
   (LLM-judged assessment of generated output) being named once and never prioritized, with no
   recorded cost from leaving it unbuilt.
4. **Calibration?** Unsolved, per (B)#3 above — circular with the human-rubric problem this
   platform already declined to build for the identical reason (not CI-automatable).
5. **Cost?** A second LLM call per graded artifact, minimum. Cheap for three generators' small
   curated sets in isolation, but the goal Nitin named is CI-gating on every model/prompt change —
   at that cadence, the judge inherits the SAME quota pressure `[[cap-compile-gap-closed]]` already
   found real for generation alone (`gemini-2.5-flash`'s free tier: 20 requests/day) doubled, since
   both the artifact call and the judge call would need it.

**(D) The regression-gate problem — the deterministic mechanism does not transfer to a noisy
judge, checked against the real, already-tested gate, not assumed.** `check_regression`
(`baseline_store.py`) is exact and relative: `candidate.pass_rate < baseline.pass_rate` →
`REGRESSED`. This is proven safe for Layer 1 precisely BECAUSE `pass_rate` is a deterministic
computation — `test_re_running_the_same_good_generator_does_not_regress` (proven three times, once
per generator) holds only because nothing in the computation varies between runs. A judge score is
not deterministic (B, above): the identical generated text, judged twice, could score differently
purely from judge-call variance — indistinguishable, with the CURRENT gate mechanism, from a real
quality drop. Distinguishing real regression from judge noise would need new, undesigned machinery
(repeated sampling, a confidence interval, a minimum-delta-to-flag threshold) — which itself needs
the noise-floor data (B)#3 already established this platform does not have. The gate mechanism
this arc proved does not straightforwardly generalize to a judge; a naive reuse would produce
false `REGRESSED` verdicts on pure noise.

**(E) A decisive, doc-grounded finding not named in ADR-0051's own original five questions: even
if built, a judge could never GATE on this platform, by its own now-Accepted constitution.**
ADR-0049 (Engineering Constitution) Article VII — "Deterministic Gates Decide": *"A release or
pass/fail verdict is derived by a single, deterministic, policy-governed engine; an LLM-authored
assessment is advisory only and never gates"* — grounded in ADR-0040's own control-point rule,
already enforced live at every control point this platform has (CP1 through CP7). Wiring a judge's
score into `check_regression`'s `PASSED`/`REGRESSED` verdict would be exactly the kind of
LLM-authored pass/fail decision Article VII forbids. A judge on this platform can therefore only
ever be an advisory signal — mirroring `CP2AdvisorySignals`'s own dormant, structurally-incapable-
of-gating slot — never a CI-blocking regression gate, regardless of how well (B)-(D) above were
ever solved. This forecloses recommendation option (a) (a CI-gating judge) architecturally, not
merely as a matter of today's engineering maturity.

**THE VERDICT.** **(b) Not worth building now — as a CI gate, or in any minimal/non-gating form
either.** Grounds, together: (A) the defect class is unobserved, not merely rare, across every
real corpus this arc has produced; (B) a judge's own reliability is unproven and uncalibratable
without ground truth this platform does not have and cannot cheaply produce; (C) four of five open
questions remain genuinely open, with no local evidence to resolve them; (D) the existing,
already-proven regression-gate mechanism does not transfer to a noisy score without undesigned
machinery; (E) even a working judge could never gate on this platform's own constitution — only
ever advise. A minimal, non-gating, human-reviewed audit tool (option (c)) was also considered and
rejected FOR NOW, not because it is architecturally impossible (Article VII permits advisory
signals), but because nothing in (A) gives it a real defect to find, and no rubric owner exists
(C.3) to write what it would grade against — an audit tool with nothing to audit and no one to
maintain its rubric is ceremony, the same shape D1's own reframe already warned against reaching
for prematurely.

**The condition that would warrant reopening this, named, not scheduled** — mirroring
`[[cap-runtime-citation-not-built]]`'s own precedent exactly: a REAL, observed instance of
silently-wrong-logic in this platform's own generated output (not a hypothetical), which would
simultaneously prove the defect class occurs here and hand a labeled example to begin calibration.
Absent that, building a judge is ceremony — a second, costly, non-deterministic LLM call with no
proof it can distinguish a real defect from noise, gated (Article VII) to advisory status even if
it worked.

**Connection to #8 (per-stage LLM assignment) and Nitin's own intent, addressed directly.** A
judge WOULD be the mechanism that validates a future #8 model/provider swap semantically, not just
structurally — but #8 itself remains unbuilt (ADR-0051 Consequences already name it as "the
cheapest item on the mentor list to build engineering-wise" but not yet done), so the judge's own
most concrete justified use case has no live consumer either — the same "no consumer" shape
`[[cap-runtime-citation-not-built]]` found for runtime citation. **Nitin's own words, re-read
precisely** (the original design-surfacing note, Item 1, above): "curated eval sets (expected
outputs, OR RUBRICS)" — his ask names rubrics as one acceptable mechanism, not an LLM judge
specifically, and his one CONCRETE example this platform ever produced (the gemini-2.5-flash
incident) is now, in full retrospect, 100% covered by Layer 1 without any judge at all. His
HYPOTHETICAL healthcare example splits cleanly per D3: its coverage-shaped half is already CAP-088
territory; only its semantic-implementation half needs a judge, and that half's real-world analog
has never once occurred on this platform. **Layer 1 + CAP-088 already satisfy the concrete,
observed form of Nitin's ask; the judge layer would only serve the hypothetical, illustrative
extension of it — not something he has flagged as an actual problem on this platform.**

Gate: `make lint` clean; `make test` 5982 unchanged — doc-only, no code/test touched. Nothing
built: no judge module, no rubric, no CI wiring, no new eval-harness code of any kind.

---

## Consequences

- **Enables, proven for the first increment (Implementation Note, above):** a curated, versioned,
  regression-gated quality score for `LiveStepDefinitionGenerator`, keyed by `GenerationIdentity`,
  proven — by a fixture standing in for the real defect shape, not merely argued — to catch the
  real `gemini-2.5-flash`-class regression before adoption. Not yet CI-wired: the score exists and
  is provably correct; nothing runs it automatically on a real pull request or model change yet.
- **Deliberately does not enable, by this ADR's own decision, not oversight:** detection of
  silently-wrong-logic (D3, row 3) — no rubric or judge exists after this increment; grading for
  any generator other than step-def; a live CI decision on the cadence question named in D2 (still
  open, not resolved by the Implementation Note).
- **Corrects a possible over-scoping before it shipped.** Absent this ADR's own reframe (D1), a
  first build could easily have reached straight for an LLM-judge — the "standard modern approach"
  — to satisfy Nitin's ask, at real cost and with a real second-drift-source risk, for a defect class
  (D3, row 1) that a compile check and a duplicate-class sweep this platform already runs would have
  caught for free. The reframe is the reason Layer 1 is deterministic-first, not judge-first.
- **Dependencies, satisfied or explicitly not required:** `GenerationIdentity` (pinning) is built and
  sufficient as the eval-score key; CAP-088's `CompletenessReport` is built and sufficient for
  coverage-shaped checks (D3, row 2); CP5's own check logic is built and directly reusable for the
  structural checks (D3, row 1). No new upstream capability is required to begin the first build.
- **Connects to #8 (per-stage LLM assignment, mentor Item 8).** This harness is the literal mechanism
  that would let a future #8 model/provider swap be *gated*, not merely *permitted* — #8 remains the
  cheapest item on the mentor list to build engineering-wise, but today nothing would catch a bad
  swap before it ships; this ADR's first build is what closes that, for the one generator it covers.
- **Connects to pinning (`GenerationIdentity`).** A version bump — a new `prompt_version`, a new
  `model` — is exactly the event that should trigger a fresh eval run against the new identity before
  it becomes the production default, fulfilling Item 1's own earlier re-run-token-cost note that
  pinning "lets an eval-harness trigger target exactly what changed."
- **Governance follow-ons, recommended, not performed here** (mirroring exactly how ADR-0048 and
  ADR-0050 each named their own matrix/register follow-ons as separate actions): (1) a
  `docs/governance/platform-capability-matrix.md` entry for **CAP-090** — Generation Quality Eval
  Harness — the next unused id after `CAP-089` (Artifact-Level Generation Cache) in the open-ended
  `CAP-060…` block (§3.1); status `Accepted`/`Implementation` (updated from this ADR's original
  `Proposed`/`Architecture` framing, above, now that the first increment is built and tested —
  Implementation Note), mirroring `CAP-088`/`CAP-089`'s own row shape for a built-and-tested,
  not-yet-wired capability rather than `CAP-087`'s pure-paper-freeze shape; (2) a
  `docs/architecture/architecture-baseline-v2.md` register entry recording this ADR, mirroring how
  ADR-0048's own entry was added in a later, separate task. Neither is performed by this ADR, and
  neither changes this ADR's Decision text if performed later.
- **Became Accepted the same day** (Implementation Note, above): the curated eval set, the three
  deterministic property checks, scoring, the CAP-088 coverage consumption, and the regression-
  gated baseline store (D2–D5) were built directly against this design, and the regression gate was
  proven — deterministically, via a fixture reproducing the real defect shape, not a live model
  swap — to catch it. The exact Proposed-to-Accepted path this ADR named in advance, mirroring
  ADR-0050's own convention. Accepted status covers this one increment's own scope only
  (`LiveStepDefinitionGenerator`, Layer 1); the remaining six generators, the judge layer, and any
  CI/live wiring stay future, separate work (D5), not implicitly authorized by this status change.
- **Relationship to the mentor item.** This is the design record for the last major unbuilt item on
  Nitin's (one mentor) list. The specific reframe (discipline, not new detection), the Layer 1/Layer
  2 split, and the step-def-first sequencing are this ADR's own reading of the real code and the real
  historical defect — not something Nitin weighed in on directly, the same caveat the surfacing note
  itself already flagged for every design-surfacing note in this arc.
- **Extended to a second generator, additively (2026-08-20 Implementation Note, above).**
  `LiveFeatureContentGenerator`'s Layer 1 is now also built, tested, and Accepted for its own
  scope — proving D5's own "same pattern, applied once step-def's own build proves the mechanism"
  claim directly: `models.py`, `scoring.py`'s `score_eval_set`, and `baseline_store.py` all reused
  verbatim, unchanged, exactly as D2 designed them to be generator-agnostic. Feature-content's own
  checks are grounded in a different real mechanism (`assembler.py`'s tag-contract validation, not
  CP5) — proof the reframe (D1) generalizes across artifact types, not just within one. Five
  generators and the judge layer remain future, separate work.
- **Extended to a third generator, additively (2026-08-20, same day, second Implementation
  Note).** `LiveTestDataGenerator`'s Layer 1 is now also built, tested, and Accepted for its own
  scope — **completing eval coverage of all three of ADR-0050's own measured/cached token sinks**
  (step-def, feature-content, test-data). The generic core (`models.py`, `scoring.py`'s
  `score_eval_set`, `baseline_store.py`) was reused verbatim a THIRD time, unchanged — no longer a
  claim resting on two data points. Test-data's own checks compose the strongest existing-detection
  grounding found in this arc yet (a live, always-on orchestration guard reused directly; CP3's
  real, public `evaluate_long_method` called directly, not ported) alongside contract-grounded
  checks that close a real, previously-unenforced gap (CP3's own `direct_webdriver_action`
  criterion explicitly excludes test-data's package). One check (field-variant coverage) was
  considered and honestly not built — no real `TestDataSpecification` this platform has ever
  emitted carries a non-empty `fields` list to ground it against. Four generators and the judge
  layer remain future, separate work.

## Ownership, runtime position, governance

- **Owns:** the eval harness's curated-set shape (D2), the deterministic property-check grading
  mechanism (D2), the score/key/store design (D2), the defect-shape taxonomy and layer boundaries
  (D3), its relationship to CP5/CAP-070/CAP-088 (D4), and the build sequence including the deferred
  judge layer (D5) — decisions only.
- **Does not own:** `GenerationIdentity`, any live generator, `CompletenessReport`/the traceability
  graph, any CP5 check (reused, not owned), the golden-baseline harness, or the judge/rubric layer
  itself (named as future scope, not designed).
- **Runtime position (built for three increments; not CI-wired, not live-wired):** generator +
  caller-supplied identity + curated eval-set case → a runner (`runner.py`'s
  `run_step_definition_eval`, `feature_content_runner.py`'s `run_feature_content_eval`, or
  `test_data_runner.py`'s `run_test_data_eval`) → property-check results per case
  (`step_definition_properties.py`, `feature_content_properties.py`, or `test_data_properties.py`)
  → aggregate `EvalScore`, keyed by `GenerationIdentity` (`scoring.py`, reused verbatim by all
  three) → `check_regression` against `EvalBaselineStore`'s current baseline (`baseline_store.py`,
  reused verbatim by all three — one JSON file per `generator_id`, no collision) →
  `ESTABLISHED_BASELINE` / `PASSED` / `REGRESSED`. This chain exists and is tested for
  `LiveStepDefinitionGenerator`, `LiveFeatureContentGenerator`, and `LiveTestDataGenerator` only
  (proven against Stub generators, never a live LLM call, in this package's own test suite) — no
  CI job invokes it, and no `PlatformContext` composition-root method exists for it.
- **Governance:** recommended `CAP-090` (not yet entered — Consequences) for the Requirement
  Intelligence Platform. This ADR is **Accepted** for its first three increments (Implementation
  Notes, above) — it now clears the same bar ADR-0050 cleared (built, tested, and proven against
  each covered generator's own real defect shapes), for the scope D5 defined. It does not claim
  any of the other four generators' eval sets, the judge layer, or CI/live wiring are built — that
  remains future, separate work, exactly as D5 sequenced it.
