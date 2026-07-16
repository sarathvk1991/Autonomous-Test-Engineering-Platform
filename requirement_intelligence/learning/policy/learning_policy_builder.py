"""Builder for the governed :class:`LearningPolicy`.

Construction only. It assembles the framework's default governed policy — a
deterministic, immutable value — and rejects nothing beyond the model's own
field constraints. It proposes no candidate, validates no learning, records
no confidence, retires nothing, and has no runtime consumers.

CAP-086A ships the governed default at ``LearningPolicyVersion`` 1.0.0 with
``enable_deterministic_engine`` reserved off — no engine exists yet. The
values are **governed data**: tuning them is a versioned policy change,
never an engine code change, and no future engine hard-codes any of them
(mirrors ADR-0022 Recommendation 5, ADR-0023 Recommendation 5, ADR-0027 D6).
"""

from __future__ import annotations

from requirement_intelligence.learning.identity import LearningPolicyId
from requirement_intelligence.learning.policy.learning_policy import (
    LearningCapabilitySwitches,
    LearningPolicy,
    LearningThresholds,
)
from requirement_intelligence.learning.version import LEARNING_POLICY_VERSION

#: The identity of the framework's default governed learning policy.
DEFAULT_LEARNING_POLICY_ID = LearningPolicyId("default-learning-policy")


class LearningPolicyBuilder:
    """Assemble the governed default :class:`LearningPolicy`."""

    def build(self) -> LearningPolicy:
        """Return the framework's default governed learning policy."""
        return LearningPolicy(
            policy_id=DEFAULT_LEARNING_POLICY_ID,
            policy_version=LEARNING_POLICY_VERSION,
            description=(
                "Default learning policy (CAP-086A): governed capability switches and "
                "deterministic thresholds. The deterministic engine is reserved off; the "
                "framework remains unwired into any runtime pipeline."
            ),
            capability_switches=LearningCapabilitySwitches(
                enable_candidate_proposal=True,
                enable_validation=True,
                enable_confidence_recording=True,
                enable_lifecycle_recording=True,
                enable_deterministic_engine=False,
                enable_ml_engine=False,
                enable_llm_engine=False,
                enable_reinforcement_learning_engine=False,
                enable_neuro_symbolic_engine=False,
            ),
            thresholds=LearningThresholds(
                # ADR-0028 §Stage 6: "a single Best Practice, in isolation, is not
                # enough" — the default floor reflects that constitutional
                # sufficiency requirement, mirroring the conservative-floor
                # discipline ADR-0027's own default policy already applies.
                minimum_best_practices_for_candidate=2,
                minimum_validation_gates_for_learning=6,
                minimum_confidence_for_learning=3,
            ),
        )


def default_learning_policy() -> LearningPolicy:
    """Return the framework's default governed learning policy."""
    return LearningPolicyBuilder().build()
