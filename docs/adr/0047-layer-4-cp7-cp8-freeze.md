# ADR-0047 — Layer 4, CP7 (Suite-Wide Sonar Governance) and CP8 (Static Execution Readiness) Freeze

- **Status:** Accepted
- **Date:** 2026-08-06
- **Supersedes:** nothing. **Amends:** ADR-0046 (Layer 4 Quality Governance Architecture Freeze — additive: D1's own numbering table and D8's own "named and scoped only... detailed design deferred to a future task" text for CP7/CP8 are now fully specified by this ADR, the same relationship ADR-0046 itself already has with ADR-0040 Decision 3's CP5 list — an inline amendment note is added there). ADR-0044 (Layer 3 Automation Engineering Architecture Freeze — additive: D5's own CP3-Sonar/`customqa:*` honesty story is now extended to suite scale by CP7, unchanged in its own text — an inline amendment note is added there).
- **Governing design:** `docs/proposals/layer-4-cp7-cp8-design.md` (CP7/CP8 Design Proposal; Status: Proposed — under review, not approved, at the time this ADR was drafted). This ADR is where that document's own eight open decisions (its §5) become binding Decision text, the same graduation ADR-0046 already performed for the CP5 design proposal's own eight open decisions.
- **Depends on:** ADR-0031 (Authoritative Layer Model — Layer 4/5 boundaries); ADR-0040 Decision 2 (deterministic-gate discipline, applied to both CP7 and CP8 below) and Decision 3 (Layer 4's own remit, restated by ADR-0046 D1 to include CP7/CP8 under corrected numbers); ADR-0044 D5 and its own three revision notes (the `customqa:*` honesty arc CP7 inherits, D2 below); ADR-0046 D1/D8 (CP7/CP8's own naming, scope boundary, and inherited-constraint anchors — this ADR's own binding target); ADR-0046 D5 (CP5's aggregate-release cohesion — the compile check CP8 is deliberately distinct from, D8 below).
- **Runtime status:** Not applicable. This is a **pure architecture freeze** — no CP7/CP8 code exists today (`suite_quality_governance/` carries CP5's own live code, per ADR-0046's own freeze and its subsequent stage-16 wiring, but nothing for CP7/CP8). This ADR authorizes a future implementation milestone; it builds nothing itself.

## Problem

ADR-0046 D8 named and scoped CP7 (suite-wide Sonar/code-quality governance) and CP8 (static
execution-readiness governance) — the real content behind the source deck's own mislabeled
"CP5"/"CP6" (`docs/proposals/layer-4-quality-governance-lld.md`'s own Finding 0) — but explicitly
deferred their detailed design: *"Neither CP7 nor CP8's detailed rule catalogue, report shape, or
task breakdown is designed by this ADR. Both are recorded as deferred."* D8 additionally
conditioned CP7's own design on a precondition it did not resolve itself: *"Sonar Community
Edition's actual claimed capabilities (security hotspots, quality-gate specifics) must be
verified against the real server before CP7 is designed in detail... flagged as a
to-verify-before-designing item, not resolved here"* — the same "verify the tool does what the
slide claims" discipline this platform's own `customqa:*` arc (ADR-0044 D5's three revision
notes) already learned the hard way once, restated here as a precondition rather than an
assumption.

`docs/proposals/layer-4-cp7-cp8-design.md` closes both gaps: it performs the Sonar-CE discovery
live, against this platform's own real, locally-running SonarQube server (edition confirmed
`community`, not assumed), and designs both control points in the same detail ADR-0046 D2–D6
already gave CP5 — surfacing eight open decisions at the design stage, the same "design proposal,
then a separate freeze locks it" two-step process ADR-0046 itself already completed for CP5's own
design proposal.

This ADR resolves both gaps: it locks the design's eight open decisions as binding Decision text
(D1–D9, below), and records the Sonar-CE discovery's own verified facts as this freeze's binding
evidentiary basis (D10) — the same two-part pattern ADR-0046 already applied to CP5's own design.

## Freeze structure — mirrors ADR-0046, and why this is a companion ADR, not an edit to it

