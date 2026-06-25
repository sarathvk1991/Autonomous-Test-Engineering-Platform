"""Unit tests for the Consolidation Engine.

Covers deterministic grouping by component, tag and endpoint; mixed-source
grouping into functional/security/quality buckets; risk roll-up; explainable
consolidation reasons; and empty input. No connectors, mappers, files or AI
are involved — the engine only reorganises the artifacts it is handed.
"""

from __future__ import annotations

import pytest

from requirement_intelligence.consolidation.consolidation_engine import (
    ConsolidationEngine,
)
from requirement_intelligence.consolidation.consolidation_exceptions import (
    ConsolidationInputError,
)
from requirement_intelligence.models.enums import (
    RiskLevel,
    SourceCategory,
    SourceSystem,
    SourceType,
)
from requirement_intelligence.models.source_artifact import SourceArtifact

# Defaults keyed per category so a builder only needs to override what matters.
_CATEGORY_DEFAULTS = {
    SourceCategory.FUNCTIONAL: (SourceSystem.JIRA, SourceType.STORY),
    SourceCategory.SECURITY: (SourceSystem.OWASP_ZAP, SourceType.DAST),
    SourceCategory.QUALITY: (SourceSystem.SONARQUBE, SourceType.SAST),
}

_counter = {"n": 0}


def _artifact(
    *,
    category: SourceCategory = SourceCategory.FUNCTIONAL,
    title: str = "Artifact",
    component: str | None = None,
    tags: list[str] | None = None,
    url: str | None = None,
    location: str | None = None,
    severity: str | None = None,
    priority: str | None = None,
) -> SourceArtifact:
    """Builds a SourceArtifact with deterministic identity for tests."""
    _counter["n"] += 1
    system, source_type = _CATEGORY_DEFAULTS[category]
    return SourceArtifact(
        artifact_id=f"art-{_counter['n']}",
        source_system=system,
        source_record_id=f"rec-{_counter['n']}",
        source_category=category,
        source_type=source_type,
        title=title,
        component=component,
        tags=tags or [],
        url=url,
        location=location,
        severity=severity,
        priority=priority,
    )


@pytest.fixture
def engine() -> ConsolidationEngine:
    return ConsolidationEngine()


# --- Grouping by dimension -------------------------------------------------
@pytest.mark.unit
def test_group_by_component(engine: ConsolidationEngine) -> None:
    artifacts = [
        _artifact(component="Authentication", title="Login story"),
        _artifact(component="authentication", title="Hardcoded creds",
                  category=SourceCategory.QUALITY),
        _artifact(component="Billing", title="Invoice story"),
    ]
    result = engine.consolidate(artifacts)

    assert len(result) == 2
    auth = next(c for c in result if c.module == "Authentication")
    # Case-insensitive value match collapses "Authentication" and "authentication".
    assert len(auth.functional_artifacts) == 1
    assert len(auth.quality_artifacts) == 1
    assert auth.consolidation_reason == "Grouped by component Authentication"


@pytest.mark.unit
def test_group_by_tag(engine: ConsolidationEngine) -> None:
    # No component -> falls through to the primary (alphabetically first) tag.
    artifacts = [
        _artifact(tags=["login", "ui"], title="A"),
        _artifact(tags=["zebra", "login"], title="B", category=SourceCategory.SECURITY),
        _artifact(tags=["payments"], title="C"),
    ]
    result = engine.consolidate(artifacts)

    by_module = {c.module: c for c in result}
    assert set(by_module) == {"login", "payments"}
    assert by_module["login"].consolidation_reason == "Grouped by shared tag login"
    # "A" (primary tag login) and "B" (primary tag login) land together.
    login = by_module["login"]
    assert len(login.functional_artifacts) == 1
    assert len(login.security_artifacts) == 1


@pytest.mark.unit
def test_group_by_endpoint(engine: ConsolidationEngine) -> None:
    # No component, no tags -> falls through to endpoint path.
    artifacts = [
        _artifact(category=SourceCategory.SECURITY, title="Missing HSTS",
                  location="https://app.example.com/login?x=1"),
        _artifact(category=SourceCategory.SECURITY, title="Reflected XSS",
                  url="https://app.example.com/login"),
        _artifact(category=SourceCategory.SECURITY, title="Open redirect",
                  location="https://app.example.com/logout"),
    ]
    result = engine.consolidate(artifacts)

    by_module = {c.module: c for c in result}
    assert set(by_module) == {"/login", "/logout"}
    assert len(by_module["/login"].security_artifacts) == 2
    assert by_module["/login"].consolidation_reason == "Grouped by endpoint /login"


