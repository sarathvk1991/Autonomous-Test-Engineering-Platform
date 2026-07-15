"""The canonical governed :class:`ImprovementPolicy`.

An ``ImprovementPolicy`` defines **what Continuous Improvement finding detection,
trend detection, and opportunity generation are allowed to do** — deterministic
configuration and enabled capability switches a future engine must obey. It is the
Continuous Improvement Framework counterpart to the Recommendation Framework's
``RecommendationPolicy``: an immutable, declarative, governed rule set that
contains **no executable logic**. A future engine reads a policy and acts within
it; the policy computes nothing.

Policy vs engine (frozen, ADR-0022)
------------------------------------
* ``ImprovementPolicy`` — the governed rules and switches (this file). Data only.
* A future deterministic / statistical / ML / LLM / hybrid Continuous Improvement
  engine (CAP-083B onward) — the behaviour that acts within them against a
  completed Historical Dataset.

Tuning improvement behaviour is therefore a *versioned policy change*, never an
engine code change, and it must never force a change to
``ContinuousImprovementResult`` or the service contract (mirrors ADR-0019
Recommendation 5: independent capability evolution).
"""

from __future__ import annotations

from pydantic import ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

from requirement_intelligence.continuous_improvement.identity import (
    ImprovementPolicyId,
    ImprovementPolicyVersion,
)
from shared.contracts.base import Schema


class ImprovementCapabilitySwitches(Schema):
    """Governed on/off switches for each Continuous Improvement capability. Data only.

    Each future capability (trend detection, recurring-finding detection,
    opportunity generation, and the future deterministic/ML/LLM engine families)
    is independently enabled/disabled here — a governed data change, never an
    engine change (mirrors ADR-0019 Recommendation 5).
    """

    model_config = ConfigDict(alias_generator=to_camel)

    enable_trend_detection: bool = Field(
        default=True, description="Whether trend detection may run."
    )
    enable_recurring_finding_detection: bool = Field(
        default=True, description="Whether recurring-finding detection may run."
    )
    enable_opportunity_generation: bool = Field(
        default=True, description="Whether opportunity generation may run."
    )
    enable_deterministic_engine: bool = Field(
        default=False,
        description="Whether the deterministic Continuous Improvement engine is enabled.",
    )
    enable_ml_engine: bool = Field(
        default=False,
        description="Whether a future ML Continuous Improvement engine is enabled (reserved).",
    )
    enable_llm_engine: bool = Field(
        default=False,
        description="Whether a future LLM Continuous Improvement engine is enabled (reserved).",
    )


class ImprovementThresholds(Schema):
    """Governed deterministic thresholds bounding a future engine. Data only.

    A rule never carries a literal bound; a future engine reads these thresholds
    the same way a Quality Governance rule names a policy field rather than a
    literal (ADR-0017 §D25).
    """

    model_config = ConfigDict(alias_generator=to_camel)

    minimum_occurrences: int = Field(
        ..., ge=1, description="Minimum recurrences before a finding may be recorded."
    )
    history_window: int = Field(
        ...,
        ge=1,
        description="Maximum number of executions a historical dataset reference may span.",
    )

    @model_validator(mode="after")
    def _validate_thresholds(self) -> ImprovementThresholds:
        """minimum_occurrences must not exceed the history window it is bounded within."""
        if self.minimum_occurrences > self.history_window:
            raise ValueError("minimum_occurrences must not exceed history_window.")
        return self


class ImprovementPolicy(Schema):
    """An immutable, declarative, governed rule set for Continuous Improvement."""

    model_config = ConfigDict(alias_generator=to_camel)

    policy_id: ImprovementPolicyId = Field(..., description="Governed policy identity.")
    policy_version: ImprovementPolicyVersion = Field(..., description="Semantic policy version.")
    description: str = Field(..., min_length=1, description="Human-readable policy summary.")

    capability_switches: ImprovementCapabilitySwitches = Field(
        ..., description="Which Continuous Improvement capabilities are enabled."
    )
    thresholds: ImprovementThresholds = Field(
        ..., description="Governed deterministic thresholds a future engine must respect."
    )
