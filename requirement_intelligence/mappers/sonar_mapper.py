"""SonarQube mapper — raw SonarQube issues to canonical ``SourceArtifact`` records.

Consumes the raw records produced by :class:`SonarQubeConnector` and emits one
:class:`SourceArtifact` per SonarQube issue.

Scope is strictly *shape translation*: explicitly mapped fields populate the
canonical fields, every other SonarQube field is preserved under ``metadata`` for
traceability, and nothing is consolidated, scored, or sent to Azure OpenAI.
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


class SonarMapper(BaseMapper):
    """Maps raw SonarQube issues into canonical :class:`SourceArtifact` records.

    Each issue maps to a ``SourceArtifact`` with ``SourceCategory.QUALITY``
    and ``SourceType.SAST``. If the issue lacks a ``key``, it raises
    :class:`UnsupportedRecordError`.
    """

    def map(self, raw_records: list[dict[str, Any]]) -> list[SourceArtifact]:
        """Map raw SonarQube records into canonical artifacts (one per issue)."""
        artifacts: list[SourceArtifact] = []
        for record in raw_records:
            for issue in self._iter_issues(record):
                artifacts.append(self._map_issue(issue))
        return artifacts

    @staticmethod
    def _iter_issues(record: dict[str, Any]) -> list[dict[str, Any]]:
        """Yield individual issue dicts from a wrapper or a bare issue record."""
        issues = record.get("issues")
        if isinstance(issues, list):
            return [issue for issue in issues if isinstance(issue, dict)]
        return [record]

    def _map_issue(self, issue: dict[str, Any]) -> SourceArtifact:
        """Translate a single raw SonarQube issue into a ``SourceArtifact``."""
        key = issue.get("key")
        if not key:
            raise UnsupportedRecordError(
                "SonarQube issue is missing a 'key'; cannot map to a SourceArtifact."
            )

        # Map tags if present
        tags_raw = issue.get("tags")
        if isinstance(tags_raw, list):
            tags = [str(t) for t in tags_raw]
        else:
            tags = []

        # Location mapping: line number if present
        line = issue.get("line")
        location = str(line) if line is not None else None

        # Build metadata (all remaining Sonar-specific fields)
        consumed_keys = {
            "key",
            "rule",
            "message",
            "severity",
            "component",
            "line",
            "tags",
            "status",
        }
        metadata: dict[str, Any] = {}
        for k, val in issue.items():
            if k not in consumed_keys:
                metadata[k] = val

        return SourceArtifact(
            artifact_id=str(uuid4()),
            source_system=SourceSystem.SONARQUBE,
            source_record_id=str(key),
            source_category=SourceCategory.QUALITY,
            source_type=SourceType.SAST,
            title=issue.get("rule") or "",
            description=issue.get("message"),
            severity=issue.get("severity"),
            component=issue.get("component"),
            location=location,
            tags=tags,
            status=issue.get("status"),
            metadata=metadata,
        )
