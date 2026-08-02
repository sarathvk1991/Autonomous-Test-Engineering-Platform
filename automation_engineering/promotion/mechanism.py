"""Promotion's mechanism (ADR-0045 D5): write a promoted candidate's Java
source into the tracked baseline, then STAGE (never auto-commit) the
resulting git-visible change.

**Resolves D5's auto-commit-vs-stage TBD: stage-for-review.** ADR-0037
originally locked "promotion ... is an explicit, reviewed step -- never
automatic"; ADR-0045 D3 narrows that -- a CLEAN, validated, non-duplicate
asset no longer needs a human to decide WHETHER it promotes. But D3 answers
a different question than D5 does. D3 is about the PROMOTION DECISION (is
this asset safe to move into the baseline at all); D5 is about the
resulting GIT HISTORY (does that move become a commit without anyone
looking at the diff first). Auto-promoting a clean asset does not imply
auto-committing it: ADR-0037's "explicit, reviewed step" language was never
about second-guessing D2/D3's own safety judgment (content-hash identity,
CP2/CP3/CP4 gates) -- it was about a human having eyes on a tracked-baseline
change before it lands, the same posture this platform already takes for
every other tracked-baseline mutation. This module therefore ``git add``s
the promoted file (staged, diffable, visible in `git status`/`git diff
--cached`) and never calls ``git commit`` -- the commit itself is left to
whatever review/merge flow the surrounding repository already uses.

This costs nothing structurally: :func:`automation_engineering.catalog.
scanner.reconcile` reads the WORKING TREE directly, not git's index or
history, so a staged-but-uncommitted promoted asset is already visible to
the very next run's catalog reconciliation (proven in
``tests/unit/test_automation_engineering_promotion_loop.py``'s loop-closing
proof). Whether the change is committed only matters for the repository's
own durable history -- never for whether the reuse loop itself closes.
"""

from __future__ import annotations

import subprocess
from collections.abc import Sequence
from pathlib import Path

from automation_engineering.catalog.scanner import JAVA_SOURCE_SUBPATH
from automation_engineering.promotion.models import Promoted


def apply_promotion(promoted: Promoted, baseline_root: Path) -> Path:
    """Write ``promoted.candidate``'s Java source into ``baseline_root`` at
    its own relative path (``src/test/java/<package>/<ClassName>.java``),
    creating parent directories as needed. Returns the written path.

    Writes ``candidate.java_source`` directly (not a filesystem copy off a
    workspace path) -- that string IS the exact content
    :mod:`.identity` computed the candidate's ``content_hash`` from, so the
    promoted file and the identity that gated its promotion can never drift
    apart.
    """
    target = baseline_root / JAVA_SOURCE_SUBPATH / promoted.candidate.relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(promoted.candidate.java_source, encoding="utf-8")
    return target


def stage_promoted_assets(paths: Sequence[Path], repo_root: Path) -> None:
    """``git add`` the promoted files -- the git-visible half of D5's
    mechanism (module docstring: stage, never commit). A no-op for an empty
    ``paths``. Requires ``repo_root`` to be inside a git working tree (true
    of this platform's own ``test-suite-baseline/``, tracked in the main
    repository).
    """
    if not paths:
        return
    subprocess.run(  # noqa: S603 - fixed argv, no shell, no untrusted input
        ["git", "add", "--", *(str(p) for p in paths)],  # noqa: S607 - `git` resolved via PATH
        cwd=repo_root,
        check=True,
        capture_output=True,
    )


__all__ = ["apply_promotion", "stage_promoted_assets"]