ADR-0046 itself is the direct precedent for how this freeze is structured, and this ADR follows
it exactly: **a new, dedicated ADR** (this document), carrying an `Amends: ADR-0046 (additive)`
header and an inline amendment note added directly onto ADR-0046's own text (not editing ADR-0046's
own D1/D8 Decision text) — never folding new Decision content into an already-Accepted ADR whose
own text is not retroactively edited. ADR-0046 itself did the identical thing one layer up: it
is a new ADR, not an edit to ADR-0040/ADR-0044/ADR-0045, carrying `Amends:` headers for all three
and inline amendment notes on each. Editing ADR-0046's own D1 table or D8 text in place would
break the very "Decision text is never edited retroactively, only amended additively" discipline
ADR-0046 itself depends on and states explicitly in its own D1 subsection ("No renumbering of
CP1–CP6 is proposed or authorized here" — the same posture toward not silently rewriting a prior
ADR's own binding text, applied here to ADR-0046's own D1/D8 instead of ADR-0040's).

## Decision

### D1 — CP7's mechanism: absolute measures via `/api/measures/component`, never the built-in leak-scoped gate, never an admin-created custom gate

**Locked per the Sonar-CE discovery (D10, below), resolving the design proposal's open decision
5.** CP7 reads absolute (non-`new_`) metric values for the tracked baseline's own live-registered
Sonar project (`Automation-POC`, the same `DEFAULT_SONAR_PROJECT_KEY` constant
`automation_engineering/stage/runner.py` already defines) via `GET /api/measures/component`,
using the pipeline's own existing least-privilege `SONAR_TOKEN` — confirmed live, this credential
already reads every metric CP7 needs, no elevated token required for this mechanism specifically.

**Not the server's own built-in quality gate.** The one quality gate that exists on this
platform's real server (`Sonar way`, built-in) is entirely `new_*`/leak-period-scoped (Clean-as-
You-Code) — it answers "what changed since the last analyzed version," never "what has the whole
accumulated suite become." Using `project_status`'s own PASS/FAIL for CP7 would be a category
error at the exact scope CP7 exists to cover.

