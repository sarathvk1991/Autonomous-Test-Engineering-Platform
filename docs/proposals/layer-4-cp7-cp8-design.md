# Layer 4 — CP7 (Suite-Wide Sonar Governance) and CP8 (Static Execution Readiness) — Design Proposal

| Field | Value |
|---|---|
| Status | Proposed — design only. **Not approved, not frozen.** |
| Type | Design Proposal (original design; no source deck for this specific document — CP7/CP8's real *content* comes from the `Quality_Governance_Layer.pptx` deck's own mislabeled "CP5"/"CP6," already transcribed and reviewed in `docs/proposals/layer-4-quality-governance-lld.md`; this document designs that content under its correct, ADR-0046-assigned numbers) |
| Layer / Control Point | Layer 4 (ADR-0031, "Suite Quality Governance"); CP7 and CP8, per ADR-0046 D1/D8 |
| Depends on | ADR-0046 D8 (CP7/CP8's naming, scope boundary, and inherited constraints — this document's own binding target); ADR-0044 D5 (CP3's Sonar gate and the `customqa:*` honesty arc CP7 must inherit, not restart); ADR-0046 D5 (CP5's aggregate-cohesion compile check — the boundary CP8 must not duplicate); ADR-0040 Decision 2 (deterministic-gate discipline, applied to both CP7 and CP8 below) |
| Governs | Nothing yet. Informs a future Layer 4 CP7/CP8 design-then-freeze ADR, mirroring how `docs/proposals/layer-4-cp5-suite-integration-governance-design.md` preceded ADR-0046's own CP5 freeze. This document does not freeze an ADR and does not authorize any build. |

---

## 0. The Sonar Community Edition discovery — verified live, this session, not assumed

ADR-0046 D8 flags this explicitly as a precondition, quoted:

> "Sonar Community Edition's actual claimed capabilities (security hotspots, quality-gate
> specifics) must be verified against the real server before CP7 is designed in detail" —
> flagged as a to-verify-before-designing item, not resolved here.

The LLD review's own S6 finding is identical: *"confirm what this repository's actual Sonar
edition supports before any CP5-successor design assumes hotspot/quality-gate features it may
not have."* Every prior mention of "Community Edition" anywhere in this repository (ADR-0046,
the LLD review, ADR-0044's own `customqa:*` arc) is stated as an **assumption**, never previously
confirmed against the real server. This document is the first task to actually check.

