"""Atomic JSON writes for run_state.json.

Every write is temp-file + fsync + rename: the temp file is created in the
SAME directory as the target (so the final rename is on one filesystem, hence
atomic on POSIX), flushed and fsynced before the rename, and the rename itself
(``os.replace``) is the single atomic step that makes the new content visible.
An interrupted write leaves either the untouched prior file or nothing new at
all — never a torn, half-written target.
"""

from __future__ import annotations

import contextlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any


def atomic_write_json(path: Path, obj: dict[str, Any]) -> None:
    """Write *obj* to *path* as JSON, atomically."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(obj, handle, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    except BaseException:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(tmp_name)
        raise


def read_json_if_valid(path: Path) -> dict[str, Any] | None:
    """Return the parsed JSON at *path*, or ``None`` if missing/unparseable.

    Used by the skip predicate's well-formedness check (invariant (b)): a
    present-but-corrupt file must never be treated as a valid, skippable
    output.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except (FileNotFoundError, OSError):
        return None
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


__all__ = ["atomic_write_json", "read_json_if_valid"]
