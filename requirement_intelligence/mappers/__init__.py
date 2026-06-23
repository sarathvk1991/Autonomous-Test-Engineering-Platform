"""Source mappers: translate raw connector records into the canonical model.

Each mapper normalises one source system's raw ``list[dict]`` into canonical
:class:`~requirement_intelligence.models.source_artifact.SourceArtifact`
records. Shape translation only — no consolidation, AI, or business rules.
"""

from __future__ import annotations

from requirement_intelligence.mappers.base_mapper import (
    BaseMapper,
    MapperError,
    UnsupportedRecordError,
)
from requirement_intelligence.mappers.jira_mapper import JiraMapper
from requirement_intelligence.mappers.zap_mapper import ZapMapper

__all__ = [
    "BaseMapper",
    "JiraMapper",
    "ZapMapper",
    "MapperError",
    "UnsupportedRecordError",
]

