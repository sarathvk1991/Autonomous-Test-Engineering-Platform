"""Controlled vocabularies for the Learning Framework.

String-valued (:class:`~enum.StrEnum`) members serialise cleanly to JSON and
compare equal to their plain-string value, matching the convention of every
prior subsystem's ``models.enums`` module. These enums carry **no runtime
logic**; they are the governed vocabulary the models are classified against.
No candidate is proposed, no validation is recorded, no confidence is
determined, and no lifecycle transition happens here — that is a future
engine's job (CAP-086B, reserved).
"""

from __future__ import annotations

from enum import StrEnum


class LearningMaturity(StrEnum):
    """The governed maturity vocabulary (ADR-0028 §Stage 8).

    Maturity measures organizational adoption, never evidence (that is
    :class:`LearningConfidenceLevel`'s own, independent axis). Learning
    evolves upward through this ladder only; it never reverts (ADR-0028
    §Stage 8, Recommendation 6 of ADR-0028).
    """

    CANDIDATE = "candidate"
    OBSERVED = "observed"
    VALIDATED = "validated"
    TRUSTED = "trusted"
    INSTITUTIONAL = "institutional"
    STANDARD = "standard"
    RETIRED = "retired"


class LearningConfidenceLevel(StrEnum):
    """The governed confidence vocabulary (ADR-0028 §Stage 9).

    Confidence is metadata, never truth: it describes how strongly the
    referenced evidence supports a claim, and is tracked independently of
    the claim's own maturity (ADR-0028 §Stage 9, Recommendation 5 of
    ADR-0026, restated for Learning). Duplicated rather than imported from
    ``OrganizationalMemoryConfidence`` on purpose (identity module
    docstring; ADR-0027 identity module docstring precedent) — the Learning
    Framework stays self-contained.
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERIFIED = "verified"


class LearningValidationGate(StrEnum):
    """The governed vocabulary of Learning Validation gates (ADR-0028 §Stage 6).

    Learning requires sufficient Organizational Knowledge, validated
    evidence, repeatability, organizational confidence, organizational
    usefulness, and complete explainability before a Learning Candidate may
    become Learning. Each member names exactly one of those six gates. A
    :class:`~requirement_intelligence.learning.models.learning_validation.
    LearningValidation` record names which gates a validation event covered
    — this vocabulary carries no judgement of its own about *whether* a gate
    was actually cleared; that determination is a future engine's job.
    """

    SUFFICIENT_ORGANIZATIONAL_KNOWLEDGE = "sufficient_organizational_knowledge"
    VALIDATED_EVIDENCE = "validated_evidence"
    REPEATABILITY = "repeatability"
    ORGANIZATIONAL_CONFIDENCE = "organizational_confidence"
    ORGANIZATIONAL_USEFULNESS = "organizational_usefulness"
    COMPLETE_EXPLAINABILITY = "complete_explainability"
