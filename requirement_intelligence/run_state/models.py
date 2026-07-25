"""Run and stage state models (ADR-0036).

``RunState`` is the authoritative record of one run's pipeline progress,
persisted as ``run_state.json`` at the run root, alongside the unchanged
``manifest.json`` (ADR-0036 D1 — a distinct file, a distinct charter: progress,
never package identity or contents).
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import ConfigDict, Field
from pydantic.alias_generators import to_camel

from shared.contracts.base import Schema


class StageStatus(StrEnum):
    """One of the five statuses ADR-0036 locks for every stage."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"


class StageError(Schema):
    """The error record ADR-0036 requires on a FAILED stage."""

    model_config = ConfigDict(alias_generator=to_camel)

    error_type: str
    message: str


class StageRecord(Schema):
    """One stage's identity, status, timing, declared artifacts, and (if
    FAILED) error record.

    ``stage_number`` cites ADR-0036's own "#" table column for traceability;
    it is ``None`` for the one stage this implementation carries that ADR-0036
    does not enumerate (``testable_requirement_emission`` — ADR-0034/ADR-0042,
    landed the same day as ADR-0036 without being cross-referenced into its
    stage table; see ``stages.py`` module docstring). Array position in
    ``RunState.stages`` reflects actual execution/dependency order, which
    diverges from ADR-0036's own "#" numbering for ``execution_package_write``
    (numbered 9, but the last stage to actually run) — using ADR-0036's literal
    numbering for resume order would be incorrect (see ``stages.py``).
    """

    model_config = ConfigDict(alias_generator=to_camel)

    stage_id: str
    stage_number: int | None
    layer: str
    name: str
    status: StageStatus
    started_at: datetime | None = None
    ended_at: datetime | None = None
    input_artifacts: tuple[str, ...] = Field(default_factory=tuple)
    output_artifacts: tuple[str, ...] = Field(default_factory=tuple)
    content_hash: str | None = None
    error: StageError | None = None


class RunState(Schema):
    """The complete, authoritative pipeline-progress record for one run."""

    model_config = ConfigDict(alias_generator=to_camel)

    run_id: str
    execution_name: str | None
    created_at: datetime
    updated_at: datetime
    contract_version: str
    stages: tuple[StageRecord, ...]


__all__ = ["RunState", "StageError", "StageRecord", "StageStatus"]
