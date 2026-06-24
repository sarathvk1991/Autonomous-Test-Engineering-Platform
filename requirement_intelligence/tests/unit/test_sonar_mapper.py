"""Unit tests for :class:`SonarMapper`.

Covers mapping raw SonarQube issues into canonical ``SourceArtifact`` records,
ensuring identity, classification, metadata extraction, tags, line mapping,
error handling, and serialization correctness.
"""

from __future__ import annotations

from typing import Any

import pytest

from requirement_intelligence.mappers.base_mapper import (
    BaseMapper,
    UnsupportedRecordError,
)
from requirement_intelligence.mappers.sonar_mapper import SonarMapper
from requirement_intelligence.models.enums import (
    SourceCategory,
    SourceSystem,
    SourceType,
)
from requirement_intelligence.models.source_artifact import SourceArtifact


def _issue(
    *,
    key: str | None = "5531ff19-d1b4-41cc-a450-f2175ca09309",
    rule: str | None = "java:S4144",
    severity: str | None = "MAJOR",
    component: str | None = "Automation-POC:src/test/java/BadCartPage.java",
    line: int | None = 73,
    status: str | None = "OPEN",
    message: str | None = "Update this method so that its implementation is not identical",
    tags: list[str] | None = None,
    extra_fields: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a raw SonarQube issue dict shaped like the real SonarQube issues."""
    record: dict[str, Any] = {}
    if key is not None:
        record["key"] = key
    if rule is not None:
        record["rule"] = rule
    if severity is not None:
        record["severity"] = severity
    if component is not None:
        record["component"] = component
    if line is not None:
        record["line"] = line
    if status is not None:
        record["status"] = status
    if message is not None:
        record["message"] = message
    if tags is not None:
        record["tags"] = tags
    else:
        record["tags"] = ["confusing", "duplicate", "suspicious"]

    if extra_fields:
        record.update(extra_fields)
    return record


# --------------------------------------------------------------------------- #
# Contract
# --------------------------------------------------------------------------- #
@pytest.mark.unit
def test_sonar_mapper_is_base_mapper() -> None:
    assert isinstance(SonarMapper(), BaseMapper)


# --------------------------------------------------------------------------- #
# Issue mapping & Field translation
# --------------------------------------------------------------------------- #
@pytest.mark.unit
def test_sonar_mapper_fields() -> None:
    raw_issue = _issue()
    [artifact] = SonarMapper().map([raw_issue])

    assert isinstance(artifact, SourceArtifact)
    assert artifact.artifact_id is not None
    assert artifact.source_system == SourceSystem.SONARQUBE
    assert artifact.source_record_id == "5531ff19-d1b4-41cc-a450-f2175ca09309"
    assert artifact.source_category == SourceCategory.QUALITY
    assert artifact.source_type == SourceType.SAST
    assert artifact.title == "java:S4144"
    assert artifact.description == "Update this method so that its implementation is not identical"
    assert artifact.severity == "MAJOR"
    assert artifact.component == "Automation-POC:src/test/java/BadCartPage.java"
    assert artifact.location == "73"
    assert artifact.tags == ["confusing", "duplicate", "suspicious"]
    assert artifact.status == "OPEN"


@pytest.mark.unit
def test_sonar_mapper_missing_line() -> None:
    raw_issue = _issue(line=None)
    [artifact] = SonarMapper().map([raw_issue])
    assert artifact.location is None


@pytest.mark.unit
def test_sonar_mapper_tags_missing() -> None:
    raw_issue = _issue(tags=None)
    del raw_issue["tags"]
    [artifact] = SonarMapper().map([raw_issue])
    assert artifact.tags == []


@pytest.mark.unit
def test_artifact_id_is_generated_and_unique() -> None:
    artifacts = SonarMapper().map([_issue(key="1"), _issue(key="2")])
    ids = {a.artifact_id for a in artifacts}
    assert len(ids) == 2
    assert all(a.artifact_id for a in artifacts)


# --------------------------------------------------------------------------- #
# Wrapper handling
# --------------------------------------------------------------------------- #
@pytest.mark.unit
def test_sonar_mapper_handles_wrapper() -> None:
    wrapper = {
        "total": 2,
        "issues": [
            _issue(key="key-1"),
            _issue(key="key-2"),
        ]
    }
    artifacts = SonarMapper().map([wrapper])
    assert len(artifacts) == 2
    assert artifacts[0].source_record_id == "key-1"
    assert artifacts[1].source_record_id == "key-2"


# --------------------------------------------------------------------------- #
# Metadata preservation
# --------------------------------------------------------------------------- #
@pytest.mark.unit
def test_sonar_mapper_metadata_preservation() -> None:
    raw_issue = _issue(
        extra_fields={
            "project": "Automation-POC",
            "effort": "15min",
            "debt": "15min",
            "author": "sarathvk619@gmail.com",
            "creationDate": "2026-06-17T12:37:22+0000",
            "updateDate": "2026-06-17T12:37:22+0000",
        }
    )
    [artifact] = SonarMapper().map([raw_issue])

    # Raw fields not mapped to canonical top-level fields should be in metadata
    assert artifact.metadata["project"] == "Automation-POC"
    assert artifact.metadata["effort"] == "15min"
    assert artifact.metadata["debt"] == "15min"
    assert artifact.metadata["author"] == "sarathvk619@gmail.com"
    assert artifact.metadata["creationDate"] == "2026-06-17T12:37:22+0000"
    assert artifact.metadata["updateDate"] == "2026-06-17T12:37:22+0000"

    # Top-level canonical mapped fields must be excluded from metadata
    assert "key" not in artifact.metadata
    assert "rule" not in artifact.metadata
    assert "message" not in artifact.metadata
    assert "severity" not in artifact.metadata
    assert "component" not in artifact.metadata
    assert "line" not in artifact.metadata
    assert "tags" not in artifact.metadata
    assert "status" not in artifact.metadata


# --------------------------------------------------------------------------- #
# Error Handling
# --------------------------------------------------------------------------- #
@pytest.mark.unit
def test_missing_key_raises() -> None:
    raw_issue = _issue(key=None)
    with pytest.raises(UnsupportedRecordError) as exc:
        SonarMapper().map([raw_issue])
    assert "key" in str(exc.value)


@pytest.mark.unit
@pytest.mark.parametrize("rule_value", [None, ""])
def test_missing_rule_raises(rule_value: str | None) -> None:
    raw_issue = _issue(rule=rule_value)
    if rule_value is not None:
        raw_issue["rule"] = rule_value  # _issue() skips None; force empty string
    with pytest.raises(UnsupportedRecordError) as exc:
        SonarMapper().map([raw_issue])
    assert "rule" in str(exc.value)


@pytest.mark.unit
@pytest.mark.parametrize("message_value", [None, ""])
def test_missing_message_raises(message_value: str | None) -> None:
    raw_issue = _issue(message=message_value)
    if message_value is not None:
        raw_issue["message"] = message_value  # _issue() skips None; force empty
    with pytest.raises(UnsupportedRecordError) as exc:
        SonarMapper().map([raw_issue])
    assert "message" in str(exc.value)


@pytest.mark.unit
def test_optional_fields_can_be_missing() -> None:
    raw_issue = _issue(
        severity=None, component=None, line=None, status=None, tags=None
    )
    del raw_issue["tags"]
    [artifact] = SonarMapper().map([raw_issue])
    assert artifact.severity is None
    assert artifact.component is None
    assert artifact.location is None
    assert artifact.status is None
    assert artifact.tags == []
    # Mandatory fields still populated.
    assert artifact.title == "java:S4144"
    assert artifact.description


@pytest.mark.unit
def test_empty_input_returns_empty_list() -> None:
    assert SonarMapper().map([]) == []


# --------------------------------------------------------------------------- #
# Serialisation Verification
# --------------------------------------------------------------------------- #
@pytest.mark.unit
def test_output_serialises_correctly() -> None:
    [artifact] = SonarMapper().map([_issue()])
    dumped = artifact.model_dump(by_alias=True, mode="json")
    assert dumped["sourceSystem"] == "sonarqube"
    assert dumped["sourceType"] == "sast"
    assert dumped["sourceCategory"] == "quality"
