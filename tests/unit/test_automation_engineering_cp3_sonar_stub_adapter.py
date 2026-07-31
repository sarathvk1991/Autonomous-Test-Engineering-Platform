"""`StubSonarQualityGateAdapter` -- deterministic, no network call, proving
`run_quality_gate` invokes submit -> poll -> fetch, in that order, exactly
once each, and that a scripted poll-time failure propagates as
`SonarScanError`.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from automation_engineering.cp3.sonar.adapter import SonarScanError, run_quality_gate
from automation_engineering.cp3.sonar.models import SonarQualityGateResult
from automation_engineering.cp3.sonar.stub_adapter import StubSonarQualityGateAdapter

pytestmark = pytest.mark.unit


def test_run_quality_gate_calls_submit_poll_fetch_in_order_exactly_once() -> None:
    adapter = StubSonarQualityGateAdapter(result=SonarQualityGateResult(passed=True))
    result = run_quality_gate(adapter, Path("/tmp/project"), "demo")

    assert result.passed is True
    assert adapter.submit_calls == [(Path("/tmp/project"), "demo")]
    assert adapter.poll_calls == ["stub-scan-1"]
    assert adapter.fetch_calls == ["demo"]


def test_run_quality_gate_uses_the_scripted_scan_id() -> None:
    adapter = StubSonarQualityGateAdapter(
        result=SonarQualityGateResult(passed=True), scan_id="custom-scan-id"
    )
    run_quality_gate(adapter, Path("/tmp/project"), "demo")
    assert adapter.poll_calls == ["custom-scan-id"]


def test_poll_error_propagates_as_sonar_scan_error() -> None:
    adapter = StubSonarQualityGateAdapter(poll_error=SonarScanError("scan failed on the server"))
    with pytest.raises(SonarScanError, match="scan failed on the server"):
        run_quality_gate(adapter, Path("/tmp/project"), "demo")
    # fetch is never reached once poll raises.
    assert adapter.fetch_calls == []


def test_fetch_without_a_scripted_result_raises() -> None:
    adapter = StubSonarQualityGateAdapter()
    with pytest.raises(SonarScanError, match="no scripted result"):
        run_quality_gate(adapter, Path("/tmp/project"), "demo")
