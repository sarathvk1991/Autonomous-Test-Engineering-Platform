"""The :class:`DeterministicRequirementEnhancementEngine` — the first real engine
behind the frozen CAP-081A boundary (CAP-081B).

Consumes only ``EngineeringContext``, ``AnalysisResult``, the governed
``EnhancementPolicy``, and the governed ``EnhancementRuleCatalog``. Produces only a
``RequirementEnhancementResult``. It never performs grounding, validation,
classification, confidence computation, governance, serialization, or execution-package
writing (Stage 2, ADR-0018).

Internal execution order (frozen for this engine, Recommendation 3)::

    1. Enhanced requirements (core: id, deterministic attributes)
    2. Relationship graph    (Recommendation 6: the single source of truth)
    3. Observations          (derived from 1 + 2 only, Recommendation 3)
    4. Findings              (surfaced observations, by reference — Recommendation 2)
    5. Metrics
    6. Summary
    7. RequirementEnhancementResult

Enriched requirements are constructed once relationships and observations are known,
so their ``relationship_ids`` / ``observation_ids`` reference ids that already exist
(Recommendation 2: references, never copies) — the *content* of an enrichment (its
attributes) is still decided in phase 1; only the object's construction is deferred
to the point every reference it names is resolvable, which ``RequirementEnhancementResult``'s
own validator requires.

Requirement extraction (Stage 2 boundary note)
------------------------------------------------
``AnalysisResult`` carries only the raw AI response text; the generated requirements
live in its strict-JSON body under ``functional_requirements`` / ``security_requirements``
/ ``quality_requirements``. Grounding's ``MatchingContextBuilder`` already recovers this
same array shape for its own purposes, but it is a **Grounding-owned** implementation
class Requirement Enhancement must not import (peer-subsystem scope, ADR-0018 §D1).
This engine therefore performs the identical, minimal, deterministic extraction
independently — the same "duplicate rather than couple" precedent ADR-0015 §C and
ADR-0016 §D6 already set for the identity primitives (see ``identity/enhancement_identity.py``).
Enhancement mints its own plain-string requirement ids (``"functional-001"`` etc.),
independent of Grounding's ``GroundedRequirementId`` scheme.

Determinism
-----------
No randomness, no UUID. Every id is a pure function of stable inputs (the enhancement
run id, a requirement id, an ordinal, or a relationship's source/target/type —
Recommendation 5). ``started_at`` / ``completed_at`` come from an injected clock
(default wall-clock), so a fixed clock yields a byte-identical result across runs,
exactly the convention ``GroundingPipeline`` and the Quality Governance pipeline use.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from requirement_intelligence.analysis.analysis_models import AnalysisResult
from requirement_intelligence.context_orchestration.models.engineering_context import (
    EngineeringContext,
)
from requirement_intelligence.enhancement.identity.enhancement_identity import (
    EnhancedRequirementId,
    RelationshipGraphId,
    RequirementEnhancementId,
    RequirementEnhancementResultId,
    RequirementObservationId,
)
from requirement_intelligence.enhancement.models.enums import (
    EnhancementInputSource,
    EnhancementSeverity,
    ObservationCategory,
    RelationshipType,
)
from requirement_intelligence.enhancement.models.observations import (
    EnhancementFinding,
    RequirementObservation,
)
from requirement_intelligence.enhancement.models.relationships import (
    RelationshipGraph,
    RequirementRelationship,
)
from requirement_intelligence.enhancement.models.requirements import (
    EnhancedRequirement,
    EnhancementAttribute,
)
from requirement_intelligence.enhancement.models.result import (
    EnhancementInputReference,
    RequirementEnhancementResult,
)
from requirement_intelligence.enhancement.models.summary import (
    EnhancementMetrics,
    EnhancementSummary,
    ObservationCategoryCount,
)
from requirement_intelligence.enhancement.policy.enhancement_policy import EnhancementPolicy
from requirement_intelligence.enhancement.rules.enhancement_rule import EnhancementMechanism
from requirement_intelligence.enhancement.rules.enhancement_rule_catalog import (
    EnhancementRuleCatalog,
)
from requirement_intelligence.enhancement.version import ENHANCEMENT_FRAMEWORK_VERSION
from requirement_intelligence.models.enums import SourceCategory

#: The response arrays that hold generated requirements, mapped to their domain, in
#: canonical domain order. Mirrors Grounding's ``_REQUIREMENT_ARRAYS`` (independently —
#: see the module docstring's "duplicate rather than couple" note).
_REQUIREMENT_ARRAYS: tuple[tuple[str, SourceCategory], ...] = (
    ("functional_requirements", SourceCategory.FUNCTIONAL),
    ("security_requirements", SourceCategory.SECURITY),
    ("quality_requirements", SourceCategory.QUALITY),
)

#: Governed, fixed keyword vocabularies the keyword-triggered relationship mechanisms
#: match against. Fixed mechanism vocabulary (like ``RuleComparator``), not a tunable
#: policy value — a future milestone may promote these into governed policy data
#: (Recommendation 7 reserves exactly this kind of extension).
_DEPENDENCY_KEYWORDS: tuple[str, ...] = ("depends on", "requires", "prerequisite")
_REFINEMENT_KEYWORDS: tuple[str, ...] = ("refines", "elaborates on", "extends")
_PARENT_CHILD_KEYWORDS: tuple[str, ...] = ("child of", "sub-requirement of", "parent requirement")

#: The shortest another requirement's normalized text may be to count as a verbatim
#: substring match — guards against trivial, near-meaningless overlaps on short text.
_MIN_SUBSTRING_MATCH_LENGTH = 8

_KEYWORD_MECHANISMS: tuple[tuple[EnhancementMechanism, tuple[str, ...], RelationshipType], ...] = (
    (
        EnhancementMechanism.EXPLICIT_DEPENDENCY_REFERENCE,
        _DEPENDENCY_KEYWORDS,
        RelationshipType.DEPENDS_ON,
    ),
    (EnhancementMechanism.REFINEMENT_REFERENCE, _REFINEMENT_KEYWORDS, RelationshipType.REFINES),
    (
        EnhancementMechanism.PARENT_CHILD_REFERENCE,
        _PARENT_CHILD_KEYWORDS,
        RelationshipType.DERIVED_FROM,
    ),
)


class RequirementExtractionError(ValueError):
    """Raised when generated requirements cannot be recovered from *analysis_result*."""


@dataclass(frozen=True)
class _GeneratedRequirement:
    """One generated requirement recovered from the AI response body. Internal only."""

    requirement_id: str
    domain: SourceCategory
    text: str
    position: int


def _normalize(text: str) -> str:
    """Deterministic text normalization: lower-case, collapsed whitespace, trimmed."""
    return " ".join(text.strip().lower().split())


def _relationship_id(source: str, target: str, relationship_type: RelationshipType) -> str:
    """A deterministic id — a pure function of source, target, and type (Recommendation 5)."""
    digest = hashlib.sha256(f"{source}:{target}:{relationship_type.value}".encode()).hexdigest()
    return f"rel-{digest[:12]}"


class DeterministicRequirementEnhancementEngine:
    """The first deterministic implementation behind ``RequirementEnhancementService``.

    Consumes only ``EngineeringContext`` / ``AnalysisResult`` / ``EnhancementPolicy`` /
    ``EnhancementRuleCatalog``. Every method below owns exactly one responsibility
    (Recommendation 4: internal engine modularity) so a future semantic, statistical,
    graph-based, or AI-assisted engine can reuse the same decomposition without
    changing the public ``enhance`` contract.
    """

    def __init__(
        self,
        *,
        policy: EnhancementPolicy,
        rule_catalog: EnhancementRuleCatalog,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        """Store the governed collaborators this engine reads. Construction only."""
        self._policy = policy
        self._catalog = rule_catalog
        self._clock = clock or (lambda: datetime.now(UTC))

    def enhance(
        self,
        engineering_context: EngineeringContext,
        analysis_result: AnalysisResult,
    ) -> RequirementEnhancementResult:
        """Enhance one run. Deterministic; raises only on malformed input (service-level)."""
        started_at = self._clock()
        enhancement_id = RequirementEnhancementId.for_run(
            analysis_result.analysis_id, analysis_result.execution_id
        )
        graph_id = RelationshipGraphId.for_enhancement(str(enhancement_id))

        generated = self._extract_generated_requirements(analysis_result)

        if not self._policy.capability_switches.enable_enrichment or not generated:
            return self._empty_result(
                enhancement_id=enhancement_id,
                graph_id=graph_id,
                analysis_result=analysis_result,
                engineering_context=engineering_context,
                started_at=started_at,
                completed_at=self._clock(),
            )

        attributes_by_id = self._enrich(generated, analysis_result)
        graph = self._build_relationship_graph(generated, graph_id)
        observations = self._generate_observations(
            enhancement_id=enhancement_id, requirements=generated, graph=graph
        )
        findings = self._surface_findings(observations)

        enhanced_requirements = self._assemble_enhanced_requirements(
            enhancement_id=enhancement_id,
            requirements=generated,
            attributes_by_id=attributes_by_id,
            graph=graph,
            observations=observations,
        )
        metrics = self._compute_metrics(generated, enhanced_requirements, graph, observations)
        summary = self._build_summary(
            enhanced_requirements=enhanced_requirements,
            graph=graph,
            observations=observations,
            findings=findings,
        )
        completed_at = self._clock()

        return RequirementEnhancementResult(
            result_id=RequirementEnhancementResultId.for_enhancement(str(enhancement_id)),
            analysis_id=analysis_result.analysis_id,
            execution_id=analysis_result.execution_id,
            enhanced_requirements=enhanced_requirements,
            relationship_graph=graph,
            observations=observations,
            findings=findings,
            summary=summary,
            metrics=metrics,
            consumed_inputs=self._consumed_inputs(engineering_context, analysis_result),
            policy_id=self._policy.policy_id,
            policy_version=self._policy.policy_version,
            framework_version=ENHANCEMENT_FRAMEWORK_VERSION,
            started_at=started_at,
            completed_at=completed_at,
        )

    # -- 0. requirement extraction (service-level; a failure here fails the whole call) --

    def _extract_generated_requirements(
        self, analysis_result: AnalysisResult
    ) -> tuple[_GeneratedRequirement, ...]:
        """Recover the generated requirements from the response body, in canonical order."""
        body = self._response_object(analysis_result)
        requirements: list[_GeneratedRequirement] = []
        for key, domain in _REQUIREMENT_ARRAYS:
            values = body.get(key, [])
            if not isinstance(values, list):
                raise RequirementExtractionError(
                    f"Response field '{key}' is not a list of requirements."
                )
            for position, value in enumerate(values):
                if not isinstance(value, str) or not value.strip():
                    continue
                requirements.append(
                    _GeneratedRequirement(
                        requirement_id=f"{domain.value}-{position + 1:03d}",
                        domain=domain,
                        text=value.strip(),
                        position=position,
                    )
                )
        return tuple(requirements)

    @staticmethod
    def _response_object(analysis_result: AnalysisResult) -> dict[str, Any]:
        """Parse the strict-JSON response body, or reject extraction."""
        text = analysis_result.llm_response.generated_text
        try:
            body = json.loads(text)
        except (json.JSONDecodeError, TypeError) as exc:
            raise RequirementExtractionError(
                "AI response body is not valid JSON; cannot recover generated requirements."
            ) from exc
        if not isinstance(body, dict):
            raise RequirementExtractionError(
                "AI response body is not a JSON object; cannot recover generated requirements."
            )
        return body

    # -- 1. enrichment (core: deterministic attributes only) -----------------------------

    def _enrich(
        self, requirements: tuple[_GeneratedRequirement, ...], analysis_result: AnalysisResult
    ) -> dict[str, tuple[EnhancementAttribute, ...]]:
        """Return the deterministic attributes for each requirement, keyed by its id."""
        rules = self._catalog.enabled_rules()
        provenance_active = self._rule_active(rules, EnhancementMechanism.PROVENANCE_ATTRIBUTE)
        traceability_active = self._rule_active(rules, EnhancementMechanism.TRACEABILITY_ATTRIBUTE)
        vocabulary = self._policy.enrichment_rules.attribute_key_vocabulary
        max_attributes = self._policy.enrichment_rules.max_attributes_per_requirement

        result: dict[str, tuple[EnhancementAttribute, ...]] = {}
        for requirement in requirements:
            attributes: list[EnhancementAttribute] = []
            if provenance_active and self._attribute_allowed("provenance", vocabulary):
                attributes.append(
                    EnhancementAttribute(
                        key="provenance",
                        value=f"{requirement.domain.value}:{requirement.position}",
                    )
                )
            if traceability_active and self._attribute_allowed("traceability", vocabulary):
                attributes.append(
                    EnhancementAttribute(
                        key="traceability",
                        value=f"{analysis_result.analysis_id}:{analysis_result.execution_id}",
                    )
                )
            result[requirement.requirement_id] = tuple(attributes[:max_attributes])
        return result

    @staticmethod
    def _attribute_allowed(key: str, vocabulary: tuple[str, ...]) -> bool:
        """An empty governed vocabulary allows every attribute key; else it restricts."""
        return not vocabulary or key in vocabulary

    # -- 2. relationship graph (the single source of truth, Recommendation 6) -----------

    def _build_relationship_graph(
        self, requirements: tuple[_GeneratedRequirement, ...], graph_id: RelationshipGraphId
    ) -> RelationshipGraph:
        """Construct the canonical graph from conservative, deterministic mechanisms only."""
        rules = self._catalog.enabled_rules()
        node_ids = tuple(requirement.requirement_id for requirement in requirements)
        out_degree: dict[str, int] = dict.fromkeys(node_ids, 0)
        max_out_degree = self._policy.relationship_rules.max_relationships_per_requirement
        enabled_types = set(self._policy.relationship_rules.enabled_relationship_types)

        edges: dict[str, RequirementRelationship] = {}

        if (
            self._rule_active(rules, EnhancementMechanism.DUPLICATE_REQUIREMENT_TEXT)
            and RelationshipType.DUPLICATES in enabled_types
        ):
            self._detect_duplicates(requirements, edges, out_degree, max_out_degree)

        for mechanism, keywords, relationship_type in _KEYWORD_MECHANISMS:
            if not self._rule_active(rules, mechanism) or relationship_type not in enabled_types:
                continue
            self._detect_keyword_relationships(
                requirements, keywords, relationship_type, edges, out_degree, max_out_degree
            )

        ordered_edges = tuple(
            sorted(
                edges.values(),
                key=lambda edge: (
                    edge.relationship_type,
                    edge.source_requirement_id,
                    edge.target_requirement_id,
                ),
            )
        )
        return RelationshipGraph(
            graph_id=graph_id, requirement_ids=node_ids, relationships=ordered_edges
        )

    def _detect_duplicates(
        self,
        requirements: tuple[_GeneratedRequirement, ...],
        edges: dict[str, RequirementRelationship],
        out_degree: dict[str, int],
        max_out_degree: int,
    ) -> None:
        """Exact normalized-text matches only — never semantic similarity."""
        by_text: dict[str, list[_GeneratedRequirement]] = {}
        for requirement in requirements:
            by_text.setdefault(_normalize(requirement.text), []).append(requirement)
        for group in by_text.values():
            if len(group) < 2:
                continue
            ordered = sorted(group, key=lambda r: r.requirement_id)
            source = ordered[0]
            for target in ordered[1:]:
                self._add_edge(
                    source.requirement_id,
                    target.requirement_id,
                    RelationshipType.DUPLICATES,
                    f"'{source.requirement_id}' and '{target.requirement_id}' have "
                    f"identical normalized text.",
                    edges,
                    out_degree,
                    max_out_degree,
                )

    def _detect_keyword_relationships(
        self,
        requirements: tuple[_GeneratedRequirement, ...],
        keywords: tuple[str, ...],
        relationship_type: RelationshipType,
        edges: dict[str, RequirementRelationship],
        out_degree: dict[str, int],
        max_out_degree: int,
    ) -> None:
        """A requirement naming a governed keyword that also embeds another's text verbatim."""
        normalized = {req.requirement_id: _normalize(req.text) for req in requirements}
        for source in requirements:
            source_text = normalized[source.requirement_id]
            if not any(keyword in source_text for keyword in keywords):
                continue
            for target in requirements:
                if target.requirement_id == source.requirement_id:
                    continue
                target_text = normalized[target.requirement_id]
                if len(target_text) < _MIN_SUBSTRING_MATCH_LENGTH:
                    continue
                if target_text not in source_text:
                    continue
                self._add_edge(
                    source.requirement_id,
                    target.requirement_id,
                    relationship_type,
                    f"'{source.requirement_id}' names a {relationship_type.value} keyword "
                    f"and embeds '{target.requirement_id}'s text verbatim.",
                    edges,
                    out_degree,
                    max_out_degree,
                )

    @staticmethod
    def _add_edge(
        source_id: str,
        target_id: str,
        relationship_type: RelationshipType,
        rationale: str,
        edges: dict[str, RequirementRelationship],
        out_degree: dict[str, int],
        max_out_degree: int,
    ) -> None:
        """Add one edge, respecting the governed per-requirement out-degree bound."""
        if out_degree.get(source_id, 0) >= max_out_degree:
            return
        relationship_id = _relationship_id(source_id, target_id, relationship_type)
        if relationship_id in edges:
            return
        edges[relationship_id] = RequirementRelationship(
            relationship_id=relationship_id,
            source_requirement_id=source_id,
            target_requirement_id=target_id,
            relationship_type=relationship_type,
            rationale=rationale,
        )
        out_degree[source_id] = out_degree.get(source_id, 0) + 1

    # -- 3. observations (derived from enhanced requirements + the graph only) ----------

    def _generate_observations(
        self,
        *,
        enhancement_id: RequirementEnhancementId,
        requirements: tuple[_GeneratedRequirement, ...],
        graph: RelationshipGraph,
    ) -> tuple[RequirementObservation, ...]:
        """Emit observations strictly from *requirements* and *graph* (Recommendation 3)."""
        rules = self._catalog.enabled_rules()
        enabled_categories = set(self._policy.observation_rules.enabled_categories)
        max_per_requirement = self._policy.observation_rules.max_observations_per_requirement

        observations: list[RequirementObservation] = []
        per_requirement_count: dict[str, int] = {}
        ordinal = 0

        def emit(
            mechanism: EnhancementMechanism,
            category: ObservationCategory,
            severity: EnhancementSeverity,
            subjects: tuple[str, ...],
            message: str,
        ) -> None:
            nonlocal ordinal
            if not self._rule_active(rules, mechanism) or category not in enabled_categories:
                return
            if len(subjects) == 1:
                count = per_requirement_count.get(subjects[0], 0)
                if count >= max_per_requirement:
                    return
                per_requirement_count[subjects[0]] = count + 1
            observations.append(
                RequirementObservation(
                    observation_id=RequirementObservationId.for_ordinal(
                        str(enhancement_id), ordinal
                    ),
                    category=category,
                    severity=severity,
                    subject_requirement_ids=subjects,
                    message=message,
                )
            )
            ordinal += 1

        source_ids = {edge.source_requirement_id for edge in graph.relationships}
        target_ids = {edge.target_requirement_id for edge in graph.relationships}
        touched_ids = source_ids | target_ids

        # ER-OBS-001 — isolated requirement: no edges at all.
        for requirement in requirements:
            if requirement.requirement_id not in touched_ids:
                emit(
                    EnhancementMechanism.ISOLATED_REQUIREMENT,
                    ObservationCategory.DEPENDENCY,
                    EnhancementSeverity.INFO,
                    (requirement.requirement_id,),
                    f"'{requirement.requirement_id}' has no relationship to any other requirement.",
                )

        # ER-OBS-002 — orphan requirement: only ever a target, never a source.
        for requirement in requirements:
            req_id = requirement.requirement_id
            if req_id in target_ids and req_id not in source_ids:
                emit(
                    EnhancementMechanism.ORPHAN_REQUIREMENT,
                    ObservationCategory.TRACEABILITY,
                    EnhancementSeverity.INFO,
                    (req_id,),
                    f"'{req_id}' is referenced by other requirements but references none itself.",
                )

        # ER-OBS-003 — one observation per DUPLICATES edge already in the graph.
        for edge in graph.relationships:
            if edge.relationship_type != RelationshipType.DUPLICATES:
                continue
            emit(
                EnhancementMechanism.DUPLICATE_REQUIREMENT_OBSERVATION,
                ObservationCategory.DUPLICATION,
                EnhancementSeverity.WARNING,
                (edge.source_requirement_id, edge.target_requirement_id),
                f"'{edge.source_requirement_id}' and '{edge.target_requirement_id}' are "
                f"recorded as duplicates.",
            )

        # ER-OBS-004 — disconnected graph: more than one connected component.
        components = self._connected_components(graph)
        if len(components) > 1:
            largest = max(components, key=len)
            disconnected = tuple(
                sorted(
                    node
                    for component in components
                    if component is not largest
                    for node in component
                )
            )
            if disconnected:
                emit(
                    EnhancementMechanism.DISCONNECTED_GRAPH,
                    ObservationCategory.CONSISTENCY,
                    EnhancementSeverity.WARNING,
                    disconnected,
                    f"The relationship graph has {len(components)} disconnected "
                    f"component(s); {len(disconnected)} requirement(s) are outside the "
                    f"largest one.",
                )

        # ER-OBS-005 — missing dependency: keyword present, nothing resolved.
        normalized = {req.requirement_id: _normalize(req.text) for req in requirements}
        for requirement in requirements:
            req_id = requirement.requirement_id
            text = normalized[req_id]
            if not any(keyword in text for keyword in _DEPENDENCY_KEYWORDS):
                continue
            has_depends_on_edge = any(
                edge.source_requirement_id == req_id
                and edge.relationship_type == RelationshipType.DEPENDS_ON
                for edge in graph.relationships
            )
            if has_depends_on_edge:
                continue
            emit(
                EnhancementMechanism.MISSING_DEPENDENCY,
                ObservationCategory.DEPENDENCY,
                EnhancementSeverity.WARNING,
                (req_id,),
                f"'{req_id}' names a dependency keyword but no dependency could be "
                f"deterministically resolved.",
            )

        # ER-OBS-006 — relationship inconsistency: a cycle in the DEPENDS_ON subgraph.
        cycle = self._find_depends_on_cycle(graph)
        if cycle:
            emit(
                EnhancementMechanism.RELATIONSHIP_INCONSISTENCY,
                ObservationCategory.CONSISTENCY,
                EnhancementSeverity.CRITICAL,
                cycle,
                f"A circular DEPENDS_ON relationship exists among {', '.join(cycle)}.",
            )

        return tuple(observations)

    @staticmethod
    def _connected_components(graph: RelationshipGraph) -> list[frozenset[str]]:
        """Deterministic undirected connected components over every edge (BFS, sorted)."""
        adjacency: dict[str, set[str]] = {node: set() for node in graph.requirement_ids}
        for edge in graph.relationships:
            adjacency[edge.source_requirement_id].add(edge.target_requirement_id)
            adjacency[edge.target_requirement_id].add(edge.source_requirement_id)

        visited: set[str] = set()
        components: list[frozenset[str]] = []
        for node in sorted(graph.requirement_ids):
            if node in visited:
                continue
            component: set[str] = set()
            queue = [node]
            while queue:
                current = queue.pop(0)
                if current in component:
                    continue
                component.add(current)
                queue.extend(sorted(adjacency[current] - component))
            visited |= component
            components.append(frozenset(component))
        return components

    @staticmethod
    def _find_depends_on_cycle(graph: RelationshipGraph) -> tuple[str, ...]:
        """Deterministic DFS cycle detection over DEPENDS_ON edges only."""
        adjacency: dict[str, list[str]] = {node: [] for node in graph.requirement_ids}
        for edge in graph.relationships:
            if edge.relationship_type == RelationshipType.DEPENDS_ON:
                adjacency[edge.source_requirement_id].append(edge.target_requirement_id)
        for node_list in adjacency.values():
            node_list.sort()

        visiting: set[str] = set()
        visited: set[str] = set()
        path: list[str] = []

        def dfs(node: str) -> tuple[str, ...]:
            visiting.add(node)
            path.append(node)
            for neighbor in adjacency[node]:
                if neighbor in visiting:
                    cycle_start = path.index(neighbor)
                    return tuple(sorted(path[cycle_start:]))
                if neighbor not in visited:
                    found = dfs(neighbor)
                    if found:
                        return found
            visiting.discard(node)
            visited.add(node)
            path.pop()
            return ()

        for node in sorted(graph.requirement_ids):
            if node not in visited:
                found = dfs(node)
                if found:
                    return found
        return ()

    # -- 4. findings (surfaced observations, by reference only) -------------------------

    @staticmethod
    def _surface_findings(
        observations: tuple[RequirementObservation, ...],
    ) -> tuple[EnhancementFinding, ...]:
        """One finding per WARNING/CRITICAL observation — INFO stays observation-only."""
        surfaced = (EnhancementSeverity.WARNING, EnhancementSeverity.CRITICAL)
        findings: list[EnhancementFinding] = []
        for observation in observations:
            if observation.severity not in surfaced:
                continue
            findings.append(
                EnhancementFinding(
                    finding_id=f"ef-{observation.observation_id}",
                    observation_id=observation.observation_id,
                    category=observation.category,
                    severity=observation.severity,
                    message=observation.message,
                )
            )
        return tuple(findings)

    # -- assemble enhanced requirements (references only, Recommendation 2) -------------

    @staticmethod
    def _assemble_enhanced_requirements(
        *,
        enhancement_id: RequirementEnhancementId,
        requirements: tuple[_GeneratedRequirement, ...],
        attributes_by_id: dict[str, tuple[EnhancementAttribute, ...]],
        graph: RelationshipGraph,
        observations: tuple[RequirementObservation, ...],
    ) -> tuple[EnhancedRequirement, ...]:
        """Construct each EnhancedRequirement once its references are all resolvable."""
        relationship_ids_by_requirement: dict[str, list[str]] = {
            req.requirement_id: [] for req in requirements
        }
        for edge in graph.relationships:
            relationship_ids_by_requirement[edge.source_requirement_id].append(edge.relationship_id)
            relationship_ids_by_requirement[edge.target_requirement_id].append(edge.relationship_id)

        observation_ids_by_requirement: dict[str, list[str]] = {
            req.requirement_id: [] for req in requirements
        }
        for observation in observations:
            for subject in observation.subject_requirement_ids:
                if subject in observation_ids_by_requirement:
                    observation_ids_by_requirement[subject].append(str(observation.observation_id))

        enhanced: list[EnhancedRequirement] = []
        for requirement in requirements:
            req_id = requirement.requirement_id
            enhanced.append(
                EnhancedRequirement(
                    enhanced_requirement_id=EnhancedRequirementId.for_requirement(
                        str(enhancement_id), req_id
                    ),
                    requirement_id=req_id,
                    attributes=attributes_by_id.get(req_id, ()),
                    relationship_ids=tuple(sorted(set(relationship_ids_by_requirement[req_id]))),
                    observation_ids=tuple(sorted(set(observation_ids_by_requirement[req_id]))),
                )
            )
        return tuple(enhanced)

    # -- 5. metrics -----------------------------------------------------------------------

    @staticmethod
    def _compute_metrics(
        generated: tuple[_GeneratedRequirement, ...],
        enhanced_requirements: tuple[EnhancedRequirement, ...],
        graph: RelationshipGraph,
        observations: tuple[RequirementObservation, ...],
    ) -> EnhancementMetrics:
        """Deterministic numeric roll-ups — recorded, never derived elsewhere."""
        total_generated = len(generated)
        total_enhanced = len(enhanced_requirements)
        return EnhancementMetrics(
            enrichment_coverage=(total_enhanced / total_generated) if total_generated else 0.0,
            relationship_density=(
                (len(graph.relationships) / total_enhanced) if total_enhanced else 0.0
            ),
            observation_rate=(len(observations) / total_enhanced) if total_enhanced else 0.0,
        )

    # -- 6. summary -----------------------------------------------------------------------

    def _build_summary(
        self,
        *,
        enhanced_requirements: tuple[EnhancedRequirement, ...],
        graph: RelationshipGraph,
        observations: tuple[RequirementObservation, ...],
        findings: tuple[EnhancementFinding, ...],
    ) -> EnhancementSummary:
        """The deterministic headline for this run."""
        category_counts: dict[ObservationCategory, int] = {}
        for observation in observations:
            category = ObservationCategory(observation.category)
            category_counts[category] = category_counts.get(category, 0) + 1
        distribution = tuple(
            ObservationCategoryCount(category=category, count=category_counts[category])
            for category in ObservationCategory
            if category_counts.get(category, 0) > 0
        )
        headline = (
            f"{len(enhanced_requirements)} requirement(s) enhanced, "
            f"{len(graph.relationships)} relationship(s), "
            f"{len(observations)} observation(s), "
            f"{len(findings)} finding(s)."
        )
        return EnhancementSummary(
            policy_id=self._policy.policy_id,
            policy_version=self._policy.policy_version,
            total_requirements_enhanced=len(enhanced_requirements),
            total_relationships=len(graph.relationships),
            total_observations=len(observations),
            total_findings=len(findings),
            observation_distribution=distribution,
            headline=headline,
        )

    # -- provenance -------------------------------------------------------------------------

    @staticmethod
    def _consumed_inputs(
        engineering_context: EngineeringContext, analysis_result: AnalysisResult
    ) -> tuple[EnhancementInputReference, ...]:
        """Record the identity and contract version of each consumed input (provenance)."""
        return (
            EnhancementInputReference(
                source=EnhancementInputSource.ENGINEERING_CONTEXT,
                input_id=str(engineering_context.context_id),
                input_version=str(engineering_context.orchestration.context_model_version),
            ),
            EnhancementInputReference(
                source=EnhancementInputSource.ANALYSIS_RESULT,
                input_id=analysis_result.analysis_id,
                input_version=analysis_result.reasoning_contract_version,
            ),
        )

    # -- empty result (enrichment disabled, or nothing was generated) ---------------------

    def _empty_result(
        self,
        *,
        enhancement_id: RequirementEnhancementId,
        graph_id: RelationshipGraphId,
        analysis_result: AnalysisResult,
        engineering_context: EngineeringContext,
        started_at: datetime,
        completed_at: datetime,
    ) -> RequirementEnhancementResult:
        """A well-defined, empty-but-valid result: nothing to enhance, or policy-disabled."""
        summary = EnhancementSummary(
            policy_id=self._policy.policy_id,
            policy_version=self._policy.policy_version,
            total_requirements_enhanced=0,
            total_relationships=0,
            total_observations=0,
            total_findings=0,
            headline="Nothing was enhanced (no generated requirements, or enrichment disabled).",
        )
        metrics = EnhancementMetrics(
            enrichment_coverage=0.0, relationship_density=0.0, observation_rate=0.0
        )
        return RequirementEnhancementResult(
            result_id=RequirementEnhancementResultId.for_enhancement(str(enhancement_id)),
            analysis_id=analysis_result.analysis_id,
            execution_id=analysis_result.execution_id,
            relationship_graph=RelationshipGraph(graph_id=graph_id),
            summary=summary,
            metrics=metrics,
            consumed_inputs=self._consumed_inputs(engineering_context, analysis_result),
            policy_id=self._policy.policy_id,
            policy_version=self._policy.policy_version,
            framework_version=ENHANCEMENT_FRAMEWORK_VERSION,
            started_at=started_at,
            completed_at=completed_at,
        )

    def _rule_active(self, rules: tuple[Any, ...], mechanism: EnhancementMechanism) -> bool:
        """Whether *mechanism* is active: catalogue-enabled AND policy-switch-enabled.

        Mirrors how the deterministic Quality Governance rule evaluator resolves a
        mandatory rule's governing toggle from the policy at evaluation time
        (ADR-0017 §D25) — the engine reads the switch the rule names, the rule never
        reads the policy itself.
        """
        for rule in rules:
            if rule.mechanism != mechanism:
                continue
            # ``Schema`` validates with ``use_enum_values=True`` (shared/contracts/base.py),
            # so ``rule.capability_switch`` is already the plain string value here.
            return bool(getattr(self._policy.capability_switches, rule.capability_switch))
        return False
