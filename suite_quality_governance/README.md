# Suite Quality Governance Layer (Layer 4)

**Status:** Build started (ADR-0046). **CP5 (suite-integration governance,
ADR-0040 Decision 3) is COMPLETE — all 4 components built:** orphaned-glue
detection (`cp5/orphaned_glue.py`, gating, ADR-0046 D2), the cross-suite
near-duplicate sweep (`cp5/near_duplicate_sweep.py`, advisory, ADR-0046
D3), promotion-wrapping (`cp5/promotion_wrap.py`, the ADR-0045-anticipated
capstone composing the other three, ADR-0046 D4), and aggregate-release
cohesion (`cp5/cohesion.py` + `cp5/compile_check.py`, gating, ADR-0046
D5). CP7/CP8 (suite Sonar governance, static execution readiness,
ADR-0046 D8 — named and scoped only, not yet designed in detail) are the
only Layer 4 work this ADR still leaves open. No `router`/API surface
exists yet — CP5 today has a pure Python function surface
(`suite_quality_governance.cp5.detect_orphaned_glue`/
`.sweep_near_duplicates`/`.evaluate_cohesion`/`.evaluate_promotion_wrap`),
no CLI or HTTP entry point, no run-state stage wiring, and is not yet
called from `automation_engineering.promotion`'s own per-asset flow (that
wiring is a future task).

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
