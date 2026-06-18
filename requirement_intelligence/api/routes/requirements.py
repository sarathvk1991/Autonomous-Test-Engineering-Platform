"""HTTP routes for requirement ingestion and analysis.

Routes are thin: they validate input, delegate to the layer's workflow/services,
and shape the response. No business logic lives in the route handlers.
"""

from __future__ import annotations

from fastapi import APIRouter, status

from requirement_intelligence.api.schemas import AnalysisJobResponse, IngestRequest

router = APIRouter(prefix="/requirements")


@router.post(
    "/ingest",
    response_model=AnalysisJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Ingest and analyze requirements from registered sources",
)
async def ingest_requirements(payload: IngestRequest) -> AnalysisJobResponse:
    """Trigger the requirement ingestion → analysis → CP1 validation pipeline.

    Implementation deferred: will delegate to
    ``requirement_intelligence.workflows.requirement_pipeline``.
    """
    raise NotImplementedError("Requirement ingestion pipeline not yet implemented")