# --- Mixed-source grouping -------------------------------------------------
@pytest.mark.unit
def test_mixed_source_grouping(engine: ConsolidationEngine) -> None:
    artifacts = [
        _artifact(category=SourceCategory.FUNCTIONAL, component="Authentication",
                  title="Authentication Story"),
        _artifact(category=SourceCategory.SECURITY, component="Authentication",
                  title="Missing HSTS Header", severity="High"),
        _artifact(category=SourceCategory.QUALITY, component="Authentication",
                  title="Hardcoded Credentials", severity="CRITICAL"),
    ]
    result = engine.consolidate(artifacts)

    assert len(result) == 1
    consolidated = result[0]
    assert consolidated.module == "Authentication"
    assert len(consolidated.functional_artifacts) == 1
    assert len(consolidated.security_artifacts) == 1
    assert len(consolidated.quality_artifacts) == 1
    assert consolidated.functional_artifacts[0].title == "Authentication Story"
    assert consolidated.security_artifacts[0].title == "Missing HSTS Header"
    assert consolidated.quality_artifacts[0].title == "Hardcoded Credentials"
    assert consolidated.business_area is None
    assert consolidated.related_artifact_ids == []
    assert consolidated.consolidated_id == "cons-component-authentication"


# --- Risk calculation ------------------------------------------------------
@pytest.mark.unit
@pytest.mark.parametrize(
    ("severities", "expected"),
    [
        (["Low", "Informational"], RiskLevel.LOW),
        (["Low", "Medium"], RiskLevel.MEDIUM),
        (["Medium", "High", "Low"], RiskLevel.HIGH),
        (["High", "CRITICAL"], RiskLevel.CRITICAL),
        (["Blocker", "Minor"], RiskLevel.CRITICAL),
    ],
)
def test_risk_calculation(
    engine: ConsolidationEngine, severities: list[str], expected: RiskLevel
) -> None:
    artifacts = [
        _artifact(category=SourceCategory.SECURITY, component="Mod", severity=s)
        for s in severities
    ]
    result = engine.consolidate(artifacts)
    assert len(result) == 1
    assert result[0].risk_level == expected


@pytest.mark.unit
def test_risk_uses_priority_fallback(engine: ConsolidationEngine) -> None:
    # JIRA functional items carry priority, not severity.
    artifacts = [_artifact(component="Mod", priority="High")]
    result = engine.consolidate(artifacts)
    assert result[0].risk_level == RiskLevel.HIGH


@pytest.mark.unit
def test_risk_defaults_low_when_unknown(engine: ConsolidationEngine) -> None:
    artifacts = [_artifact(component="Mod", severity="nonsense-value")]
    result = engine.consolidate(artifacts)
    assert result[0].risk_level == RiskLevel.LOW


# --- Consolidation reason --------------------------------------------------
@pytest.mark.unit
def test_consolidation_reason_text(engine: ConsolidationEngine) -> None:
    component = engine.consolidate([_artifact(component="Payments")])[0]
    tag = engine.consolidate([_artifact(tags=["checkout"])])[0]
    endpoint = engine.consolidate(
        [_artifact(category=SourceCategory.SECURITY, url="https://x/api/orders")]
    )[0]
    risk = engine.consolidate(
        [_artifact(category=SourceCategory.SECURITY, severity="High")]
    )[0]

    assert component.consolidation_reason == "Grouped by component Payments"
    assert tag.consolidation_reason == "Grouped by shared tag checkout"
    assert endpoint.consolidation_reason == "Grouped by endpoint /api/orders"
    assert risk.consolidation_reason == "Grouped by risk category high"


# --- Determinism & ordering ------------------------------------------------
@pytest.mark.unit
def test_grouping_is_deterministic(engine: ConsolidationEngine) -> None:
    artifacts = [
        _artifact(component="B"),
        _artifact(component="A"),
        _artifact(component="B"),
    ]
    first = engine.consolidate(artifacts)
    second = engine.consolidate(artifacts)

    # Group order follows first appearance: B before A.
    assert [c.module for c in first] == ["B", "A"]
    assert [c.consolidated_id for c in first] == [c.consolidated_id for c in second]


# --- Empty / invalid input -------------------------------------------------
@pytest.mark.unit
def test_empty_input(engine: ConsolidationEngine) -> None:
    assert engine.consolidate([]) == []


@pytest.mark.unit
def test_invalid_input_type(engine: ConsolidationEngine) -> None:
    with pytest.raises(ConsolidationInputError, match="Expected a list of SourceArtifact"):
        engine.consolidate("not-a-list")  # type: ignore[arg-type]


@pytest.mark.unit
def test_invalid_member_type(engine: ConsolidationEngine) -> None:
    with pytest.raises(ConsolidationInputError, match="Expected SourceArtifact"):
        engine.consolidate([_artifact(component="Mod"), "nope"])  # type: ignore[list-item]
