"""Run lockfile (ADR-0036): prevents two processes operating on one run_id
concurrently.

Mechanism (ADR-0036 leaves this an implementation TBD; this is the chosen
scheme, flagged as such): a ``run.lock`` file at the run root, created via
``os.open`` with ``O_CREAT | O_EXCL`` — an atomic, kernel-enforced
create-if-absent that two processes racing to acquire the same lock cannot
both win — containing the acquiring process's PID as plain text.

Stale-lock detection is explicit: a lock is stale if its PID is missing,
unparseable, or names a process that no longer exists (checked via
``os.kill(pid, 0)`` — sends no signal, only tests whether the process could be
signalled; ``ProcessLookupError`` means no such process). A ``PermissionError``
(the PID exists but is owned by another user) is treated as LIVE, not stale —
this implementation cannot prove absence, so it must not assume it. A live
lock is never broken; a stale lock is removed and the acquisition retried
once.
"""

from __future__ import annotations

import contextlib
import os
from pathlib import Path
from types import TracebackType


class RunLockError(RuntimeError):
    """Raised when a run is locked by another live process."""


class RunLock:
    """A PID-based, stale-detecting lock at ``<run_dir>/run.lock``."""

    def __init__(self, run_dir: Path) -> None:
        self._lock_path = run_dir / "run.lock"
        self._acquired = False

    @property
    def path(self) -> Path:
        return self._lock_path

    def acquire(self) -> None:
        """Acquire the lock, breaking one stale lock if found. Raises
        RunLockError if a live lock is held by another process."""
        self._lock_path.parent.mkdir(parents=True, exist_ok=True)
        for _attempt in range(2):  # one real attempt, one retry after breaking a stale lock
            try:
                fd = os.open(str(self._lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            except FileExistsError:
                if not self._is_stale():
                    holder = self._read_pid()
                    raise RunLockError(
                        f"Run is locked by another live process (pid={holder})."
                    ) from None
                self._break_stale_lock()
                continue
            else:
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    handle.write(str(os.getpid()))
                self._acquired = True
                return
        raise RunLockError("Could not acquire run lock after breaking a stale lock.")

    def release(self) -> None:
        """Release the lock if this instance holds it. A no-op otherwise."""
        if self._acquired:
            with contextlib.suppress(FileNotFoundError):
                self._lock_path.unlink()
            self._acquired = False

    def _break_stale_lock(self) -> None:
        with contextlib.suppress(FileNotFoundError):
            self._lock_path.unlink()

    def _read_pid(self) -> int | None:
        try:
            return int(self._lock_path.read_text(encoding="utf-8").strip())
        except (FileNotFoundError, ValueError):
            return None

    def _is_stale(self) -> bool:
        pid = self._read_pid()
        if pid is None:
            return True  # missing or unparseable content -> stale
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return True  # no such process -> stale
        except PermissionError:
            return False  # process exists, owned by someone else -> live, not stale
        else:
            return False  # process exists -> live

    def __enter__(self) -> RunLock:
        self.acquire()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.release()


__all__ = ["RunLock", "RunLockError"]
