"""Canonical version constants for the Recommendation Framework.

Kept in the recommendation package (not ``platform_metadata``) so registering the
framework changes no existing platform catalogue or manifest field, and the
Architecture Version stays 1.2.0 — mirroring ``enhancement/version.py`` (ADR-0018) and
``quality_governance/version.py`` (ADR-0017).
"""

from __future__ import annotations

from requirement_intelligence.recommendation.identity.recommendation_identity import (
    RecommendationFrameworkVersion,
    RecommendationPolicyVersion,
)

#: Version of the Recommendation Framework code/contract. 1.0.0 is the CAP-082A
#: foundation: canonical models, typed identities, enumerations, the governed policy
#: and its builder, and the dormant recommendation service contract.
RECOMMENDATION_FRAMEWORK_VERSION = RecommendationFrameworkVersion(1, 0, 0)

#: Version of the governed default recommendation policy. 1.0.0 was the CAP-082A
#: foundation policy (capability switches and deterministic configuration as data
#: only, no capability exercised). 1.1.0 is the CAP-082B tuning: the governed
#: ``enable_deterministic_engine`` switch flips to ``True`` now that
#: ``DeterministicRecommendationEngine`` exists — a versioned policy *value* change,
#: never a policy *shape* change and never an engine code change (Recommendation 5).
RECOMMENDATION_POLICY_VERSION = RecommendationPolicyVersion(1, 1, 0)
