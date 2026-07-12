"""Builder for the governed :class:`AssessmentPolicy`.

Construction only. It assembles the framework's default governed interpretation
policy — a deterministic, immutable value — and rejects nothing beyond the model's own
field constraints. It performs no assessment, interprets no evaluation, and has no
runtime consumers.

CAP-080A.2 ships the governed default at ``AssessmentPolicyVersion`` 1.0.0. The values
are **governed data**: tuning them is a versioned policy change under the golden
re-baseline procedure, never an engine code change (ADR-0017 Recommendation 4).
"""

from __future__ import annotations

from requirement_intelligence.quality_governance.assessment.policy import (
    ASSESSMENT_POLICY_VERSION,
    DEFAULT_ASSESSMENT_POLICY_ID,
    AssessmentConflictPolicy,
    AssessmentPolicy,
    AssessmentWeights,
)
from requirement_intelligence.quality_governance.evaluation.models import RuleCategory


class AssessmentPolicyBuilder:
    """Assemble the governed default :class:`AssessmentPolicy`."""

    def build(self) -> AssessmentPolicy:
        """Return the framework's default governed assessment policy."""
        return AssessmentPolicy(
            policy_id=DEFAULT_ASSESSMENT_POLICY_ID,
            policy_version=ASSESSMENT_POLICY_VERSION,
            description=(
                "Default assessment policy (CAP-080A.2): governed interpretation of rule "
                "evaluations into observations."
            ),
            precedence=(
                RuleCategory.MANDATORY_RELEASE,
                RuleCategory.CROSS_SUBSYSTEM,
                RuleCategory.GROUNDING,
                RuleCategory.VALIDATION,
                RuleCategory.CP1,
                RuleCategory.ADVISORY,
            ),
            conflict_resolution=AssessmentConflictPolicy.MANDATORY_WINS,
            weights=AssessmentWeights(
                mandatory_weight=8,
                failure_weight=4,
                warning_weight=2,
                advisory_weight=1,
            ),
            mandatory_failure_is_blocking=True,
            failure_severity_is_blocking=True,
            treat_advisory_as_warning=False,
            include_skipped_as_warning=False,
            emit_recommendations=True,
        )


def default_assessment_policy() -> AssessmentPolicy:
    """Return the framework's default governed assessment policy."""
    return AssessmentPolicyBuilder().build()
