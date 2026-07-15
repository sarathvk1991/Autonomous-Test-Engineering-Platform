"""Builder for the governed :class:`ImprovementPolicy`.

Construction only. It assembles the framework's default governed policy — a
deterministic, immutable value — and rejects nothing beyond the model's own field
constraints. It generates no finding, observes no trend, names no opportunity, and
has no runtime consumers.

CAP-083A shipped the governed default at ``ImprovementPolicyVersion`` 1.0.0 with
``enable_deterministic_engine`` reserved off. CAP-083B advances it to 1.1.0 and
flips that switch to ``True`` now that
``DeterministicContinuousImprovementEngine`` exists. The values are **governed
data**: tuning them is a versioned policy change, never an engine code change,
and no future engine hard-codes any of them (mirrors ADR-0019 Recommendation 5).
"""

from __future__ import annotations

from requirement_intelligence.continuous_improvement.identity import (
    ImprovementPolicyId,
)
from requirement_intelligence.continuous_improvement.policy.continuous_improvement_policy import (
    ImprovementCapabilitySwitches,
    ImprovementPolicy,
    ImprovementThresholds,
)
from requirement_intelligence.continuous_improvement.version import IMPROVEMENT_POLICY_VERSION

#: The identity of the framework's default governed improvement policy.
DEFAULT_IMPROVEMENT_POLICY_ID = ImprovementPolicyId("default-improvement-policy")


class ImprovementPolicyBuilder:
    """Assemble the governed default :class:`ImprovementPolicy`."""

    def build(self) -> ImprovementPolicy:
        """Return the framework's default governed improvement policy."""
        return ImprovementPolicy(
            policy_id=DEFAULT_IMPROVEMENT_POLICY_ID,
            policy_version=IMPROVEMENT_POLICY_VERSION,
            description=(
                "Default improvement policy (CAP-083B): governed capability "
                "switches and deterministic thresholds. The deterministic engine "
                "is enabled; the framework remains unwired into any runtime pipeline."
            ),
            capability_switches=ImprovementCapabilitySwitches(
                enable_trend_detection=True,
                enable_recurring_finding_detection=True,
                enable_opportunity_generation=True,
                enable_deterministic_engine=True,
                enable_ml_engine=False,
                enable_llm_engine=False,
            ),
            thresholds=ImprovementThresholds(
                minimum_occurrences=3,
                history_window=25,
            ),
        )


def default_improvement_policy() -> ImprovementPolicy:
    """Return the framework's default governed improvement policy."""
    return ImprovementPolicyBuilder().build()
