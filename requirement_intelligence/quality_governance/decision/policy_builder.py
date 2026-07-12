"""Builder for the governed :class:`DecisionPolicy`.

Construction only. It assembles the framework's default governed decision policy — a
deterministic, immutable value — and rejects nothing beyond the model's own field
constraints. It performs no decision, evaluates no rule, and has no runtime consumers.

CAP-080A.3 ships the governed default at ``DecisionPolicyVersion`` 1.0.0. The values
are **governed data**: tuning them is a versioned policy change under the golden
re-baseline procedure, never an engine code change (ADR-0017 Recommendation 4).
"""

from __future__ import annotations

from requirement_intelligence.quality_governance.assessment.models import AssessmentLevel
from requirement_intelligence.quality_governance.decision.policy import (
    DECISION_POLICY_VERSION,
    DEFAULT_DECISION_POLICY_ID,
    DecisionPolicy,
    DecisionRule,
)
from requirement_intelligence.quality_governance.models.enums import QualityDecision


class DecisionPolicyBuilder:
    """Assemble the governed default :class:`DecisionPolicy`."""

    def build(self) -> DecisionPolicy:
        """Return the framework's default governed decision policy."""
        return DecisionPolicy(
            policy_id=DEFAULT_DECISION_POLICY_ID,
            policy_version=DECISION_POLICY_VERSION,
            description=(
                "Default decision policy (CAP-080A.3): governed base mapping plus mandatory "
                "release gates."
            ),
            level_mapping=(
                DecisionRule(
                    level=AssessmentLevel.CLEAN,
                    decision=QualityDecision.PASS,
                    note="No failing rule of any severity.",
                ),
                DecisionRule(
                    level=AssessmentLevel.ADVISORY_ONLY,
                    decision=QualityDecision.PASS,
                    note="Only advisory rules failed; releasable without reservation.",
                ),
                DecisionRule(
                    level=AssessmentLevel.WARNINGS_PRESENT,
                    decision=QualityDecision.PASS_WITH_WARNINGS,
                    note="Warning-severity rules failed; releasable with reservations.",
                ),
                DecisionRule(
                    level=AssessmentLevel.FAILURES_PRESENT,
                    decision=QualityDecision.FAIL,
                    note="A blocking rule failed; not releasable on quality grounds.",
                ),
            ),
            fail_on_blocking_failure=True,
            fail_on_mandatory_failure=True,
            warn_on_advisory=False,
            emit_recommendations=True,
        )


def default_decision_policy() -> DecisionPolicy:
    """Return the framework's default governed decision policy."""
    return DecisionPolicyBuilder().build()
