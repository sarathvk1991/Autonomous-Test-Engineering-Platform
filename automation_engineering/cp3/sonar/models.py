"""SonarQube quality-gate result shapes -- the parsed form of the server's
own ``/api/qualitygates/project_status`` response (ADR-0044 D5's hard CP3
gate). ``status``/``metricKey``/``actualValue``/``errorThreshold`` are the
server's own vocabulary, carried through unchanged -- this module performs
no re-interpretation of what the server decided, only structures it.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SonarQualityGateCondition:
    """One quality-gate condition the server evaluated (e.g. one
    ``customqa:direct-webdriver-action`` threshold check). ``status`` is
    the server's own per-condition verdict, ``"OK"`` or ``"ERROR"``."""

    metric_key: str
    status: str
    actual_value: str
    error_threshold: str | None = None


@dataclass(frozen=True, slots=True)
class SonarQualityGateResult:
    """The server's own overall quality-gate verdict for one analysis.

    ``passed`` is ``True`` iff the server's own ``projectStatus.status`` is
    ``"OK"`` -- CP3's Sonar criterion (:mod:`automation_engineering.cp3.gate`)
    gates on this boolean alone (ADR-0040 Decision 2: a deterministic
    pass/fail on the server's own verdict, never re-judged here).
    """

    passed: bool
    conditions: tuple[SonarQualityGateCondition, ...] = ()


__all__ = ["SonarQualityGateCondition", "SonarQualityGateResult"]
