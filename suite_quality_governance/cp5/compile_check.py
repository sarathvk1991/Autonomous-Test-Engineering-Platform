"""CP5's compile-check seam (ADR-0046 D5's own compile half): does the
assembled suite's test sources compile as a whole -- the same
``Protocol`` + stub/live seam this platform already uses for CP3's
SonarQube adapter (`automation_engineering.cp3.sonar.adapter`), so the
gate LOGIC (`suite_quality_governance.cp5.cohesion`) is unit-tested
without a live JDK/Maven toolchain.

**"Compiles," never "runs" -- the structural boundary ADR-0046 D5 locks.**
ADR-0046 D5, quoted: "Invoking a JDK/Maven toolchain to compile the
assembled suite is the same kind of dependency as CP3's Sonar server -- a
build-time tool call, never a SUT or browser -- so it is consistently
Layer 4's, not Layer 5's... 'Does it then successfully run' (a smoke test
passing) remains Layer 5's." This module invokes exactly one Maven
lifecycle phase, ``test-compile`` -- it compiles test sources; it never
invokes ``test`` (which would EXECUTE them), never launches a browser,
never touches a SUT. `:class:`LiveCompileChecker`'s own `subprocess.run`
argv is the structural proof: its own module-level constant
(:data:`_COMPILE_GOAL`) is the literal string ``"test-compile"``, never
``"test"`` -- there is no code path in this module that can invoke
execution, by construction, not merely by convention.

Two implementations:

* :class:`StubCompileChecker` -- deterministic, fixture-driven, test/dev
  scaffolding only. Every unit test in this package uses this one; no
  subprocess is ever spawned.
* :class:`LiveCompileChecker` -- the real ``mvn test-compile`` invocation.
  Its own mechanics (argv construction, success/failure parsing) are
  fake-tested (`subprocess.run` mocked, mirroring
  `tests/unit/test_automation_engineering_cp3_sonar_live_adapter.py`'s own
  "no real Maven process... is ever made here" discipline) -- the
  automated test suite never depends on a real JDK/Maven toolchain being
  present on whatever machine runs it. **Unlike CP3's Sonar adapter**
  (never exercised live in this build -- no SonarQube server was
  reachable), a real Maven/JDK toolchain IS reachable in this
  environment, and `LiveCompileChecker` was additionally verified
  directly against it, once, manually -- see this module's own build
  record in `docs/architecture/architecture-baseline-v2.md` for what that
  real invocation found. That verification is not re-run by the automated
  suite (the same portability reasoning `LiveSonarQualityGateAdapter`
  already establishes: a machine running `make test` is never assumed to
  have `mvn` installed).
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Protocol

from suite_quality_governance.cp5.models import CompileResult

#: The Maven lifecycle phase this checker invokes -- compiles TEST sources
#: only, never executes them. This platform's own generated/tracked Java
#: lives entirely under `src/test/java` (ADR-0037 Path A), so this is the
#: phase that actually covers it; `compile` alone would compile nothing
#: (there is no `src/main/java` this platform generates into).
_COMPILE_GOAL = "test-compile"


class CompileError(Exception):
    """Raised when the compile process itself could not be run or its
    outcome could not be determined at all (a missing `pom.xml`, `mvn` not
    on `PATH`, an unexpected subprocess crash) -- **never** for a normal
    "the Java has real compile errors" outcome, which is a legitimate
    :class:`CompileResult` (`passed=False`, `errors` populated), not an
    exception. Mirrors :class:`automation_engineering.cp3.sonar.adapter.
    SonarScanError`'s own infra-failure-vs-normal-result split exactly.

    Caught by :mod:`suite_quality_governance.cp5.cohesion` and turned into
    a deterministic `FAIL` criterion -- CP5's cohesion check fails closed,
    it never crashes (ADR-0040 Decision 2).
    """


class CompileChecker(Protocol):
    """Compile an already-on-disk Maven project's test sources; return
    whether it succeeded. Structural typing only -- :class:`StubCompileChecker`
    and :class:`LiveCompileChecker` both satisfy this without inheriting
    from it, the same discipline every other seam in this platform uses.
    """

    def compile(self, project_root: Path) -> CompileResult:
        """Compile `project_root`'s test sources (never executes them).

        Raises
        ------
        CompileError
            The compile process itself could not be run or its outcome
            could not be determined (see class docstring) -- never for a
            normal compile failure, which is a returned `CompileResult`.
        """
        ...


class StubCompileChecker:
    """Deterministic, fixture-driven stand-in for the live compile checker
    -- test/dev scaffolding only, mirroring `automation_engineering.cp3.
    sonar.stub_adapter.StubSonarQualityGateAdapter`'s own discipline
    exactly: a canned result (or a canned :class:`CompileError`), never a
    real subprocess, recording every call so a test can assert it was
    invoked with the expected `project_root`.
    """

    def __init__(
        self,
        *,
        result: CompileResult | None = None,
        error: CompileError | None = None,
    ) -> None:
        self._result = result
        self._error = error
        self.calls: list[Path] = []

    def compile(self, project_root: Path) -> CompileResult:
        self.calls.append(project_root)
        if self._error is not None:
            raise self._error
        if self._result is None:
            raise CompileError(
                "StubCompileChecker has no scripted outcome; construct it "
                "with result=... or error=...."
            )
        return self._result


def _parse_compile_errors(output: str) -> tuple[str, ...]:
    """One entry per `[ERROR]`-prefixed line in Maven's own `-q` output --
    the real, observed shape of a `mvn test-compile` failure (verified
    directly against this repository's own `test-suite-baseline/`, module
    docstring). Skips the two `[ERROR]` lines Maven always emits around
    the "re-run with -e" help text (blank/boilerplate, never a real
    compile diagnostic) by requiring at least one non-space character
    after the prefix.
    """
    errors = []
    for line in output.splitlines():
        stripped = line.strip()
        if stripped.startswith("[ERROR]"):
            detail = stripped[len("[ERROR]") :].strip()
            if detail:
                errors.append(detail)
    return tuple(errors)


class LiveCompileChecker:
    """Real ``mvn test-compile`` implementation of :class:`CompileChecker`
    (structural -- no explicit base class, matching this platform's own
    `Protocol` discipline).
    """

    def compile(self, project_root: Path) -> CompileResult:
        pom_path = project_root / "pom.xml"
        if not pom_path.exists():
            raise CompileError(f"No pom.xml found at {pom_path}")
        completed = subprocess.run(  # noqa: S603 - fixed argv, no shell, no untrusted input
            [  # noqa: S607 - `mvn` resolved via PATH, the same convention `LiveSonarQualityGateAdapter` uses
                "mvn",
                "-q",
                "-f",
                str(pom_path),
                _COMPILE_GOAL,
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode == 0:
            return CompileResult(passed=True)
        errors = _parse_compile_errors(completed.stdout) or _parse_compile_errors(
            completed.stderr
        )
        if not errors:
            errors = (
                completed.stderr.strip()
                or completed.stdout.strip()
                or f"mvn {_COMPILE_GOAL} exited {completed.returncode} with no output",
            )
        return CompileResult(passed=False, errors=errors)


def run_compile_check(checker: CompileChecker, project_root: Path) -> CompileResult:
    """The one function `suite_quality_governance.cp5.cohesion`'s own
    gate calls -- every checker is otherwise exercised only by its own
    unit tests. A thin pass-through today (the compile check is a single
    step, unlike CP3's submit/poll/fetch), kept as its own function so a
    caller never invokes `checker.compile(...)` directly and so this
    module's own shape mirrors `automation_engineering.cp3.sonar.adapter.
    run_quality_gate`'s call-site discipline exactly.
    """
    return checker.compile(project_root)


__all__ = [
    "CompileChecker",
    "CompileError",
    "LiveCompileChecker",
    "StubCompileChecker",
    "run_compile_check",
]
