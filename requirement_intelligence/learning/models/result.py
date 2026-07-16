"""The :class:`LearningResult` — the frozen runtime contract of the Learning
Framework (CAP-086A architecture freeze, ADR-0029 §D3/§D4).

CAP-086A freezes the architecture before any engine exists — exactly as
CAP-083A did for ``ContinuousImprovementResult`` before CAP-083B's
deterministic engine, CAP-084A did for ``KnowledgeGraphResult`` before
CAP-084B's, and CAP-085A did for ``OrganizationalMemoryResult`` before
CAP-085B's. A future CAP-086B milestone implements the first real engine
behind this unchanged contract, and a future CAP-086B.1 milestone would
permanently certify ``LearningResult`` as the canonical runtime contract —
exactly as CAP-085B.1 certified ``OrganizationalMemoryResult`` (ADR-0027
§D18) — neither of which is introduced by this milestone.

It **is**:

* the complete runtime output — the single object a future deterministic
  Learning engine (CAP-086B, reserved) will cross from into serialization,
  exactly as ``OrganizationalMemoryResult`` crosses from the Organizational
  Memory Framework's own deterministic engine;
* the canonical runtime contract — the only Learning aggregate, the fourth
  and final Layer 2 runtime contract (ADR-0020), and the first to consume a
  single already-completed Layer 2 tier (``OrganizationalMemoryResult`)
  rather than a Historical Dataset reference or a fan-in pair (ADR-0028
  §Stage 12, ADR-0029 §D2);
* independently versioned — ``result_version``
  (:class:`LearningResultVersion`) evolves on its own axis, never forcing
  (or forced by) the framework, policy, or learning/lifecycle/validation
  schema versions, and vice versa (ADR-0029 §D3, mirroring ADR-0027
  §D3/§D6);
* deterministic — a pure function of the consumed
  ``OrganizationalMemoryResult`` and the governed policy; no randomness, no
  wall-clock dependence beyond the injected clock;
* immutable — ``frozen=True`` (via ``Schema``), tuple-backed collections, no
  field can change after construction;
* self-contained — every candidate, learning, validation, confidence,
  lifecycle record, summary metric, and consumed result reference already
  lives here, so the result is reproducible with no need to re-run curation
  or inspect any runtime service (mirrors Recommendation 9 of ADR-0027,
  extended one tier);
* explainable — every candidate, learning, validation, confidence, and
  lifecycle record is reconstructable from this object alone; no upstream
  subsystem, engine, provider, policy, or service need ever be inspected or
  re-run (ADR-0028 §Stage 10);
* serializer-independent — a future serializer projects this object; this
  object never depends on a serializer existing;
* execution-package-independent — this object exists and is fully
  meaningful with no Execution Package, CLI phase, or manifest wired to it
  at all (CAP-086A — none of those exist yet);
* engine-independent — this object's shape does not depend on which engine
  produced it; a future deterministic, ML, LLM, GraphRAG, reinforcement
  learning, or neuro-symbolic engine emits the identical contract (ADR-0028
  §Stage 17, Recommendation 14 of ADR-0028).

It is **not**:

* Runtime Truth; Historical Truth; Derived Knowledge; Organizational
  Knowledge (``OrganizationalMemoryResult`` remains exactly what ADR-0027
  already froze it as — this object references it, it never becomes it); a
  report; Markdown; JSON formatting; an execution artifact; a manifest; a
  CLI object; a renderer; a serializer; a transport object; a projection; an
  Execution Package object; a Feature, a Prediction, an Optimization, or an
  Autonomous Decision (ADR-0028 §Stage 12-15); the Learning engine itself; a
  service; a policy; a builder; the Historical Dataset; the Organizational
  Memory Framework.

Each of those is a separate, later owner that *consumes* this object (or, for
the consumed ``OrganizationalMemoryResult``, a separate, earlier owner this
object *references* — never embeds); none of them computes anything this
object doesn't already carry.

The validators enforce cross-referential integrity only. No candidate,
learning, validation, confidence, or lifecycle record is computed here
(CAP-086A architecture freeze, ADR-0029).
"""

from __future__ import annotations

from datetime import datetime

from pydantic import ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

