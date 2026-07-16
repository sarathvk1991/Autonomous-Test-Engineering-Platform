"""``DeterministicOrganizationalMemoryEngine`` — the first real implementation
behind ``OrganizationalMemoryService`` (CAP-085B, ADR-0027 §D9-§D17).

Mirrors the modular, thin-pipeline-orchestrator discipline the Knowledge
Graph Framework's own deterministic engine established (ADR-0023 §D10),
pre-specified one milestone ahead of implementation by CAP-085A.1's own
D9/D12. The engine's only job is to call each collaborator once, in the
frozen order, and thread its output into the next:

    ContinuousImprovementResult + KnowledgeGraphResult
        -> ExperienceCollector -> experiences
        -> ExperienceClusterer -> clusters
        -> LessonGenerator -> lessons
        -> LessonConsolidator -> consolidated lessons
        -> BestPracticeGenerator -> best practices
        -> PromotionRecorder -> promotions
        -> LifecycleRecorder -> lifecycles
        -> SummaryBuilder -> summary
        -> MetricsBuilder -> metrics
        -> ResultBuilder -> OrganizationalMemoryResult

Pure deterministic function: the same pair of consumed Layer 2 results, under
the same governed policy, always produces an identical
``OrganizationalMemoryResult`` (up to its own minted identity, which is
itself a pure function of the two consumed result ids).

The engine consumes **only** ``ContinuousImprovementResult`` and
``KnowledgeGraphResult`` (ADR-0027 §D2, Recommendation 6/7) — never a Layer 1
runtime contract, never a Historical Dataset reference, and never any private
collaborator that resolves one (the pattern ADR-0022/ADR-0023 each privately
implement for their own subsystems). Organizational Memory never touches
Historical Truth directly; it only ever reads the two Layer 2 peer results
already produced from it.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

from requirement_intelligence.continuous_improvement.models.result import (
    ContinuousImprovementResult,
)
from requirement_intelligence.knowledge_graph.models.result import KnowledgeGraphResult
from requirement_intelligence.organizational_memory.engine.best_practice_generator import (
    BestPracticeGenerator,
)
from requirement_intelligence.organizational_memory.engine.experience_clusterer import (
    ExperienceClusterer,
)
from requirement_intelligence.organizational_memory.engine.experience_collector import (
    ExperienceCollector,
)
from requirement_intelligence.organizational_memory.engine.lesson_consolidator import (
    LessonConsolidator,
)
from requirement_intelligence.organizational_memory.engine.lesson_generator import LessonGenerator
from requirement_intelligence.organizational_memory.engine.lifecycle_recorder import (
    LifecycleRecorder,
)
from requirement_intelligence.organizational_memory.engine.metrics_builder import MetricsBuilder
from requirement_intelligence.organizational_memory.engine.promotion_recorder import (
    PromotionRecorder,
)
from requirement_intelligence.organizational_memory.engine.result_builder import ResultBuilder
from requirement_intelligence.organizational_memory.engine.summary_builder import SummaryBuilder
from requirement_intelligence.organizational_memory.identity import (
    OrganizationalMemoryEngineVersion,
    OrganizationalMemoryId,
)
from requirement_intelligence.organizational_memory.models.result import OrganizationalMemoryResult
from requirement_intelligence.organizational_memory.models.summary import (
    OrganizationalMemoryMetrics,
    OrganizationalMemorySummary,
)
from requirement_intelligence.organizational_memory.policy import OrganizationalMemoryPolicy
from requirement_intelligence.organizational_memory.version import (
    ORGANIZATIONAL_MEMORY_FRAMEWORK_VERSION,
)

#: Version of the deterministic engine's own internal implementation
#: (CAP-085B foundation) — independent of ``OrganizationalMemoryFrameworkVersion``
#: (the frozen public contract). Retuning the engine's internal algorithm
#: advances this version, never the framework or result-contract version.
ORGANIZATIONAL_MEMORY_ENGINE_VERSION = OrganizationalMemoryEngineVersion(1, 0, 0)


class DeterministicOrganizationalMemoryEngine:
    """The first deterministic implementation behind ``OrganizationalMemoryService``.

    Consumes only the two completed Layer 2 results and the governed
    :class:`OrganizationalMemoryPolicy`. Every collaborator below owns exactly
    one responsibility so a future statistical, ML, LLM, GraphRAG, or
    neuro-symbolic engine can reuse the same decomposition without changing
    the public ``build`` contract.
    """

    def __init__(
        self,
        *,
        policy: OrganizationalMemoryPolicy,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        """Store the governed collaborators this engine reads. Construction only."""
        self._policy = policy
        self._clock = clock or (lambda: datetime.now(UTC))

        self._experience_collector = ExperienceCollector()
        self._experience_clusterer = ExperienceClusterer()
        self._lesson_generator = LessonGenerator(policy)
        self._lesson_consolidator = LessonConsolidator()
        self._best_practice_generator = BestPracticeGenerator(policy)
        self._promotion_recorder = PromotionRecorder(policy)
        self._lifecycle_recorder = LifecycleRecorder(policy)
        self._summary_builder = SummaryBuilder()
        self._metrics_builder = MetricsBuilder()
        self._result_builder = ResultBuilder()

    def build(
        self,
        continuous_improvement_result: ContinuousImprovementResult,
        knowledge_graph_result: KnowledgeGraphResult,
    ) -> OrganizationalMemoryResult:
        """Build curated Organizational Memory. Deterministic."""
        started_at = self._clock()
        memory_id = OrganizationalMemoryId.for_inputs(
            str(continuous_improvement_result.result_id), str(knowledge_graph_result.result_id)
        )
        memory_id_str = str(memory_id)

        if not self._policy.capability_switches.enable_experience_capture:
            return self._empty_result(
                memory_id=memory_id,
                continuous_improvement_result_id=str(continuous_improvement_result.result_id),
                knowledge_graph_result_id=str(knowledge_graph_result.result_id),
                started_at=started_at,
                completed_at=self._clock(),
                headline=(
                    "Organizational Memory curation is disabled by policy "
                    "(enable_experience_capture=False)."
                ),
            )

        experiences = self._experience_collector.collect(
            continuous_improvement_result, knowledge_graph_result
        )
        clusters = self._experience_clusterer.cluster(experiences)
        lessons = self._lesson_consolidator.consolidate(
            self._lesson_generator.generate(clusters, memory_id_str)
        )
        best_practices = self._best_practice_generator.generate(
            lessons, experiences, memory_id_str
        )

        completed_at = self._clock()
        promotions = self._promotion_recorder.record(
            lessons, best_practices, memory_id_str, completed_at
        )
        lifecycles = self._lifecycle_recorder.record(
            experiences, lessons, best_practices, memory_id_str
        )

        summary = self._summary_builder.build(
            self._policy.policy_id,
            self._policy.policy_version,
            experiences,
            lessons,
            best_practices,
            promotions,
        )
        metrics = self._metrics_builder.build(
            experiences, lessons, best_practices, promotions, lifecycles
        )

        return self._result_builder.build(
            memory_id=memory_id,
            continuous_improvement_result_id=str(continuous_improvement_result.result_id),
            knowledge_graph_result_id=str(knowledge_graph_result.result_id),
            experiences=experiences,
            lessons=lessons,
            best_practices=best_practices,
            promotions=promotions,
            lifecycles=lifecycles,
            summary=summary,
            metrics=metrics,
            policy_id=self._policy.policy_id,
            policy_version=self._policy.policy_version,
            framework_version=ORGANIZATIONAL_MEMORY_FRAMEWORK_VERSION,
            started_at=started_at,
            completed_at=completed_at,
        )

    def _empty_result(
        self,
        *,
        memory_id: OrganizationalMemoryId,
        continuous_improvement_result_id: str,
        knowledge_graph_result_id: str,
        started_at: datetime,
        completed_at: datetime,
        headline: str,
    ) -> OrganizationalMemoryResult:
        """The policy-disabled short-circuit path — still a genuine, valid result."""
        summary = OrganizationalMemorySummary(
            policy_id=self._policy.policy_id,
            policy_version=self._policy.policy_version,
            total_experiences=0,
            total_lessons=0,
            total_best_practices=0,
            total_promotions=0,
            headline=headline,
        )
        metrics = OrganizationalMemoryMetrics(
            experience_count=0,
            lesson_count=0,
            best_practice_count=0,
            promotion_count=0,
            active_count=0,
            deprecated_count=0,
            historical_count=0,
            archived_count=0,
        )
        return self._result_builder.build(
            memory_id=memory_id,
            continuous_improvement_result_id=continuous_improvement_result_id,
            knowledge_graph_result_id=knowledge_graph_result_id,
            experiences=(),
            lessons=(),
            best_practices=(),
            promotions=(),
            lifecycles=(),
            summary=summary,
            metrics=metrics,
            policy_id=self._policy.policy_id,
            policy_version=self._policy.policy_version,
            framework_version=ORGANIZATIONAL_MEMORY_FRAMEWORK_VERSION,
            started_at=started_at,
            completed_at=completed_at,
        )
