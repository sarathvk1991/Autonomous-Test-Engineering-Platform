"""The :class:`OrganizationalMemoryResult` — the frozen runtime contract of the
Organizational Memory Framework (CAP-085A architecture freeze, ADR-0027
§D3/§D4).

CAP-085A freezes the architecture before any engine exists — exactly as
CAP-083A did for ``ContinuousImprovementResult`` before CAP-083B's
deterministic engine, and CAP-084A did for ``KnowledgeGraphResult`` before
CAP-084B's.

It **is**:

* the complete runtime output — the single object a future deterministic
  Organizational Memory engine (reserved, CAP-085B) will cross from into
  serialization, exactly as ``KnowledgeGraphResult`` crosses from the
  Knowledge Graph Framework's own deterministic engine;
* the canonical runtime contract — the only Organizational Memory aggregate,
  the third Layer 2 runtime contract (ADR-0020), and the first to consume
  *two* completed Layer 2 peers rather than a Historical Dataset reference
  directly (ADR-0025 §Stage 7/8's fan-in exception, ADR-0027 §D2);
* independently versioned — ``result_version``
  (:class:`OrganizationalMemoryResultVersion`) evolves on its own axis, never
  forcing (or forced by) the framework, policy, or lesson/best-practice/
  lifecycle schema versions, and vice versa (ADR-0027 §D3, mirroring ADR-0023
  §D5/§D6);
* deterministic — a pure function of the two consumed Layer 2 results and the
  governed policy; no randomness, no wall-clock dependence beyond the
  injected clock;
* immutable — ``frozen=True`` (via ``Schema``), tuple-backed collections, no
  field can change after construction;
* self-contained — every experience, lesson, best practice, promotion,
  lifecycle record, summary metric, and consumed Layer 2 result reference
  already lives here, so the result is reproducible with no need to re-run
  curation or inspect any runtime service (mirrors Recommendation 8 of
  ADR-0022, Recommendation 8 of ADR-0023);
* explainable — every experience, lesson, best practice, promotion, and
  lifecycle record is reconstructable from this object alone; no upstream
  subsystem, engine, provider, policy, or service need ever be inspected or
  re-run (Recommendation 9 of ADR-0027);
* serializer-independent — a future serializer projects this object; this
  object never depends on a serializer existing;
* execution-package-independent — this object exists and is fully meaningful
  with no Execution Package, CLI phase, or manifest wired to it at all
  (CAP-085A — none of those exist yet);
* engine-independent — this object's shape does not depend on which engine
  produced it; a future deterministic, statistical, ML, LLM, GraphRAG, or
  neuro-symbolic engine emits the identical contract (Recommendation 12 of
  ADR-0027, ADR-0026 §Stage 13).

It is **not**:

* Runtime Truth; Historical Truth; Derived Knowledge (``ContinuousImprovementResult``
  and ``KnowledgeGraphResult`` remain exactly what ADR-0022/ADR-0023 already
  froze them as — this object references them, it never becomes them); a
  report; Markdown; JSON formatting; an execution artifact; a manifest; a CLI
  object; a renderer; a serializer; a transport object; a projection; an
  Execution Package object; a predictor; an optimizer; the Organizational
  Memory engine itself; a service; a policy; a builder; the Historical
  Dataset.

Each of those is a separate, later owner that *consumes* this object (or, for
the two consumed Layer 2 results, a separate, earlier owner this object
*references* — never embeds); none of them computes anything this object
doesn't already carry.

The validators enforce cross-referential integrity only. No experience,
lesson, best practice, promotion, or lifecycle record is computed here
(CAP-085A architecture freeze, ADR-0027).
"""

from __future__ import annotations

from datetime import datetime

from pydantic import ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

from requirement_intelligence.organizational_memory.identity import (
    OrganizationalMemoryFrameworkVersion,
    OrganizationalMemoryId,
    OrganizationalMemoryPolicyId,
    OrganizationalMemoryPolicyVersion,
    OrganizationalMemoryResultId,
    OrganizationalMemoryResultVersion,
)
from requirement_intelligence.organizational_memory.models.best_practice import BestPractice
from requirement_intelligence.organizational_memory.models.experience import Experience
from requirement_intelligence.organizational_memory.models.knowledge_lifecycle import (
    KnowledgeLifecycle,
)
from requirement_intelligence.organizational_memory.models.knowledge_promotion import (
    KnowledgePromotion,
)
from requirement_intelligence.organizational_memory.models.lesson import Lesson
from requirement_intelligence.organizational_memory.models.summary import (
    OrganizationalMemoryMetrics,
    OrganizationalMemorySummary,
)
from shared.contracts.base import Schema

