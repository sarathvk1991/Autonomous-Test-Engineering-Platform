"""Grounding confidence model.

Confidence is a deterministic integer, but this milestone builds only the
*carrier*: no scoring is performed here. The model records the score, its band,
the signed components that (by design) sum to it, and the two versions that make
a historical score interpretable — the configuration in force and the framework
code that produced it.
"""

from __future__ import annotations

from pydantic import ConfigDict, Field
from pydantic.alias_generators import to_camel

from requirement_intelligence.grounding.identity.grounding_identity import (
    GroundingConfigurationVersion,
    GroundingFrameworkVersion,
)
from requirement_intelligence.grounding.models.enums import ConfidenceBand
from shared.contracts.base import Schema


class ConfidenceComponent(Schema):
    """One signed contribution to a confidence score, with its reason.

    The score is fully reconstructable from its components, so the number can
    always be explained. ``delta`` may be positive (a bonus) or negative (a penalty).
    """

    model_config = ConfigDict(alias_generator=to_camel)

    factor: str = Field(..., min_length=1, description="What this contribution represents.")
    delta: int = Field(..., description="Signed points contributed (bonus > 0, penalty < 0).")
    reason: str = Field(..., min_length=1, description="Why this contribution applied.")


class GroundingConfidence(Schema):
    """A requirement's grounding confidence, carrying how it was computed.

    ``configuration_version`` and ``framework_version`` are stamped onto every value
    so two scores are known to be directly comparable (same versions) or comparable
    only after accounting for a rule change (different versions) — the same
    auditability discipline ``OrchestrationMetadata`` applies to a context.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    score: int = Field(..., ge=0, le=100, description="Deterministic 0-100 confidence.")
    band: ConfidenceBand = Field(..., description="Coarse band the score falls into.")
    components: tuple[ConfidenceComponent, ...] = Field(
        default=(), description="Signed contributions that reconstruct the score."
    )
    configuration_version: GroundingConfigurationVersion = Field(
        ..., description="Version of the grounding configuration in force."
    )
    framework_version: GroundingFrameworkVersion = Field(
        ..., description="Version of the grounding framework code."
    )
