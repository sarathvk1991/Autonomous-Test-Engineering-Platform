"""The LIVE compile checker's own mechanics -- fake-tested (mirrors
`tests/unit/test_automation_engineering_cp3_sonar_live_adapter.py`'s own
"no real Maven process... is ever made here" discipline). No real `mvn`
process is ever spawned here: `subprocess.run` is mocked, proving the
argv construction and output-parsing logic is correct WITHOUT proving a
live toolchain's actual behavior in this specific test.

(A real `mvn test-compile` toolchain does happen to be reachable in this
development environment, and `LiveCompileChecker` was additionally
verified directly against it once, manually, outside this automated
suite -- see `docs/architecture/architecture-baseline-v2.md` for what
that real invocation found. The automated suite itself never depends on
`mvn`/a JDK being installed, mirroring `LiveSonarQualityGateAdapter`'s own
portability discipline.)

Also covers `StubCompileChecker` and the structural "compiles, never
runs" proof: the argv this module ever constructs contains the literal
string `"test-compile"` and never `"test"`.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

from suite_quality_governance.cp5.compile_check import (
    CompileError,
    LiveCompileChecker,
    StubCompileChecker,
    run_compile_check,
)

_SUBPROCESS_RUN = "suite_quality_governance.cp5.compile_check.subprocess.run"


def _completed(
    returncode: int, stdout: str = "", stderr: str = ""
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr=stderr)


class TestLiveCompileCheckerArgvIsCompileOnlyNeverExecute:
    def test_argv_invokes_test_compile_never_test(self, tmp_path: Path) -> None:
        (tmp_path / "pom.xml").write_text("<project/>", encoding="utf-8")
        with patch(_SUBPROCESS_RUN, return_value=_completed(0)) as run:
            LiveCompileChecker().compile(tmp_path)

        args, _kwargs = run.call_args
        argv = args[0]
        assert "test-compile" in argv
        assert "test" not in argv  # the execute-tests goal must never appear
        assert argv[0] == "mvn"
        assert str(tmp_path / "pom.xml") in argv

    def test_argv_never_contains_any_execution_or_sut_flag(self, tmp_path: Path) -> None:
        """Structural proof of the compile-not-run boundary (ADR-0046 D5):
        no goal or flag this module ever constructs names test EXECUTION
        or a SUT/browser concept."""
        (tmp_path / "pom.xml").write_text("<project/>", encoding="utf-8")
        with patch(_SUBPROCESS_RUN, return_value=_completed(0)) as run:
            LiveCompileChecker().compile(tmp_path)

        argv_text = " ".join(run.call_args.args[0])
        for forbidden in ("verify", "integration-test", "selenium", "webdriver", "surefire:test"):
            assert forbidden not in argv_text


class TestLiveCompileCheckerParsing:
    def test_returncode_zero_is_a_pass_with_no_errors(self, tmp_path: Path) -> None:
        (tmp_path / "pom.xml").write_text("<project/>", encoding="utf-8")
        with patch(_SUBPROCESS_RUN, return_value=_completed(0)):
            result = LiveCompileChecker().compile(tmp_path)

        assert result.passed is True
        assert result.errors == ()

    def test_nonzero_returncode_parses_one_error_per_error_line(self, tmp_path: Path) -> None:
        (tmp_path / "pom.xml").write_text("<project/>", encoding="utf-8")
        stdout = (
            "[ERROR] COMPILATION ERROR : \n"
            "[ERROR] /repo/LoginSteps.java:[8,45] cannot find symbol\n"
            "  symbol:   class LoginPage\n"
            "  location: class com.automation.steps.LoginSteps\n"
            "[ERROR] /repo/CartSteps.java:[3,28] cannot find symbol\n"
            "[ERROR] \n"
            "[ERROR] -> [Help 1]\n"
        )
        with patch(_SUBPROCESS_RUN, return_value=_completed(1, stdout=stdout)):
            result = LiveCompileChecker().compile(tmp_path)

        assert result.passed is False
        # "COMPILATION ERROR :", the two file diagnostics, and "-> [Help 1]" --
        # every non-empty [ERROR]-prefixed line, indented continuation lines
        # (symbol:/location:) excluded.
        assert len(result.errors) == 4
        assert any("LoginSteps.java" in e for e in result.errors)
        assert any("CartSteps.java" in e for e in result.errors)
        # A bare "[ERROR]" with nothing after it contributes no entry.
        assert not any(e == "" for e in result.errors)

    def test_nonzero_returncode_with_unparseable_output_falls_back_to_raw_text(
        self, tmp_path: Path
    ) -> None:
        (tmp_path / "pom.xml").write_text("<project/>", encoding="utf-8")
        with patch(_SUBPROCESS_RUN, return_value=_completed(1, stderr="permission denied")):
            result = LiveCompileChecker().compile(tmp_path)

        assert result.passed is False
        assert result.errors == ("permission denied",)


class TestLiveCompileCheckerInfrastructureFailures:
    def test_missing_pom_raises_compile_error_never_a_result(self, tmp_path: Path) -> None:
        # No pom.xml written -- an infra-level failure, not a code-quality one.
        try:
            LiveCompileChecker().compile(tmp_path)
            raise AssertionError("expected CompileError")
        except CompileError as exc:
            assert "pom.xml" in str(exc)


class TestStubCompileChecker:
    def test_returns_scripted_result_and_records_the_call(self, tmp_path: Path) -> None:
        from suite_quality_governance.cp5.models import CompileResult

        stub = StubCompileChecker(result=CompileResult(passed=True))
        result = run_compile_check(stub, tmp_path)

        assert result.passed is True
        assert stub.calls == [tmp_path]

    def test_raises_scripted_error(self, tmp_path: Path) -> None:
        stub = StubCompileChecker(error=CompileError("boom"))
        try:
            run_compile_check(stub, tmp_path)
            raise AssertionError("expected CompileError")
        except CompileError as exc:
            assert str(exc) == "boom"

    def test_raises_if_unscripted(self, tmp_path: Path) -> None:
        stub = StubCompileChecker()
        try:
            run_compile_check(stub, tmp_path)
            raise AssertionError("expected CompileError")
        except CompileError:
            pass
