"""Unit tests for the Canonical Data Model.

Covers the two architectural enhancements (the ``SourceSystem`` enum and the
``datetime`` timestamp fields) plus the cross-cutting guarantees the models
must keep: camelCase JSON via aliases, enum-by-value serialisation, frozen +
strict (``extra="forbid"``) behaviour, and safe mutable defaults.
"""

from __future__ import annotations

from datetime import datetime

import pytest
from pydantic import ValidationError

from requirement_intelligence.models.consolidated_artifact import ConsolidatedArtifact
from requirement_intelligence.models.enums import (
    RiskLevel,
    SourceCategory,
    SourceSystem,
    SourceType,
)
from requirement_intelligence.models.requirement_package import RequirementPackage
from requirement_intelligence.models.source_artifact import SourceArtifact


def _make_artifact(**overrides: object) -> SourceArtifact:
    """Build a valid SourceArtifact, overriding individual fields as needed."""
    data: dict[str, object] = {
        "artifactId": "ART-1",
        "sourceSystem": SourceSystem.JIRA,
        "sourceRecordId": "PROJ-42",
        "sourceCategory": SourceCategory.FUNCTIONAL,
        "sourceType": SourceType.STORY,
        "title": "Login should lock after 5 attempts",
    }
    data.update(overrides)
    return SourceArtifact(**data)


# --------------------------------------------------------------------------- #
# 1. SourceSystem enum
# --------------------------------------------------------------------------- #
@pytest.mark.unit
@pytest.mark.parametrize(
    ("member", "value"),
    [
        (SourceSystem.JIRA, "jira"),
        (SourceSystem.OWASP_ZAP, "owasp_zap"),
        (SourceSystem.SONARQUBE, "sonarqube"),
        (SourceSystem.HP_ALM, "hp_alm"),
        (SourceSystem.AZURE_DEVOPS, "azure_devops"),
        (SourceSystem.TEST_ENGINE, "test_engine"),
        (SourceSystem.FAILURE_ENGINE, "failure_engine"),
    ],
)
def test_source_system_serializes_by_value(member: SourceSystem, value: str) -> None:
    # StrEnum members compare equal to their plain-string value.
    assert member == value
    assert member.value == value
    assert str(member) == value


# --------------------------------------------------------------------------- #
# 2. SourceArtifact.source_system typing
# --------------------------------------------------------------------------- #
@pytest.mark.unit
def test_source_system_accepts_enum_member() -> None:
    artifact = _make_artifact(sourceSystem=SourceSystem.JIRA)
    # Schema sets use_enum_values=True, so the value is stored (and compares
    # equal to the member via StrEnum). This is what guarantees by-value JSON.
    assert artifact.source_system == SourceSystem.JIRA
    assert artifact.source_system == "jira"


@pytest.mark.unit
def test_source_system_accepts_camel_string_input() -> None:
    artifact = _make_artifact(sourceSystem="jira")
    assert artifact.source_system == SourceSystem.JIRA


@pytest.mark.unit
def test_source_system_serializes_to_camel_value() -> None:
    dumped = _make_artifact().model_dump(by_alias=True)
    assert dumped["sourceSystem"] == "jira"


# --------------------------------------------------------------------------- #
# 3. datetime parsing
# --------------------------------------------------------------------------- #
@pytest.mark.unit
def test_iso8601_strings_parsed_to_datetime() -> None:
    artifact = _make_artifact(
        createdAt="2026-01-15T09:30:00+00:00",
        updatedAt="2026-02-20T14:45:00+00:00",
    )
    assert isinstance(artifact.created_at, datetime)
    assert isinstance(artifact.updated_at, datetime)
    assert artifact.created_at.year == 2026
    assert artifact.updated_at.month == 2


@pytest.mark.unit
def test_datetime_roundtrips_to_iso8601_with_camel_keys() -> None:
    artifact = _make_artifact(createdAt="2026-01-15T09:30:00+00:00")
    dumped = artifact.model_dump(by_alias=True, mode="json")
    assert "createdAt" in dumped
    assert dumped["createdAt"].startswith("2026-01-15T09:30:00")


# --------------------------------------------------------------------------- #
# 4. strict schema behaviour
# --------------------------------------------------------------------------- #
@pytest.mark.unit
def test_extra_fields_rejected() -> None:
    with pytest.raises(ValidationError):
        _make_artifact(unexpected="nope")


@pytest.mark.unit
def test_invalid_source_system_rejected() -> None:
    with pytest.raises(ValidationError):
        _make_artifact(sourceSystem="not_a_real_system")


@pytest.mark.unit
def test_model_is_frozen() -> None:
    artifact = _make_artifact()
    with pytest.raises(ValidationError):
        artifact.title = "mutated"  # type: ignore[misc]


# --------------------------------------------------------------------------- #
# 5. default factories
# --------------------------------------------------------------------------- #
@pytest.mark.unit
def test_collection_fields_default_empty() -> None:
    artifact = _make_artifact()
    assert artifact.tags == []
    assert artifact.metadata == {}


@pytest.mark.unit
def test_mutable_defaults_not_shared_between_instances() -> None:
    first = _make_artifact(artifactId="A", tags=["x"], metadata={"k": "v"})
    second = _make_artifact(artifactId="B")
    assert second.tags == []
    assert second.metadata == {}
    assert first.tags == ["x"]


# --------------------------------------------------------------------------- #
# 6. existing model compatibility
# --------------------------------------------------------------------------- #
@pytest.mark.unit
def test_consolidated_artifact_accepts_source_artifacts() -> None:
    functional = _make_artifact(artifactId="F-1")
    security = _make_artifact(
        artifactId="S-1",
        sourceSystem=SourceSystem.OWASP_ZAP,
        sourceCategory=SourceCategory.SECURITY,
        sourceType=SourceType.DAST,
        title="Reflected XSS",
    )
    consolidated = ConsolidatedArtifact(
        consolidatedId="C-1",
        module="auth",
        riskLevel=RiskLevel.HIGH,
        functionalArtifacts=[functional],
        securityArtifacts=[security],
    )
    dumped = consolidated.model_dump(by_alias=True)
    assert dumped["functionalArtifacts"][0]["sourceSystem"] == "jira"
    assert dumped["securityArtifacts"][0]["sourceType"] == "dast"


@pytest.mark.unit
def test_requirement_package_accepts_supporting_artifacts() -> None:
    package = RequirementPackage(
        packageId="P-1",
        module="auth",
        requirements=["Account must lock after 5 failed attempts"],
        supportingArtifacts=["ART-1", "S-1"],
    )
    dumped = package.model_dump(by_alias=True)
    assert dumped["supportingArtifacts"] == ["ART-1", "S-1"]
    assert dumped["packageId"] == "P-1"
