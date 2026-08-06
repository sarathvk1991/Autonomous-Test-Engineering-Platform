"""The LIVE SonarQube adapter's own submit/poll/parse mechanics -- fake-
tested (ADR-0044 D5's own test story: "the adapter mechanics (submit/poll/
parse) are fake-tested; the live gate is exercised only where Sonar
exists"). No real Maven process and no real network call is ever made
here: ``subprocess.run`` is mocked for `submit_scan`, and ``respx`` mocks
the SonarQube Web API's own HTTP responses for `poll_for_completion`/
`fetch_quality_gate_result` -- this proves the adapter's own request-
building and response-parsing logic is correct, WITHOUT proving a live
server's actual behavior (that remains unexercised in this environment,
per this build's own report -- no SonarQube server was reachable here).

Also covers `fetch_measures` (ADR-0047 D1/D6) -- CP7's own added
mechanic, mirroring the identical fake-testing discipline: ``respx``
mocks ``/api/measures/component``, proving the request shape (metric
keys joined, the least-privilege token as HTTP Basic auth) and the
response-parsing logic (a metric the server's own response array omits
becomes `value=None`, ADR-0047 D5/D10 -- never a faked default), without
depending on any live server being reachable in this environment.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

import httpx
import pytest
import respx

from automation_engineering.cp3.sonar.adapter import SonarScanError
from automation_engineering.cp3.sonar.live_adapter import LiveSonarQualityGateAdapter

_BASE_URL = "https://sonar.example.com"
_SUBPROCESS_RUN = "automation_engineering.cp3.sonar.live_adapter.subprocess.run"


def _adapter(**overrides: object) -> LiveSonarQualityGateAdapter:
    kwargs: dict[str, object] = {
        "base_url": _BASE_URL,
        "token": "secret-token",
        "poll_interval_seconds": 0.0,
        "max_poll_attempts": 5,
    }
    kwargs.update(overrides)
    return LiveSonarQualityGateAdapter(**kwargs)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# submit_scan
# ---------------------------------------------------------------------------


def test_submit_scan_parses_ce_task_id_from_report_task_file(tmp_path: Path) -> None:
    report_dir = tmp_path / "target" / "sonar"
    report_dir.mkdir(parents=True)
    (report_dir / "report-task.txt").write_text(
        "projectKey=demo\nserverUrl=https://sonar.example.com\nceTaskId=ABC123\n",
        encoding="utf-8",
    )
    completed = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")

    with patch(_SUBPROCESS_RUN, return_value=completed) as run:
        task_id = _adapter().submit_scan(tmp_path, "demo")

    assert task_id == "ABC123"
    # The token travels via the environment, never as a CLI argument.
    _, kwargs = run.call_args
    assert kwargs["env"]["SONAR_TOKEN"] == "secret-token"
    assert not any("secret-token" in str(arg) for arg in run.call_args.args[0])


def test_submit_scan_uses_the_fully_qualified_sonar_goal(tmp_path: Path) -> None:
    """F3 (2026-08-05): the short `sonar:sonar` prefix only resolves against
    a `~/.m2/settings.xml` that registers the plugin group -- reproduced
    live as a real, environment-dependent failure
    (`architecture-baseline-v2.md` §4 item 17). The fully qualified goal
    needs no such registration on any machine."""
    report_dir = tmp_path / "target" / "sonar"
    report_dir.mkdir(parents=True)
    (report_dir / "report-task.txt").write_text("ceTaskId=ABC123\n", encoding="utf-8")
    completed = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")

    with patch(_SUBPROCESS_RUN, return_value=completed) as run:
        _adapter().submit_scan(tmp_path, "demo")

    argv = run.call_args.args[0]
    assert "org.sonarsource.scanner.maven:sonar-maven-plugin:sonar" in argv
    assert "sonar:sonar" not in argv


def test_submit_scan_raises_on_nonzero_exit(tmp_path: Path) -> None:
    completed = subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="build failed")
    with (
        patch(_SUBPROCESS_RUN, return_value=completed),
        pytest.raises(SonarScanError, match="build failed"),
    ):
        _adapter().submit_scan(tmp_path, "demo")


def test_submit_scan_raises_when_report_task_file_missing(tmp_path: Path) -> None:
    completed = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
    with (
        patch(_SUBPROCESS_RUN, return_value=completed),
        pytest.raises(SonarScanError, match=r"report-task\.txt"),
    ):
        _adapter().submit_scan(tmp_path, "demo")


# ---------------------------------------------------------------------------
# poll_for_completion
# ---------------------------------------------------------------------------


@respx.mock
def test_poll_for_completion_returns_on_success_status() -> None:
    respx.get(f"{_BASE_URL}/api/ce/task").mock(
        return_value=httpx.Response(200, json={"task": {"id": "T1", "status": "SUCCESS"}})
    )
    _adapter().poll_for_completion("T1")  # must not raise


@respx.mock
def test_poll_for_completion_raises_on_failed_status() -> None:
    respx.get(f"{_BASE_URL}/api/ce/task").mock(
        return_value=httpx.Response(200, json={"task": {"id": "T1", "status": "FAILED"}})
    )
    try:
        _adapter().poll_for_completion("T1")
    except SonarScanError as exc:
        assert "FAILED" in str(exc)
    else:
        raise AssertionError("expected SonarScanError")


@respx.mock
def test_poll_for_completion_polls_until_terminal_status() -> None:
    route = respx.get(f"{_BASE_URL}/api/ce/task")
    route.side_effect = [
        httpx.Response(200, json={"task": {"id": "T1", "status": "IN_PROGRESS"}}),
        httpx.Response(200, json={"task": {"id": "T1", "status": "SUCCESS"}}),
    ]
    _adapter().poll_for_completion("T1")  # must not raise
    assert route.call_count == 2


@respx.mock
def test_poll_for_completion_raises_after_exhausting_attempts() -> None:
    respx.get(f"{_BASE_URL}/api/ce/task").mock(
        return_value=httpx.Response(200, json={"task": {"id": "T1", "status": "IN_PROGRESS"}})
    )
    try:
        _adapter(max_poll_attempts=3).poll_for_completion("T1")
    except SonarScanError as exc:
        assert "did not complete" in str(exc)
    else:
        raise AssertionError("expected SonarScanError")


# ---------------------------------------------------------------------------
# fetch_quality_gate_result
# ---------------------------------------------------------------------------


@respx.mock
def test_fetch_quality_gate_result_parses_a_passing_gate() -> None:
    respx.get(f"{_BASE_URL}/api/qualitygates/project_status").mock(
        return_value=httpx.Response(200, json={"projectStatus": {"status": "OK", "conditions": []}})
    )
    result = _adapter().fetch_quality_gate_result("demo")
    assert result.passed is True
    assert result.conditions == ()


@respx.mock
def test_fetch_quality_gate_result_parses_a_failing_gate_with_conditions() -> None:
    respx.get(f"{_BASE_URL}/api/qualitygates/project_status").mock(
        return_value=httpx.Response(
            200,
            json={
                "projectStatus": {
                    "status": "ERROR",
                    "conditions": [
                        {
                            "metricKey": "customqa:direct-webdriver-action",
                            "status": "ERROR",
                            "actualValue": "3",
                            "errorThreshold": "0",
                        },
                        {
                            "metricKey": "coverage",
                            "status": "OK",
                            "actualValue": "85",
                            "errorThreshold": "80",
                        },
                    ],
                }
            },
        )
    )
    result = _adapter().fetch_quality_gate_result("demo")
    assert result.passed is False
    assert len(result.conditions) == 2
    failing = next(
        c for c in result.conditions if c.metric_key == "customqa:direct-webdriver-action"
    )
    assert failing.status == "ERROR"
    assert failing.actual_value == "3"
    assert failing.error_threshold == "0"


# ---------------------------------------------------------------------------
# fetch_measures (ADR-0047 D1/D6)
# ---------------------------------------------------------------------------


@respx.mock
def test_fetch_measures_requests_the_joined_metric_keys_for_the_project() -> None:
    route = respx.get(f"{_BASE_URL}/api/measures/component").mock(
        return_value=httpx.Response(
            200,
            json={
                "component": {
                    "key": "demo",
                    "measures": [
                        {"metric": "violations", "value": "0", "bestValue": True},
                        {"metric": "bugs", "value": "0", "bestValue": True},
                    ],
                }
            },
        )
    )

    result = _adapter().fetch_measures("demo", ("violations", "bugs"))

    assert route.calls.last.request.url.params["component"] == "demo"
    assert route.calls.last.request.url.params["metricKeys"] == "violations,bugs"
    assert result.project_key == "demo"
    assert [m.metric_key for m in result.measures] == ["violations", "bugs"]
    assert [m.value for m in result.measures] == ["0", "0"]


@respx.mock
def test_fetch_measures_reports_a_key_the_server_omits_as_unmeasured() -> None:
    """ADR-0047 D5/D10's own real, observed server behavior: a metric with
    no computed value (`coverage` with no JaCoCo report ever submitted) is
    OMITTED from the response array entirely -- confirmed here to become
    `value=None`, never a faked `"0"` or dropped from the result."""
    respx.get(f"{_BASE_URL}/api/measures/component").mock(
        return_value=httpx.Response(
            200,
            json={
                "component": {
                    "key": "demo",
                    "measures": [{"metric": "violations", "value": "0", "bestValue": True}],
                }
            },
        )
    )

    result = _adapter().fetch_measures("demo", ("violations", "coverage"))

    by_key = {m.metric_key: m.value for m in result.measures}
    assert by_key["violations"] == "0"
    assert by_key["coverage"] is None  # omitted by the server -- unmeasured, not faked


@respx.mock
def test_fetch_measures_uses_the_same_least_privilege_token_as_the_quality_gate() -> None:
    route = respx.get(f"{_BASE_URL}/api/measures/component").mock(
        return_value=httpx.Response(200, json={"component": {"key": "demo", "measures": []}})
    )

    _adapter().fetch_measures("demo", ("violations",))

    auth_header = route.calls.last.request.headers["authorization"]
    assert auth_header.startswith("Basic ")  # same HTTP Basic auth scheme every other call uses
