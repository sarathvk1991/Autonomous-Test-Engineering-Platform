"""Controlled vocabularies for the Grounding Framework.

String-valued (:class:`~enum.StrEnum`) members serialise cleanly to JSON and
compare equal to their plain-string value, matching the convention of
:mod:`requirement_intelligence.models.enums`. These enums carry **no runtime
logic**; they are the governed vocabulary the models are classified against.
"""

from __future__ import annotations

from enum import StrEnum


class SupportClassification(StrEnum):
    """How strongly the supplied evidence supports a generated requirement.

    ``UNKNOWN`` is deliberately distinct from ``UNSUPPORTED``: a requirement that
    cannot be assessed (e.g. a domain that received no evidence) is *unassessable*,
    not *hallucinated*. Only ``UNSUPPORTED`` and ``CONTRADICTED`` are hallucination
    classes.
    """

    SUPPORTED = "supported"
    PARTIALLY_SUPPORTED = "partially_supported"
    WEAKLY_SUPPORTED = "weakly_supported"
    UNSUPPORTED = "unsupported"
    CONTRADICTED = "contradicted"
    UNKNOWN = "unknown"


class EvidenceRelation(StrEnum):
    """The nature of one requirement-to-evidence link."""

    DIRECT = "direct"
    CORROBORATING = "corroborating"
    PARTIAL = "partial"
    DERIVED = "derived"
    CONTRADICTING = "contradicting"
    NEGATIVE = "negative"
    MISSING = "missing"


class ConfidenceBand(StrEnum):
    """The coarse band a numeric grounding confidence falls into."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class GroundingSeverity(StrEnum):
    """The severity of a grounding finding."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


#: The two classifications that constitute a hallucination and therefore always
#: raise a :class:`~requirement_intelligence.grounding.models.findings.GroundingFinding`.
HALLUCINATION_CLASSIFICATIONS: frozenset[SupportClassification] = frozenset(
    {SupportClassification.UNSUPPORTED, SupportClassification.CONTRADICTED}
)

#: Relations that assert support for a requirement (as opposed to absence or conflict).
SUPPORTING_RELATIONS: frozenset[EvidenceRelation] = frozenset(
    {
        EvidenceRelation.DIRECT,
        EvidenceRelation.CORROBORATING,
        EvidenceRelation.PARTIAL,
        EvidenceRelation.DERIVED,
    }
)

#: Relations that assert conflict with a requirement.
CONFLICTING_RELATIONS: frozenset[EvidenceRelation] = frozenset(
    {EvidenceRelation.CONTRADICTING, EvidenceRelation.NEGATIVE}
)
