# Automation Engineering Layer

**Status:** Built and wired (ADR-0044; run-state stage 15, ADR-0036). Six
subsystems — catalog (`catalog/`), reuse (`reuse/`), generation
(`generation/`), CP3 (`cp3/`), CP4 (`cp4/`), promotion (`promotion/`) — are
chained into a runnable, resumable stage by `stage/runner.py`
(`run_automation_engineering_stage`/`execute_automation_engineering_stage`),
mirroring Layer 2's own stage-14 integration shape. CLI-invocable via
`analyze --with-automation-engineering` (`scripts/run_requirement_analysis.py`,
off by default — a real, live-SonarQube-dependent stage, not folded into the
unconditional pipeline sequence). No `router`/API surface exists yet — Layer
3 today has a CLI entry point, not an HTTP one; `app/api/router.py`'s own
`automation_engineering_router` import stays commented out until that is
built.

Generate and maintain automated test code/assets from engineered features.
