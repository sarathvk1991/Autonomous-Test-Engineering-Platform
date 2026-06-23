"""JIRA mapper — raw JIRA issues to canonical ``SourceArtifact`` records.

Consumes the raw records produced by :class:`JiraConnector` and emits one
:class:`SourceArtifact` per JIRA issue. The connector returns the raw JIRA
export verbatim, so a record may be either:

* the export wrapper ``{"epic_id": ..., "issues": [ ... ]}``, or
* an individual issue dict (``{"key": ..., "fields": { ... }}``).

Both shapes are accepted; the mapper flattens any wrapper into its issues.

Scope is strictly *shape translation*: explicitly mapped fields populate the
canonical fields, every other JIRA field is preserved under ``metadata`` for
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

# JIRA issue-type name (lower-cased) -> canonical SourceType.
_ISSUE_TYPE_MAP: dict[str, SourceType] = {
    "epic": SourceType.EPIC,
    "story": SourceType.STORY,
    "bug": SourceType.DEFECT,
}

# ``fields`` keys consumed into canonical fields; everything else is preserved
# verbatim under ``metadata``. ``description`` is added dynamically only when it
# is a plain string we actually consume (see ``_map_issue``).
_CONSUMED_FIELD_KEYS: frozenset[str] = frozenset(
    {"summary", "status", "priority", "labels", "issuetype", "created", "updated"}
)

# Top-level issue keys consumed into canonical fields.
_CONSUMED_TOP_LEVEL_KEYS: frozenset[str] = frozenset({"key", "self", "fields"})


class JiraMapper(BaseMapper):
    """Maps raw JIRA issues into canonical :class:`SourceArtifact` records.

    Issue types map as ``Epic -> EPIC``, ``Story -> STORY``, ``Bug -> DEFECT``;
    every artifact is classified ``SourceCategory.FUNCTIONAL`` and
    ``SourceSystem.JIRA``. Unsupported issue types raise
    :class:`UnsupportedRecordError` rather than being silently dropped.
    """

    def map(self, raw_records: list[dict[str, Any]]) -> list[SourceArtifact]:
        """Map raw JIRA records into canonical artifacts (one per issue)."""
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
        """Translate a single raw JIRA issue into a ``SourceArtifact``."""
        fields: dict[str, Any] = issue.get("fields") or {}

        issue_key = issue.get("key")
        if not issue_key:
            raise UnsupportedRecordError(
                "JIRA issue is missing a 'key'; cannot map to a SourceArtifact."
            )

        source_type = self._resolve_source_type(fields, issue_key)

        description = fields.get("description")
        consumed_field_keys = set(_CONSUMED_FIELD_KEYS)
        if isinstance(description, str):
            # Canonicalise the text; it adds no traceability value in metadata.
            consumed_field_keys.add("description")
        elif description is not None:
            # Non-string descriptions (e.g. ADF objects) are not canonicalised;
            # leave the field empty and preserve the raw value in metadata.
            description = None
        else:
            # Absent description: nothing to canonicalise and a null in metadata
            # is just noise, so treat it as consumed too.
            consumed_field_keys.add("description")

        return SourceArtifact(
            artifact_id=str(uuid4()),
            source_system=SourceSystem.JIRA,
            source_record_id=str(issue_key),
            source_category=SourceCategory.FUNCTIONAL,
            source_type=source_type,
            title=fields.get("summary") or "",
            description=description,
            status=self._name_of(fields.get("status")),
            priority=self._name_of(fields.get("priority")),
            tags=list(fields.get("labels") or []),
            url=issue.get("self"),
            created_at=fields.get("created"),
            updated_at=fields.get("updated"),
            metadata=self._build_metadata(issue, fields, consumed_field_keys),
        )

    @staticmethod
    def _resolve_source_type(fields: dict[str, Any], issue_key: str) -> SourceType:
        """Map the JIRA issue-type name to a canonical ``SourceType``."""
        issue_type = fields.get("issuetype") or {}
        name = str(issue_type.get("name", "")).strip().lower()
        try:
            return _ISSUE_TYPE_MAP[name]
        except KeyError as exc:
            raise UnsupportedRecordError(
                f"Unsupported JIRA issue type "
                f"{issue_type.get('name')!r} on issue {issue_key!r}; "
                f"expected one of {sorted(_ISSUE_TYPE_MAP)}."
            ) from exc

    @staticmethod
    def _name_of(value: Any) -> str | None:
        """Extract the ``name`` from a JIRA sub-object (status/priority)."""
        if isinstance(value, dict):
            name = value.get("name")
            return str(name) if name is not None else None
        return None

    @staticmethod
    def _build_metadata(
        issue: dict[str, Any],
        fields: dict[str, Any],
        consumed_field_keys: set[str],
    ) -> dict[str, Any]:
        """Preserve every JIRA field not mapped to a canonical field."""
        metadata: dict[str, Any] = {
            key: value
            for key, value in issue.items()
            if key not in _CONSUMED_TOP_LEVEL_KEYS
        }
        remaining_fields = {
            key: value
            for key, value in fields.items()
            if key not in consumed_field_keys
        }
        if remaining_fields:
            metadata["fields"] = remaining_fields
        return metadata