#: Version of the ``OrganizationalMemoryResult`` **runtime contract** schema.
#: Independent of every other Organizational Memory version axis —
#: ``OrganizationalMemoryFrameworkVersion``, ``OrganizationalMemoryPolicyVersion``,
#: ``LessonVersion``, ``BestPracticeVersion``, ``KnowledgeLifecycleVersion`` — a
#: change here never forces any of those to change, and vice versa (frozen,
#: CAP-085A, ADR-0027 §D3, mirroring ``KnowledgeGraphResultVersion``, ADR-0023
#: §D5/§D6).
ORGANIZATIONAL_MEMORY_RESULT_VERSION = OrganizationalMemoryResultVersion(1, 0, 0)


class OrganizationalMemoryResult(Schema):
    """The complete, deterministic curated organizational knowledge for one build.

    ``OrganizationalMemoryResult`` is the **permanent runtime contract** — the
    only Organizational Memory object that crosses into serialization. It is
    **not** a report, an execution artifact, serialization, a renderer, or a
    calculator: it already contains everything (every experience, lesson,
    best practice, promotion record, lifecycle record, the summary, the
    metrics, the governing policy identity/version, and the two consumed
    Layer 2 result references) any downstream projection needs.

    **Serialization invariant (frozen, mirrors ADR-0023 §D8).** Every future
    execution artifact concerning Organizational Memory will be a **pure
    projection** of an ``OrganizationalMemoryResult`` — reproducible from it
    alone, computing nothing. A renderer must never call an Organizational
    Memory engine, ``PlatformContext``, capture an experience, promote a
    lesson, institutionalize a best practice, or invoke a policy.

    **Ownership (frozen, CAP-085A, ADR-0027 §D3).** This is the **sole**
    owner of every experience, lesson, best practice, promotion record,
    lifecycle record, summary metric, policy identity/version, and consumed
    Layer 2 result reference produced by the Organizational Memory Framework.
    Nothing upstream and nothing downstream owns these — no execution
    artifact, manifest, or other subsystem may duplicate that ownership
    (Recommendation 1 of ADR-0027). The future engine that assembles this
    object is engine-internal implementation detail — it is not part of this
    contract, and it is not named by any field here.

    **Explainability (frozen, CAP-085A, Recommendation 9 of ADR-0027).**
    Every experience, lesson, best practice, promotion, and lifecycle record
    is explainable entirely from this object's contents, traceable through
    the two referenced Layer 2 result ids down to Historical Truth and
    Runtime Truth (ADR-0026 §Stage 9) — no downstream consumer should ever
    need to re-run curation or inspect the engine, the service, or
    ``PlatformContext``.

    **Truth Hierarchy boundary (frozen, ADR-0025 §Stage 2, ADR-0026 §Stage
    2).** This result is Organizational Knowledge: derived exclusively from
    Derived Knowledge (``ContinuousImprovementResult`` and
    ``KnowledgeGraphResult``), never itself Derived Knowledge, Historical
    Truth, or Runtime Truth. It must never be written back into either
    consumed result, and no future Organizational Memory build may consume a
    prior ``OrganizationalMemoryResult`` as an input (mirrors Recommendation
    11 of ADR-0022, Recommendation 11/17 of ADR-0023, Recommendation 2 of
    ADR-0025).

    **Runtime boundary (frozen, CAP-085A).** Runtime ends at this object:
    ``ContinuousImprovementResult`` + ``KnowledgeGraphResult`` → (future
    engine) → ``OrganizationalMemoryResult``. Everything after that —
    serialization, reports, Markdown, JSON, the Execution Package — is
    projection only, and does not exist yet (CAP-085A introduces none of it).

    **Golden regression boundary (frozen).** A future golden dataset compares
    this object's content, never Markdown or JSON formatting. A presentation
    change must never invalidate a runtime regression baseline; only a
    change to this object's content (or its ``result_version``) is a runtime
    regression.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    result_id: OrganizationalMemoryResultId = Field(..., description="Deterministic result id.")
    memory_id: OrganizationalMemoryId = Field(
        ..., description="Deterministic identity of the memory build this result represents."
    )
    continuous_improvement_result_id: str = Field(
        ...,
        min_length=1,
        description="Id of the consumed ContinuousImprovementResult (reference only).",
    )
    knowledge_graph_result_id: str = Field(
        ..., min_length=1, description="Id of the consumed KnowledgeGraphResult (reference only)."
    )

    experiences: tuple[Experience, ...] = Field(
        default=(), description="Every experience captured for this build."
    )
    lessons: tuple[Lesson, ...] = Field(
        default=(), description="Every lesson promoted for this build."
    )
    best_practices: tuple[BestPractice, ...] = Field(
        default=(), description="Every best practice promoted for this build."
    )
    promotions: tuple[KnowledgePromotion, ...] = Field(
        default=(), description="Every promotion record for this build."
    )
    lifecycles: tuple[KnowledgeLifecycle, ...] = Field(
        default=(), description="Every lifecycle-state record for this build."
    )
    summary: OrganizationalMemorySummary = Field(
        ..., description="The headline summary of this build."
    )
    metrics: OrganizationalMemoryMetrics = Field(
        ..., description="The deterministic numeric roll-up."
    )

    policy_id: OrganizationalMemoryPolicyId = Field(
        ..., description="Identity of the governing policy."
    )
    policy_version: OrganizationalMemoryPolicyVersion = Field(
        ..., description="Version of the governing policy."
    )
    framework_version: OrganizationalMemoryFrameworkVersion = Field(...)
    result_version: OrganizationalMemoryResultVersion = Field(
        default=ORGANIZATIONAL_MEMORY_RESULT_VERSION,
        description="Version of the OrganizationalMemoryResult runtime-contract schema.",
    )
    started_at: datetime = Field(..., description="When this Organizational Memory build started.")
    completed_at: datetime = Field(
        ..., description="When this Organizational Memory build completed."
    )

    @model_validator(mode="after")
    def _validate_result(self) -> OrganizationalMemoryResult:
        """Cross-references and lifetime must be internally consistent."""
        if self.completed_at < self.started_at:
            raise ValueError("completed_at precedes started_at.")

        experience_ids = [experience.experience_id for experience in self.experiences]
        if len(experience_ids) != len(set(experience_ids)):
            raise ValueError("experiences must not contain duplicate ids.")
        known_experience_ids = set(experience_ids)

        lesson_ids = [lesson.lesson_id for lesson in self.lessons]
        if len(lesson_ids) != len(set(lesson_ids)):
            raise ValueError("lessons must not contain duplicate ids.")
        known_lesson_ids = set(lesson_ids)

        best_practice_ids = [bp.best_practice_id for bp in self.best_practices]
        if len(best_practice_ids) != len(set(best_practice_ids)):
            raise ValueError("best_practices must not contain duplicate ids.")
        known_best_practice_ids = set(best_practice_ids)

        for lesson in self.lessons:
            for experience_id in lesson.source_experience_ids:
                if experience_id not in known_experience_ids:
                    raise ValueError(
                        f"Lesson {lesson.lesson_id!r} references source experience "
                        f"{experience_id!r}, which is not present in this result's experiences."
                    )

        for best_practice in self.best_practices:
            for lesson_id in best_practice.source_lesson_ids:
                if lesson_id not in known_lesson_ids:
                    raise ValueError(
                        f"BestPractice {best_practice.best_practice_id!r} references source "
                        f"lesson {lesson_id!r}, which is not present in this result's lessons."
                    )

        promotion_ids = [promotion.promotion_id for promotion in self.promotions]
        if len(promotion_ids) != len(set(promotion_ids)):
            raise ValueError("promotions must not contain duplicate ids.")
        known_subject_ids = (
            {str(i) for i in known_experience_ids}
            | {str(i) for i in known_lesson_ids}
            | {str(i) for i in known_best_practice_ids}
        )
        for promotion in self.promotions:
            for source_id in promotion.source_ids:
                if source_id not in known_subject_ids:
                    raise ValueError(
                        f"KnowledgePromotion {promotion.promotion_id!r} references source id "
                        f"{source_id!r}, which is not present among this result's experiences, "
                        f"lessons, or best practices."
                    )
            for target_id in promotion.target_ids:
                if target_id not in known_subject_ids:
                    raise ValueError(
                        f"KnowledgePromotion {promotion.promotion_id!r} references target id "
                        f"{target_id!r}, which is not present among this result's experiences, "
                        f"lessons, or best practices."
                    )

        lifecycle_ids = [lifecycle.lifecycle_id for lifecycle in self.lifecycles]
        if len(lifecycle_ids) != len(set(lifecycle_ids)):
            raise ValueError("lifecycles must not contain duplicate ids.")
        for lifecycle in self.lifecycles:
            if lifecycle.subject_id not in known_subject_ids:
                raise ValueError(
                    f"KnowledgeLifecycle {lifecycle.lifecycle_id!r} references subject id "
                    f"{lifecycle.subject_id!r}, which is not present among this result's "
                    f"experiences, lessons, or best practices."
                )

        return self
