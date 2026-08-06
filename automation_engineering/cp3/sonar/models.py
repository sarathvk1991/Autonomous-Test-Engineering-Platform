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


@dataclass(frozen=True, slots=True)
class SonarMeasure:
    """One metric's own absolute (non-``new_``) value from
    ``/api/measures/component`` (ADR-0047 D1/D6) -- CP7's own mechanism,
    distinct from ``SonarQualityGateResult`` above (CP3's own per-run
    quality-GATE verdict, a different endpoint entirely). ``value`` is
    ``None`` when the server's own response omits this metric key
    entirely -- confirmed, live, this platform's real behavior for a
    metric nothing has ever fed (``coverage``/``duplicated_lines_density``
    with no JaCoCo report ever submitted, ADR-0047 D5/D10) -- never
    defaulted to ``"0"`` or any other faked value.
    """

    metric_key: str
    value: str | None


@dataclass(frozen=True, slots=True)
class SonarMeasuresResult:
    """The server's own whole-project measures for a named set of metric
    keys -- the adapter's own generic return shape (ADR-0047 D6). One
    ``SonarMeasure`` per requested key, in the order requested, whether or
    not the server actually had a value for it (module docstring). Layer
    4's own domain-specific report
    (:class:`suite_quality_governance.cp7.models.Cp7WholeSuiteQualityReport`)
    is built FROM this, not instead of it -- this shape carries no
    Layer-4-specific grouping or interpretation, mirroring
    ``SonarQualityGateResult``'s own "carries through the server's
    vocabulary unchanged" discipline.
    """

    project_key: str
    measures: tuple[SonarMeasure, ...]


__all__ = [
    "SonarMeasure",
    "SonarMeasuresResult",
    "SonarQualityGateCondition",
    "SonarQualityGateResult",
]
