"""Deterministic, fixture-driven stand-in for the live SonarQube adapter --
test/dev scaffolding only, mirroring
:class:`feature_engineering.remediation.remediator.StubFeatureRemediator`'s
own discipline exactly: a canned result, never a real network call or
subprocess, so CP3's gate LOGIC (:mod:`automation_engineering.cp3.gate`) is
unit-tested without a live SonarQube server (ADR-0044 D5's own test story).

Also stands in for CP7's own :meth:`~.adapter.SonarQualityGateAdapter.
fetch_measures` (ADR-0047 D6) -- a `measures` result must be scripted
explicitly, the same "no scripted outcome is a test-authoring error, not a
silent default" discipline every other method here already applies. This
is distinct from a `SonarMeasure` whose own `value` is `None` (a
LEGITIMATE, scripted "the server has no value for this metric" case,
ADR-0047 D5) -- the stub itself never fabricates that distinction; the
test author scripts it explicitly via `SonarMeasuresResult`.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from automation_engineering.cp3.sonar.adapter import SonarScanError
from automation_engineering.cp3.sonar.models import SonarMeasuresResult, SonarQualityGateResult


class StubSonarQualityGateAdapter:
    """Returns a pre-authored :class:`SonarQualityGateResult` (or raises a
    pre-authored :class:`SonarScanError` at the poll step) every time,
    recording every call so a test can assert submit -> poll -> fetch
    happened, in that order, exactly once per
    :func:`~automation_engineering.cp3.sonar.adapter.run_quality_gate`
    invocation.
    """

    def __init__(
        self,
        *,
        result: SonarQualityGateResult | None = None,
        scan_id: str = "stub-scan-1",
        poll_error: SonarScanError | None = None,
        measures: SonarMeasuresResult | None = None,
    ) -> None:
        self._result = result
        self._scan_id = scan_id
        self._poll_error = poll_error
        self._measures = measures
        self.submit_calls: list[tuple[Path, str]] = []
        self.poll_calls: list[str] = []
        self.fetch_calls: list[str] = []
        self.measures_calls: list[tuple[str, tuple[str, ...]]] = []

    def submit_scan(self, project_root: Path, project_key: str) -> str:
        self.submit_calls.append((project_root, project_key))
        return self._scan_id

    def poll_for_completion(self, task_id: str) -> None:
        self.poll_calls.append(task_id)
        if self._poll_error is not None:
            raise self._poll_error

    def fetch_quality_gate_result(self, project_key: str) -> SonarQualityGateResult:
        self.fetch_calls.append(project_key)
        if self._result is None:
            raise SonarScanError(
                "StubSonarQualityGateAdapter has no scripted result; "
                "construct it with `result=...`."
            )
        return self._result

    def fetch_measures(
        self, project_key: str, metric_keys: Sequence[str]
    ) -> SonarMeasuresResult:
        self.measures_calls.append((project_key, tuple(metric_keys)))
        if self._measures is None:
            raise SonarScanError(
                "StubSonarQualityGateAdapter has no scripted measures; "
                "construct it with `measures=...`."
            )
        return self._measures


__all__ = ["StubSonarQualityGateAdapter"]
