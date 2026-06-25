"""Deterministic grouping and risk rules for the Consolidation Engine.

This module holds the *pure* heuristics the engine applies. Everything here is
deterministic and explainable — there is no AI, no I/O and no source-specific
branching. Given the same :class:`SourceArtifact`, every function returns the
same result every time.

Phase-1 grouping cascade (highest priority first):

1. ``component`` — the owning module / component.
2. shared ``tags`` — the artifact's primary (alphabetically first) tag.
3. ``endpoint`` — the URL / location path the artifact concerns.
4. ``risk`` category — the normalised risk level, as a last-resort bucket.

The first dimension that yields a value decides the group an artifact lands in,
which keeps grouping deterministic and the reasoning easy to explain.
"""

from __future__ import annotations

import re
from enum import StrEnum
from typing import NamedTuple
from urllib.parse import urlparse

from requirement_intelligence.models.enums import RiskLevel
from requirement_intelligence.models.source_artifact import SourceArtifact


class GroupingDimension(StrEnum):
    """The dimension a group of artifacts was formed on."""

    COMPONENT = "component"
    TAG = "tag"
    ENDPOINT = "endpoint"
    RISK = "risk"


class GroupingKey(NamedTuple):
    """The deterministic key an artifact is grouped under.

    ``dimension`` is which heuristic matched, ``value`` is the normalised
    (lower-cased) grouping value used for equality, and ``label`` is the
    human-readable form used for the module name and the consolidation reason.
    """

    dimension: GroupingDimension
    value: str
    label: str


# --- Risk normalisation ----------------------------------------------------

# Source systems use heterogeneous severity / priority vocabularies. This map
# normalises the common values across JIRA priority, OWASP ZAP risk and
# SonarQube severity onto the platform's single :class:`RiskLevel` scale.
_SEVERITY_TO_RISK: dict[str, RiskLevel] = {
    # CRITICAL
    "critical": RiskLevel.CRITICAL,
    "blocker": RiskLevel.CRITICAL,
    # HIGH
    "high": RiskLevel.HIGH,
    "highest": RiskLevel.HIGH,
    "major": RiskLevel.HIGH,
    # MEDIUM
    "medium": RiskLevel.MEDIUM,
    "moderate": RiskLevel.MEDIUM,
    # LOW
    "low": RiskLevel.LOW,
    "lowest": RiskLevel.LOW,
    "minor": RiskLevel.LOW,
    "info": RiskLevel.LOW,
    "informational": RiskLevel.LOW,
    "trivial": RiskLevel.LOW,
    "none": RiskLevel.LOW,
}

# Ordering used to roll a set of risks up to the single most severe.
_RISK_ORDER: dict[RiskLevel, int] = {
    RiskLevel.LOW: 0,
    RiskLevel.MEDIUM: 1,
    RiskLevel.HIGH: 2,
    RiskLevel.CRITICAL: 3,
}


def normalize_severity(value: str | None) -> RiskLevel | None:
    """Maps a free-form severity / priority string onto a :class:`RiskLevel`.

    Args:
        value: A raw severity or priority label (e.g. ``"Blocker"``, ``"High"``).

    Returns:
        RiskLevel | None: The normalised risk, or ``None`` if unrecognised.
    """
    if not value or not isinstance(value, str):
        return None
    return _SEVERITY_TO_RISK.get(value.strip().lower())


def artifact_risk(artifact: SourceArtifact) -> RiskLevel:
    """Determines the risk level of a single artifact.

    ``severity`` is preferred (ZAP/Sonar findings); ``priority`` is used as a
    fallback (JIRA functional items). Unrecognised or absent values default to
    :attr:`RiskLevel.LOW` so a group always has a well-defined risk.
    """
    return (
        normalize_severity(artifact.severity)
        or normalize_severity(artifact.priority)
        or RiskLevel.LOW
    )


def rollup_risk(artifacts: list[SourceArtifact]) -> RiskLevel:
    """Rolls a group of artifacts up to the single most severe risk level.

    Any CRITICAL -> CRITICAL; else any HIGH -> HIGH; else any MEDIUM -> MEDIUM;
    otherwise LOW. An empty group rolls up to :attr:`RiskLevel.LOW`.
    """
    highest = RiskLevel.LOW
    for artifact in artifacts:
        risk = artifact_risk(artifact)
        if _RISK_ORDER[risk] > _RISK_ORDER[highest]:
            highest = risk
    return highest


# --- Grouping --------------------------------------------------------------

def _clean(value: str | None) -> str | None:
    """Returns a stripped string, or ``None`` if it is empty / not a string."""
    if not value or not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _primary_tag(tags: list[str]) -> str | None:
    """Returns the alphabetically-first non-empty tag, for stable grouping."""
    cleaned = sorted({t.strip() for t in tags if isinstance(t, str) and t.strip()})
    return cleaned[0] if cleaned else None


def extract_endpoint(artifact: SourceArtifact) -> str | None:
    """Extracts a normalised endpoint path from an artifact's URL / location.

    ZAP findings carry the scanned URL in ``location``; deep-link ``url`` values
    are also considered. Non-URL locations (e.g. a SonarQube line number) yield
    ``None`` so they fall through to the next grouping dimension.
    """
    raw = _clean(artifact.url) or _clean(artifact.location)
    if raw is None:
        return None

    parsed = urlparse(raw)
    if parsed.netloc:
        path = parsed.path.rstrip("/") or "/"
        return path.lower()
    if raw.startswith("/"):
        return raw.rstrip("/").lower() or "/"
    return None


def derive_grouping_key(artifact: SourceArtifact) -> GroupingKey:
    """Computes the deterministic grouping key for a single artifact.

    Applies the Phase-1 cascade (component -> tag -> endpoint -> risk) and
    returns the first dimension that produces a value.
    """
    component = _clean(artifact.component)
    if component is not None:
        return GroupingKey(GroupingDimension.COMPONENT, component.lower(), component)

    tag = _primary_tag(artifact.tags)
    if tag is not None:
        return GroupingKey(GroupingDimension.TAG, tag.lower(), tag)

    endpoint = extract_endpoint(artifact)
    if endpoint is not None:
        return GroupingKey(GroupingDimension.ENDPOINT, endpoint, endpoint)

    risk = artifact_risk(artifact)
    return GroupingKey(GroupingDimension.RISK, risk.value, f"{risk.value.title()} risk")


_REASON_TEMPLATES: dict[GroupingDimension, str] = {
    GroupingDimension.COMPONENT: "Grouped by component {label}",
    GroupingDimension.TAG: "Grouped by shared tag {label}",
    GroupingDimension.ENDPOINT: "Grouped by endpoint {label}",
    GroupingDimension.RISK: "Grouped by risk category {value}",
}


def build_reason(key: GroupingKey) -> str:
    """Builds the explainable, human-readable reason a group was formed."""
    return _REASON_TEMPLATES[key.dimension].format(label=key.label, value=key.value)


def build_consolidated_id(key: GroupingKey) -> str:
    """Builds a stable, deterministic id for a consolidation group.

    The id is derived purely from the grouping key, so the same group always
    gets the same id across runs (no random UUIDs).
    """
    slug = re.sub(r"[^a-z0-9]+", "-", key.value.lower()).strip("-") or "unknown"
    return f"cons-{key.dimension.value}-{slug}"
