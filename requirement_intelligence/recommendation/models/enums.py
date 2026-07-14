"""Controlled vocabularies for the Recommendation Framework.

String-valued (:class:`~enum.StrEnum`) members serialise cleanly to JSON and compare
equal to their plain-string value, matching the convention of
:mod:`requirement_intelligence.enhancement.models.enums` and
:mod:`requirement_intelligence.quality_governance.models.enums`. These enums carry
**no runtime logic**; they are the governed vocabulary the models are classified
against. No recommendation is generated here — that is a future engine's job
(ADR-0019, CAP-082B).
"""

from __future__ import annotations

from enum import StrEnum


class RecommendationSource(StrEnum):
    """Which upstream runtime contract a recommendation's evidence was drawn from.

    The five completed results a future :class:`~requirement_intelligence.recommendation.
    recommendation_service.RecommendationService` consumes (ADR-0019 §D2). The
    Recommendation Framework never re-runs any of these subsystems; it only names, by
    reference, which one grounded a given recommendation (Recommendation 1).
    """

    ENHANCEMENT = "enhancement"
    GROUNDING = "grounding"
    VALIDATION = "validation"
    CP1 = "cp1"
    QUALITY_GOVERNANCE = "quality_governance"


class RecommendationType(StrEnum):
    """The governed vocabulary of what action a :class:`Recommendation` suggests.

    A single canonical recommendation model carries all nine types: future
    capabilities add a recommendation *type* to this enum, never a competing
    recommendation model (mirrors ``RelationshipType``, ADR-0018 Recommendation 2).
    No type implies a computation; a future recommendation engine assigns one.

    ``ADD_REQUIREMENT``
        A gap suggests a new requirement should be authored.
    ``CLARIFY_REQUIREMENT``
        An existing requirement's wording should be clarified.
    ``RESOLVE_DUPLICATE``
        Two requirements should be reconciled or merged.
    ``RESOLVE_DEPENDENCY``
        A missing or unresolved dependency should be addressed.
    ``RESOLVE_CONFLICT``
        Two requirements that conflict should be reconciled.
    ``STRENGTHEN_EVIDENCE``
        A requirement's supporting evidence should be strengthened.
    ``ADDRESS_VALIDATION_ISSUE``
        A structural validation issue should be corrected.
    ``ADDRESS_ENGINEERING_GAP``
        An engineering-readiness gap (CP1) should be closed.
    ``IMPROVE_QUALITY_SCORE``
        An action that would improve the release quality verdict.
    """

    ADD_REQUIREMENT = "add_requirement"
    CLARIFY_REQUIREMENT = "clarify_requirement"
    RESOLVE_DUPLICATE = "resolve_duplicate"
    RESOLVE_DEPENDENCY = "resolve_dependency"
    RESOLVE_CONFLICT = "resolve_conflict"
    STRENGTHEN_EVIDENCE = "strengthen_evidence"
    ADDRESS_VALIDATION_ISSUE = "address_validation_issue"
    ADDRESS_ENGINEERING_GAP = "address_engineering_gap"
    IMPROVE_QUALITY_SCORE = "improve_quality_score"


class RecommendationPriority(StrEnum):
    """The governed urgency of a :class:`Recommendation`. Recorded, never computed."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RecommendationEffort(StrEnum):
    """The governed estimated effort of acting on a :class:`Recommendation`.

    Recorded, never computed — a future engine assigns this; no capability in this
    milestone estimates effort.
    """

    TRIVIAL = "trivial"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
