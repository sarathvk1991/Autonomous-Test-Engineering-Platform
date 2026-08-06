# Suite Quality Governance Layer (Layer 4)

**Status:** Build started (ADR-0046). CP5 (suite-integration governance,
ADR-0040 Decision 3) — component 1 of 4, orphaned-glue detection
(`cp5/orphaned_glue.py`, `cp5/pattern_matching.py`, `cp5/models.py`) — is
built. The remaining three CP5 components (cross-suite near-duplicate
sweep, promotion-wrapping, aggregate-release cohesion, ADR-0046 D3–D5) and
CP7/CP8 (suite Sonar governance, static execution readiness, ADR-0046 D8)
are not yet built. No `router`/API surface exists yet — CP5 today has a
pure Python function surface (`suite_quality_governance.cp5.
detect_orphaned_glue`), no CLI or HTTP entry point, no run-state stage
wiring.

Validates the accumulated automation suite as a whole (Layer 4, per
ADR-0031: "Suite Quality Governance") — consumes Layer 3's Validated
Automation Package and the catalog/reuse-engine machinery Layer 3 already
built (`automation_engineering/catalog/`, `automation_engineering/reuse/`),
per ADR-0046 D7's "reuses, does not rebuild" discipline.

This package follows the same internal structure as the Requirement
Intelligence Layer (`api/`, `services/`, `models/`, `tests/`, …) and will
expose a `router` mounted in `app/api/router.py` once a runtime surface is
built.
