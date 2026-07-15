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

#: Version of the governed default improvement policy. 1.0.0 was the CAP-083A
#: foundation policy (capability switches and deterministic thresholds as data
#: only, no capability exercised). 1.1.0 is the CAP-083B tuning: the governed
#: ``enable_deterministic_engine`` switch flips to ``True`` now that
#: ``DeterministicContinuousImprovementEngine`` exists — a versioned policy
#: *value* change, never a policy *shape* change and never an engine code
#: change (mirrors ADR-0019 Recommendation 5).
IMPROVEMENT_POLICY_VERSION = ImprovementPolicyVersion(1, 1, 0)
