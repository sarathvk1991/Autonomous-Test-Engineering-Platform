"""OWASP ZAP mapper — raw ZAP alerts to canonical ``SourceArtifact`` records.

Consumes the raw records produced by :class:`ZapConnector` and emits one
:class:`SourceArtifact` per ZAP alert.

Scope is strictly *shape translation*: explicitly mapped fields populate the
canonical fields, reference URLs and CWE/WASC IDs are structured in metadata,
every other ZAP field is preserved under ``metadata`` for traceability, and
nothing is consolidated, scored, or sent to Azure OpenAI.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from requirement_intelligence.mappers.base_mapper import (
    BaseMapper,
    UnsupportedRecordError,
)
from requirement_intelligence.models.enums import (
    SourceCategory,
    SourceSystem,
    SourceType,
)
from requirement_intelligence.models.source_artifact import SourceArtifact


class ZapMapper(BaseMapper):
    """Maps raw OWASP ZAP alerts into canonical :class:`SourceArtifact` records.

    Each alert maps to a ``SourceArtifact`` with ``SourceCategory.SECURITY``
    and ``SourceType.DAST``. An alert that lacks a ``pluginId`` or an ``alert``
    (title) is rejected with :class:`UnsupportedRecordError` rather than mapped
    to a degenerate, untitled artifact.
    """

    def map(self, raw_records: list[dict[str, Any]]) -> list[SourceArtifact]:
        """Map raw ZAP records into canonical artifacts (one per alert)."""
        artifacts: list[SourceArtifact] = []
        for record in raw_records:
            artifacts.append(self._map_alert(record))
        return artifacts

    def _map_alert(self, alert: dict[str, Any]) -> SourceArtifact:
        """Translate a single raw ZAP alert into a ``SourceArtifact``."""
        plugin_id = alert.get("pluginId")
        if not plugin_id:
            raise UnsupportedRecordError(
                "ZAP alert is missing a 'pluginId'; cannot map to a SourceArtifact."
            )

        alert_name = alert.get("alert")
        if not alert_name:
            raise UnsupportedRecordError(
                "ZAP alert is missing an 'alert' (title); "
                "cannot map to a SourceArtifact."
            )

        # Map tags if present
        tags_raw = alert.get("tags")
        if isinstance(tags_raw, dict):
            tags = list(tags_raw.keys())
        elif isinstance(tags_raw, list):
            tags = [str(t) for t in tags_raw]
        else:
            tags = []

        # Map reference URLs
        ref_raw = alert.get("reference") or ""
        reference_urls = [
            line.strip()
            for line in ref_raw.splitlines()
            if line.strip()
        ]

        # Consumed keys to exclude from remaining metadata
        consumed_keys = {"pluginId", "alert", "description", "risk", "url", "tags"}

        # Build metadata
        metadata: dict[str, Any] = {
            "cweid": alert.get("cweid"),
            "wascid": alert.get("wascid"),
            "reference_urls": reference_urls,
        }
        for key, val in alert.items():
            if key not in consumed_keys:
                metadata[key] = val

        return SourceArtifact(
            artifact_id=str(uuid4()),
            source_system=SourceSystem.OWASP_ZAP,
            source_record_id=str(plugin_id),
            source_category=SourceCategory.SECURITY,
            source_type=SourceType.DAST,
            title=alert_name,
            description=alert.get("description"),
            severity=alert.get("risk"),
            location=alert.get("url"),
            tags=tags,
            metadata=metadata,
        )
