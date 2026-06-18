"""Aggregate API router for the modular monolith.

Each platform layer owns its own :class:`fastapi.APIRouter`. This module is the
single composition point where those layer routers are mounted under a common
``/api/v1`` prefix. Adding a new layer is a one-line ``include_router`` call.
"""

from __future__ import annotations

from fastapi import APIRouter

from requirement_intelligence.api.router import router as requirement_intelligence_router

api_router = APIRouter(prefix="/api/v1")

# --- Phase 1 -----------------------------------------------------------------
api_router.include_router(requirement_intelligence_router)

# --- Future phases (mount as each layer is implemented) ----------------------
# api_router.include_router(feature_engineering_router)
# api_router.include_router(automation_engineering_router)
# api_router.include_router(quality_governance_router)
# api_router.include_router(execution_router)
# api_router.include_router(failure_intelligence_router)
