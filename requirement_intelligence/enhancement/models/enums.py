"""Controlled vocabularies for the Requirement Intelligence Enhancement Framework.

String-valued (:class:`~enum.StrEnum`) members serialise cleanly to JSON and compare
equal to their plain-string value, matching the convention of
:mod:`requirement_intelligence.quality_governance.models.enums`. These enums carry
**no runtime logic**; they are the governed vocabulary the models are classified
against. No relationship, observation, or finding is derived here — that is a future
engine's job (ADR-0018).
"""

from __future__ import annotations

from enum import StrEnum


class RelationshipType(StrEnum):
    """The governed vocabulary of requirement-to-requirement relationships.

    A single canonical relationship model carries all nine types (Recommendation 2):
    future capabilities add a relationship *type* to this enum, never a competing
    relationship model. No type implies a computation; a future relationship-detection
    engine assigns one.

    ``DEPENDS_ON``
        The source requirement cannot be satisfied unless the target is.
    ``REFINES``
        The source requirement narrows or elaborates the target.
    ``CONFLICTS_WITH``
        The source and target requirements cannot both hold as stated.
    ``DUPLICATES``
        The source and target requirements express the same intent.
    ``DERIVED_FROM``
        The source requirement was generated from the target.
    ``SUPPORTS``
        The source requirement provides evidence or rationale for the target.
    ``IMPLEMENTS``
        The source requirement is a concrete realisation of the target.
    ``VALIDATES``
        The source requirement verifies that the target is satisfied.
    ``MITIGATES``
        The source requirement reduces a risk the target identifies.
    """

    DEPENDS_ON = "depends_on"
    REFINES = "refines"
    CONFLICTS_WITH = "conflicts_with"
    DUPLICATES = "duplicates"
    DERIVED_FROM = "derived_from"
    SUPPORTS = "supports"
    IMPLEMENTS = "implements"
    VALIDATES = "validates"
    MITIGATES = "mitigates"


class ObservationCategory(StrEnum):
    """The governed vocabulary of what a :class:`RequirementObservation` notices.

    Observations are produced **before** any recommendation (Recommendation 3); this
    vocabulary is the fixed set of things a future observation engine may notice about
    one requirement or the requirement set as a whole. No category implies a
    calculation.
    """

    COMPLETENESS = "completeness"
    CONSISTENCY = "consistency"
    DUPLICATION = "duplication"
    TRACEABILITY = "traceability"
    DEPENDENCY = "dependency"
    ADVISORY = "advisory"


class EnhancementSeverity(StrEnum):
    """The severity of a :class:`RequirementObservation` or :class:`EnhancementFinding`.

    ``INFO`` records an observation that surfaces nothing actionable. ``WARNING`` and
    ``CRITICAL`` grade how strongly a future consumer (e.g. Quality Governance) should
    weigh the observation. Requirement Enhancement never gates or decides on these
    severities itself (Recommendation 3) — it only records them for a downstream
    consumer to interpret.
    """

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class EnhancementInputSource(StrEnum):
    """The upstream input one enhancement run consumes.

    The two inputs the frozen ``RequirementEnhancementService.enhance`` signature
    takes (ADR-0018 §D). Requirement Enhancement is a **consumer only** of these; it
    never re-runs Engineering Context Orchestration or Analysis.
    """

    ENGINEERING_CONTEXT = "engineering_context"
    ANALYSIS_RESULT = "analysis_result"
