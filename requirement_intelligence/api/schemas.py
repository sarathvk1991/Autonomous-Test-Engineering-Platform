"""API request/response schemas for the Requirement Intelligence Layer.

These are the layer's *transport* contracts (what crosses the HTTP boundary),
kept separate from the internal canonical domain model so the API can evolve
independently of internal representations.
"""

from __future__ import annotations

from shared.contracts.base import Schema
from shared.enums.base import SourceSystem


class IngestRequest(Schema):
    """Request to ingest requirements from one or more registered sources."""

    sources: list[SourceSystem]
    project_key: str | None = None


class AnalysisJobResponse(Schema):
    """Response acknowledging an ingestion/analysis run."""

    job_id: str
    status: str
