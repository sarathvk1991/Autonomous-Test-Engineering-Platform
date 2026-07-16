"""The canonical governed :class:`OrganizationalMemoryPolicy`.

An ``OrganizationalMemoryPolicy`` defines **what lesson promotion, best-practice
promotion, retirement, and confidence governance are allowed to do** —
deterministic configuration and enabled capability switches a future engine
must obey. It is the Organizational Memory Framework counterpart to the
Continuous Improvement Framework's ``ImprovementPolicy`` and the Knowledge
Graph Framework's ``KnowledgeGraphPolicy``: an immutable, declarative, governed
rule set that contains **no executable logic**. A future engine reads a policy
and acts within it; the policy computes nothing.

Policy vs engine (frozen, ADR-0027)
------------------------------------
* ``OrganizationalMemoryPolicy`` — the governed rules and switches (this
  file). Data only.
* A future deterministic / statistical / ML / LLM / GraphRAG / neuro-symbolic
  Organizational Memory engine (CAP-085B onward, reserved) — the behaviour
  that acts within them against two consumed Layer 2 results.

Tuning promotion/retirement behaviour is therefore a *versioned policy
change*, never an engine code change, and it must never force a change to
``OrganizationalMemoryResult`` or the service contract (mirrors ADR-0022
Recommendation 5, ADR-0023 Recommendation 5, itself mirroring ADR-0019
Recommendation 5).
"""

from __future__ import annotations

from pydantic import ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

from requirement_intelligence.organizational_memory.identity import (
    OrganizationalMemoryPolicyId,
    OrganizationalMemoryPolicyVersion,
)
from shared.contracts.base import Schema


class OrganizationalMemoryCapabilitySwitches(Schema):
    """Governed on/off switches for each Organizational Memory capability. Data only.

    Each future capability (experience capture, lesson promotion, best-practice
    promotion, retirement, and the future deterministic/ML/LLM/GraphRAG/
    neuro-symbolic engine families) is independently enabled/disabled here — a
    governed data change, never an engine change (mirrors ADR-0022
    Recommendation 5, ADR-0023 Recommendation 5).
    """

    model_config = ConfigDict(alias_generator=to_camel)

    enable_experience_capture: bool = Field(
        default=True, description="Whether experience capture may run."
    )
    enable_lesson_promotion: bool = Field(
        default=True, description="Whether Experience → Lesson promotion may run."
    )
    enable_best_practice_promotion: bool = Field(
        default=True, description="Whether Lesson → BestPractice promotion may run."
    )
    enable_retirement: bool = Field(
        default=True, description="Whether lifecycle retirement recording may run."
    )
    enable_deterministic_engine: bool = Field(
        default=False,
        description="Whether the deterministic Organizational Memory engine is enabled (reserved).",
    )
    enable_ml_engine: bool = Field(
        default=False,
        description="Whether a future ML Organizational Memory engine is enabled (reserved).",
    )
    enable_llm_engine: bool = Field(
        default=False,
        description="Whether a future LLM Organizational Memory engine is enabled (reserved).",
    )
    enable_graph_rag_engine: bool = Field(
        default=False,
        description=(
            "Whether a future Graph RAG Organizational Memory engine is enabled (reserved)."
        ),
    )
    enable_neuro_symbolic_engine: bool = Field(
        default=False,
        description=(
            "Whether a future neuro-symbolic Organizational Memory engine is enabled (reserved)."
        ),
    )


class OrganizationalMemoryThresholds(Schema):
    """Governed deterministic thresholds bounding a future engine. Data only.

    A rule never carries a literal bound; a future engine reads these
    thresholds the same way a Continuous Improvement rule names a policy
    field rather than a literal (ADR-0022, mirroring ADR-0017 §D25).
    """

    model_config = ConfigDict(alias_generator=to_camel)

    minimum_experiences_for_lesson: int = Field(
        ...,
        ge=1,
        description=(
            "Minimum number of Experiences a future engine must gather before promoting a Lesson."
        ),
    )
    minimum_lessons_for_best_practice: int = Field(
        ...,
        ge=1,
        description=(
            "Minimum number of Lessons a future engine must gather before promoting a "
            "BestPractice."
        ),
    )
    minimum_confidence_for_best_practice: int = Field(
        ...,
        ge=0,
        le=3,
        description=(
            "Minimum ordinal confidence level (0=LOW..3=VERIFIED) a Lesson must reach "
            "before a future engine may promote it to a BestPractice."
        ),
    )

    @model_validator(mode="after")
    def _validate_thresholds(self) -> OrganizationalMemoryThresholds:
        """The best-practice floor must not be looser than the lesson floor it builds on."""
        if self.minimum_lessons_for_best_practice < 1:
            raise ValueError("minimum_lessons_for_best_practice must be at least 1.")
        return self


class OrganizationalMemoryPolicy(Schema):
    """An immutable, declarative, governed rule set for Organizational Memory curation."""

    model_config = ConfigDict(alias_generator=to_camel)

    policy_id: OrganizationalMemoryPolicyId = Field(..., description="Governed policy identity.")
    policy_version: OrganizationalMemoryPolicyVersion = Field(
        ..., description="Semantic policy version."
    )
    description: str = Field(..., min_length=1, description="Human-readable policy summary.")

    capability_switches: OrganizationalMemoryCapabilitySwitches = Field(
        ..., description="Which Organizational Memory capabilities are enabled."
    )
    thresholds: OrganizationalMemoryThresholds = Field(
        ..., description="Governed deterministic thresholds a future engine must respect."
    )
