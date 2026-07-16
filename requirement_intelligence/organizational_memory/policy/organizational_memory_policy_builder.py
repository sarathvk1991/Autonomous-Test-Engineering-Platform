"""Builder for the governed :class:`OrganizationalMemoryPolicy`.

Construction only. It assembles the framework's default governed policy — a
deterministic, immutable value — and rejects nothing beyond the model's own
field constraints. It captures no experience, promotes no lesson, promotes no
best practice, retires nothing, and has no runtime consumers.

CAP-085A ships the governed default at ``OrganizationalMemoryPolicyVersion``
1.0.0 with ``enable_deterministic_engine`` reserved off — no engine exists
yet. The values are **governed data**: tuning them is a versioned policy
change, never an engine code change, and no future engine hard-codes any of
them (mirrors ADR-0022 Recommendation 5, ADR-0023 Recommendation 5).
"""

from __future__ import annotations

from requirement_intelligence.organizational_memory.identity import OrganizationalMemoryPolicyId
from requirement_intelligence.organizational_memory.policy.organizational_memory_policy import (
    OrganizationalMemoryCapabilitySwitches,
    OrganizationalMemoryPolicy,
    OrganizationalMemoryThresholds,
)
from requirement_intelligence.organizational_memory.version import (
    ORGANIZATIONAL_MEMORY_POLICY_VERSION,
)

#: The identity of the framework's default governed organizational memory policy.
DEFAULT_ORGANIZATIONAL_MEMORY_POLICY_ID = OrganizationalMemoryPolicyId(
    "default-organizational-memory-policy"
)


class OrganizationalMemoryPolicyBuilder:
    """Assemble the governed default :class:`OrganizationalMemoryPolicy`."""

    def build(self) -> OrganizationalMemoryPolicy:
        """Return the framework's default governed organizational memory policy."""
        return OrganizationalMemoryPolicy(
            policy_id=DEFAULT_ORGANIZATIONAL_MEMORY_POLICY_ID,
            policy_version=ORGANIZATIONAL_MEMORY_POLICY_VERSION,
            description=(
                "Default organizational memory policy (CAP-085A): governed capability "
                "switches and deterministic thresholds. The deterministic engine is "
                "reserved off; the framework remains unwired into any runtime pipeline."
            ),
            capability_switches=OrganizationalMemoryCapabilitySwitches(
                enable_experience_capture=True,
                enable_lesson_promotion=True,
                enable_best_practice_promotion=True,
                enable_retirement=True,
                enable_deterministic_engine=False,
                enable_ml_engine=False,
                enable_llm_engine=False,
                enable_graph_rag_engine=False,
                enable_neuro_symbolic_engine=False,
            ),
            thresholds=OrganizationalMemoryThresholds(
                minimum_experiences_for_lesson=3,
                minimum_lessons_for_best_practice=2,
                minimum_confidence_for_best_practice=3,
            ),
        )


def default_organizational_memory_policy() -> OrganizationalMemoryPolicy:
    """Return the framework's default governed organizational memory policy."""
    return OrganizationalMemoryPolicyBuilder().build()