from requirement_intelligence.learning.identity import (
    LearningFrameworkVersion,
    LearningPolicyId,
    LearningPolicyVersion,
    LearningResultId,
    LearningResultVersion,
)
from requirement_intelligence.learning.models.learning import Learning
from requirement_intelligence.learning.models.learning_candidate import LearningCandidate
from requirement_intelligence.learning.models.learning_confidence import LearningConfidence
from requirement_intelligence.learning.models.learning_lifecycle import LearningLifecycle
from requirement_intelligence.learning.models.learning_validation import LearningValidation
from requirement_intelligence.learning.models.summary import LearningMetrics, LearningSummary
from shared.contracts.base import Schema

#: Version of the ``LearningResult`` **runtime contract** schema. Independent
#: of every other Learning version axis — ``LearningFrameworkVersion``,
#: ``LearningPolicyVersion``, ``LearningVersion``, ``LearningLifecycleVersion``,
#: ``LearningValidationVersion`` — a change here never forces any of those to
#: change, and vice versa (frozen, CAP-086A, ADR-0029 §D3, mirroring
#: ``OrganizationalMemoryResultVersion``, ADR-0027 §D3/§D6).
LEARNING_RESULT_VERSION = LearningResultVersion(1, 0, 0)


class LearningResult(Schema):
    """The complete, deterministic learned knowledge for one build.

    ``LearningResult`` is the **permanent runtime contract** — the only
    Learning object that crosses into serialization. It is **not** a report,
    an execution artifact, serialization, a renderer, or a calculator: it
    already contains everything (every candidate, learning, validation
    record, confidence record, lifecycle record, the summary, the metrics,
    the governing policy identity/version, and the consumed
    ``OrganizationalMemoryResult`` reference) any downstream projection
    needs.

    **Serialization invariant (frozen, mirrors ADR-0027 §D19).** Every
    future execution artifact concerning Learning will be a **pure
    projection** of a ``LearningResult`` — reproducible from it alone,
    computing nothing. A renderer must never call a Learning engine,
    ``PlatformContext``, propose a candidate, validate a learning, record a
    confidence, or invoke a policy.

    **Ownership (frozen, CAP-086A, ADR-0029 §D3).** This is the **sole**
    owner of every candidate, learning, validation record, confidence
    record, lifecycle record, summary metric, policy identity/version, and
    consumed ``OrganizationalMemoryResult`` reference produced by the
    Learning Framework. Nothing upstream and nothing downstream owns these —
    no execution artifact, manifest, or other subsystem may duplicate that
    ownership (Recommendation 5 of ADR-0028). The future engine that
    assembles this object is engine-internal implementation detail — it is
    not part of this contract, and it is not named by any field here.

    **Explainability (frozen, CAP-086A, ADR-0028 §Stage 10).** Every
    candidate, learning, validation, confidence, and lifecycle record is
    explainable entirely from this object's contents, traceable through the
    referenced ``OrganizationalMemoryResult`` id down to Best Practice,
    Lesson, Experience, Historical Dataset, Execution Ids, and Runtime Truth
    — no downstream consumer should ever need to re-run curation or inspect
    the engine, the service, or ``PlatformContext``.

    **Truth Hierarchy boundary (frozen, ADR-0028 §Stage 2).** This result is
    Learned Knowledge: derived exclusively from Organizational Knowledge
    (``OrganizationalMemoryResult``), never itself Organizational Knowledge,
    Derived Knowledge, Historical Truth, or Runtime Truth. It must never be
    written back into the consumed result, and no future Learning build may
    consume a prior ``LearningResult`` as an input (mirrors Recommendation
    19 of ADR-0027, Recommendation 20 of ADR-0028).

    **Runtime boundary (frozen, CAP-086A).** Runtime ends at this object:
    ``OrganizationalMemoryResult`` → (future engine, reserved) →
    ``LearningResult``. Everything after that — serialization, reports,
    Markdown, JSON, the Execution Package — is projection only and must
    compute nothing; none of it exists yet (CAP-086A introduces none of it).
    This boundary is now permanently frozen: future serializers, reports,
    and Execution Package integrations must consume ``LearningResult`` only,
    never the engine, the service, or ``PlatformContext``.

    **Golden regression boundary (frozen).** A future golden dataset
    compares this object's content, never Markdown or JSON formatting. A
    presentation change must never invalidate a runtime regression baseline;
    only a change to this object's content (or its ``result_version``) is a
    runtime regression.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    result_id: LearningResultId = Field(..., description="Deterministic result id.")
    organizational_memory_result_id: str = Field(
        ...,
        min_length=1,
        description="Id of the consumed OrganizationalMemoryResult (reference only).",
    )

    candidates: tuple[LearningCandidate, ...] = Field(
        default=(), description="Every learning candidate proposed for this build."
    )
    learnings: tuple[Learning, ...] = Field(
        default=(), description="Every learning validated for this build."
    )
    validations: tuple[LearningValidation, ...] = Field(
        default=(), description="Every validation record for this build."
    )
    confidences: tuple[LearningConfidence, ...] = Field(
        default=(), description="Every confidence record for this build."
    )
    lifecycles: tuple[LearningLifecycle, ...] = Field(
        default=(), description="Every maturity-state record for this build."
    )
    summary: LearningSummary = Field(..., description="The headline summary of this build.")
    metrics: LearningMetrics = Field(..., description="The deterministic numeric roll-up.")

    policy_id: LearningPolicyId = Field(..., description="Identity of the governing policy.")
    policy_version: LearningPolicyVersion = Field(
        ..., description="Version of the governing policy."
    )
    framework_version: LearningFrameworkVersion = Field(...)
    result_version: LearningResultVersion = Field(
        default=LEARNING_RESULT_VERSION,
        description="Version of the LearningResult runtime-contract schema.",
    )
    started_at: datetime = Field(..., description="When this Learning build started.")
    completed_at: datetime = Field(..., description="When this Learning build completed.")

    @model_validator(mode="after")
    def _validate_result(self) -> LearningResult:
        """Cross-references and lifetime must be internally consistent."""
        if self.completed_at < self.started_at:
            raise ValueError("completed_at precedes started_at.")

        candidate_ids = [candidate.candidate_id for candidate in self.candidates]
        if len(candidate_ids) != len(set(candidate_ids)):
            raise ValueError("candidates must not contain duplicate ids.")
        known_candidate_ids = set(candidate_ids)

        learning_ids = [learning.learning_id for learning in self.learnings]
        if len(learning_ids) != len(set(learning_ids)):
            raise ValueError("learnings must not contain duplicate ids.")
        known_learning_ids = set(learning_ids)

        validation_ids = [validation.validation_id for validation in self.validations]
        if len(validation_ids) != len(set(validation_ids)):
            raise ValueError("validations must not contain duplicate ids.")
        known_validation_ids = set(validation_ids)

        for validation in self.validations:
            if validation.candidate_id not in known_candidate_ids:
                raise ValueError(
                    f"LearningValidation {validation.validation_id!r} references candidate "
                    f"{validation.candidate_id!r}, which is not present in this result's "
                    f"candidates."
                )

        for learning in self.learnings:
            if learning.candidate_id not in known_candidate_ids:
                raise ValueError(
                    f"Learning {learning.learning_id!r} references candidate "
                    f"{learning.candidate_id!r}, which is not present in this result's "
                    f"candidates."
                )
            if learning.validation_id not in known_validation_ids:
                raise ValueError(
                    f"Learning {learning.learning_id!r} references validation "
                    f"{learning.validation_id!r}, which is not present in this result's "
                    f"validations."
                )

        confidence_ids = [confidence.confidence_id for confidence in self.confidences]
        if len(confidence_ids) != len(set(confidence_ids)):
            raise ValueError("confidences must not contain duplicate ids.")
        known_subject_ids = (
            {str(i) for i in known_candidate_ids} | {str(i) for i in known_learning_ids}
        )
        for confidence in self.confidences:
            if confidence.subject_id not in known_subject_ids:
                raise ValueError(
                    f"LearningConfidence {confidence.confidence_id!r} references subject "
                    f"{confidence.subject_id!r}, which is not present among this result's "
                    f"candidates or learnings."
                )

        lifecycle_ids = [lifecycle.lifecycle_id for lifecycle in self.lifecycles]
        if len(lifecycle_ids) != len(set(lifecycle_ids)):
            raise ValueError("lifecycles must not contain duplicate ids.")
        for lifecycle in self.lifecycles:
            if lifecycle.subject_id not in known_subject_ids:
                raise ValueError(
                    f"LearningLifecycle {lifecycle.lifecycle_id!r} references subject "
                    f"{lifecycle.subject_id!r}, which is not present among this result's "
                    f"candidates or learnings."
                )

        return self
