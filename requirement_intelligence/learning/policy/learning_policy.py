"""The canonical governed :class:`LearningPolicy`.

A ``LearningPolicy`` defines **what candidate proposal, validation,
confidence recording, and lifecycle governance are allowed to do** —
deterministic configuration and enabled capability switches a future engine
must obey. It is the Learning Framework counterpart to the Organizational
Memory Framework's ``OrganizationalMemoryPolicy``: an immutable, declarative,
governed rule set that contains **no executable logic**. A future engine
reads a policy and acts within it; the policy computes nothing.

Policy vs engine (frozen, ADR-0029)
------------------------------------
* ``LearningPolicy`` — the governed rules and switches (this file). Data
  only.
* A future deterministic / ML / LLM / GraphRAG / reinforcement learning /
  neuro-symbolic Learning engine (CAP-086B onward, reserved) — the
  behaviour that acts within them against one consumed
  ``OrganizationalMemoryResult``.

Tuning validation/promotion behaviour is therefore a *versioned policy
change*, never an engine code change, and it must never force a change to
``LearningResult`` or the service contract (mirrors ADR-0022 Recommendation
5, ADR-0023 Recommendation 5, ADR-0027 D6, itself mirroring ADR-0019
Recommendation 5).
"""

from __future__ import annotations

from pydantic import ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

from requirement_intelligence.learning.identity import LearningPolicyId, LearningPolicyVersion
from shared.contracts.base import Schema


class LearningCapabilitySwitches(Schema):
    """Governed on/off switches for each Learning capability. Data only.

    Each future capability (candidate proposal, validation, confidence
    recording, lifecycle recording, and the future deterministic/ML/LLM/
    reinforcement-learning/neuro-symbolic engine families) is independently
    enabled/disabled here — a governed data change, never an engine change
    (mirrors ADR-0022 Recommendation 5, ADR-0023 Recommendation 5, ADR-0027
    D6).
    """

    model_config = ConfigDict(alias_generator=to_camel)

    enable_candidate_proposal: bool = Field(
        default=True, description="Whether learning candidate proposal may run."
    )
    enable_validation: bool = Field(
        default=True, description="Whether Candidate → Learning validation may run."
    )
    enable_confidence_recording: bool = Field(
        default=True, description="Whether confidence recording may run."
    )
    enable_lifecycle_recording: bool = Field(
        default=True, description="Whether maturity lifecycle recording may run."
    )
    enable_deterministic_engine: bool = Field(
        default=False,
        description="Whether the deterministic Learning engine is enabled (reserved).",
    )
    enable_ml_engine: bool = Field(
        default=False, description="Whether a future ML Learning engine is enabled (reserved)."
    )
    enable_llm_engine: bool = Field(
        default=False, description="Whether a future LLM Learning engine is enabled (reserved)."
    )
    enable_reinforcement_learning_engine: bool = Field(
        default=False,
        description=(
            "Whether a future reinforcement learning Learning engine is enabled (reserved)."
        ),
    )
    enable_neuro_symbolic_engine: bool = Field(
        default=False,
        description="Whether a future neuro-symbolic Learning engine is enabled (reserved).",
    )


class LearningThresholds(Schema):
    """Governed deterministic thresholds bounding a future engine. Data only.

    A rule never carries a literal bound; a future engine reads these
    thresholds the same way an Organizational Memory rule names a policy
    field rather than a literal (ADR-0027, mirroring ADR-0017 §D25).
    """

    model_config = ConfigDict(alias_generator=to_camel)

    minimum_best_practices_for_candidate: int = Field(
        ...,
        ge=1,
        description=(
            "Minimum number of Best Practices a future engine must gather before proposing "
            "a Learning Candidate."
        ),
    )
    minimum_validation_gates_for_learning: int = Field(
        ...,
        ge=1,
        le=6,
        description=(
            "Minimum number of the six governed Stage 6 gates a future engine must clear "
            "before promoting a Learning Candidate to Learning."
        ),
    )
    minimum_confidence_for_learning: int = Field(
        ...,
        ge=0,
        le=3,
        description=(
            "Minimum ordinal confidence level (0=LOW..3=VERIFIED) a candidate must reach "
            "before a future engine may promote it to Learning."
        ),
    )

    @model_validator(mode="after")
    def _validate_thresholds(self) -> LearningThresholds:
        """The validation-gate floor must not exceed the six governed gates."""
        if self.minimum_validation_gates_for_learning > 6:
            raise ValueError("minimum_validation_gates_for_learning must not exceed 6.")
        return self


class LearningPolicy(Schema):
    """An immutable, declarative, governed rule set for Learning validation."""

    model_config = ConfigDict(alias_generator=to_camel)

    policy_id: LearningPolicyId = Field(..., description="Governed policy identity.")
    policy_version: LearningPolicyVersion = Field(..., description="Semantic policy version.")
    description: str = Field(..., min_length=1, description="Human-readable policy summary.")

    capability_switches: LearningCapabilitySwitches = Field(
        ..., description="Which Learning capabilities are enabled."
    )
    thresholds: LearningThresholds = Field(
        ..., description="Governed deterministic thresholds a future engine must respect."
    )
