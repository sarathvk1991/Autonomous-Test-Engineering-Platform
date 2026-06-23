"""Unit tests for :class:`JiraMapper`.

Covers issue-type mapping, canonical field translation, metadata preservation,
datetime parsing, both input shapes (export wrapper and bare issues), and the
error path for unsupported issue types.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import pytest

from requirement_intelligence.mappers.base_mapper import (
    BaseMapper,
    UnsupportedRecordError,
)
from requirement_intelligence.mappers.jira_mapper import JiraMapper
from requirement_intelligence.models.enums import (
    SourceCategory,
    SourceSystem,
    SourceType,
)
from requirement_intelligence.models.source_artifact import SourceArtifact


def _issue(
    *,
    key: str = "SCRUM-11",
    issue_type: str = "Story",
    summary: str = "As a user, I want to view products",
    description: Any = "Given a user\nWhen page loads\nThen products show",
    status: str | None = "To Do",
    priority: str | None = "High",
    labels: list[str] | None = None,
    self_link: str | None = "https://example.atlassian.net/rest/api/2/issue/10042",
    created: str | None = "2026-06-18T14:57:34.849+0530",
    updated: str | None = "2026-06-18T14:57:35.620+0530",
    extra_fields: dict[str, Any] | None = None,
    extra_top_level: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a raw JIRA issue dict shaped like the real export."""
    fields: dict[str, Any] = {
        "summary": summary,
        "description": description,
        "issuetype": {"id": "10001", "name": issue_type},
        "status": {"name": status} if status is not None else None,
        "priority": {"name": priority} if priority is not None else None,
        "labels": labels if labels is not None else [],
        "created": created,
        "updated": updated,
        "project": {"key": "SCRUM", "name": "My Automation Product"},
    }
    if extra_fields:
        fields.update(extra_fields)
    issue: dict[str, Any] = {
        "id": "10042",
        "key": key,
        "self": self_link,
        "fields": fields,
    }
    if extra_top_level:
        issue.update(extra_top_level)
    return issue


def _wrapper(*issues: dict[str, Any]) -> dict[str, Any]:
    """Build the JIRA export wrapper the connector returns."""
    return {"epic_id": "SCRUM-10", "total_issues": len(issues), "issues": list(issues)}


# --------------------------------------------------------------------------- #
# Contract
# --------------------------------------------------------------------------- #
@pytest.mark.unit
def test_jira_mapper_is_base_mapper() -> None:
    assert isinstance(JiraMapper(), BaseMapper)


@pytest.mark.unit
def test_base_mapper_cannot_be_instantiated() -> None:
    with pytest.raises(TypeError):
        BaseMapper()  # type: ignore[abstract]


# --------------------------------------------------------------------------- #
# Issue-type mapping
# --------------------------------------------------------------------------- #
@pytest.mark.unit
@pytest.mark.parametrize(
    ("issue_type", "expected"),
    [
        ("Epic", SourceType.EPIC),
        ("Story", SourceType.STORY),
        ("Bug", SourceType.DEFECT),
        ("bug", SourceType.DEFECT),  # case-insensitive
    ],
)
def test_issue_type_mapping(issue_type: str, expected: SourceType) -> None:
    [artifact] = JiraMapper().map([_issue(issue_type=issue_type)])
    assert artifact.source_type == expected


@pytest.mark.unit
def test_unsupported_issue_type_raises() -> None:
    with pytest.raises(UnsupportedRecordError):
        JiraMapper().map([_issue(issue_type="Sub-task")])


@pytest.mark.unit
def test_missing_key_raises() -> None:
    issue = _issue()
    del issue["key"]
    with pytest.raises(UnsupportedRecordError):
        JiraMapper().map([issue])


# --------------------------------------------------------------------------- #
# Field translation
# --------------------------------------------------------------------------- #
@pytest.mark.unit
def test_canonical_fields_mapped() -> None:
    [artifact] = JiraMapper().map(
        [_issue(key="SCRUM-11", labels=["ui", "inventory"])]
    )
    assert isinstance(artifact, SourceArtifact)
    assert artifact.source_system == SourceSystem.JIRA
    assert artifact.source_category == SourceCategory.FUNCTIONAL
    assert artifact.source_record_id == "SCRUM-11"
    assert artifact.title == "As a user, I want to view products"
    assert artifact.description.startswith("Given a user")
    assert artifact.status == "To Do"
    assert artifact.priority == "High"
    assert artifact.tags == ["ui", "inventory"]
    assert artifact.url == "https://example.atlassian.net/rest/api/2/issue/10042"


