"""Controlled vocabularies for the Quality Governance Framework.

String-valued (:class:`~enum.StrEnum`) members serialise cleanly to JSON and
compare equal to their plain-string value, matching the convention of
:mod:`requirement_intelligence.grounding.models.enums`. These enums carry **no
runtime logic**; they are the governed vocabulary the models are classified
against. No decision is derived here — that is the future decision engine's job.
"""

from __future__ import annotations

from enum import StrEnum


class QualityDecision(StrEnum):
    """The governed release decision for one Requirement Intelligence run.

    Semantics (frozen, CAP-080A). The decision is a **governance verdict**, not a
    numeric grade: a future decision engine derives it by evaluating governed rules,
    never by thresholding a single score (ADR-0017 Recommendation 7).

    ``PASS``
        Every governed quality rule is satisfied. The run is releasable with no
        governance reservation.
    ``PASS_WITH_WARNINGS``
        No release-blocking rule is violated, but one or more warning-level rules
        are. The run is releasable, with recorded reservations a consumer may act on.
    ``FAIL``
        At least one release-blocking (failure-level or mandatory) rule is violated.
        The run must not be released on quality grounds.
    """

    PASS = "pass"  # noqa: S105 — a decision verdict, not a secret
    PASS_WITH_WARNINGS = "pass_with_warnings"  # noqa: S105 — a decision verdict, not a secret
    FAIL = "fail"


class QualitySeverity(StrEnum):
    """The severity of a :class:`QualityFinding`.

    ``INFO`` records an observation that influences no decision. ``WARNING`` maps to
    ``PASS_WITH_WARNINGS``: a governed warning threshold was crossed. ``FAILURE``
    maps to ``FAIL``: a governed failure threshold or mandatory release rule was
    violated.
    """

    INFO = "info"
    WARNING = "warning"
    FAILURE = "failure"


class QualityFindingCategory(StrEnum):
    """The kind of governance problem a :class:`QualityFinding` records.

    These are **governance** categories only. They are not Grounding, Validation, or
    CP1 findings — each governs a policy relationship *between* an upstream result and
    the governed ``QualityPolicy`` (ADR-0017 Recommendation 1). No category implies a
    calculation; the future engine assigns one when a governed rule is violated.
    """

    GROUNDING_COVERAGE_BELOW_POLICY = "grounding_coverage_below_policy"
    HALLUCINATION_RATE_EXCEEDED = "hallucination_rate_exceeded"
    CONFIDENCE_BELOW_THRESHOLD = "confidence_below_threshold"
    EVIDENCE_COVERAGE_BELOW_POLICY = "evidence_coverage_below_policy"
    VALIDATION_POLICY_VIOLATED = "validation_policy_violated"
    CP1_POLICY_VIOLATED = "cp1_policy_violated"
    ENGINEERING_READINESS_NOT_MET = "engineering_readiness_not_met"
    MIXED_QUALITY_EVIDENCE = "mixed_quality_evidence"
    RELEASE_POLICY_VIOLATION = "release_policy_violation"


class QualityInputSource(StrEnum):
    """A completed upstream runtime result Quality Governance consumes.

    The three peer inputs of the governance dependency graph (ADR-0017
    Recommendation 5). Quality Governance is a **consumer only** of these; it never
    re-runs the subsystems that produce them.
    """

    GROUNDING = "grounding"
    VALIDATION = "validation"
    CP1 = "cp1"


#: Severities that reserve or block a release, and therefore cannot accompany a
#: clean ``PASS``. A ``WARNING`` finding implies at least ``PASS_WITH_WARNINGS``; a
#: ``FAILURE`` finding implies ``FAIL``.
DECISION_AFFECTING_SEVERITIES: frozenset[QualitySeverity] = frozenset(
    {QualitySeverity.WARNING, QualitySeverity.FAILURE}
)