**Not an admin-created custom "Overall Code" gate.** Creating a second quality gate is an admin
action the pipeline's own token cannot perform (`/api/qualitygates/list`'s own `actions.create:
false` for this token, confirmed live) — the same one-time-human-admin-action shape the
`customqa` profile's own import/assignment already established (`test-suite-baseline/sonar/
README.md`). CP7 reading raw measures directly needs no new admin dependency beyond what already
exists; this is locked as the simpler, lower-dependency mechanism, not merely a preference.

### D2 — CP7 inherits CP3's `customqa:*` honesty story; it does not restart it

Restated as binding, per ADR-0046 D8's own instruction ("CP7 must inherit CP3's own honest Sonar
profile/scope story, never restart it") and ADR-0044 D5's three revision notes (this ADR's own
amendment note on ADR-0044, below, cross-references this explicitly): Sonar performs generic Java
quality analysis only; this platform's own architectural rules (`direct-webdriver-action`,
`long-method`) are static Layer 3 checks, never Sonar rules, because `java:S138`'s own permanent
`scope:"MAIN"` metadata makes a `src/test/java`-resident rule structurally unreachable regardless
of correct profile assignment; the `customqa` profile's own real, current role is exclusively the
generic-quality baseline CP3's Sonar criterion already gates on. CP7's own generic-quality
metrics (D3, below) extend this identical, already-corrected story to suite scale — they are not
a fresh "Sonar does everything" narrative, and any future CP7 revision that reasons about a
specific rule's applicability must ask whether that rule's own `scope` metadata covers `TEST` as
well as `MAIN`, the same question that resolved the `long-method` gap.

### D3 — CP7's gate discipline: report-only initially; generic-quality/reliability rating-gating deferred until the suite genuinely compiles

**Locked, resolving the design proposal's open decision 1.** CP7 ships, initially, entirely
**report-only**: every metric it reads (`violations`, `bugs`, `code_smells`, `sqale_rating`,
`reliability_rating`) is surfaced in CP7's own whole-suite quality-metrics report, and **none of
them gates CP7's own PASS/FAIL yet**. This is not a weaker freeze than CP5's own — it is the
correct freeze given a fact this platform's own build history already recorded and CP5's own
`suite_quality_governance/README.md` restates: **the real tracked baseline does not currently
compile** (`mvn test-compile` fails — 34 step-definition classes reference page-object classes
that were never generated, a pre-existing gap, not something this ADR causes or resolves). A
Sonar measure computed against a suite state that does not even compile is not a meaningful
number to gate a release decision on — the measures CP7 would read today (all currently clean,
per D10) reflect a suite Sonar has only ever scanned in its pre-compile-failure form, not
necessarily what the suite's own real, current Java content would score if it could be
meaningfully re-analyzed post-fix.

**Rating-based gating (`reliability_rating`/`sqale_rating` at an explicit floor — the "A" grade,
i.e. `1.0`, given this suite's own current, real, clean measurement, per D10) is a tracked
fast-follow, not designed further here.** Its own trigger, stated precisely: the suite genuinely
compiles (CP5-cohesion's own `compiles` criterion, ADR-0046 D5, passes) **and** a fresh Sonar
scan against that compiling state produces real, calibratable scores. This mirrors ADR-0046 D3's
own "configurable default, not a proven constant... resolve/tune against real observed data"
posture for the near-dup threshold, applied here to a different metric family for the identical
reason: a threshold locked against data collected before the underlying defect it would help
catch is even fixable is not evidence, it is a guess dressed as a number.

### D4 — CP7's security dimension: report-only, permanently, absent a future explicit decision

**Locked, resolving the design proposal's open decision 2.** `vulnerabilities`,
`security_hotspots`, and `security_rating` are surfaced in CP7's own report, **never gated**. Two
independent, both-confirmed reasons, restated from the design proposal's own §0.4/§3.2: (a) this
platform's own least-privilege `SONAR_TOKEN` cannot reach the hotspot review/triage workflow
(`/api/hotspots/search` → `"Insufficient privileges"`, confirmed live) — gating hard on a count
nobody on this pipeline can meaningfully triage would manufacture false urgency, not real signal;
(b) test-automation code's own real security profile is thin by nature (Selenium/Cucumber
step-definition code has no production attack surface of its own), confirmed rather than merely
assumed — Sonar CE genuinely evaluates 36 security-hotspot and 35 vulnerability Java rules
(refining, not overturning, the LLD review's own S3/S6 lean: CE is not structurally blind to
security, the review workflow is what a non-admin token cannot reach). **This posture does not
change unless a future, explicit decision changes it** (e.g. a triage-capable token is
provisioned and a team decides the signal is worth gating) — never silently, as a side effect of
some other CP7 revision.

### D5 — CP7's coverage/duplication dimension: unmeasured today, report-only once JaCoCo is wired, never gated before then

**Locked, resolving the design proposal's open decision 3: defer.** `coverage` and
`duplicated_lines_density` are genuinely unmeasured on the live server today (both metric keys
exist in the server's own catalog; neither returns a value for `Automation-POC`, confirmed live)
— `coverage` because no JaCoCo XML report is ever submitted (the JaCoCo report-import plugin is
deployed server-side, confirmed live in `docker logs`; nothing feeds it, `sonar.coverage.jacoco.
xmlReportPaths` is never passed by `LiveSonarQualityGateAdapter`'s own scan submission).
`duplicated_lines_density`'s absence is recorded as unresolved (D10), not assumed to mean zero
duplication. **CP7's first implementation ships without either metric** — reported as "not yet
measured," a state distinct from and never conflated with "measured and clean" (the same false-
pass-avoidance discipline `Cp5PromotionWrapResult.compile_attribution`'s own `None`-vs-populated
split already establishes one control point over). The JaCoCo-wiring build task itself (D11,
Consequences) is a tracked prerequisite, not built by this ADR and not required before CP7's own
report-only-everything-else first implementation ships.

### D6 — CP7's adapter shape: extends the existing `SonarQualityGateAdapter` seam with `fetch_measures`, never a second, parallel Protocol

**Locked, resolving the design proposal's open decision 4.** CP7 extends
`automation_engineering.cp3.sonar.adapter.SonarQualityGateAdapter` (the same `Protocol` +
`StubSonarQualityGateAdapter` + `LiveSonarQualityGateAdapter` seam CP3 already uses) with a
fourth method, shaped `fetch_measures(project_key: str, metric_keys: Sequence[str]) ->
Cp7MeasuresResult` (or an equivalent name chosen at implementation), hitting the same
`/api/measures/component` endpoint D1/D10 confirm works against this platform's own real token
— **not** a second, measures-scoped Protocol. This is the more consistent choice against ADR-0046
D7's own "no second mechanism" discipline (already binding on CP5's own four components,
extended here across control points that share one underlying live dependency — the same Sonar
server, the same authentication, the same stub-vs-live testing discipline): one adapter Protocol
per live-infrastructure boundary, not one per control point that happens to consume it.

### D7 — CP8's scope: static readiness over this platform's own real config, `pom.xml` validated against its OWN declarations, never a hardcoded expected-dependency list

**Locked, resolving the design proposal's open decisions 6 and 7 together — both concern what CP8
actually reads, and are one design question, not two.** CP8 validates:

- **Assets present** — at least one `.feature` file under the tracked baseline's own features
  root, at least one step-definition class in the reconciled catalog (reused from
  `automation_engineering.catalog.scanner.reconcile`, never a second scan, per ADR-0046 D7's own
  "reuse, don't rebuild" discipline extended here), the tracked runner class
  (`src/test/java/com/automation/runners/RunCucumberTest.java`) present.
- **`pom.xml` well-formed and structurally valid** — parses as valid XML; the dependency/plugin
  declarations it actually contains are internally consistent (a `<dependency>` with a missing
  `<artifactId>`, a malformed version coordinate, that class of structural defect). **CP8 does
  NOT validate against a hardcoded expected-dependency list** (the design proposal's own §4.1
  point 2's tentative lean, superseded here) — `pom.xml` is this platform's own single source of
  truth for what the suite depends on; a hardcoded parallel list would drift the moment a real
  dependency changes and would duplicate, not validate, the POM's own authority. CP8 checks the
  POM is well-formed and internally coherent, not that it lists some other document's own
  independently-maintained opinion of what it should contain.
- **`junit-platform.properties` present, well-formed, and internally coherent with the reconciled
  catalog** — parses as a valid properties file; its own `cucumber.glue` value names at least one
  package that genuinely contains a class in the assembled suite's own reconciled catalog (a real,
  catchable misconfiguration, D8 below); its `cucumber.plugin` value's declared output paths are
  syntactically well-formed.
- **Not a speculative Layer-5-facing environment-config surface.** No such config exists in this
  repository today (confirmed by direct inspection, restated from the design proposal's own
  §4.1 point 4) — CP8 validates what genuinely exists, not an invented shape for something that
  might exist later. A future CP8 revision may extend this once Layer 5's own execution-config
  surface is itself designed and built — not anticipated here.

### D8 — CP8 is its own, distinct deterministic gate — non-redundant with CP5-cohesion by construction, not by convention

**Locked, resolving the design proposal's open decision 8.** CP8 (static readiness, D7) and CP5's
own aggregate-cohesion compile check (ADR-0046 D5, `suite_quality_governance/cp5/cohesion.py`)
remain **two separately-reportable, separately-gating checks — never merged into one combined
verdict.** The boundary, restated as binding: CP5-cohesion answers "does the assembled suite
COMPILE" (a real `mvn test-compile`, the authoritative, expensive-but-conclusive proof every
class's syntax is valid and every referenced dependency resolves); CP8 answers "is the suite
CONFIGURED to be EXECUTABLE" (cheap, static, no JDK/Maven/network). **The overlap is deliberate,
not accidental**: a missing `cucumber-java` dependency would trip both — CP8 cheaply, first,
before CP5-cohesion's own expensive compile is even attempted, the identical "fail fast on the
cheap check first" discipline `AssetGateOutcomes.first_failure`'s own CP2-before-CP3-before-CP4
ordering already establishes one layer down. **Where they do not overlap is CP8's own real
value**: a `cucumber.glue` package pointing at zero classes compiles perfectly clean under
`mvn test-compile` (a Java compiler has no concept of Cucumber's own runtime glue-scanning
convention) and would only surface as "zero steps matched" at Layer 5 execution time, absent
CP8. **CP8 does not verify dependency resolvability the strong way** (D7's own restated scope) —
CP5-cohesion's successful compile already proves that, more authoritatively; CP8 claiming to
verify it too would silently duplicate what CP5-cohesion already does, the same "no second
mechanism for what one component already proves" discipline ADR-0046 D7 already locks for CP5's
own four components.

### D9 — CP8's gate discipline: deterministic, gates from the start, unconditional on compile state

**Locked, resolving the design proposal's own §4.5 lean into binding text (this was already the
design's own stated posture, not one of its eight explicitly-open decisions — ratified here,
not overturned).** Unlike CP7 (D3: report-only until the suite genuinely compiles), **CP8 gates
immediately, as a real deterministic PASS/FAIL, from its first implementation.** Every CP8 check
(D7) is statically true or false independent of whether the suite currently compiles — a missing
feature file, a malformed `pom.xml`, a `cucumber.glue` package with zero classes are each
detectable and meaningful regardless of the platform's own current, separate, tracked
page-object-generation gap (D12, Consequences) that keeps the suite from compiling today. CP8's
own evidence is never "does the suite compile" (D8's own boundary) — it never inherits CP7's own
compile-state precondition. Action on a CP8 fail: **flag for review**, the same shared human
review queue every control point in this platform already joins (ADR-0045 D3/Recommendation 2,
extended to CP5 by ADR-0046 D4/Recommendation 3, extended here to CP7's own eventual gates and to
CP8) — never auto-fix a missing asset or a malformed config file.

### D10 — The Sonar-CE discovery's own verified facts, recorded as this freeze's binding evidentiary basis

Per ADR-0046 D8's own precondition ("must be verified against the real server... not resolved
here") and the `customqa:*` arc's own lesson (verify, never assume, what a tool actually claims
to do) — the following facts were confirmed live, this session, against this platform's own real,
locally-running SonarQube server (version `26.4.0.121862`), and are locked here as the basis D1,
D3, D4, and D5 above each rest on, not independently re-derivable assumptions:

- **Edition: genuinely `community`** (`/api/navigation/global`'s own `edition` field), standalone,
  not a paid tier — the first live confirmation anywhere in this repository; every prior mention
  was stated as an assumption.
- **The server's only quality gate (`Sonar way`, built-in) is entirely `new_*`/leak-period-scoped**
  — structurally the wrong tool for a whole-suite check (D1's own basis).
- **Absolute, whole-project measures ARE readable by the pipeline's own least-privilege token**
  via `/api/measures/component` — `violations`, `bugs`, `vulnerabilities`, `code_smells`,
  `security_hotspots`, `sqale_index`, `sqale_rating`, `reliability_rating`, `security_rating` all
  confirmed present and populated for `Automation-POC` (all currently best-value/clean).
- **`coverage` and `duplicated_lines_density` are unmeasured** — both metric keys exist in the
  server's own 149-entry metric catalog; neither returned a value for this project (D5's own
  basis).
- **Sonar CE genuinely evaluates security-relevant Java rules** (36 `SECURITY_HOTSPOT` + 35
  `VULNERABILITY` rules confirmed present and active) — **what is permission-gated is the
  hotspot review/triage workflow** (`/api/hotspots/search` → `"Insufficient privileges"` for the
  pipeline's own token), not detection itself (D4's own basis, refining rather than overturning
  the LLD review's own S3/S6 lean).
- **Creating a second, custom quality gate needs an admin token the pipeline's own credential does
  not hold** (`actions.create: false`, confirmed live) — the identical admin-boundary shape the
  `customqa` profile's own import/assignment already established, now confirmed for a different
  admin surface (D1's own basis).
- **Branch/PR-analysis multi-tenancy is flagged, not independently re-proven** — only one branch
  (`main`) has ever been analyzed; this document does not submit a second branch's scan to
  independently confirm the widely-documented Community Edition constraint, and states this
  distinction honestly rather than blurring "observed" with "inherited public knowledge."

## Consequences

- **CP7 and CP8 are now fully designed and locked (D1–D9), the same detail ADR-0046 D2–D6 already
  gave CP5.** CP7 ships report-only across every metric family it reads; CP8 ships as a real,
  gating deterministic check from its first implementation.
- **D11 — the JaCoCo-coverage-report-submission prerequisite is tracked, not built here.**
  `LiveSonarQualityGateAdapter`'s own scan-submission call would need to pass
  `sonar.coverage.jacoco.xmlReportPaths` for `coverage`/`duplicated_lines_density` to ever become
  measurable, let alone gateable (D5). Trigger: a dedicated build task wires this; until then, CP7
  reports both metrics as "not yet measured."
- **D12 — CP7's rating-gating trigger is the page-object generation gap closing, which is itself
  the reason the suite does not compile today.** `suite_quality_governance/README.md`'s own
  recorded finding (34 step-definition classes reference page-object classes never generated by
  this platform's current wiring — stage 15's own step 4/module docstring names this exact scope
  boundary) blocks CP5-cohesion's own `compiles` criterion from passing, which is D3's own named
  trigger for CP7's rating-gating to activate. Closing that gap is tracked as a separate,
  already-named prerequisite (CP5-cohesion's own README, and this ADR's own D3) — not built,
  scoped, or authorized here.
- **The `fetch_measures` adapter capability (D6) is new build work, does not exist today** —
  resolve at implementation, mirroring how ADR-0046 itself deferred the orphan-detection
  pattern-vs-text evaluator's own build to implementation.
- **CP8's own static-readiness build is new work, does not exist today** — resolve at
  implementation.
- **Additive amendment notes, recorded alongside this ADR:** ADR-0046 (an additive note near D1's
  own table and D8's own text, recording that CP7/CP8 are now fully specified by this ADR — the
  same pattern ADR-0046 itself already used for ADR-0040/ADR-0044/ADR-0045); ADR-0044 (an
  additive note near D5's own third revision, recording that CP7 extends this ADR's own
  `customqa:*`/Sonar honesty story to suite scale, per D2 above, with no change to ADR-0044's own
  text).
- **Open TBDs this ADR does not resolve, each with a stated trigger:** the exact rating-gate
  floor value once compiling, real scores exist (D3) — resolve once D12's own prerequisite
  closes; whether CP7's security posture ever changes from report-only (D4) — resolve only via a
  future, explicit decision, never silently; the JaCoCo-wiring build task (D11); the page-object-
  generation gap (D12); `duplicated_lines_density`'s own unresolved absence (D10) — re-check once
  the suite has grown past its current small size.

## Recommendations (permanent)

1. **CP7 never gates on a rating/violation threshold before the suite genuinely compiles
   (CP5-cohesion's own `compiles` criterion passes) and a fresh scan against that compiling state
   produces real scores** — D3's own trigger is binding, not advisory; a future implementation
   that locks a rating floor against today's pre-fix scores violates this ADR's own central
   reasoning.
2. **CP7's security dimension stays report-only until an explicit, future decision changes it** —
   D4's own posture is not provisional-by-default; it requires a deliberate future ADR/decision to
   flip, never a side effect of some other CP7 revision.
3. **No second quality gate is ever admin-created for CP7 without first re-confirming raw measures
   are insufficient** — D1's own "measures, not a custom gate" choice is the locked default, not
   merely today's convenience.
4. **No second Sonar adapter Protocol is ever built for CP7** — D6's "extend, don't parallel"
   choice is binding, the same ADR-0046 D7 "no second mechanism" discipline applied to this live
   boundary specifically.
5. **CP8 never validates against a hardcoded dependency list** — D7's own "the POM is the source
   of truth" reasoning is binding; a future implementation that reintroduces a parallel, hand-
   maintained expected-dependency list for CP8 violates this ADR's own central decision.
6. **CP8 and CP5-cohesion are never merged into one combined verdict** — D8's own "two, separately
   reportable, complementary checks" choice is binding; the two answer structurally different
   questions and a future implementation collapsing them into one boolean would lose exactly the
   distinction (glue-package misconfiguration vs. compile failure) this ADR exists to preserve.
7. **CP8 never inherits CP7's own compile-state precondition** — D9's own "gates now,
   unconditionally" choice is binding; CP8's static evidence is meaningful regardless of whether
   D12's own page-object gap is ever closed.

## Ownership, scope, and governance

- **Owns:** CP7's own mechanism (absolute measures, D1), CP3-honesty inheritance (D2), gate
  discipline and its own compile-state-gated rating trigger (D3), security posture (D4),
  coverage/duplication posture (D5), and adapter shape (D6). CP8's own scope (static readiness
  over this platform's own real config, D7), its boundary against CP5-cohesion (D8) and its own
  unconditional gate discipline (D9). The Sonar-CE discovery's own verified facts as this freeze's
  binding basis (D10).
- **Does not own:** CP5's own suite-integration governance (orphaned-glue, near-duplicate sweep,
  promotion-wrapping, aggregate cohesion) — already frozen and built, ADR-0046 D2–D7, unchanged by
  this ADR; Layer 5's own execution/dynamic-readiness concern (D9's own restated boundary); the
  JaCoCo-wiring build task or the page-object-generation gap (D11/D12, tracked, not built here);
  CAP-080's own subsystem or ADR-0017's governance (ADR-0046 D10, untouched, out of this ADR's own
  scope entirely).
- **Governance:** Accepted as an architecture freeze, effective immediately. Authorizes a future
  Layer 4 implementation milestone to build CP7/CP8 against D1–D9 without redesigning them, the
  same authorization ADR-0046 already gave CP5's own D2–D7. Amends ADR-0046 and ADR-0044
  additively (see each ADR's own added note); supersedes neither.
