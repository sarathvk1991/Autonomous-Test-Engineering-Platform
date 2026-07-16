"""``DeterministicLearningEngine`` — the first real implementation behind
``LearningService`` (CAP-086B, ADR-0029 D9-D26).

Mirrors the modular, thin-pipeline-orchestrator discipline the Organizational
Memory Framework's own deterministic engine established (ADR-0027 §D17),
pre-specified one milestone ahead of implementation by CAP-086A.1's own D9,
and corrected by this milestone's own Stage 0 review (see ADR-0029 D9/D16's
"Stage 0 Constitutional Correction"): validation now runs *before*
generation, because ``Learning.validation_id`` is a required field and
``LearningGenerator`` alone constructs ``Learning`` (D17). The engine's only
job is to call each collaborator once, in the frozen order, and thread its
output into the next:

    OrganizationalMemoryResult
        -> LearningCandidateCollector -> candidates
        -> LearningCandidateClusterer -> consolidated candidates
        -> LearningValidator -> validations
        -> LearningGenerator -> learnings
        -> InstitutionalizationEvaluator -> institutionalized ids (internal)
        -> StabilityEvaluator -> stable ids (internal, reserved output)
        -> ConfidenceRecorder -> confidences
        -> PromotionRecorder -> promotion events (internal, reserved output)
        -> LifecycleRecorder -> lifecycles
        -> SummaryBuilder -> summary
        -> MetricsBuilder -> metrics
        -> ResultBuilder -> LearningResult

Pure deterministic function (ADR-0029 D21): the same consumed
``OrganizationalMemoryResult``, under the same governed policy, always
produces an identical ``LearningResult`` (up to its own minted identity,
which is itself a pure function of the consumed result's own id).

The engine consumes **only** ``OrganizationalMemoryResult`` (ADR-0029 D2,
Recommendation 6/7) — never a Layer 1 runtime contract, never
``ContinuousImprovementResult`` or ``KnowledgeGraphResult`` directly, never
a Historical Dataset reference, and never any private collaborator that
resolves one. Learning never touches Historical Truth or Derived Knowledge
directly; it only ever reads the one Organizational Knowledge result already
produced from them.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

from requirement_intelligence.learning.engine.confidence_recorder import ConfidenceRecorder
from requirement_intelligence.learning.engine.institutionalization_evaluator import (
    InstitutionalizationEvaluator,
)
from requirement_intelligence.learning.engine.learning_candidate_clusterer import (
    LearningCandidateClusterer,
)
from requirement_intelligence.learning.engine.learning_candidate_collector import (
    LearningCandidateCollector,
)
from requirement_intelligence.learning.engine.learning_generator import LearningGenerator
from requirement_intelligence.learning.engine.learning_validator import LearningValidator
from requirement_intelligence.learning.engine.lifecycle_recorder import LifecycleRecorder
from requirement_intelligence.learning.engine.metrics_builder import MetricsBuilder
from requirement_intelligence.learning.engine.promotion_recorder import PromotionRecorder
from requirement_intelligence.learning.engine.result_builder import ResultBuilder
from requirement_intelligence.learning.engine.stability_evaluator import StabilityEvaluator
from requirement_intelligence.learning.engine.summary_builder import SummaryBuilder
from requirement_intelligence.learning.identity import LearningEngineVersion
from requirement_intelligence.learning.models.result import LearningResult
from requirement_intelligence.learning.models.summary import LearningMetrics, LearningSummary
from requirement_intelligence.learning.policy import LearningPolicy
from requirement_intelligence.learning.version import LEARNING_FRAMEWORK_VERSION
from requirement_intelligence.organizational_memory.models.result import (
    OrganizationalMemoryResult,
)

#: Version of the deterministic engine's own internal implementation
#: (CAP-086B foundation) — independent of ``LearningFrameworkVersion`` (the
#: frozen public contract). Retuning the engine's internal algorithm
#: advances this version, never the framework or result-contract version.
LEARNING_ENGINE_VERSION = LearningEngineVersion(1, 0, 0)


class DeterministicLearningEngine:
    """The first deterministic implementation behind ``LearningService``.

    Consumes only the one completed ``OrganizationalMemoryResult`` and the
    governed :class:`LearningPolicy`. Every collaborator below owns exactly
    one responsibility so a future statistical, ML, LLM, GraphRAG,
    reinforcement learning, or neuro-symbolic engine can reuse the same
    decomposition without changing the public ``build`` contract.
    """

    def __init__(
        self,
        *,
        policy: LearningPolicy,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        """Store the governed collaborators this engine reads. Construction only."""
        self._policy = policy
        self._clock = clock or (lambda: datetime.now(UTC))

        self._candidate_collector = LearningCandidateCollector(policy)
        self._candidate_clusterer = LearningCandidateClusterer()
        self._validator = LearningValidator(policy)
        self._generator = LearningGenerator(policy)
        self._institutionalization_evaluator = InstitutionalizationEvaluator()
        self._stability_evaluator = StabilityEvaluator()
        self._confidence_recorder = ConfidenceRecorder(policy)
        self._promotion_recorder = PromotionRecorder()
        self._lifecycle_recorder = LifecycleRecorder(policy)
        self._summary_builder = SummaryBuilder()
        self._metrics_builder = MetricsBuilder()
        self._result_builder = ResultBuilder()

    def build(self, organizational_memory_result: OrganizationalMemoryResult) -> LearningResult:
        """Build validated Learning from one completed Organizational Memory result."""
        started_at = self._clock()
        source_id = str(organizational_memory_result.result_id)

        if not self._policy.capability_switches.enable_candidate_proposal:
            return self._empty_result(
                organizational_memory_result_id=source_id,
                started_at=started_at,
                completed_at=self._clock(),
                headline="Learning is disabled by policy (enable_candidate_proposal=False).",
            )

        candidates = self._candidate_clusterer.cluster(
            self._candidate_collector.collect(organizational_memory_result)
        )
        validated_at = self._clock()
        validations = self._validator.validate(candidates, source_id, validated_at)
        learnings = self._generator.generate(candidates, validations, source_id)

        institutionalized_ids = self._institutionalization_evaluator.evaluate(learnings)
        # Stability is a deterministic, reserved decision (D13) — computed for
        # every build, exercised end to end, never persisted (no LearningResult
        # field exists for it yet).
        self._stability_evaluator.evaluate(learnings, institutionalized_ids)

        completed_at = self._clock()
        candidates_by_id = {str(candidate.candidate_id): candidate for candidate in candidates}
        confidences = self._confidence_recorder.record(
            learnings, candidates_by_id, source_id, completed_at
        )
        # Promotion is a deterministic, reserved decision (D10) — computed for
        # every build, exercised end to end, never persisted (no dedicated
        # LearningPromotion model exists yet).
        self._promotion_recorder.record(learnings, completed_at)
        lifecycles = self._lifecycle_recorder.record(
            candidates, learnings, institutionalized_ids, source_id
        )

        summary = self._summary_builder.build(
            self._policy.policy_id,
            self._policy.policy_version,
            candidates,
            learnings,
            validations,
        )
        metrics = self._metrics_builder.build(candidates, learnings, validations, lifecycles)

        return self._result_builder.build(
            organizational_memory_result_id=source_id,
            candidates=candidates,
            learnings=learnings,
            validations=validations,
            confidences=confidences,
            lifecycles=lifecycles,
            summary=summary,
            metrics=metrics,
            policy_id=self._policy.policy_id,
            policy_version=self._policy.policy_version,
            framework_version=LEARNING_FRAMEWORK_VERSION,
            started_at=started_at,
            completed_at=completed_at,
        )

    def _empty_result(
        self,
        *,
        organizational_memory_result_id: str,
        started_at: datetime,
        completed_at: datetime,
        headline: str,
    ) -> LearningResult:
        """The policy-disabled short-circuit path — still a genuine, valid result."""
        summary = LearningSummary(
            policy_id=self._policy.policy_id,
            policy_version=self._policy.policy_version,
            total_candidates=0,
            total_learnings=0,
            total_validations=0,
            headline=headline,
        )
        metrics = LearningMetrics(
            candidate_count=0,
            learning_count=0,
            validation_count=0,
            observed_count=0,
            validated_count=0,
            trusted_count=0,
            institutional_count=0,
            standard_count=0,
            retired_count=0,
        )
        return self._result_builder.build(
            organizational_memory_result_id=organizational_memory_result_id,
            candidates=(),
            learnings=(),
            validations=(),
            confidences=(),
            lifecycles=(),
            summary=summary,
            metrics=metrics,
            policy_id=self._policy.policy_id,
            policy_version=self._policy.policy_version,
            framework_version=LEARNING_FRAMEWORK_VERSION,
            started_at=started_at,
            completed_at=completed_at,
        )
