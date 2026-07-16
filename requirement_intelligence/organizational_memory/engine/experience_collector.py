"""Deterministic experience capture (CAP-085B).

``ExperienceCollector`` is the **sole Experience authority**: it is the only
component that constructs :class:`Experience` instances, and it does so
directly from the two completed Layer 2 results
:class:`~requirement_intelligence.organizational_memory.
organizational_memory_service.OrganizationalMemoryService.build` receives.
It performs **no inference, no AI, no heuristics** — every experience it
emits is a direct, governed reference to an entity the consumed results
already name (Recommendation 2 of ADR-0027: nodes/experiences reference
runtime contracts, they never duplicate them).

Every ``Experience`` references exactly one source object:

* :class:`ImprovementFinding`, :class:`ImprovementTrend`,
  :class:`ImprovementOpportunity` from ``ContinuousImprovementResult``;
* :class:`KnowledgeFinding`, :class:`KnowledgeObservation`,
  :class:`KnowledgeSubgraph` from ``KnowledgeGraphResult``.

Never both. Never a copy of the source object's content beyond its own
human-readable description text, which the source object already carries
verbatim (never re-derived, never re-worded).
"""

from __future__ import annotations

from requirement_intelligence.continuous_improvement.models.result import (
    ContinuousImprovementResult,
)
from requirement_intelligence.knowledge_graph.models.result import KnowledgeGraphResult
from requirement_intelligence.organizational_memory.identity import ExperienceId
from requirement_intelligence.organizational_memory.models.enums import (
    OrganizationalMemoryConfidence,
    OrganizationalMemorySourceLayer,
)
from requirement_intelligence.organizational_memory.models.experience import Experience

#: Every newly captured Experience starts at the bottom of the confidence
#: ladder (ADR-0026 §Stage 3: Observed) — it may only rise through governed
#: promotion (ADR-0026 §Stage 8), never at capture time.
_INITIAL_CONFIDENCE = OrganizationalMemoryConfidence.LOW


class ExperienceCollector:
    """Capture governed Experiences from two completed Layer 2 results.

    The sole Experience authority (Recommendation 1 of ADR-0027: Organizational
    Memory owns platform curation). Deduplicates by :class:`ExperienceId` — the
    same referenced entity, seen more than once, yields exactly one Experience.
    """

    def collect(
        self,
        continuous_improvement_result: ContinuousImprovementResult,
        knowledge_graph_result: KnowledgeGraphResult,
    ) -> tuple[Experience, ...]:
        """Deterministically capture one Experience per governed source object."""
        experiences: dict[ExperienceId, Experience] = {}

        for finding in continuous_improvement_result.findings:
            self._add(
                experiences,
                OrganizationalMemorySourceLayer.CONTINUOUS_IMPROVEMENT,
                str(finding.finding_id),
                finding.message,
            )
        for trend in continuous_improvement_result.trends:
            self._add(
                experiences,
                OrganizationalMemorySourceLayer.CONTINUOUS_IMPROVEMENT,
                str(trend.trend_id),
                trend.message,
            )
        for opportunity in continuous_improvement_result.opportunities:
            self._add(
                experiences,
                OrganizationalMemorySourceLayer.CONTINUOUS_IMPROVEMENT,
                str(opportunity.opportunity_id),
                opportunity.description,
            )
        for kg_finding in knowledge_graph_result.findings:
            self._add(
                experiences,
                OrganizationalMemorySourceLayer.KNOWLEDGE_GRAPH,
                str(kg_finding.finding_id),
                kg_finding.message,
            )
        for observation in knowledge_graph_result.observations:
            self._add(
                experiences,
                OrganizationalMemorySourceLayer.KNOWLEDGE_GRAPH,
                str(observation.observation_id),
                observation.description,
            )
        for subgraph in knowledge_graph_result.subgraphs:
            self._add(
                experiences,
                OrganizationalMemorySourceLayer.KNOWLEDGE_GRAPH,
                str(subgraph.subgraph_id),
                subgraph.label,
            )

        return tuple(experiences.values())

    @staticmethod
    def _add(
        experiences: dict[ExperienceId, Experience],
        source_layer: OrganizationalMemorySourceLayer,
        source_reference_id: str,
        description: str,
    ) -> None:
        """Insert the experience for *source_reference_id* if not already present."""
        experience_id = ExperienceId.for_source(source_layer.value, source_reference_id)
        if experience_id in experiences:
            return
        experiences[experience_id] = Experience(
            experience_id=experience_id,
            source_layer=source_layer,
            source_reference_id=source_reference_id,
            description=description,
            confidence=_INITIAL_CONFIDENCE,
        )
