"""Builder for the governed :class:`QualityPolicy`.

Construction only. It assembles the framework's default governed policy — a
deterministic, immutable value — and rejects nothing beyond the model's own field
constraints. It performs no governance, evaluates no rule, and has no runtime
consumers.

CAP-080A ships the governed default at ``QualityPolicyVersion`` 1.0.0. The values
are **governed data**: tuning them is a versioned policy change under the golden
re-baseline procedure, never an engine code change, and the future decision engine
hard-codes none of them (ADR-0017 Recommendation 2).
"""

from __future__ import annotations

from requirement_intelligence.quality_governance.identity.quality_identity import QualityPolicyId
from requirement_intelligence.quality_governance.policy.quality_policy import (
    QualityPolicy,
    QualityReleaseRules,
    QualitySeverityThresholds,
    QualityThresholds,
)
from requirement_intelligence.quality_governance.version import QUALITY_POLICY_VERSION

#: The identity of the framework's default governed quality policy.
DEFAULT_QUALITY_POLICY_ID = QualityPolicyId("default-quality-policy")


class QualityPolicyBuilder:
    """Assemble the governed default :class:`QualityPolicy`."""

    def build(self) -> QualityPolicy:
        """Return the framework's default governed quality policy."""
        return QualityPolicy(
            policy_id=DEFAULT_QUALITY_POLICY_ID,
            policy_version=QUALITY_POLICY_VERSION,
            description="Default quality policy (CAP-080A): governed thresholds and release rules.",
            failure_thresholds=QualityThresholds(
                minimum_grounding_score=60,
                maximum_hallucination_rate=0.10,
                minimum_confidence=50,
                minimum_evidence_coverage=0.50,
            ),
            warning_thresholds=QualityThresholds(
                minimum_grounding_score=80,
                maximum_hallucination_rate=0.02,
                minimum_confidence=70,
                minimum_evidence_coverage=0.70,
            ),
            validation_severity_thresholds=QualitySeverityThresholds(
                max_critical=0,
                max_high=0,
                max_medium=5,
                max_low=20,
            ),
            cp1_severity_thresholds=QualitySeverityThresholds(
                max_critical=0,
                max_high=0,
                max_medium=3,
                max_low=10,
            ),
            required_engineering_readiness=True,
            release_rules=QualityReleaseRules(
                block_on_hallucination=True,
                block_on_validation_failure=True,
                block_on_cp1_failure=True,
                require_engineering_readiness=True,
            ),
        )


def default_quality_policy() -> QualityPolicy:
    """Return the framework's default governed quality policy."""
    return QualityPolicyBuilder().build()