**The server was unreachable on first attempt** (`curl http://localhost:9000/api/server/version`
→ connection refused) — mirroring this platform's own established precedent for when a live
dependency is not running in the current session (`LiveCompileChecker`'s and
`LiveSonarQualityGateAdapter`'s own docstrings both record the identical "not reachable in this
build" finding at earlier points). A `docker ps` check found a `sonarqube:latest` container
(name `sonarqube`) that had just started; once it finished booting (`docker logs` showed its full
plugin-deployment sequence complete), the server answered. **Every finding below is a real,
live API response against that server, version `26.4.0.121862`** — the same version
`test-suite-baseline/sonar/README.md` already recorded from the 2026-08-04 `customqa` admin
procedure — captured in this session, not carried forward from memory.

### 0.1 Edition — confirmed directly

`GET /api/navigation/global` (using the pipeline's own least-privilege `SONAR_TOKEN`, no admin
credential needed for this endpoint):

```json
{
  "edition": "community",
  "standalone": true,
  "versionEOL": "2026-06-08",
  "documentationUrl": "https://docs.sonarsource.com/sonarqube-community-build"
}
```

**Confirmed: this server is genuinely SonarQube Community Build (Community Edition)**,
standalone (no cluster), not a paid tier. `versionEOL` (2026-06-08) is already past relative to
this document's own date — consistent with Community Build's rolling-release model (the docs
URL itself uses the newer "community-build" naming SonarSource adopted after the assumption in
ADR-0046/the LLD review was written), not evidence of an abandoned install; not investigated
further here, out of this discovery's own scope.

### 0.2 The default quality gate is NEW-CODE-scoped, not whole-suite — the load-bearing finding

`GET /api/qualitygates/show?name=Sonar%20way` (the only quality gate that exists on this server —
`GET /api/qualitygates/list` returns exactly one, built-in, and `actions.create: false` for this
token, meaning the pipeline's own token cannot create a second one):

```json
{
  "name": "Sonar way",
  "conditions": [
    {"metric": "new_violations", "op": "GT", "error": "0"},
    {"metric": "new_coverage", "op": "LT", "error": "80"},
    {"metric": "new_duplicated_lines_density", "op": "GT", "error": "3"},
    {"metric": "new_security_hotspots_reviewed", "op": "LT", "error": "100"}
  ],
  "isBuiltIn": true,
  "isDefault": true
}
```

**Every condition is a `new_*` metric** — SonarQube's "Clean as You Code" (CAYC) methodology,
which this server's built-in gate enforces exclusively. `new_*` metrics are computed against a
**leak period** (`GET /api/qualitygates/project_status?projectKey=Automation-POC` shows this
project's own period is `PREVIOUS_VERSION`, dated `2026-04-29`) — i.e. "what changed since the
last analyzed version," never "what the whole accumulated codebase currently is."

**This is exactly the distinction CP3 already gates on for its own per-run scope** (CP3's Sonar
criterion is, itself, evaluating this same `new_*`-scoped gate — a fact this discovery surfaces
as relevant context, not a defect in CP3's own already-shipped, Accepted design, and not
re-litigated here). **For CP7, which must govern what the SUITE HAS BECOME as a whole (§1.1,
below), this built-in gate is structurally the wrong tool** — a suite that has accumulated real
problems in code written and promoted many versions ago would show `new_violations: 0` forever
(nothing NEW was added this analysis), passing the built-in gate cleanly while the whole-suite
picture is not actually clean. CP7 cannot use `project_status`'s own PASS/FAIL verdict as its
gate input; it needs the suite's **absolute** metrics instead (§3.2).

**Creating a custom, whole-suite ("Overall Code") quality gate is a one-time admin action, not
something the pipeline's own token can do at runtime** — `actions.create: false` on
`/api/qualitygates/list`'s response, using the exact same `SONAR_TOKEN` the customqa profile
import already established cannot administer profiles either
(`test-suite-baseline/sonar/README.md`'s own recorded "Insufficient privileges" finding for
profile/project administration). This mirrors that precedent exactly, for a different admin
surface.

### 0.3 Absolute whole-project measures ARE readable by the pipeline's own token

`GET /api/measures/component?component=Automation-POC&metricKeys=violations,bugs,vulnerabilities,code_smells,security_hotspots,sqale_index,sqale_rating,reliability_rating,security_rating`
— using `SONAR_TOKEN`, no admin credential — returned real values for every metric requested
(all currently best-value / zero, for this platform's own real, 35-asset baseline):

```json
{"metric": "violations", "value": "0", "bestValue": true},
{"metric": "bugs", "value": "0", "bestValue": true},
{"metric": "vulnerabilities", "value": "0", "bestValue": true},
{"metric": "code_smells", "value": "0", "bestValue": true},
{"metric": "security_hotspots", "value": "0", "bestValue": true},
{"metric": "sqale_index", "value": "0", "bestValue": true},
{"metric": "sqale_rating", "value": "1.0", "bestValue": true},
{"metric": "reliability_rating", "value": "1.0", "bestValue": true},
{"metric": "security_rating", "value": "1.0", "bestValue": true}
```

**This is the mechanism CP7 should actually use**: `/api/measures/component` with absolute
(non-`new_`) metric keys, read directly, gated against explicit thresholds this design surfaces
for review (§3.2/§5) — not the quality-gate endpoint at all, and not an admin-created custom
gate, which would need the same admin action §0.2 already found is out of the pipeline token's
own reach (available as a *future* option if a team wants it, not required to build CP7).

**Two metrics requested but never returned: `coverage`, `duplicated_lines_density`.** Neither
appears in the response at all (SonarQube omits a metric key entirely rather than returning a
zero when no computation ever produced a value) — `coverage` needs an externally-submitted
JaCoCo XML report (`sonar.coverage.jacoco.xmlReportPaths`) this pipeline has never wired, even
though the JaCoCo *report-import* plugin is deployed on the server (confirmed in `docker logs`:
`Deploy JaCoCo / 1.5.1.5340`) — the plugin exists, nothing feeds it. `duplicated_lines_density`'s
absence is not conclusively explained by this discovery alone (duplication is normally computed
natively, without external input); flagged honestly as unresolved, not asserted as a capability
gap, and re-checkable once the suite has grown past its current small size.

### 0.4 Security: Sonar CE genuinely computes hotspots/vulnerabilities for Java — the review workflow is what's permission-gated, not the detection

`GET /api/rules/search?languages=java&types=SECURITY_HOTSPOT` → **36** rules. `types=VULNERABILITY`
→ **35** rules. **Community Edition's Java analyzer does evaluate real security-relevant rules**
— the LLD review's own S3/S6 framing ("Sonar's security ratings/hotspots are largely
inapplicable to test-automation code," "Sonar CE has materially reduced security-analysis
capability") is **confirmed correct in effect** (this suite currently scores `0`
vulnerabilities/hotspots, unsurprising for Selenium/Cucumber step-definition code with no
production attack surface of its own) **but was reasoning from the wrong mechanism** — CE is not
structurally blind to security rules; it runs them. What CE (or, more precisely, this pipeline's
own least-privilege token) genuinely cannot do: `GET /api/hotspots/search?projectKey=Automation-POC`
→ `{"errors":[{"msg":"Insufficient privileges"}]}`. The **aggregate count** (`security_hotspots`
measure, §0.3) is readable by the ordinary analysis token; the **per-hotspot review/triage list**
is not — the same admin-boundary shape §0.2 already found for quality-gate creation and the
customqa README already found for profile management, applied to a third surface.

### 0.5 Branch analysis — not independently re-verified live, flagged as inherited knowledge

`GET /api/project_branches/list?project=Automation-POC` returns exactly one branch (`main`),
consistent with — but not conclusive proof of — the widely-documented Community Edition
constraint that multi-branch/pull-request analysis is a Developer-Edition-and-above feature.
This document does not submit a second branch's scan to independently confirm the constraint
(that would require a real `mvn sonar:sonar -Dsonar.branch.name=...` invocation, out of this
discovery's own read-only scope) — stated honestly as inherited, publicly-documented knowledge,
not something this session verified by attempting and observing a rejection.

### 0.6 Rating model — Standard, not the newer MQR mode

`hasMQRConditions: false` / `hasStandardConditions: false` on both `/api/qualitygates/list` and
`/api/qualitygates/show` responses confirm this server runs SonarQube's legacy "Standard" rating
model (the `_rating` metrics observed in §0.3 are the familiar A–E letter grades, here shown as
their numeric equivalents — `1.0` = A), not the newer Multi-Quality-Rule/Software-Qualities
model SonarSource introduced more recently. Relevant only if a future CP7 threshold is expressed
in rating terms (§5) — noted so that choice is made against the model this server actually runs.

### 0.7 What this discovery changes about CP7's own design, stated plainly

The LLD review's S3/S6 lean ("scope security down, verify CE capability before assuming") is
**upheld**, but for a more precise reason than originally stated: not "CE can't detect security
issues for test code" (it can, and does), but **"this pipeline's own least-privilege token can
read security COUNTS but not the review workflow, and test-automation code's real security
profile is thin enough that a hard gate on it would mostly just add noise, not caught real
risk."** And the deck's own implicit assumption — that a whole-suite Sonar governance component
can simply reuse the server's own built-in quality-gate PASS/FAIL the way CP3 does — is now
known to be the wrong mechanism for whole-suite scope specifically; CP7's design below is built
on absolute measures instead, not on repeating CP3's own new-code-scoped pattern at a bigger
radius.

---

## 1. What CP7/CP8 must fulfill — the Accepted spec

ADR-0046 D1/D8 name and scope both control points; quoted in full, since this document's own
binding target:

> "CP7 | Layer 4 | Suite-wide quality (Sonar) governance — the deck's mislabeled 'CP5' | Named
> and scoped only (D8) — detailed design deferred to a future task"
>
> "CP8 | Layer 4 | Static execution-readiness governance — the deck's mislabeled static-half
> 'CP6' | Named and scoped only (D8) — detailed design deferred to a future task"

D8 itself, quoted:

> "CP7 — scope: whole-suite Sonar/code-quality governance, distinct from CP3's per-run gate...
> CP7 governs what the *entire accumulated suite* has become; CP3 (ADR-0044 D5) gates what one
> run's own generated Java produced. Without this distinction CP7 is a redundant CP3 re-run...
> CP7's security dimension must be scoped down honestly... Sonar Community Edition's actual
> claimed capabilities... must be verified against the real server before CP7 is designed in
> detail — flagged as a to-verify-before-designing item, not resolved here."
>
> "CP8 — scope: static execution-readiness governance only. Assets present, dependencies
> resolvable, build/framework configuration (`pom.xml`, Cucumber, Selenium, environment config)
> valid and well-formed — the same static-source-only posture CP4 already established (ADR-0044
> D6), no running-browser or SUT dependency. The deck's own dynamic readiness content (build
> succeeds, smoke test passes) is explicitly excluded from CP8 and from Layer 4 entirely (D1) —
> it is Layer 5's."

D1's own numbering-order note is restated here for completeness, not re-litigated: CP7/CP8
logically gate a suite *before* Layer 5's CP6 (execution) ever runs, yet carry higher numbers —
"a cosmetic consequence of control points being locked incrementally... nothing in this
platform's control-point machinery requires CP numbers to be monotonic with pipeline order."

**This document designs both in the same detail ADR-0046 D2–D6 already gave CP5** — the content
this deck's own mislabeled "CP5"/"CP6" describes (`docs/proposals/layer-4-quality-governance-lld.md`
§6–§16), now under its correct numbers, informed by §0's live discovery.

## 2. The CP3 `customqa:*` honesty arc — what CP7 inherits, does not restart

ADR-0046 D8 requires this explicitly: *"CP7 must inherit CP3's own honest Sonar profile/scope
story, never restart it."* Restated here, from this repository's own real build history
(`docs/architecture/architecture-baseline-v2.md` items 18/21/24; ADR-0044 D5's three revision
notes), as the facts CP7's own design must carry forward rather than re-derive or re-assume:

1. **Sonar performs generic Java quality analysis only.** The `customqa` profile
   (`test-suite-baseline/sonar/customqa-profile.xml`) is a full copy of the built-in `Sonar way`
   baseline (549 rules) — CP3's Sonar criterion gates on *that*, never on this platform's own
   architectural rules.
2. **This platform's own architectural rules (`direct-webdriver-action`, `long-method`) are
   static Python checks, not Sonar rules** (`automation_engineering/cp3/architecture.py`) —
   discovered, not assumed, after `java:S138` (the rule `long-method` was originally meant to
   map to) turned out permanently `scope:"MAIN"`, structurally unable to ever evaluate this
   platform's `src/test/java`-resident generated code, on any server, regardless of correct
   profile assignment.
3. **`scope:MAIN` vs. the test tree is a real, load-bearing constraint, not a one-off.** Every
   class Layer 3 generates or promotes lives under `src/test/java` (ADR-0037 Path A). Any future
   CP7 rule reasoning ("does Sonar check X") must ask, specifically, whether the rule's own
   `scope` metadata covers `TEST` as well as `MAIN` — §0's own discovery did not re-derive this
   per-rule (out of this document's own scope; flagged as the correct question to ask before
   CP7 leans on any specific rule beyond the whole-project aggregate measures §0.3 already
   confirmed work regardless of scope, since those are project-level rollups, not
   per-rule-scope-sensitive).
4. **The profile realities are recorded, versioned, and honestly labeled** — `customqa-profile.xml`
   carries the `S138`-at-`max=40` activation for historical/proof-of-mechanism value only; its
   real, current role is exclusively the generic-quality baseline.
5. **The adapter's own test discipline (stub-tested unit tests, a live server needed only for
   real end-to-end exercise) is the established pattern** — `automation_engineering/cp3/sonar/`'s
   `SonarQualityGateAdapter` Protocol + `StubSonarQualityGateAdapter`/`LiveSonarQualityGateAdapter`
   split. CP7 extends this seam (§3.5), not a parallel one.

CP7 is this same honest story, restated at suite scope, refined by §0's own live findings — not
a fresh "Sonar does everything" narrative.

## 3. CP7 — whole-suite Sonar quality governance

### 3.1 Relationship to CP3 — the LLD review's own S1 finding, confirmed

**S1 is confirmed as sound, distinct from its label conflict:** *"CP5 governs what the SUITE has
become (the entire accumulated baseline), CP3 gates what a single RUN produced."* Concretely:

| | CP3 (ADR-0044 D5, Accepted, live) | CP7 (this proposal) |
|---|---|---|
| Scope | This run's own freshly-generated Java classes, scanned as part of the per-run workspace project | The whole tracked baseline (`test-suite-baseline`), as it currently, accumulated stands |
| Sonar mechanism | `mvn sonar:sonar` against the workspace copy; `project_status`'s own `new_*`-scoped verdict (a hard gate) | `GET /api/measures/component` against the tracked baseline's own live-registered project (`Automation-POC`), absolute (non-`new_`) metrics (§0.2/§0.3 — the `new_*` gate is the wrong tool for this scope) |
| When it runs | Every generation batch, before promotion (stage 15) | After promotion has accumulated the suite further — naturally CP5-adjacent in the pipeline (both run after stage 15's own staging), but a distinct concern from CP5's own suite-integration checks |
| Gate discipline | Deterministic (ADR-0040 D2) | Deterministic (ADR-0040 D2, §3.4) |

CP7 does not re-scan the workspace; it reads the ALREADY-SCANNED tracked baseline's own
accumulated project-level measures. Every promoted, tracked-baseline class was already scanned
once by CP3's own per-run submission at promotion time (Sonar's project-level measures are a
running rollup of every analysis submitted against that project key, not a single-scan
snapshot) — CP7 does not need to re-submit a scan of its own; **it reads what already
accumulated from every prior CP3 run**, the same "the code IS the effective source of truth,
reconciled fresh" posture `automation_engineering.catalog.scanner.reconcile` already establishes
for the catalog (ADR-0044 D3), applied to Sonar's own project-level measures instead of the
Java-source catalog.

**Without this distinction, CP7 would be a redundant CP3 re-run (D8's own words) — it is not
one**, because it reads a materially different signal (accumulated project measures, not a
fresh per-run scan) even when, mechanically, no new `mvn sonar:sonar` submission is required
to produce it.

### 3.2 What CP7 checks — absolute measures, explicit thresholds, not the built-in gate

Per §0.2/§0.3's own findings, CP7's mechanism is: fetch a named set of ABSOLUTE metric keys via
`/api/measures/component` for the tracked baseline's own project key
(`DEFAULT_SONAR_PROJECT_KEY = "Automation-POC"`, the same constant `automation_engineering/stage/runner.py`
already defines and CP7 should reuse, not re-declare), and gate on each against an explicit
threshold — never the server's own built-in `project_status` PASS/FAIL, which is new-code-scoped
and therefore structurally answers a different question (§0.2).

Proposed metric families (real metric keys, all confirmed present in this server's own 149-entry
`/api/metrics/search` catalog, §0.3's own live query):

- **Generic quality** — `violations` (all Sonar-flagged issues, project-wide), `bugs`,
  `code_smells`, `sqale_rating` (maintainability rating) — the direct, whole-suite analogue of
  what CP3 already gates per-run, per the `customqa`-profile's own now-exclusive role (§2 point 1).
- **Reliability** — `reliability_rating` — a real, currently-clean (`1.0`) metric this session
  confirmed is populated and readable.
- **Coverage / duplication** — `coverage`, `duplicated_lines_density` — metric keys exist in the
  catalog but returned no value for this project (§0.3): **CP7 cannot honestly gate on either
  today.** Wiring `sonar.coverage.jacoco.xmlReportPaths` (the JaCoCo plugin is already deployed
  server-side, confirmed live) is a separate, tracked prerequisite (§6) — not something this
  design fabricates a threshold against without real data, the same discipline ADR-0046 D3
  already used for the near-dup cluster threshold ("configurable default... resolve/tune against
  real observed... data").
- **Security — informational, not gating (§0.4/§0.7's own reasoning, surfaced for review, not
  locked here):** `vulnerabilities`, `security_hotspots`, `security_rating`, all confirmed
  readable by the pipeline's own least-privilege token. Proposed as REPORTED in CP7's own
  quality-metrics output, never a hard PASS/FAIL threshold — test-automation code's real security
  profile is thin (S3, confirmed not merely assumed, §0.4), and the token that would be needed to
  meaningfully TRIAGE a hotspot finding (rather than merely count it) is not one the pipeline
  holds today (§0.4's own "Insufficient privileges" finding) — gating hard on a number nobody on
  this pipeline can act on beyond "re-run the count" would manufacture false urgency, not real
  signal. A future team that wants this gated harder can revisit once a triage-capable token
  exists — recorded as an open decision (§5), not foreclosed.

### 3.3 Deterministic gate discipline (ADR-0040 Decision 2)

Every metric CP7 reads is server-computed, numeric, and compared against an explicit threshold —
"compilation results" and "coverage counts" are literally named in Decision 2's own deterministic
list, and CP7's own metrics are the identical class of evidence at a different scope. **No
LLM/embedding-derived signal participates in CP7's gate** — mirroring CP5's own D6 discipline
exactly (deterministic components gate; nothing advisory-only ever does). CP7's proposed
composition:

| Signal | Nature | Composition |
|---|---|---|
| `violations`/`bugs`/`code_smells`/`sqale_rating` (generic quality, absolute) | Deterministic | Contributes to CP7's own PASS/FAIL (threshold TBD, §5) |
| `reliability_rating` (absolute) | Deterministic | Contributes to CP7's own PASS/FAIL (threshold TBD, §5) |
| `coverage`/`duplicated_lines_density` | Deterministic, but currently unmeasured (§3.2) | Not gated until the JaCoCo-report prerequisite (§6) is closed — reported as "not yet measured," never silently treated as a pass |
| `vulnerabilities`/`security_hotspots`/`security_rating` | Deterministic | Reported only, never gates (§3.2's own reasoning) — the same "surfaced, not gating" shape ADR-0046 D6 already gives CP5's own near-dup sweep, for a different reason (there: inherently advisory evidence; here: a real signal this pipeline cannot yet meaningfully act on) |

Action on a CP7 fail: **flag for review**, joining the same shared human review queue every
other control point in this platform already uses (ADR-0045 D3/Recommendation 2's own "one
queue, not a new one per layer" discipline, restated as binding on CP7 too, mirroring how CP5's
own promotion-wrap already extended it, `suite_quality_governance/cp5/promotion_wrap.py`'s own
module docstring) — never an auto-fix, consistent with every deterministic gate this platform
has built so far.

### 3.4 What building CP7 needs — a real, new capability, not yet built anywhere

`automation_engineering/cp3/sonar/adapter.py`'s own `SonarQualityGateAdapter` Protocol has three
methods today: `submit_scan`, `poll_for_completion`, `fetch_quality_gate_result` — **none of
which fetches absolute measures**. CP7 needs a fourth capability this Protocol does not have:
something shaped like `fetch_measures(project_key: str, metric_keys: Sequence[str]) ->
Cp7MeasuresResult`, hitting `/api/measures/component` (§0.3's own confirmed-working endpoint),
mirroring the identical stub/live seam split every other live-infrastructure boundary in this
platform already uses (`StubSonarQualityGateAdapter`/`LiveSonarQualityGateAdapter`,
`StubCompileChecker`/`LiveCompileChecker`). This is new build work — named here, not built by
this design document (§7).

Whether CP7 extends the EXISTING `SonarQualityGateAdapter` Protocol with this fourth method, or
introduces a second, narrower Protocol scoped to measures-fetching only, is itself an open
decision (§5) — both are structurally sound; this document does not pick one.

## 4. CP8 — static execution-readiness governance

### 4.1 What CP8 checks, concretely — grounded in this platform's own real config, not invented

D8's own text names four categories: assets present, dependencies resolvable, build/framework
configuration valid, environment configuration valid. Mapped onto this platform's own real,
inspected files (`test-suite-baseline/`), not a hypothetical:

1. **Assets present.** `test-suite-baseline/src/test/resources/features/` contains at least one
   `.feature` file; `src/test/java/` contains at least one step-definition class (the catalog,
   `automation_engineering.catalog.scanner.reconcile`, already derives exactly this — CP8 reuses
   it, does not rescan, mirroring CP5's own D7 "reuse, don't rebuild" discipline). A tracked
   runner class exists (`src/test/java/com/automation/runners/RunCucumberTest.java`, confirmed
   present, real, in this repository today).
2. **Build/framework configuration valid.** `pom.xml` parses as well-formed XML and DECLARES the
   dependencies the suite structurally needs to compile and run under Cucumber-on-JUnit-Platform
   — confirmed, by direct inspection, that this platform's own real `pom.xml` declares exactly
   these: `cucumber-java`, `cucumber-junit-platform-engine`, `junit-jupiter-api`,
   `junit-platform-suite`, `junit-platform-launcher`, `selenium-java` (plus
   `maven-compiler-plugin`/`maven-surefire-plugin`). CP8 checks these artifact ids are DECLARED —
   a pure, static XML-presence check, never "are they actually resolvable from a repository"
   (§4.2 explains why that stronger form is deliberately NOT CP8's own job).
3. **Cucumber/JUnit config valid.** `src/test/resources/junit-platform.properties` (confirmed
   present, real, in this repository today) exists and parses as a well-formed properties file;
   its `cucumber.glue` value names at least one package that genuinely contains a class in the
   assembled suite (a real, catchable misconfiguration a Java compiler is structurally blind to —
   see §4.2); its `cucumber.plugin` value's declared output paths are well-formed relative paths,
   not malformed strings that would fail Cucumber's own plugin-string parser at runtime before a
   single scenario executes.
4. **Environment configuration.** Scoped, deliberately, to the ASSEMBLED SUITE'S OWN execution
   config (the items above) — not this platform's own pipeline `.env` (`SONAR_TOKEN`,
   `GOOGLE_API_KEY`, etc.), which is this platform's OWN runtime configuration, not the generated
   test suite's. Whether Layer 5's own execution environment needs a distinct, suite-facing
   config surface (e.g. `WebDriver` target URLs, browser selection) that CP8 should also validate
   is an open decision (§5) — no such config currently exists in this repository to inspect, so
   this document does not invent a shape for it.

Each check above is deterministic, pure-Python, and requires no JDK, no Maven invocation, no
network call — genuinely static, mirroring CP4's own "no running-browser or SUT dependency"
posture (ADR-0044 D6) that D8 itself cites as CP8's own precedent.

### 4.2 The CP5-cohesion boundary — a deliberate, non-redundant overlap, not an accidental one

**CP5-cohesion (`suite_quality_governance/cp5/cohesion.py`, ADR-0046 D5, already built) answers
"does the assembled suite COMPILE"** — a real `mvn test-compile` invocation, the authoritative,
expensive-but-conclusive proof that every class's syntax is valid and every dependency it
actually references resolves. **CP8 answers a different question: "is the suite CONFIGURED to
be EXECUTABLE"** — never invoking `mvn`, never proving resolvability the strong way, checking
instead that the DECLARATIONS a build/execution would need are present and well-formed.

**The honest overlap, stated plainly:** if `pom.xml` were missing `cucumber-java` entirely, BOTH
CP8 (a static "is it declared" check) and CP5-cohesion (a real compile, which would fail for the
same underlying reason) would object. This is not wasted duplication — it is a cheap, fast
pre-check (CP8, pure XML parsing, no JDK/network) surfacing an obvious misconfiguration BEFORE a
much more expensive compile is even attempted, the same "fail fast on the cheap check first"
discipline `AssetGateOutcomes.first_failure`'s own CP2-before-CP3-before-CP4 ordering already
uses one layer down (`automation_engineering/promotion/models.py`).

**Where they do NOT overlap — CP8 catches what compiling structurally cannot:** `cucumber.glue`
pointing at a package with zero classes in it, or a step-definition package that compiles fine
in isolation but is simply never named in `cucumber.glue`, is **invisible to `mvn test-compile`**
— a Java compiler has no concept of Cucumber's own runtime glue-scanning convention; the suite
would compile perfectly clean and then discover, only at Layer 5 execution time, that zero steps
matched. This is CP8's own, genuinely distinct value: catching Cucumber-specific
runtime-configuration defects a compile step is structurally blind to, before Layer 5 ever
attempts to run anything.

**Composition, proposed:** CP8 runs BEFORE CP5-cohesion's own compile check (cheaper, so it
should fail first if it's going to fail at all) — but this document does not require CP8 and
CP5-cohesion be composed into one combined verdict; they remain two, separately-reportable
checks, mirroring how CP3's own coverage criteria and its Sonar criterion stay two named
criteria inside one composite result rather than collapsing into an undifferentiated boolean.

### 4.3 The Layer 5 boundary — static readiness vs. dynamic execution

D1/D8 both already draw this line; restated here as CP8's own structural contract: CP8 never
invokes a build that EXECUTES anything (`mvn test`, not merely `mvn test-compile`), never
launches a browser, never touches a SUT. "Does the suite then successfully run" (a real `mvn
test` / smoke-scenario execution) is Layer 5's, unconditionally, per ADR-0046 D5's own text
already establishing this exact static/live boundary for CP5-cohesion's neighbor check — D1
restates the same boundary applies to CP8 by name ("The deck's own dynamic readiness content...
is explicitly excluded from CP8 and from Layer 4 entirely").

### 4.4 Dependency resolvability, without a build — the honest scope

D8's own text names "dependencies resolvable" as a CP8 check. **The strong form — are these
artifacts actually downloadable from a real Maven repository right now — needs either a network
call or a real `mvn` invocation, crossing into CP5-cohesion's own territory** (a successful
compile already proves every declared dependency resolved; that's what compiling means).
**CP8's own honest scope is the weak, purely-static form: are the RIGHT dependencies DECLARED at
all** (§4.1 point 2) — a pom.xml XML-parse-and-presence check, nothing more. This is a
deliberate scope decision, not an oversight: claiming CP8 verifies "resolvable" in the strong
sense would silently duplicate what CP5-cohesion already proves more authoritatively, the same
"no second mechanism for what one component already does" discipline ADR-0046 D7 already locks
for CP5's own four components, extended here across control points.

### 4.5 Deterministic gate discipline (ADR-0040 Decision 2)

Every CP8 check above is a pure, deterministic file-presence/parse/reference check — no
LLM/embedding evidence anywhere. Action on fail: **flag for review**, the same shared queue CP7
and every prior control point already join (§3.3) — never auto-fix a missing asset or a
malformed config file, mirroring CP5's own "flag, never auto-act" posture (ADR-0046 D2/D3,
Recommendation 2) for the identical reason: a missing feature file or a wrong glue package could
be a genuine defect OR a mid-refactor, in-progress state a human is the right party to judge —
this is not the class of thing a deterministic gate should silently "fix."

## 5. Open decisions surfaced for review

**CP7:**

1. **Exact gate thresholds for `violations`/`bugs`/`code_smells`/`sqale_rating`/
   `reliability_rating`** — this document surfaces the metric families (§3.2) and confirms they
   are real, currently-readable, currently-clean values; it does not lock a threshold. Mirroring
   ADR-0046 D3's own "configurable default, not a proven constant" posture for the near-dup
   threshold: a reasonable starting default (e.g., `violations == 0` given this suite's own
   current, real, clean measurement) should be confirmed or tuned once the suite has grown
   enough to produce a real, non-trivial measurement to calibrate against.
2. **Whether `vulnerabilities`/`security_hotspots`/`security_rating` stay report-only forever, or
   become gated once/if a triage-capable token is provisioned** — §3.2/§0.4 record the reasoning
   for report-only NOW; this is not locked as a permanent architectural stance.
3. **Whether the JaCoCo-coverage-report-submission prerequisite (§3.2, §6) is worth building
   before CP7's first implementation, or deferred to a later CP7 revision** that ships without a
   coverage/duplication gate initially (both metric families are simply unmeasured, not
   estimated, per §3.2 — an honest "not yet gated" state, not a silent pass).
4. **Whether CP7 extends `SonarQualityGateAdapter` with a fourth method, or introduces a second,
   measures-scoped Protocol** (§3.4) — both are sound; this document does not pick.
5. **Whether an admin-created custom "Overall Code" quality gate (§0.2) is ever worth pursuing**
   as an alternative to reading raw measures directly — this document's own recommendation is
   "no, read measures directly" (fewer moving parts, no new admin dependency beyond what already
   exists), but records the alternative since it is technically available to a future admin.

**CP8:**

6. **Whether Layer 5 needs its own suite-facing execution-environment config surface** (distinct
   from this platform's own `.env`) for CP8 to validate — no such config exists in this
   repository today (§4.1 point 4); this document does not invent one speculatively.
7. **The exact list of `pom.xml` artifact ids CP8 checks for** (§4.1 point 2 names this
   platform's own current, real six) — should this list be hard-coded against today's known
   dependency set, or derived from some other declared source of truth (e.g. ADR-0041's own
   stack decision)? This document leans toward hard-coding the currently-real set (simplest,
   matches what actually exists) but does not lock it.
8. **Composition: does CP8 stay a fully separate, standalone check, or does it compose into one
   combined verdict with CP5-cohesion** (§4.2's own "runs first, stays separately reported"
   lean) — surfaced, not locked, mirroring how CP5's own D6 composition rule was itself a
   locked-at-freeze decision, not assumed at design stage.

## 6. Tracked prerequisites this discovery surfaced (not CP7/CP8 build items themselves)

- **JaCoCo XML report submission is not wired anywhere in this pipeline** (§0.3/§3.2) — a
  separate, tracked build task (submitting `sonar.coverage.jacoco.xmlReportPaths` as part of
  CP3's own existing scan-submission call, `automation_engineering/cp3/sonar/live_adapter.py`)
  would need to land before CP7's own coverage/duplication gate could ever be honestly enabled.
  Not built here, not required for CP7's own first implementation (§3.2's own report-only-until
  posture for these two metrics).
- **`duplicated_lines_density`'s absence is unresolved** (§0.3) — worth a fresh live check once
  the suite has grown past its current small size, to distinguish "genuinely no duplication
  detected" from "a computation this discovery did not fully diagnose."

## 7. What CP7/CP8 do NOT do

- **CP7 is not a redundant CP3 re-run** (§3.1) — it reads accumulated, whole-project measures a
  fresh per-run scan does not need to re-produce, using a different endpoint than CP3's own
  new-code-scoped gate.
- **CP7 does not gate security hard** (§3.2/§0.4) — report-only, by design, for now.
- **CP8 does not compile anything** — CP5-cohesion's own, already-built job (§4.2).
- **CP8 does not verify dependencies are actually resolvable from a repository** — CP5-cohesion's
  successful compile already proves that, more authoritatively (§4.4).
- **CP8 does not run anything, launch a browser, or touch a SUT** — Layer 5's, unconditionally
  (§4.3).
- **Neither CP7 nor CP8 is CP5's own suite-integration governance** (orphaned-glue,
  near-duplicate sweep, promotion-wrapping, aggregate cohesion) — that is a separate, already-
  frozen-and-built control point (ADR-0046 D2–D7); this document designs the two DIFFERENT
  control points ADR-0046 D8 named and scoped but deferred.
- **This document builds no code and freezes no ADR.** It is a design proposal — analogous in
  status to `docs/proposals/layer-4-cp5-suite-integration-governance-design.md` before ADR-0046
  graduated its own eight open decisions into binding Decision text. A future task may do the
  same for CP7/CP8's own open decisions (§5) at a future freeze.

## 8. Confirmation

- Clean tree, `main`, pushed tip, at the point this design began (`15e12cd`, "CP5 wiring").
  `make lint`: clean. `make test`: 5491 passed, unchanged (documentation-only task; no source
  file under test was touched).
- §0's Sonar CE discovery is live, direct, and verified this session (edition, quality-gate
  scope, absolute-measures readability, hotspot rule existence vs. review-permission boundary,
  branch-analysis note flagged as inherited not independently re-proven) — not carried forward
  from any prior assumption in ADR-0046 or the LLD review.
- CP7 and CP8 are both designed at the same level of detail ADR-0046 D2–D6 gave CP5: what each
  checks, how each relates to its nearest existing neighbor (CP3 for CP7; CP5-cohesion and Layer
  5 for CP8), each one's gate discipline (both deterministic, ADR-0040 D2), and what new build
  work either would require.
- No code was written. No ADR Decision text was changed. This document itself is Proposed —
  design only, informing a future CP7/CP8 design-then-freeze task, mirroring the two-step
  process ADR-0046 itself already completed for CP5.
