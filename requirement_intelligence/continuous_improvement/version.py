"""Canonical version constants for the Continuous Improvement Framework.

Kept in the continuous_improvement package (not ``platform_metadata``) so
registering the framework changes no existing platform catalogue or manifest
field, and the Architecture Version stays 1.2.0 — mirroring
``recommendation/version.py`` (ADR-0019).
"""

from __future__ import annotations

from requirement_intelligence.continuous_improvement.identity import (
    ContinuousImprovementFrameworkVersion,
    ImprovementPolicyVersion,
)

#: Version of the Continuous Improvement Framework code/contract. 1.0.0 is the
#: CAP-083A foundation: canonical models, typed identities, enumerations, the
#: governed policy and its builder, and the dormant Continuous Improvement
#: service contract.
CONTINUOUS_IMPROVEMENT_FRAMEWORK_VERSION = ContinuousImprovementFrameworkVersion(1, 0, 0)

#: Version of the governed default improvement policy. 1.0.0 is the CAP-083A
#: foundation policy — governed capability switches and deterministic thresholds
#: as data only; no capability is exercised and no consumer reads them yet.
#: Tuning advances this version, never a code change (mirrors ADR-0019
#: Recommendation 5).
IMPROVEMENT_POLICY_VERSION = ImprovementPolicyVersion(1, 0, 0)
