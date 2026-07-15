"""Controlled vocabularies for the Continuous Improvement Framework.

String-valued (:class:`~enum.StrEnum`) members serialise cleanly to JSON and
compare equal to their plain-string value, matching the convention of every prior
subsystem's ``models.enums`` module. These enums carry **no runtime logic**; they
are the governed vocabulary the models are classified against. No finding, trend,
or opportunity is derived here — that is a future engine's job (CAP-083B).
"""

from __future__ import annotations

from enum import StrEnum


class ImprovementSourceLayer(StrEnum):
    """Which Layer 1 subsystem an observed recurrence concerns.

    Names the *subject* of a finding/trend/opportunity by reference only — the
    Continuous Improvement Framework never re-runs, re-implements, or imports any
    of these subsystems (ADR-0021 §Stage 8: Historical Truth only, never Runtime
    Truth or a Layer 1 implementation directly).
    """

    ENHANCEMENT = "enhancement"
    GROUNDING = "grounding"
    VALIDATION = "validation"
    CP1 = "cp1"
    QUALITY_GOVERNANCE = "quality_governance"
    RECOMMENDATION = "recommendation"


class ImprovementSeverity(StrEnum):
    """The severity of an :class:`ImprovementFinding`. Recorded, never computed."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class ImprovementFindingCategory(StrEnum):
    """The governed vocabulary of what an :class:`ImprovementFinding` recurs as.

    Each member names one deterministically distinguishable recurring pattern
    across many executions — never a pattern observed within a single execution
    (that is the corresponding Layer 1 subsystem's own finding/issue vocabulary).
    """

    RECURRING_VALIDATION_FAILURE = "recurring_validation_failure"
    RECURRING_GROUNDING_CONTRADICTION = "recurring_grounding_contradiction"
    RECURRING_GOVERNANCE_FAILURE = "recurring_governance_failure"
    RECURRING_RECOMMENDATION = "recurring_recommendation"
    #: Added additively in CAP-083B alongside the governed rule catalogue's fifth
    #: recurrence rule (Requirement Enhancement) — a StrEnum member addition never
    #: breaks an existing consumer, mirroring the additive-versioning discipline
    #: used throughout this platform (e.g. ``CP1Result`` 1.0 → 1.1).
    RECURRING_ENHANCEMENT_ISSUE = "recurring_enhancement_issue"


class ImprovementTrendDirection(StrEnum):
    """The observed direction of an :class:`ImprovementTrend`. Observation only.

    No member implies a prediction — Continuous Improvement observes what already
    happened across the historical dataset; estimating what will happen next is
    Layer 4's job (Prediction & Insights, ADR-0020).
    """

    IMPROVING = "improving"
    DEGRADING = "degrading"
    STABLE = "stable"
    VOLATILE = "volatile"


class ImprovementOpportunityCategory(StrEnum):
    """The governed vocabulary of what an :class:`ImprovementOpportunity` names.

    Describes *what should receive attention* — never *the optimal plan* (that is
    Layer 5's job, Optimization, ADR-0020 Recommendation 3 of this milestone).
    """

    RECURRING_DOCUMENTATION_GAP = "recurring_documentation_gap"
    RECURRING_ARCHITECTURE_WEAKNESS = "recurring_architecture_weakness"
    RECURRING_QUALITY_ISSUE = "recurring_quality_issue"
    RECURRING_RECOMMENDATION_CATEGORY = "recurring_recommendation_category"
