"""The :class:`LearningSummary` and :class:`LearningMetrics` — the headline
and deterministic numeric roll-up for one Learning build.

Both are pure data containers, mirroring ``OrganizationalMemorySummary`` /
``OrganizationalMemoryMetrics`` (ADR-0027): recorded values, never
model-internal calculations. Nothing is computed here — a future engine
(CAP-086B, reserved) computes every field exactly once from already-finished
collaborators.
"""

from __future__ import annotations

from pydantic import ConfigDict, Field
from pydantic.alias_generators import to_camel

from requirement_intelligence.learning.identity import LearningPolicyId, LearningPolicyVersion
from shared.contracts.base import Schema


class LearningSummary(Schema):
    """The governed headline for one Learning build. A pure data container.

    Carries only the governing policy's identity/version (mirrors
    ``OrganizationalMemorySummary.policy_version``); this is a reference,
    never a duplicate policy shape.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    policy_id: LearningPolicyId = Field(..., description="Governing policy identity.")
    policy_version: LearningPolicyVersion = Field(..., description="Governing policy version.")

    total_candidates: int = Field(..., ge=0, description="Total learning candidates recorded.")
    total_learnings: int = Field(..., ge=0, description="Total learnings recorded.")
    total_validations: int = Field(..., ge=0, description="Total validation records recorded.")

    headline: str = Field(..., min_length=1, description="One-line deterministic build summary.")


class LearningMetrics(Schema):
    """Deterministic numeric roll-ups for one Learning build. Data only.

    Every count is a recorded value, never a model-internal calculation — a
    future engine (CAP-086B, reserved) computes each exactly once.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    candidate_count: int = Field(..., ge=0, description="Total number of learning candidates.")
    learning_count: int = Field(..., ge=0, description="Total number of learnings.")
    validation_count: int = Field(..., ge=0, description="Total number of validation records.")
    observed_count: int = Field(
        ..., ge=0, description="Number of subjects currently at OBSERVED maturity."
    )
    validated_count: int = Field(
        ..., ge=0, description="Number of subjects currently at VALIDATED maturity."
    )
    trusted_count: int = Field(
        ..., ge=0, description="Number of subjects currently at TRUSTED maturity."
    )
    institutional_count: int = Field(
        ..., ge=0, description="Number of subjects currently at INSTITUTIONAL maturity."
    )
    standard_count: int = Field(
        ..., ge=0, description="Number of subjects currently at STANDARD maturity."
    )
    retired_count: int = Field(
        ..., ge=0, description="Number of subjects currently at RETIRED maturity."
    )
