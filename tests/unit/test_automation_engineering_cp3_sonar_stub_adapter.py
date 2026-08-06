"""`StubSonarQualityGateAdapter` -- deterministic, no network call, proving
`run_quality_gate` invokes submit -> poll -> fetch, in that order, exactly
once each, and that a scripted poll-time failure propagates as
`SonarScanError`.

Also covers `fetch_measures` (ADR-0047 D6) -- CP7's own added mechanic on
this SAME adapter Protocol, proving it is scripted, called, and honest
about an unmeasured metric the same way every other method here already
is.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from automation_engineering.cp3.sonar.adapter import SonarScanError, run_quality_gate
from automation_engineering.cp3.sonar.models import (
    SonarMeasure,
    SonarMeasuresResult,
    SonarQualityGateResult,
)
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


# ---------------------------------------------------------------------------
# fetch_measures (ADR-0047 D6)
# ---------------------------------------------------------------------------


def test_fetch_measures_returns_the_scripted_result_and_records_the_call() -> None:
    scripted = SonarMeasuresResult(
        project_key="demo",
        measures=(SonarMeasure(metric_key="violations", value="0"),),
    )
    adapter = StubSonarQualityGateAdapter(measures=scripted)

    result = adapter.fetch_measures("demo", ("violations",))

    assert result is scripted
    assert adapter.measures_calls == [("demo", ("violations",))]


def test_fetch_measures_without_a_scripted_result_raises() -> None:
    adapter = StubSonarQualityGateAdapter()
    with pytest.raises(SonarScanError, match="no scripted measures"):
        adapter.fetch_measures("demo", ("violations",))


def test_fetch_measures_honestly_carries_an_unmeasured_metric() -> None:
    """A stub can script `value=None` for a metric the server has no
    value for (ADR-0047 D5) -- the stub never fabricates this on its own;
    the test author scripts it explicitly, the same discipline the module
    docstring states."""
    scripted = SonarMeasuresResult(
        project_key="demo",
        measures=(SonarMeasure(metric_key="coverage", value=None),),
    )
    adapter = StubSonarQualityGateAdapter(measures=scripted)

    result = adapter.fetch_measures("demo", ("coverage",))

    assert result.measures[0].value is None
