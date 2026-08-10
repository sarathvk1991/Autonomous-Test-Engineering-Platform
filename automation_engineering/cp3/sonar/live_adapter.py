"""The real SonarQube adapter (ADR-0044 D5's own hard-gate mechanics).

SonarQube has no REST endpoint that accepts raw source text for scanning --
analysis is always performed by the scanner engine against an on-disk,
buildable project (the ``sonar-scanner`` CLI or a build-tool plugin).
Given ADR-0041's own Maven/JDK21 stack, this adapter submits via the
Sonar-Maven-plugin's own fully qualified goal (:data:`_SONAR_GOAL`, F3 below)
against `project_root` -- an already-on-disk Maven project; stage 15's own
orchestration (`automation_engineering/stage/runner.py`) writes generated
Java into that project's per-run workspace copy before CP3 is ever called,
promotion (ADR-0045) separately copies a clean, promoted subset into the
TRACKED baseline afterward -- two different write targets, neither this
adapter's own job. On success, the Sonar Maven plugin writes
``target/sonar/report-task.txt`` (``key=value`` lines including
``ceTaskId``) -- the real, documented hand-off between "scan submitted" and
"poll the Compute Engine task API for it."

Polling (`GET /api/ce/task?id=...`) and the quality-gate fetch
(`GET /api/qualitygates/project_status?projectKey=...`) are SonarQube's own
stable, documented Web API endpoints, called via ``httpx`` (already a
runtime dependency of this platform -- ``requirement_intelligence``'s own
JIRA/SonarQube/ZAP connectors use it; NOT reused directly here, since
those connectors are Layer 1's own internal module and this platform's
layers do not import each other's internals -- this adapter makes its own,
independent ``httpx`` calls). No new third-party dependency was added for
this build.

The token authenticates as the HTTP Basic-auth username with an empty
password -- SonarQube's own documented token-auth convention -- and is
passed to the Maven subprocess via the ``SONAR_TOKEN`` environment
variable, never a CLI argument, so it never appears in a process listing.

**Not exercised against a real server in this build.** `curl --max-time 3
http://localhost:9000/api/system/status` from this environment returns no
connection (verified directly, not assumed) -- there is no SonarQube
server reachable here. This module's own HTTP/subprocess mechanics are
therefore proven correct only by direct reading and by
:mod:`automation_engineering.cp3.sonar.stub_adapter`'s equivalent, faked
call sequence -- never by a passing live integration test. Stated
honestly, per ADR-0044 D5's own instruction not to fabricate a live pass.

Which quality profile a scan is graded against (2026-08-04, F4 revision
build task 1): SonarQube resolves this ENTIRELY server-side, from whatever
profile is assigned to ``project_key`` at scan time -- confirmed directly
against a live server (26.4.0.121862, ``GET /api/settings/list_definitions``
carries no ``sonar.profile`` key at all; that per-scan analysis parameter
was removed from SonarQube years before this version). There is therefore
no argument this adapter's own ``submit_scan`` could pass to select
:data:`CUSTOMQA_PROFILE_NAME` -- assigning it to a project is a one-time,
server-side administrative action (``POST /api/qualityprofiles/add_project``
or the SonarQube UI), never a per-scan parameter, and never something this
low-privilege, submit-a-scan-only adapter should be doing at runtime
even if it could (least privilege, `.env.example`'s own Security Guidelines
section). See ``test-suite-baseline/sonar/README.md`` for the exact,
runnable one-time admin procedure and the live proof it produces.
"""

from __future__ import annotations

import os
import subprocess
import time
from collections.abc import Sequence
from pathlib import Path

import httpx

from automation_engineering.cp3.sonar.adapter import SonarScanError
from automation_engineering.cp3.sonar.models import (
    SonarMeasure,
    SonarMeasuresResult,
    SonarQualityGateCondition,
    SonarQualityGateResult,
)

_TERMINAL_TASK_STATUSES = frozenset({"SUCCESS", "FAILED", "CANCELED"})
_REPORT_TASK_RELATIVE_PATH = Path("target/sonar/report-task.txt")

