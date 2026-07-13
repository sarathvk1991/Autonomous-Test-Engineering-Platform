"""Canonical version constants for the Requirement Intelligence Enhancement Framework.

Kept in the enhancement package (not ``platform_metadata``) so registering the
framework changes no existing platform catalogue or manifest field, and the
Architecture Version stays 1.2.0 — mirroring ``quality_governance/version.py``
(ADR-0017). A later milestone may surface these in the platform capability catalogue
when Requirement Enhancement becomes a runtime-wired capability.
"""

from __future__ import annotations

from requirement_intelligence.enhancement.identity.enhancement_identity import (
    EnhancementFrameworkVersion,
    EnhancementPolicyVersion,
)

#: Version of the Requirement Enhancement Framework code/contract. 1.0.0 is the
#: CAP-081A foundation: canonical models, typed identities, enumerations, the governed
#: policy and its builder, and the dormant enhancement service contract.
ENHANCEMENT_FRAMEWORK_VERSION = EnhancementFrameworkVersion(1, 0, 0)

#: Version of the governed default enhancement policy. 1.0.0 is the CAP-081A
#: foundation policy — governed capability switches and deterministic configuration as
#: data only; no capability is exercised and no consumer reads them yet. Tuning
#: advances this version, never a code change (Recommendation 4).
ENHANCEMENT_POLICY_VERSION = EnhancementPolicyVersion(1, 0, 0)