@pytest.mark.unit
def test_artifact_id_is_generated_and_unique() -> None:
    artifacts = JiraMapper().map(_wrapper(_issue(key="A"), _issue(key="B"))["issues"])
    ids = {a.artifact_id for a in artifacts}
    assert len(ids) == 2
    assert all(a.artifact_id for a in artifacts)


@pytest.mark.unit
def test_missing_optional_fields_become_none_or_empty() -> None:
    [artifact] = JiraMapper().map(
        [_issue(status=None, priority=None, description=None, labels=None)]
    )
    assert artifact.status is None
    assert artifact.priority is None
    assert artifact.description is None
    assert artifact.tags == []


# --------------------------------------------------------------------------- #
# datetime parsing
# --------------------------------------------------------------------------- #
@pytest.mark.unit
def test_timestamps_parsed_to_datetime() -> None:
    [artifact] = JiraMapper().map([_issue()])
    assert isinstance(artifact.created_at, datetime)
    assert isinstance(artifact.updated_at, datetime)
    assert artifact.created_at.year == 2026


# --------------------------------------------------------------------------- #
# Metadata preservation
# --------------------------------------------------------------------------- #
@pytest.mark.unit
def test_unmapped_fields_preserved_in_metadata() -> None:
    [artifact] = JiraMapper().map(
        [_issue(extra_fields={"customfield_101": "X"}, extra_top_level={"id": "999"})]
    )
    # Remaining top-level + nested fields are preserved; mapped ones are not.
    assert artifact.metadata["id"] == "999"
    assert artifact.metadata["fields"]["project"]["key"] == "SCRUM"
    assert artifact.metadata["fields"]["customfield_101"] == "X"
    assert "summary" not in artifact.metadata["fields"]
    assert "status" not in artifact.metadata["fields"]
    assert "key" not in artifact.metadata


@pytest.mark.unit
def test_non_string_description_preserved_in_metadata() -> None:
    adf = {"type": "doc", "content": []}
    [artifact] = JiraMapper().map([_issue(description=adf)])
    assert artifact.description is None
    assert artifact.metadata["fields"]["description"] == adf


@pytest.mark.unit
def test_none_description_not_stored_in_metadata() -> None:
    [artifact] = JiraMapper().map([_issue(description=None)])
    assert artifact.description is None
    assert "description" not in artifact.metadata.get("fields", {})


@pytest.mark.unit
def test_string_description_not_stored_in_metadata() -> None:
    [artifact] = JiraMapper().map([_issue(description="Real description text")])
    assert artifact.description == "Real description text"
    assert "description" not in artifact.metadata.get("fields", {})


# --------------------------------------------------------------------------- #
# Input shapes
# --------------------------------------------------------------------------- #
@pytest.mark.unit
def test_maps_export_wrapper_record() -> None:
    artifacts = JiraMapper().map([_wrapper(_issue(key="A"), _issue(key="B"))])
    assert [a.source_record_id for a in artifacts] == ["A", "B"]


@pytest.mark.unit
def test_maps_bare_issue_records() -> None:
    artifacts = JiraMapper().map([_issue(key="A"), _issue(key="B")])
    assert [a.source_record_id for a in artifacts] == ["A", "B"]


@pytest.mark.unit
def test_empty_input_returns_empty_list() -> None:
    assert JiraMapper().map([]) == []


# --------------------------------------------------------------------------- #
# Serialisation stays canonical
# --------------------------------------------------------------------------- #
@pytest.mark.unit
def test_output_serialises_to_camel_case_json() -> None:
    [artifact] = JiraMapper().map([_issue()])
    dumped = artifact.model_dump(by_alias=True, mode="json")
    assert dumped["sourceSystem"] == "jira"
    assert dumped["sourceType"] == "story"
    assert dumped["sourceCategory"] == "functional"
    assert dumped["createdAt"].startswith("2026-06-18T14:57:34")
