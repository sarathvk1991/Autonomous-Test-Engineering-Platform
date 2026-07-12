"""Canonical version constants for the Quality Governance Framework.

Kept in the quality_governance package (not ``platform_metadata``) so registering
the framework changes no existing platform catalogue or manifest field, and the
Architecture Version stays 1.2.0. A later milestone may surface these in the
platform capability catalogue when Quality Governance becomes a runtime-wired
capability.
"""

from __future__ import annotations

from requirement_intelligence.quality_governance.identity.quality_identity import (
    QualityGovernanceVersion,
    QualityPolicyVersion,
)

#: Version of the Quality Governance Framework code/contract. 1.0.0 is the CAP-080A
#: foundation: canonical models, typed identities, enumerations, the governed policy
#: and its builder, and the dormant governance service contract.
QUALITY_GOVERNANCE_FRAMEWORK_VERSION = QualityGovernanceVersion(1, 0, 0)

#: Version of the governed default quality policy. 1.0.0 is the CAP-080A foundation
#: policy — governed thresholds and release rules as data only; no rule is evaluated
#: and no consumer reads them yet. Tuning advances this version under the golden
#: re-baseline procedure, never a code change (ADR-0017 Recommendation 2).
QUALITY_POLICY_VERSION = QualityPolicyVersion(1, 0, 0)
