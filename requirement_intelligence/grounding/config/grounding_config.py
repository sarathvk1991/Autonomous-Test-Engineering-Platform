"""Governed grounding configuration.

Following the "policy is data" principle of ADR-0015, the weights and thresholds
that will drive matching, classification, and confidence live in a versioned
configuration object rather than as literals scattered through the code.

**This milestone (CAP-077A) defines the versioned container only — it holds no
weights and no thresholds yet.** They arrive with the matching and confidence
milestones (CAP-077B onward), each bump advancing ``GroundingConfigurationVersion``
under the golden re-baseline procedure. The empty container exists now so every
downstream model can already reference a governed configuration version.
"""

from __future__ import annotations

from pydantic import ConfigDict, Field
from pydantic.alias_generators import to_camel

from requirement_intelligence.grounding.identity.grounding_identity import (
    GroundingConfigurationVersion,
    GroundingFrameworkVersion,
)
from requirement_intelligence.grounding.version import (
    GROUNDING_CONFIGURATION_VERSION,
    GROUNDING_FRAMEWORK_VERSION,
)
from shared.contracts.base import Schema


class GroundingConfiguration(Schema):
    """The governed, versioned grounding configuration.

    Reserved for weights and thresholds (matching cut-offs, confidence base values
    and penalties, band boundaries, score weights). None are present yet; the model
    carries only its identity so a value can be referenced and audited today.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    version: GroundingConfigurationVersion = Field(
        ..., description="Semantic version of this configuration."
    )
    framework_version: GroundingFrameworkVersion = Field(
        ..., description="Framework version this configuration targets."
    )


def default_grounding_configuration() -> GroundingConfiguration:
    """Return the default, weightless grounding configuration for this milestone."""
    return GroundingConfiguration(
        version=GROUNDING_CONFIGURATION_VERSION,
        framework_version=GROUNDING_FRAMEWORK_VERSION,
    )
