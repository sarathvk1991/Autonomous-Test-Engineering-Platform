"""Router for the Requirement Intelligence Layer.

Aggregates the layer's route modules under a single prefix/tag. Mounted by the
application-level router in ``app/api/router.py``.
"""

from __future__ import annotations

from fastapi import APIRouter

from requirement_intelligence.api.routes import requirements

router = APIRouter(prefix="/requirement-intelligence", tags=["requirement-intelligence"])

router.include_router(requirements.router)
