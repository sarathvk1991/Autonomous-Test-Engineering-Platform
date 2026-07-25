"""Run and stage state model (ADR-0036, ADR-0032 carve-out 2).

``run_state.json`` sits at the root of each run's directory, alongside the
existing, unchanged ``manifest.json`` — the authoritative record of pipeline
progress for that run. See ``run_state_manager.RunStateManager`` for the
lifecycle API, ``stages.STAGE_DEFINITIONS`` for the stage enumeration (and its
one reported divergence from ADR-0036's literal table), ``atomic_write`` for
the temp+fsync+rename writer, and ``lockfile`` for the run-level lock.
"""

from __future__ import annotations

from requirement_intelligence.run_state.lockfile import RunLock, RunLockError
from requirement_intelligence.run_state.models import RunState, StageError, StageRecord, StageStatus
from requirement_intelligence.run_state.run_state_manager import (
    RunStateCorruptError,
    RunStateManager,
    generate_run_id,
)
from requirement_intelligence.run_state.stages import (
    LIVE_STAGE_IDS,
    PLACEHOLDER_STAGE_IDS,
    STAGE_DEFINITIONS,
    StageDefinition,
    stage_definition,
)

__all__ = [
    "LIVE_STAGE_IDS",
    "PLACEHOLDER_STAGE_IDS",
    "STAGE_DEFINITIONS",
    "RunLock",
    "RunLockError",
    "RunState",
    "RunStateCorruptError",
    "RunStateManager",
    "StageDefinition",
    "StageError",
    "StageRecord",
    "StageStatus",
    "generate_run_id",
    "stage_definition",
]
