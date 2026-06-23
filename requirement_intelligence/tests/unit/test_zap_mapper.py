"""Unit tests for :class:`ZapMapper`.

Covers mapping raw OWASP ZAP alerts into canonical ``SourceArtifact`` records,
ensuring identity, classification, metadata extraction, references formatting,
tags normalisation, error handling, and serialization correctness.
"""

from __future__ import annotations

from typing import Any
import pytest

from requirement_intelligence.mappers.base_mapper import (
    BaseMapper,
    UnsupportedRecordError,
)
from requirement_intelligence.mappers.zap_mapper import ZapMapper
from requirement_intelligence.models.enums import (
    SourceCategory,
    SourceSystem,
    SourceType,
)
from requirement_intelligence.models.source_artifact import SourceArtifact


def _alert(
    *,
    plugin_id: str | None = "10020",
    alert: str | None = "Missing Anti-clickjacking Header",
    description: str | None = "The response does not protect against ClickJacking.",
    risk: str | None = "Medium",
    url: str | None = "https://www.saucedemo.com/",
    tags: dict[str, str] | list[str] | None = None,
    cweid: str | None = "1021",
    wascid: str | None = "15",
    reference: str | None = "https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/X-Frame-Options",
    extra_fields: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a raw OWASP ZAP alert dict shaped like the real ZAP alerts."""
    record: dict[str, Any] = {}
    if plugin_id is not None:
        record["pluginId"] = plugin_id
    if alert is not None:
        record["alert"] = alert
    if description is not None:
        record["description"] = description
    if risk is not None:
        record["risk"] = risk
    if url is not None:
        record["url"] = url
    if tags is not None:
        record["tags"] = tags
    else:
        record["tags"] = {
            "OWASP_2021_A05": "https://owasp.org/Top10/A05_2021-Security_Misconfiguration/",
            "POLICY_QA_STD": "",
        }
    if cweid is not None:
        record["cweid"] = cweid
    if wascid is not None:
        record["wascid"] = wascid
    if reference is not None:
        record["reference"] = reference

    if extra_fields:
        record.update(extra_fields)
    return record


# --------------------------------------------------------------------------- #
# Contract
# --------------------------------------------------------------------------- #
@pytest.mark.unit
def test_zap_mapper_is_base_mapper() -> None:
    assert isinstance(ZapMapper(), BaseMapper)


# --------------------------------------------------------------------------- #
# Alert mapping & Field translation
# --------------------------------------------------------------------------- #
@pytest.mark.unit
def test_zap_mapper_fields() -> None:
    raw_alert = _alert()
    [artifact] = ZapMapper().map([raw_alert])

    assert isinstance(artifact, SourceArtifact)
    assert artifact.artifact_id is not None
    assert artifact.source_system == SourceSystem.OWASP_ZAP
    assert artifact.source_record_id == "10020"
    assert artifact.source_category == SourceCategory.SECURITY
    assert artifact.source_type == SourceType.DAST
    assert artifact.title == "Missing Anti-clickjacking Header"
    assert artifact.description == "The response does not protect against ClickJacking."
    assert artifact.severity == "Medium"  # Check that severity matches raw risk directly
    assert artifact.location == "https://www.saucedemo.com/"
    assert set(artifact.tags) == {"OWASP_2021_A05", "POLICY_QA_STD"}


@pytest.mark.unit
def test_zap_mapper_tags_list() -> None:
    raw_alert = _alert(tags=["tag_one", "tag_two"])
    [artifact] = ZapMapper().map([raw_alert])
    assert artifact.tags == ["tag_one", "tag_two"]


@pytest.mark.unit
def test_zap_mapper_tags_missing() -> None:
    raw_alert = _alert(tags=None)
    del raw_alert["tags"]
    [artifact] = ZapMapper().map([raw_alert])
    assert artifact.tags == []


@pytest.mark.unit
def test_artifact_id_is_generated_and_unique() -> None:
    artifacts = ZapMapper().map([_alert(plugin_id="1"), _alert(plugin_id="2")])
    ids = {a.artifact_id for a in artifacts}
    assert len(ids) == 2
    assert all(a.artifact_id for a in artifacts)


# --------------------------------------------------------------------------- #
# Metadata & Reference URLs
# --------------------------------------------------------------------------- #
@pytest.mark.unit
def test_zap_mapper_metadata_preservation() -> None:
    raw_alert = _alert(
        cweid="1021",
        wascid="15",
        reference="https://ref1.com\nhttps://ref2.com",
        extra_fields={"confidence": "High", "method": "GET", "evidence": "no-cookie"},
    )
    [artifact] = ZapMapper().map([raw_alert])

    assert artifact.metadata["cweid"] == "1021"
    assert artifact.metadata["wascid"] == "15"
    assert artifact.metadata["reference_urls"] == ["https://ref1.com", "https://ref2.com"]

    # Raw fields that are not mapped to top-level canonical fields should remain
    assert artifact.metadata["cweid"] == "1021"
    assert artifact.metadata["wascid"] == "15"
    assert artifact.metadata["reference"] == "https://ref1.com\nhttps://ref2.com"
    assert artifact.metadata["confidence"] == "High"
    assert artifact.metadata["method"] == "GET"
    assert artifact.metadata["evidence"] == "no-cookie"

    # Top-level canonical mapped fields must be excluded from metadata
    assert "pluginId" not in artifact.metadata
    assert "alert" not in artifact.metadata
    assert "description" not in artifact.metadata
    assert "risk" not in artifact.metadata
    assert "url" not in artifact.metadata
    assert "tags" not in artifact.metadata


# --------------------------------------------------------------------------- #
# Error Handling
# --------------------------------------------------------------------------- #
@pytest.mark.unit
def test_missing_plugin_id_raises() -> None:
    raw_alert = _alert(plugin_id=None)
    with pytest.raises(UnsupportedRecordError) as exc:
        ZapMapper().map([raw_alert])
    assert "pluginId" in str(exc.value)


@pytest.mark.unit
def test_empty_input_returns_empty_list() -> None:
    assert ZapMapper().map([]) == []


# --------------------------------------------------------------------------- #
# Serialisation Verification
# --------------------------------------------------------------------------- #
@pytest.mark.unit
def test_output_serialises_correctly() -> None:
    [artifact] = ZapMapper().map([_alert()])
    dumped = artifact.model_dump(by_alias=True, mode="json")
    assert dumped["sourceSystem"] == "owasp_zap"
    assert dumped["sourceType"] == "dast"
    assert dumped["sourceCategory"] == "security"
