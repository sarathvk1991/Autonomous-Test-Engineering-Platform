"""The SonarQube adapter seam (ADR-0044 D5's own test story): submit a
Maven project for a scan, poll for completion, parse the quality-gate
verdict -- three distinct, separately fake-testable mechanics, mirroring
the same ``Protocol`` + stub/live seam this platform already uses for LLM
providers (:class:`feature_engineering.remediation.remediator.
FeatureRemediator` / ``StubFeatureRemediator``).

Two implementations exist:

* :class:`~.stub_adapter.StubSonarQualityGateAdapter` -- deterministic,
  fixture-driven, test/dev scaffolding only. Every unit test in this
  package uses this one; none makes a network call.
* :class:`~.live_adapter.LiveSonarQualityGateAdapter` -- the real
  ``mvn sonar:sonar`` + SonarQube Web API implementation, exercised only
  where a live SonarQube server actually exists (D5: "CP3 needs a live
  SonarQube server" must never be read as "every unit test needs a live
  SonarQube server").

Neither this module nor :func:`run_quality_gate` ever imports ``httpx`` or
``subprocess`` -- those are :mod:`.live_adapter`'s own concern, so this
seam's own gate-logic tests (:mod:`automation_engineering.cp3.gate`) never
carry a live-infrastructure dependency merely by importing this module.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from automation_engineering.cp3.sonar.models import SonarQualityGateResult


class SonarScanError(Exception):
    """Raised when a scan cannot be submitted, fails on the server side, a
    poll times out, or a quality-gate result cannot be parsed.

    CP3's own gate (:func:`automation_engineering.cp3.gate.evaluate_cp3`)
    catches this and turns it into a deterministic ``FAIL`` criterion -- it
    never propagates out of CP3 itself (ADR-0040 Decision 2: a control
    point is always a clean pass/fail, never a crash).
    """


class SonarQualityGateAdapter(Protocol):
    """Submit an already-on-disk Maven project's generated Java for
    analysis, poll for completion, and fetch the server's own quality-gate
    verdict. Structural typing only -- :class:`~.stub_adapter.
    StubSonarQualityGateAdapter` and :class:`~.live_adapter.
    LiveSonarQualityGateAdapter` both satisfy this without inheriting from
    it, the same discipline every other seam in this platform already uses.
    """

    def submit_scan(self, project_root: Path, project_key: str) -> str:
        """Submit `project_root` for analysis; return an implementation-
        defined task/analysis id :meth:`poll_for_completion` can track."""
        ...

    def poll_for_completion(self, task_id: str) -> None:
        """Block until the scan identified by `task_id` finishes.

        Raises
        ------
        SonarScanError
            If the scan fails, is canceled, or times out server-side.
        """
        ...

    def fetch_quality_gate_result(self, project_key: str) -> SonarQualityGateResult:
        """Fetch and parse the server's own quality-gate verdict for
        `project_key`'s most recent analysis."""
        ...


def run_quality_gate(
    adapter: SonarQualityGateAdapter, project_root: Path, project_key: str
) -> SonarQualityGateResult:
    """Submit, poll, then fetch -- in the only order that makes sense, so
    no caller has to (mis)order the three mechanics itself. This is the
    ONE function CP3's own gate (:mod:`automation_engineering.cp3.gate`)
    calls; every adapter is otherwise exercised only by its own unit
    tests.
    """
    task_id = adapter.submit_scan(project_root, project_key)
    adapter.poll_for_completion(task_id)
    return adapter.fetch_quality_gate_result(project_key)


__all__ = ["SonarQualityGateAdapter", "SonarScanError", "run_quality_gate"]
