"""The canonical governed :class:`QualityPolicy`.

A ``QualityPolicy`` defines **what constitutes acceptable quality** — the numeric
bars, severity budgets, and mandatory release rules a future decision engine must
obey. It is the Quality Governance counterpart to the Grounding ``MatchingPolicy``
and the orchestration ``OrchestrationPolicy``: an immutable, declarative, governed
rule set that contains **no executable logic**. The engine reads a policy and
evaluates it; the policy computes nothing.

Policy vs engine (frozen, ADR-0017)
-----------------------------------
* ``QualityPolicy`` — the governed thresholds and rules (this file). Data only.
* The future decision engine — the behaviour that evaluates them against completed
  ``GroundingResult`` / ``ValidationResult`` / ``CP1Result`` inputs.

Tuning governance behaviour is therefore a *versioned policy change* under the
golden re-baseline procedure, never an engine code change, and it must never force a
change to ``QualityGovernanceResult``, ``QualityAssessment``, or the service contract
(ADR-0017 Recommendation 2).

Two bands, plus mandatory rules (frozen, ADR-0017 Recommendation 7)
-------------------------------------------------------------------
The decision is **not** a threshold over a single score. ``failure_thresholds`` and
``warning_thresholds`` express the numeric bars for ``FAIL`` and
``PASS_WITH_WARNINGS`` respectively, while ``release_rules`` express mandatory gates
that can ``FAIL`` a run irrespective of its score. This is what lets a high-scoring
run ``FAIL`` (a mandatory rule violated) and a lower-scoring run ``PASS`` (all
mandatory rules satisfied).
"""

from __future__ import annotations

from pydantic import ConfigDict, Field
from pydantic.alias_generators import to_camel

from requirement_intelligence.quality_governance.identity.quality_identity import (
    QualityPolicyId,
    QualityPolicyVersion,
)
from shared.contracts.base import Schema


class QualityThresholds(Schema):
    """The governed numeric bars for one decision band. Data only.

    Each field is a minimum a run must clear (or, for the rate, a maximum it must not
    exceed) for the band. Nothing here is compared to anything — the future engine
    reads these bars and evaluates them.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    minimum_grounding_score: int = Field(
        ..., ge=0, le=100, description="Minimum acceptable grounding score (0-100)."
    )
    maximum_hallucination_rate: float = Field(
        ..., ge=0.0, le=1.0, description="Maximum acceptable hallucination rate (0-1)."
    )
    minimum_confidence: int = Field(
        ..., ge=0, le=100, description="Minimum acceptable average grounding confidence (0-100)."
    )
    minimum_evidence_coverage: float = Field(
        ..., ge=0.0, le=1.0, description="Minimum acceptable evidence coverage (0-1)."
    )


class QualitySeverityThresholds(Schema):
    """Governed maximum tolerated finding counts by severity, for one upstream result.

    Applied independently to Validation and to CP1 (each governs its own severity
    budget). Data only — the engine compares an upstream result's finding counts to
    these caps; the policy performs no comparison.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    max_critical: int = Field(
        ..., ge=0, description="Maximum tolerated critical-severity findings."
    )
    max_high: int = Field(..., ge=0, description="Maximum tolerated high-severity findings.")
    max_medium: int = Field(..., ge=0, description="Maximum tolerated medium-severity findings.")
    max_low: int = Field(..., ge=0, description="Maximum tolerated low-severity findings.")


class QualityReleaseRules(Schema):
    """The governed mandatory release gates. Data only.

    Each boolean, when set, is a gate a future decision engine must honour — a
    violation forces ``FAIL`` regardless of the numeric score (ADR-0017
    Recommendation 7). The policy evaluates nothing; it declares which gates apply.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    block_on_hallucination: bool = Field(
        default=True, description="FAIL if the hallucination rate exceeds the failure threshold."
    )
    block_on_validation_failure: bool = Field(
        default=True, description="FAIL if Validation reported a failing verdict."
    )
    block_on_cp1_failure: bool = Field(
        default=True, description="FAIL if CP1 reported a failing (not-ready) verdict."
    )
    require_engineering_readiness: bool = Field(
        default=True, description="FAIL if engineering readiness is not met."
    )


class QualityPolicy(Schema):
    """An immutable, declarative, governed rule set for acceptable release quality."""

    model_config = ConfigDict(alias_generator=to_camel)

    policy_id: QualityPolicyId = Field(..., description="Governed policy identity.")
    policy_version: QualityPolicyVersion = Field(..., description="Semantic policy version.")
    description: str = Field(..., min_length=1, description="Human-readable policy summary.")

    failure_thresholds: QualityThresholds = Field(
        ..., description="Bars below which a run FAILs on quality grounds."
    )
    warning_thresholds: QualityThresholds = Field(
        ..., description="Bars below which a run PASSes only with warnings."
    )
    validation_severity_thresholds: QualitySeverityThresholds = Field(
        ..., description="Tolerated Validation finding counts by severity."
    )
    cp1_severity_thresholds: QualitySeverityThresholds = Field(
        ..., description="Tolerated CP1 finding counts by severity."
    )
    required_engineering_readiness: bool = Field(
        default=True, description="Whether engineering readiness is mandatory for release."
    )
    release_rules: QualityReleaseRules = Field(
        ..., description="Mandatory release gates independent of the numeric score."
    )
