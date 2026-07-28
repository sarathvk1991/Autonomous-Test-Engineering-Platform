"""Per-run workspace materialization (ADR-0037, Path A).

ADR-0037 requires generated features to land in an UNTRACKED, PER-RUN
workspace, structurally distinct from the TRACKED baseline module -- so
Layer 6 self-healing's blast radius is bounded to one run's disposable
output, never the framework every run depends on (ADR-0037 D2). The
initial stage-14 wiring did not honor this: callers had to supply a
`features_root` directly, and the only committed candidate value anywhere
(`feature_engineering.generation.assembler.DEFAULT_FEATURES_ROOT`) points at
the single, SHARED, tracked `test-suite-baseline/src/test/resources/features/`
path. Two runs -- or a run and the tracked source -- would share one
directory, exactly the sharing ADR-0037 D2 exists to prevent.

This module fixes that: :func:`materialize_workspace` gives each run its own
isolated copy of the tracked baseline module, under that run's own directory
(`output/executions/<run_id>/workspace/` -- untracked, since `output/` is
repo-root-`.gitignore`d, per `.gitignore:39`) -- so
`@SelectClasspathResource("features")` (ADR-0041) resolves within the copy,
never against the tracked module or another run's copy.

Materialization choice: **full copy**, not a symlinked framework or a git
worktree. The tracked baseline is tiny (11 tracked files, ~52KB via
`git ls-files test-suite-baseline/`) -- duplicating it per run is trivially
cheap, and a full copy needs no read-only enforcement (a symlink approach
would require preventing writes through the links) and no coupling to git
(a worktree would tie a disposable, potentially-healed workspace to a git
ref). Correct and simple beats clever and coupled for a foundation piece.

Idempotent and resume-safe: if the run's workspace directory already
exists, it is returned UNCHANGED -- never re-copied, never wiped. A resumed
run must find its own prior generation intact, not a fresh baseline copy
that destroys it (the one real hazard Path A introduces).
"""

from __future__ import annotations

import shutil
from pathlib import Path

#: The tracked baseline module Path A copies FROM -- source only, a run
#: never writes to this path.
DEFAULT_BASELINE_ROOT = Path("test-suite-baseline")

#: Relative to a run's workspace copy -- the fixed path ADR-0041's
#: `@SelectClasspathResource("features")` requires.
FEATURES_SUBPATH = Path("src/test/resources/features")

#: Never copied into a run's workspace: `target/` is Maven build output
#: (regenerated, not source); `workspace/` is the baseline's own reserved,
#: currently-empty name (`test-suite-baseline/.gitignore`) -- excluded
#: defensively in case a future baseline-side use of that name appears.
_EXCLUDED_NAMES = frozenset({"target", "workspace"})


def _ignore_build_output(_directory: str, names: list[str]) -> set[str]:
    return {name for name in names if name in _EXCLUDED_NAMES}


def materialize_workspace(run_dir: Path, *, baseline_root: Path = DEFAULT_BASELINE_ROOT) -> Path:
    """Return this run's own isolated workspace directory.

    Creates it -- a full copy of `baseline_root`, excluding build output --
    the first time. Idempotent: a second call for the SAME `run_dir` (a
    resumed run, or a second stage-14 attempt within one run) returns the
    existing workspace untouched, never re-copying and never wiping
    whatever generation already landed there.
    """
    workspace_dir = run_dir / "workspace"
    if workspace_dir.exists():
        return workspace_dir
    shutil.copytree(baseline_root, workspace_dir, ignore=_ignore_build_output)
    return workspace_dir


def features_root_for(workspace_dir: Path) -> Path:
    """The fixed, ADR-0041-required features path within one run's own
    materialized workspace."""
    return workspace_dir / FEATURES_SUBPATH


__all__ = [
    "DEFAULT_BASELINE_ROOT",
    "FEATURES_SUBPATH",
    "features_root_for",
    "materialize_workspace",
]
