"""Execution history — directory layout, history, and ``latest/`` management.

Owns *where* an execution package is written. It resolves the target directory
(``latest/``, a timestamped history dir, or a named history dir), creates it, and
keeps ``latest/`` in sync by copying (never symlinking, for cross-platform
compatibility). It never overwrites a previous execution.
"""

from __future__ import annotations

import shutil
from datetime import UTC, datetime
from pathlib import Path


def _clear_dir(directory: Path) -> None:
    """Remove *directory* if present and recreate it empty."""
    if directory.exists():
        shutil.rmtree(directory)
    directory.mkdir(parents=True, exist_ok=True)


def _copy_into(src: Path, dest: Path) -> None:
    """Replace *dest* with a fresh copy of *src* (copy, not symlink)."""
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest)


def _unique_dir(base: Path, name: str, separator: str) -> Path:
    """Return a non-existing directory ``base/name`` with a suffix on collision."""
    candidate = base / name
    counter = 1
    while candidate.exists():
        candidate = base / f"{name}{separator}{counter}"
        counter += 1
    return candidate


class ExecutionHistory:
    """Resolve and manage execution output directories under a base path."""

    def __init__(self, output_base: Path) -> None:
        """Create a history manager rooted at *output_base* (e.g. output/executions)."""
        self.output_base = output_base
        self.latest_dir = output_base.parent / "latest"

    def resolve_target(
        self, *, save_execution: bool, execution_name: str | None = None
    ) -> Path:
        """Return the directory to write this execution into.

        * Not persisted          -> ``latest/`` (refreshed each run).
        * Persisted, named        -> ``<base>/<name>`` (``-1``, ``-2`` on collision).
        * Persisted, unnamed      -> ``<base>/<timestamp>`` (``_1`` on collision).
        """
        if not save_execution:
            return self.latest_dir
        if execution_name:
            return _unique_dir(self.output_base, execution_name, "-")
        stamp = datetime.now(UTC).strftime("%Y-%m-%d_%H-%M-%S")
        return _unique_dir(self.output_base, stamp, "_")

    def prepare(self, target_dir: Path) -> None:
        """Create *target_dir*; clear it first only when it is ``latest/``."""
        if target_dir == self.latest_dir:
            _clear_dir(target_dir)
        else:
            target_dir.mkdir(parents=True, exist_ok=True)

    def finalize(self, target_dir: Path, *, save_execution: bool) -> None:
        """Refresh ``latest/`` from a persisted history directory."""
        if save_execution and target_dir != self.latest_dir:
            _copy_into(target_dir, self.latest_dir)