#: ADR-0047 D5/D11 (latent #5/item #39): the JaCoCo XML report path this
#: adapter now always passes to the scan, matching where
#: ``test-suite-baseline/pom.xml``'s own ``jacoco-maven-plugin`` (``report``
#: goal, bound to the ``test`` phase) writes it. This adapter never runs
#: tests itself (this module's own docstring: it scans an already-on-disk
#: project) -- the report must already exist from a prior ``mvn test`` for
#: coverage to become measured; if it does not (tests were never run before
#: the scan, or a project with no JaCoCo plugin at all), the Sonar Maven
#: plugin simply finds nothing at this path and coverage stays unmeasured,
#: exactly the pre-existing degrade -- passing this argument unconditionally
#: never turns a missing report into a scan failure.
_JACOCO_XML_REPORT_RELATIVE_PATH = Path("target/site/jacoco/jacoco.xml")

#: The FULLY QUALIFIED Sonar-Maven-plugin goal (F3, 2026-08-05, this stage-15
#: wiring build). The short form (`sonar:sonar`) only resolves if the
#: invoking machine's own `~/.m2/settings.xml` registers
#: `org.sonarsource.scanner.maven` under `pluginGroups` -- Maven's default
#: plugin-group search (`org.apache.maven.plugins`/`org.codehaus.mojo`) does
#: not include it. Reproduced live (`architecture-baseline-v2.md` §4 item
#: 17): on a machine with no such registration, the short form fails with
#: `exit 1`, `"No plugin found for prefix 'sonar'"` -- an environment-
#: portability gap, not a code-quality signal about the scanned Java, and
#: exactly the kind of failure this stage's own CP3 call would otherwise
#: misattribute. The fully qualified form needs no `pluginGroups`
#: registration on any machine -- it names the plugin's own Maven
#: coordinates directly, the same way any other non-core plugin goal would
#: be invoked without relying on a local, undeclared environment convention.
_SONAR_GOAL = "org.sonarsource.scanner.maven:sonar-maven-plugin:sonar"

#: The quality profile name CP3's Sonar gate expects to be assigned to
#: whatever project it scans (ADR-0044 D5 revision, ADR-0037 Recommendation
#: 3) -- documentation only, since SonarQube has no scanner-time parameter
#: to select it (see this module's own docstring). The versioned artifact
#: this name refers to lives at ``test-suite-baseline/sonar/customqa-profile
#: .xml``; ``test-suite-baseline/sonar/README.md`` is the runnable
#: import/assign procedure. Verifies only the Sonar-expressible half of
#: ``customqa:*`` (today: ``java:S138``/long-method) -- never
#: ``direct-webdriver-action``, a static Layer 3 check, not a Sonar rule.
CUSTOMQA_PROFILE_NAME = "customqa"


