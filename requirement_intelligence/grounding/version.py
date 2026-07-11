"""Canonical version constants for the Grounding Framework.

Kept in the grounding package (not ``platform_metadata``) so registering the
framework changes no existing platform catalogue or manifest field. A later
milestone may surface these in the platform capability catalogue when grounding
becomes a runtime-wired capability.
"""

from __future__ import annotations

from requirement_intelligence.grounding.identity.grounding_identity import (
    GroundingConfigurationVersion,
    GroundingFrameworkVersion,
)

#: Version of the Grounding Framework code/contract. 1.0.0 is the CAP-077A
#: foundation: models, identities, enums, builders, and configuration container.
GROUNDING_FRAMEWORK_VERSION = GroundingFrameworkVersion(1, 0, 0)

#: Version of the governed grounding configuration. 1.0.0 is weightless
#: (CAP-077A); weights arrive additively in later milestones.
GROUNDING_CONFIGURATION_VERSION = GroundingConfigurationVersion(1, 0, 0)
