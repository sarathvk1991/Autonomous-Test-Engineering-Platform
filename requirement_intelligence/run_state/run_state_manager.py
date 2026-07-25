"""RunStateManager — the single owner of run_state.json's lifecycle.

Wraps the atomic writer, the stage-status transitions, the skip predicate, and
the contract_version global-invalidation check (ADR-0036 + this
implementation's TBD resolutions, all reported in the module/function
docstrings below rather than silently decided).
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from requirement_intelligence.run_state.atomic_write import atomic_write_json, read_json_if_valid
from requirement_intelligence.run_state.models import RunState, StageError, StageRecord, StageStatus
from requirement_intelligence.run_state.stages import STAGE_DEFINITIONS

_RUN_STATE_FILENAME = "run_state.json"


class RunStateCorruptError(RuntimeError):
    """Raised when run_state.json exists but cannot be parsed into a RunState.

    Distinct from "no run_state.json at all" (a legitimate legacy-run case,
    handled by ``RunStateManager.try_load`` returning ``None``, never raising)
    — this is a genuine corruption of a file this implementation itself wrote.
    """


def generate_run_id() -> str:
    """Mint a platform-assigned run_id: compact UTC timestamp + 8 hex chars.

    ADR-0036 leaves the exact scheme an implementation TBD ("format,
    timestamp-derived vs. random vs. content-addressed") and locks only that
    it is platform-assigned, unique per invocation, and is the path, not the
    label. This is the chosen scheme, flagged as this implementation's choice,
    not an ADR mandate: sortable (chronological directory listing), collision-
    resistant even for two invocations in the same microsecond (the random
    suffix), filesystem-safe on every OS (no colons), stdlib only.
    """
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%f")
    suffix = uuid4().hex[:8]
    return f"run-{timestamp}Z-{suffix}"


def _hash_artifacts(paths: Sequence[Path]) -> str:
    """sha256 over sorted (path, content-sha256) pairs. A missing file
    contributes a stable sentinel so a removed input changes the hash too —
    the hash always reflects "what is on disk right now", never a cached
    assumption."""
    entries: list[tuple[str, str]] = []
    for path in sorted(paths, key=str):
        if path.exists():
            entries.append((str(path), hashlib.sha256(path.read_bytes()).hexdigest()))
        else:
            entries.append((str(path), "<missing>"))
    payload = json.dumps(entries, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _initial_stages() -> tuple[StageRecord, ...]:
    return tuple(
        StageRecord(
            stage_id=definition.stage_id,
            stage_number=definition.stage_number,
            layer=definition.layer,
            name=definition.name,
            status=StageStatus.PENDING,
        )
        for definition in STAGE_DEFINITIONS
    )


class RunStateManager:
    """Owns one run's ``run_state.json``: creation, loading, stage
    transitions, the skip predicate, and contract_version invalidation."""

    def __init__(self, run_dir: Path, state: RunState) -> None:
        self._run_dir = run_dir
        self._path = run_dir / _RUN_STATE_FILENAME
        self._state = state

    @property
    def path(self) -> Path:
        return self._path

    @property
    def state(self) -> RunState:
        return self._state

    # -- construction --------------------------------------------------

    @classmethod
    def create(
        cls, run_dir: Path, *, run_id: str, execution_name: str | None, contract_version: str
    ) -> RunStateManager:
        """Start a brand-new run: every stage PENDING."""
        now = datetime.now(UTC)
        state = RunState(
            run_id=run_id,
            execution_name=execution_name,
            created_at=now,
            updated_at=now,
            contract_version=contract_version,
            stages=_initial_stages(),
        )
        manager = cls(run_dir, state)
        manager._persist()
        return manager

    @classmethod
    def try_load(cls, run_dir: Path, *, current_contract_version: str) -> RunStateManager | None:
        """Load an existing run's state, applying contract_version global
        invalidation if needed.

        Returns ``None`` if ``run_state.json`` does not exist at all — the
        legitimate, expected case for a pre-Part-3 run directory named by
        ``--execution-name`` under the old convention (backward-compatible
        reading: no crash, no exception, an explicit ``None`` the caller must
        handle and report). Raises :class:`RunStateCorruptError` if the file
        exists but cannot be parsed — a genuine corruption of a file this
        implementation itself is supposed to have written correctly, which
        must not be silently treated as "no state" (that would silently
        discard real progress).
        """
        path = run_dir / _RUN_STATE_FILENAME
        if not path.exists():
            return None
        raw = read_json_if_valid(path)
        if raw is None:
            raise RunStateCorruptError(
                f"{path} exists but is not valid JSON — refusing to silently treat "
                "this run as having no recorded state."
            )
        state = RunState.model_validate(raw)

        if state.contract_version != current_contract_version:
            # CONTRACT_VERSION CHANGE = GLOBAL INVALIDATION (never per-stage hash
            # diffing across versions — a version bump changes the hashed field
            # set by design, so hashes from a different contract_version are not
            # comparable at all). Every stage resets to PENDING; run_id,
            # execution_name, and created_at are preserved (same run identity,
            # invalidated progress).
            state = state.model_copy(
                update={
                    "contract_version": current_contract_version,
                    "updated_at": datetime.now(UTC),
                    "stages": _initial_stages(),
                }
            )

        manager = cls(run_dir, state)
        manager._persist()  # the invalidation itself (if any) must be durable
        return manager

    # -- stage transitions -----------------------------------------------

    def start_stage(self, stage_id: str, *, input_artifacts: Sequence[Path] = ()) -> None:
        """Mark *stage_id* RUNNING. Records the input-artifact hash now (over
        whatever exists on disk at start time) for a later skip decision."""
        now = datetime.now(UTC)
        content_hash = _hash_artifacts(input_artifacts) if input_artifacts else None
        self._update(
            stage_id,
            status=StageStatus.RUNNING,
            started_at=now,
            ended_at=None,
            input_artifacts=tuple(str(p) for p in input_artifacts),
            content_hash=content_hash,
            error=None,
        )

    def succeed_stage(self, stage_id: str, *, output_artifacts: Sequence[Path] = ()) -> None:
        self._update(
            stage_id,
            status=StageStatus.SUCCEEDED,
            ended_at=datetime.now(UTC),
            output_artifacts=tuple(str(p) for p in output_artifacts),
        )

    def fail_stage(self, stage_id: str, *, error: BaseException) -> None:
        self._update(
            stage_id,
            status=StageStatus.FAILED,
            ended_at=datetime.now(UTC),
            error=StageError(error_type=type(error).__name__, message=str(error)),
        )

    def skip_stage(self, stage_id: str) -> None:
        """Mark *stage_id* SKIPPED. Caller must have already confirmed
        :meth:`should_skip` — this method performs no check itself."""
        self._update(stage_id, status=StageStatus.SKIPPED, ended_at=datetime.now(UTC))

    # -- skip predicate ----------------------------------------------------

    def should_skip(
        self,
        stage_id: str,
        *,
        input_artifacts: Sequence[Path] = (),
        output_artifacts: Sequence[Path] = (),
    ) -> bool:
        """Whether *stage_id* may be marked SKIPPED on resume.

        Both invariants must hold; hash-match alone is never sufficient
        (content_hash answers "did the declared inputs change", never "is the
        prior output still present and valid" — a stage whose hash matches but
        whose output is missing or corrupt must re-run):

        (a) the stage previously SUCCEEDED, and its declared inputs' content
            hash, recomputed now, still matches the hash recorded when it ran;
        (b) every declared output artifact exists, and — for ``.json``
            artifacts — parses as valid JSON. A present-but-corrupt or
            present-but-truncated output is treated exactly like a missing one.
        """
        record = self._find(stage_id)
        if record.status != StageStatus.SUCCEEDED:
            return False

        # invariant (a)
        current_hash = _hash_artifacts(input_artifacts) if input_artifacts else None
        if record.content_hash != current_hash:
            return False

        # invariant (b)
        for artifact in output_artifacts:
            if not artifact.exists():
                return False
            if artifact.suffix == ".json" and read_json_if_valid(artifact) is None:
                return False
        return True

    # -- resume --------------------------------------------------------

    def first_non_succeeded_stage_id(self) -> str | None:
        """The stage id to resume from, per ADR-0036's resume semantics
        (first non-SUCCEEDED in execution/dependency order — see
        ``stages.py`` for why this is NOT ADR-0036's literal "#" order).
        ``None`` if every stage has already succeeded."""
        for record in self._state.stages:
            if record.status != StageStatus.SUCCEEDED:
                return record.stage_id
        return None

    # -- internal --------------------------------------------------------

    def _find(self, stage_id: str) -> StageRecord:
        for record in self._state.stages:
            if record.stage_id == stage_id:
                return record
        raise ValueError(f"Unknown stage_id {stage_id!r}")

    def _update(self, stage_id: str, **updates: object) -> None:
        stages = list(self._state.stages)
        index = next(i for i, s in enumerate(stages) if s.stage_id == stage_id)
        stages[index] = stages[index].model_copy(update=updates)
        self._state = self._state.model_copy(
            update={"stages": tuple(stages), "updated_at": datetime.now(UTC)}
        )
        self._persist()

    def _persist(self) -> None:
        atomic_write_json(self._path, self._state.model_dump(mode="json", by_alias=True))


__all__ = ["RunStateCorruptError", "RunStateManager", "generate_run_id"]
