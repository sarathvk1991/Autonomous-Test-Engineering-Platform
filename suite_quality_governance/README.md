# Suite Quality Governance Layer (Layer 4)

**Status:** CP5 (suite-integration governance, ADR-0040 Decision 3) is
COMPLETE and WIRED. **All 4 components built:** orphaned-glue detection
(`cp5/orphaned_glue.py`, gating, ADR-0046 D2), the cross-suite
near-duplicate sweep (`cp5/near_duplicate_sweep.py`, advisory, ADR-0046
D3), promotion-wrapping (`cp5/promotion_wrap.py`, the ADR-0045-anticipated
capstone composing the other three, ADR-0046 D4), and aggregate-release
cohesion (`cp5/cohesion.py` + `cp5/compile_check.py`, gating, ADR-0046
D5). **Wired (2026-08-06):** `suite_quality_governance/stage/runner.py`
runs the capstone as ADR-0036 stage 16, immediately after stage 15's own
per-asset promotion has staged its candidates (`git add`, ADR-0046 D4) --
CLI-invocable via `analyze --with-automation-engineering
--with-suite-quality-governance` (off by default, mirroring stage 15's own
live-infrastructure posture: a JDK/Maven toolchain, an embedding
provider). Stage 16 moved from a PENDING placeholder into a real,
resumable run-state stage; see `docs/architecture/architecture-baseline-v2
.md` item 28 for the full wiring record.

**CP7 (whole-suite Sonar quality governance, ADR-0047) is BUILT, REPORT-ONLY, NOT wired.**
`cp7/measures.py::fetch_whole_suite_quality_report` reads the tracked
baseline's own already-accumulated Sonar project measures
(`violations`/`bugs`/`code_smells`/`sqale_rating`/`reliability_rating`
generic-quality; `vulnerabilities`/`security_hotspots`/`security_rating`
security; `coverage`/`duplicated_lines_density` — genuinely unmeasured on
the real server today, no JaCoCo report ever submitted) via a new
`fetch_measures` method on the SAME `SonarQualityGateAdapter` Protocol CP3
already uses (`automation_engineering/cp3/sonar/`, ADR-0047 D6 — no
second adapter). `Cp7WholeSuiteQualityReport` has no `overall_verdict`: it
is a report, not a gate (ADR-0047 D3/D4/D5 — rating-gating deferred until
the suite compiles and real scores exist; security/coverage report-only
pending their own separate prerequisites). Not yet called from any CLI
stage or run-state wiring — that is a future task, the same
"components first, wiring later" sequencing CP5's own four components
went through before stage 16 wired them.

**CP8 (static execution readiness, ADR-0047) is designed and frozen, not yet built.**

No `router`/HTTP API surface exists yet -- CP5/CP7 are reachable via CP5's
own CLI stage and via pure Python function surfaces
(`suite_quality_governance.cp5.detect_orphaned_glue`/
`.sweep_near_duplicates`/`.evaluate_cohesion`/`.evaluate_promotion_wrap`;
`suite_quality_governance.cp7.fetch_whole_suite_quality_report`).

**Real, live finding (2026-08-06, manually verified, not part of the
automated suite — see `cp5/compile_check.py`'s own docstring for why):**
running `mvn test-compile` directly against the real tracked
`test-suite-baseline/pom.xml` in this development environment returns
exit code 1 — the tracked baseline does **not** currently compile as a
whole. All 34 step-definition classes reference page-object classes
(`LoginPage`, `InventoryPage`, …) that do not yet exist under
`com.automation.pages` in the tracked baseline. This is exactly the kind
of defect CP5's `compiles` criterion (ADR-0046 D5) exists to catch, and is
independent evidence the check is meaningful, not merely well-typed.
Confirmed the invocation writes only to the already-`.gitignore`d
`target/` directory — `git status --porcelain` was clean immediately
after, with `target/` reported `!!` (ignored) by `git status --ignored`.

Validates the accumulated automation suite as a whole (Layer 4, per
ADR-0031: "Suite Quality Governance") — consumes Layer 3's Validated
Automation Package and the catalog/reuse-engine machinery Layer 3 already
built (`automation_engineering/catalog/`, `automation_engineering/reuse/`),
per ADR-0046 D7's "reuses, does not rebuild" discipline.

This package follows the same internal structure as the Requirement
Intelligence Layer (`api/`, `services/`, `models/`, `tests/`, …) and will
expose a `router` mounted in `app/api/router.py` once a runtime surface is
built.