class LiveSonarQualityGateAdapter:
    """Real ``mvn sonar:sonar`` + SonarQube Web API implementation of
    :class:`~automation_engineering.cp3.sonar.adapter.SonarQualityGateAdapter`
    (structural -- no explicit base class, matching this platform's own
    ``Protocol`` discipline).
    """

    def __init__(
        self,
        *,
        base_url: str,
        token: str,
        timeout_seconds: float = 30.0,
        poll_interval_seconds: float = 2.0,
        max_poll_attempts: int = 150,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._token = token
        self._timeout_seconds = timeout_seconds
        self._poll_interval_seconds = poll_interval_seconds
        self._max_poll_attempts = max_poll_attempts

    def submit_scan(self, project_root: Path, project_key: str) -> str:
        env = {**os.environ, "SONAR_TOKEN": self._token}
        completed = subprocess.run(  # noqa: S603 - fixed argv, no shell, no untrusted input
            [  # noqa: S607 - `mvn` resolved via PATH, the same convention every dev/CI shell uses
                "mvn",
                "-q",
                "-f",
                str(project_root / "pom.xml"),
                _SONAR_GOAL,
                f"-Dsonar.host.url={self._base_url}",
                f"-Dsonar.projectKey={project_key}",
                f"-Dsonar.coverage.jacoco.xmlReportPaths="
                f"{project_root / _JACOCO_XML_REPORT_RELATIVE_PATH}",
            ],
            capture_output=True,
            text=True,
            check=False,
            env=env,
        )
        if completed.returncode != 0:
            raise SonarScanError(
                f"mvn sonar:sonar exited {completed.returncode} for {project_root}: "
                f"{completed.stderr.strip() or completed.stdout.strip()}"
            )
        report_path = project_root / _REPORT_TASK_RELATIVE_PATH
        if not report_path.exists():
            raise SonarScanError(
                f"mvn sonar:sonar exited 0 but wrote no report-task.txt at {report_path}"
            )
        properties = dict(
            line.split("=", 1)
            for line in report_path.read_text(encoding="utf-8").splitlines()
            if "=" in line
        )
        task_id = properties.get("ceTaskId")
        if not task_id:
            raise SonarScanError(f"{report_path} has no ceTaskId entry")
        return task_id

    def poll_for_completion(self, task_id: str) -> None:
        with httpx.Client(
            base_url=self._base_url, auth=self._basic_auth(), timeout=self._timeout_seconds
        ) as client:
            for _ in range(self._max_poll_attempts):
                response = client.get("/api/ce/task", params={"id": task_id})
                response.raise_for_status()
                status = response.json()["task"]["status"]
                if status == "SUCCESS":
                    return
                if status in _TERMINAL_TASK_STATUSES:
                    raise SonarScanError(
                        f"SonarQube analysis task {task_id} ended with status {status}"
                    )
                time.sleep(self._poll_interval_seconds)
        raise SonarScanError(
            f"SonarQube analysis task {task_id} did not complete within "
            f"{self._max_poll_attempts} polls"
        )

    def fetch_quality_gate_result(self, project_key: str) -> SonarQualityGateResult:
        with httpx.Client(
            base_url=self._base_url, auth=self._basic_auth(), timeout=self._timeout_seconds
        ) as client:
            response = client.get(
                "/api/qualitygates/project_status", params={"projectKey": project_key}
            )
            response.raise_for_status()
            project_status = response.json()["projectStatus"]
        conditions = tuple(
            SonarQualityGateCondition(
                metric_key=condition["metricKey"],
                status=condition["status"],
                actual_value=condition.get("actualValue", ""),
                error_threshold=condition.get("errorThreshold"),
            )
            for condition in project_status.get("conditions", [])
        )
        return SonarQualityGateResult(
            passed=project_status["status"] == "OK", conditions=conditions
        )

    def fetch_measures(
        self, project_key: str, metric_keys: Sequence[str]
    ) -> SonarMeasuresResult:
        """CP7's own mechanism (ADR-0047 D1/D6) -- ``GET /api/measures/
        component``, never a scan submission. Confirmed live, this
        platform's real server (ADR-0047 D10): the pipeline's own
        least-privilege token already reads every metric CP7 needs; a
        metric with no computed value (``coverage``/``duplicated_lines_
        density`` with no JaCoCo report ever submitted) is OMITTED from
        the server's own response array entirely, never returned as a
        null or zero -- ``.get(key)`` below reproduces that same "absent
        means unmeasured" shape as ``value=None``, never a faked default.
        """
        with httpx.Client(
            base_url=self._base_url, auth=self._basic_auth(), timeout=self._timeout_seconds
        ) as client:
            response = client.get(
                "/api/measures/component",
                params={"component": project_key, "metricKeys": ",".join(metric_keys)},
            )
            response.raise_for_status()
            raw_measures = response.json()["component"].get("measures", [])
        values_by_key = {m["metric"]: m.get("value") for m in raw_measures}
        measures = tuple(
            SonarMeasure(metric_key=key, value=values_by_key.get(key)) for key in metric_keys
        )
        return SonarMeasuresResult(project_key=project_key, measures=measures)

    def _basic_auth(self) -> httpx.BasicAuth:
        return httpx.BasicAuth(self._token, "")


__all__ = ["LiveSonarQualityGateAdapter"]
