"""Behavioural and architecture tests for DeterministicRequirementEnhancementEngine (CAP-081B).

Covers enrichment, relationship construction, observation generation, findings,
metrics, summary, ``PlatformContext`` integration, containment, and determinism
(Stage 9). The engine is exercised against real ``EngineeringContext`` /
``AnalysisResult`` objects produced by the golden pipeline fixture, with the response
body replaced by hand-crafted requirement text so every mechanism's outcome is
predictable and verifiable.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from requirement_intelligence.analysis.analysis_models import AnalysisResult
from requirement_intelligence.enhancement.engine import (
    DeterministicRequirementEnhancementEngine,
    RequirementExtractionError,
    _GeneratedRequirement,
    _relationship_id,
)
from requirement_intelligence.enhancement.identity.enhancement_identity import (
    RelationshipGraphId,
    RequirementEnhancementId,
)
from requirement_intelligence.enhancement.models.enums import (
    EnhancementSeverity,
    ObservationCategory,
    RelationshipType,
)
from requirement_intelligence.enhancement.models.relationships import (
    RelationshipGraph,
    RequirementRelationship,
)
from requirement_intelligence.enhancement.policy import default_enhancement_policy
from requirement_intelligence.enhancement.rules import default_enhancement_rule_catalog
from requirement_intelligence.models.enums import SourceCategory
from requirement_intelligence.platform.platform_context import PlatformContext
from tests.productization.conftest import _run_golden_pipeline

_REPO_ROOT = Path(__file__).resolve().parents[2]
_ENHANCEMENT_PKG = _REPO_ROOT / "requirement_intelligence" / "enhancement"
_FIXED_CLOCK = lambda: datetime(2026, 1, 1, tzinfo=UTC)  # noqa: E731


@pytest.fixture(scope="module")
def golden_pipeline(tmp_path_factory: pytest.TempPathFactory) -> Any:
    return _run_golden_pipeline(tmp_path_factory.mktemp("golden-enhancement"))


def _with_requirements(pipeline: Any, body: dict[str, list[str]]) -> AnalysisResult:
    """Return an AnalysisResult carrying *body* as its strict-JSON response text."""
    text = json.dumps(body)
    new_llm_response = pipeline.analysis_result.llm_response.model_copy(
        update={"generated_text": text}
    )
    return pipeline.analysis_result.model_copy(update={"llm_response": new_llm_response})


def _engine(*, policy=None, catalog=None, clock=None) -> DeterministicRequirementEnhancementEngine:
    return DeterministicRequirementEnhancementEngine(
        policy=policy or default_enhancement_policy(),
        rule_catalog=catalog or default_enhancement_rule_catalog(),
        clock=clock,
    )


# ===========================================================================
# Extraction
# ===========================================================================


@pytest.mark.unit
class TestExtraction:
    def test_extracts_requirements_in_domain_and_position_order(self, golden_pipeline: Any) -> None:
        analysis_result = _with_requirements(
            golden_pipeline,
            {
                "functional_requirements": ["Alpha.", "Beta."],
                "security_requirements": ["Gamma."],
                "quality_requirements": [],
            },
        )
        result = _engine().enhance(golden_pipeline.engineering_context, analysis_result)
        ids = [req.requirement_id for req in result.enhanced_requirements]
        assert ids == ["functional-001", "functional-002", "security-001"]

    def test_blank_and_non_string_entries_are_skipped(self, golden_pipeline: Any) -> None:
        analysis_result = _with_requirements(
            golden_pipeline,
            {"functional_requirements": ["Alpha.", "  ", "", "Beta."]},
        )
        result = _engine().enhance(golden_pipeline.engineering_context, analysis_result)
        assert len(result.enhanced_requirements) == 2

    def test_no_requirements_produces_a_well_defined_empty_result(
        self, golden_pipeline: Any
    ) -> None:
        analysis_result = _with_requirements(golden_pipeline, {})
        result = _engine().enhance(golden_pipeline.engineering_context, analysis_result)
        assert result.enhanced_requirements == ()
        assert result.relationship_graph.relationships == ()
        assert result.observations == ()
        assert result.metrics.enrichment_coverage == 0.0

    def test_malformed_json_body_raises_extraction_error(self, golden_pipeline: Any) -> None:
        new_llm_response = golden_pipeline.analysis_result.llm_response.model_copy(
            update={"generated_text": "not json"}
        )
        bad = golden_pipeline.analysis_result.model_copy(update={"llm_response": new_llm_response})
        with pytest.raises(RequirementExtractionError):
            _engine().enhance(golden_pipeline.engineering_context, bad)

    def test_non_list_requirement_field_raises_extraction_error(self, golden_pipeline: Any) -> None:
        new_llm_response = golden_pipeline.analysis_result.llm_response.model_copy(
            update={"generated_text": json.dumps({"functional_requirements": "not a list"})}
        )
        bad = golden_pipeline.analysis_result.model_copy(update={"llm_response": new_llm_response})
        with pytest.raises(RequirementExtractionError):
            _engine().enhance(golden_pipeline.engineering_context, bad)


# ===========================================================================
# Enrichment
# ===========================================================================


@pytest.mark.unit
class TestEnrichment:
    def test_enhanced_requirement_ids_are_deterministic(self, golden_pipeline: Any) -> None:
        analysis_result = _with_requirements(
            golden_pipeline, {"functional_requirements": ["Alpha."]}
        )
        r1 = _engine().enhance(golden_pipeline.engineering_context, analysis_result)
        r2 = _engine().enhance(golden_pipeline.engineering_context, analysis_result)
        assert (
            r1.enhanced_requirements[0].enhanced_requirement_id
            == r2.enhanced_requirements[0].enhanced_requirement_id
        )

    def test_provenance_attribute_records_domain_and_position(self, golden_pipeline: Any) -> None:
        analysis_result = _with_requirements(
            golden_pipeline, {"security_requirements": ["First.", "Second."]}
        )
        result = _engine().enhance(golden_pipeline.engineering_context, analysis_result)
        second = result.enhanced_requirements[1]
        provenance = {a.key: a.value for a in second.attributes}["provenance"]
        assert provenance == "security:1"

    def test_traceability_attribute_records_analysis_and_execution_id(
        self, golden_pipeline: Any
    ) -> None:
        analysis_result = _with_requirements(
            golden_pipeline, {"functional_requirements": ["Alpha."]}
        )
        result = _engine().enhance(golden_pipeline.engineering_context, analysis_result)
        traceability = {a.key: a.value for a in result.enhanced_requirements[0].attributes}[
            "traceability"
        ]
        assert traceability == f"{analysis_result.analysis_id}:{analysis_result.execution_id}"

    def test_attribute_vocabulary_restricts_which_attributes_attach(
        self, golden_pipeline: Any
    ) -> None:
        policy = default_enhancement_policy().model_copy(
            update={
                "enrichment_rules": default_enhancement_policy().enrichment_rules.model_copy(
                    update={"attribute_key_vocabulary": ("provenance",)}
                )
            }
        )
        analysis_result = _with_requirements(
            golden_pipeline, {"functional_requirements": ["Alpha."]}
        )
        result = _engine(policy=policy).enhance(
            golden_pipeline.engineering_context, analysis_result
        )
        keys = {a.key for a in result.enhanced_requirements[0].attributes}
        assert keys == {"provenance"}

    def test_max_attributes_per_requirement_is_respected(self, golden_pipeline: Any) -> None:
        base = default_enhancement_policy()
        policy = base.model_copy(
            update={
                "enrichment_rules": base.enrichment_rules.model_copy(
                    update={"max_attributes_per_requirement": 1}
                )
            }
        )
        analysis_result = _with_requirements(
            golden_pipeline, {"functional_requirements": ["Alpha."]}
        )
        result = _engine(policy=policy).enhance(
            golden_pipeline.engineering_context, analysis_result
        )
        assert len(result.enhanced_requirements[0].attributes) == 1

    def test_enrichment_disabled_produces_empty_result(self, golden_pipeline: Any) -> None:
        base = default_enhancement_policy()
        policy = base.model_copy(
            update={
                "capability_switches": base.capability_switches.model_copy(
                    update={"enable_enrichment": False}
                )
            }
        )
        analysis_result = _with_requirements(
            golden_pipeline, {"functional_requirements": ["Alpha.", "Beta."]}
        )
        result = _engine(policy=policy).enhance(
            golden_pipeline.engineering_context, analysis_result
        )
        assert result.enhanced_requirements == ()
        assert result.summary.headline.startswith("Nothing was enhanced")

    def test_enrichment_coverage_is_complete_for_a_typical_run(self, golden_pipeline: Any) -> None:
        analysis_result = _with_requirements(
            golden_pipeline, {"functional_requirements": ["Alpha.", "Beta.", "Gamma."]}
        )
        result = _engine().enhance(golden_pipeline.engineering_context, analysis_result)
        assert result.metrics.enrichment_coverage == 1.0

    def test_requirement_id_naming_convention(self, golden_pipeline: Any) -> None:
        analysis_result = _with_requirements(golden_pipeline, {"quality_requirements": ["Alpha."]})
        result = _engine().enhance(golden_pipeline.engineering_context, analysis_result)
        assert result.enhanced_requirements[0].requirement_id == "quality-001"


# ===========================================================================
# Relationships
# ===========================================================================


@pytest.mark.unit
class TestRelationships:
    def test_exact_duplicate_text_produces_a_duplicates_edge(self, golden_pipeline: Any) -> None:
        analysis_result = _with_requirements(
            golden_pipeline,
            {"functional_requirements": ["Same requirement text.", "Same requirement text."]},
        )
        result = _engine().enhance(golden_pipeline.engineering_context, analysis_result)
        assert len(result.relationship_graph.relationships) == 1
        edge = result.relationship_graph.relationships[0]
        assert edge.relationship_type == RelationshipType.DUPLICATES
        assert edge.source_requirement_id == "functional-001"
        assert edge.target_requirement_id == "functional-002"

    def test_duplicate_detection_normalizes_case_and_whitespace(self, golden_pipeline: Any) -> None:
        analysis_result = _with_requirements(
            golden_pipeline,
            {"functional_requirements": ["  Same   Text.  ", "same text."]},
        )
        result = _engine().enhance(golden_pipeline.engineering_context, analysis_result)
        assert len(result.relationship_graph.relationships) == 1

    def test_merely_similar_text_is_not_a_duplicate(self, golden_pipeline: Any) -> None:
        analysis_result = _with_requirements(
            golden_pipeline,
            {
                "functional_requirements": [
                    "The system must log in users.",
                    "The system must log out users.",
                ]
            },
        )
        result = _engine().enhance(golden_pipeline.engineering_context, analysis_result)
        assert result.relationship_graph.relationships == ()

    def test_dependency_keyword_and_substring_produces_depends_on(
        self, golden_pipeline: Any
    ) -> None:
        analysis_result = _with_requirements(
            golden_pipeline,
            {
                "functional_requirements": [
                    "Base widget must render.",
                    "Extended widget depends on Base widget must render. for layout.",
                ]
            },
        )
        result = _engine().enhance(golden_pipeline.engineering_context, analysis_result)
        edges = result.relationship_graph.relationships
        assert len(edges) == 1
        assert edges[0].relationship_type == RelationshipType.DEPENDS_ON
        assert edges[0].source_requirement_id == "functional-002"
        assert edges[0].target_requirement_id == "functional-001"

    def test_refinement_keyword_and_substring_produces_refines(self, golden_pipeline: Any) -> None:
        analysis_result = _with_requirements(
            golden_pipeline,
            {
                "functional_requirements": [
                    "Base widget must render.",
                    "This refines Base widget must render. with more detail.",
                ]
            },
        )
        result = _engine().enhance(golden_pipeline.engineering_context, analysis_result)
        edges = result.relationship_graph.relationships
        assert len(edges) == 1
        assert edges[0].relationship_type == RelationshipType.REFINES

    def test_parent_child_keyword_and_substring_produces_derived_from(
        self, golden_pipeline: Any
    ) -> None:
        analysis_result = _with_requirements(
            golden_pipeline,
            {
                "functional_requirements": [
                    "Base widget must render.",
                    "This is a child of Base widget must render. in the hierarchy.",
                ]
            },
        )
        result = _engine().enhance(golden_pipeline.engineering_context, analysis_result)
        edges = result.relationship_graph.relationships
        assert len(edges) == 1
        assert edges[0].relationship_type == RelationshipType.DERIVED_FROM

    def test_relationship_id_is_a_pure_function_of_source_target_type(self) -> None:
        a = _relationship_id("req-1", "req-2", RelationshipType.DEPENDS_ON)
        b = _relationship_id("req-1", "req-2", RelationshipType.DEPENDS_ON)
        c = _relationship_id("req-1", "req-2", RelationshipType.REFINES)
        d = _relationship_id("req-2", "req-1", RelationshipType.DEPENDS_ON)
        assert a == b
        assert a != c
        assert a != d

    def test_max_relationships_per_requirement_bounds_out_degree(
        self, golden_pipeline: Any
    ) -> None:
        base = default_enhancement_policy()
        policy = base.model_copy(
            update={
                "relationship_rules": base.relationship_rules.model_copy(
                    update={"max_relationships_per_requirement": 1}
                )
            }
        )
        analysis_result = _with_requirements(
            golden_pipeline,
            {
                "functional_requirements": [
                    "Alpha component ready.",
                    "Beta component ready.",
                    "Combined depends on Alpha component ready. and depends on "
                    "Beta component ready. both.",
                ]
            },
        )
        result = _engine(policy=policy).enhance(
            golden_pipeline.engineering_context, analysis_result
        )
        out_edges = [
            e
            for e in result.relationship_graph.relationships
            if e.source_requirement_id == "functional-003"
        ]
        assert len(out_edges) == 1

    def test_disabling_a_relationship_type_suppresses_it(self, golden_pipeline: Any) -> None:
        base = default_enhancement_policy()
        policy = base.model_copy(
            update={
                "relationship_rules": base.relationship_rules.model_copy(
                    update={
                        "enabled_relationship_types": tuple(
                            t for t in RelationshipType if t != RelationshipType.DEPENDS_ON
                        )
                    }
                )
            }
        )
        analysis_result = _with_requirements(
            golden_pipeline,
            {
                "functional_requirements": [
                    "Base widget must render.",
                    "Extended widget depends on Base widget must render. for layout.",
                ]
            },
        )
        result = _engine(policy=policy).enhance(
            golden_pipeline.engineering_context, analysis_result
        )
        assert result.relationship_graph.relationships == ()

    def test_relationship_detection_disabled_leaves_nodes_but_no_edges(
        self, golden_pipeline: Any
    ) -> None:
        base = default_enhancement_policy()
        policy = base.model_copy(
            update={
                "capability_switches": base.capability_switches.model_copy(
                    update={"enable_relationship_detection": False}
                )
            }
        )
        analysis_result = _with_requirements(
            golden_pipeline,
            {"functional_requirements": ["Same text.", "Same text."]},
        )
        result = _engine(policy=policy).enhance(
            golden_pipeline.engineering_context, analysis_result
        )
        assert len(result.relationship_graph.requirement_ids) == 2
        assert result.relationship_graph.relationships == ()

    def test_no_self_relationships(self, golden_pipeline: Any) -> None:
        analysis_result = _with_requirements(
            golden_pipeline,
            {"functional_requirements": ["Repeats itself. Repeats itself. depends on itself."]},
        )
        result = _engine().enhance(golden_pipeline.engineering_context, analysis_result)
        for edge in result.relationship_graph.relationships:
            assert edge.source_requirement_id != edge.target_requirement_id

    def test_every_edge_has_a_non_empty_rationale(self, golden_pipeline: Any) -> None:
        analysis_result = _with_requirements(
            golden_pipeline,
            {"functional_requirements": ["Same text.", "Same text."]},
        )
        result = _engine().enhance(golden_pipeline.engineering_context, analysis_result)
        for edge in result.relationship_graph.relationships:
            assert edge.rationale.strip()

    def test_graph_round_trips(self, golden_pipeline: Any) -> None:
        analysis_result = _with_requirements(
            golden_pipeline,
            {"functional_requirements": ["Same text.", "Same text."]},
        )
        result = _engine().enhance(golden_pipeline.engineering_context, analysis_result)
        dumped = result.relationship_graph.model_dump(mode="json", by_alias=True)
        assert RelationshipGraph.model_validate(dumped) == result.relationship_graph

    def test_graph_is_deterministic_across_two_runs(self, golden_pipeline: Any) -> None:
        analysis_result = _with_requirements(
            golden_pipeline,
            {"functional_requirements": ["Same text.", "Same text.", "Different one."]},
        )
        engine = _engine(clock=_FIXED_CLOCK)
        r1 = engine.enhance(golden_pipeline.engineering_context, analysis_result)
        r2 = engine.enhance(golden_pipeline.engineering_context, analysis_result)
        assert r1.relationship_graph == r2.relationship_graph


# ===========================================================================
# Observations
# ===========================================================================


@pytest.mark.unit
class TestObservations:
    def test_isolated_requirement_observed(self, golden_pipeline: Any) -> None:
        analysis_result = _with_requirements(
            golden_pipeline,
            {"functional_requirements": ["Alpha unrelated.", "Beta unconnected."]},
        )
        result = _engine().enhance(golden_pipeline.engineering_context, analysis_result)
        isolated = [
            o
            for o in result.observations
            if o.category == ObservationCategory.DEPENDENCY and "no relationship" in o.message
        ]
        assert {o.subject_requirement_ids for o in isolated} == {
            ("functional-001",),
            ("functional-002",),
        }

    def test_orphan_requirement_observed(self, golden_pipeline: Any) -> None:
        analysis_result = _with_requirements(
            golden_pipeline,
            {
                "functional_requirements": [
                    "Base widget must render.",
                    "Extended widget depends on Base widget must render. for layout.",
                ]
            },
        )
        result = _engine().enhance(golden_pipeline.engineering_context, analysis_result)
        orphan = [
            o for o in result.observations if "is referenced by other requirements" in o.message
        ]
        assert len(orphan) == 1
        assert orphan[0].subject_requirement_ids == ("functional-001",)

    def test_duplicate_requirement_observation_per_edge(self, golden_pipeline: Any) -> None:
        analysis_result = _with_requirements(
            golden_pipeline,
            {"functional_requirements": ["Same text.", "Same text."]},
        )
        result = _engine().enhance(golden_pipeline.engineering_context, analysis_result)
        duplicates = [
            o for o in result.observations if o.category == ObservationCategory.DUPLICATION
        ]
        assert len(duplicates) == 1
        assert duplicates[0].severity == EnhancementSeverity.WARNING
        assert set(duplicates[0].subject_requirement_ids) == {"functional-001", "functional-002"}

    def test_disconnected_graph_observed_when_multiple_components(
        self, golden_pipeline: Any
    ) -> None:
        analysis_result = _with_requirements(
            golden_pipeline,
            {"functional_requirements": ["Alpha unrelated.", "Beta unconnected."]},
        )
        result = _engine().enhance(golden_pipeline.engineering_context, analysis_result)
        disconnected = [
            o for o in result.observations if o.category == ObservationCategory.CONSISTENCY
        ]
        assert len(disconnected) == 1
        assert disconnected[0].severity == EnhancementSeverity.WARNING

    def test_no_disconnected_graph_when_fully_connected(self, golden_pipeline: Any) -> None:
        analysis_result = _with_requirements(
            golden_pipeline,
            {"functional_requirements": ["Same text.", "Same text."]},
        )
        result = _engine().enhance(golden_pipeline.engineering_context, analysis_result)
        assert not any(o.category == ObservationCategory.CONSISTENCY for o in result.observations)

    def test_missing_dependency_observed_when_keyword_unresolved(
        self, golden_pipeline: Any
    ) -> None:
        analysis_result = _with_requirements(
            golden_pipeline,
            {
                "functional_requirements": [
                    "Alpha requires something external not listed here.",
                    "Beta widget unrelated content.",
                ]
            },
        )
        result = _engine().enhance(golden_pipeline.engineering_context, analysis_result)
        missing = [
            o
            for o in result.observations
            if o.category == ObservationCategory.DEPENDENCY and "dependency could be" in o.message
        ]
        assert len(missing) == 1
        assert missing[0].subject_requirement_ids == ("functional-001",)

    def test_no_missing_dependency_once_resolved(self, golden_pipeline: Any) -> None:
        analysis_result = _with_requirements(
            golden_pipeline,
            {
                "functional_requirements": [
                    "Base widget must render.",
                    "Extended widget depends on Base widget must render. for layout.",
                ]
            },
        )
        result = _engine().enhance(golden_pipeline.engineering_context, analysis_result)
        assert not any(
            "dependency could be" in o.message and "functional-002" in o.subject_requirement_ids
            for o in result.observations
        )

    def test_relationship_inconsistency_observed_for_a_cycle(self) -> None:
        engine = _engine()
        req_a = _GeneratedRequirement("a", SourceCategory.FUNCTIONAL, "text a", 0)
        req_b = _GeneratedRequirement("b", SourceCategory.FUNCTIONAL, "text b", 1)
        graph = RelationshipGraph(
            graph_id=RelationshipGraphId.for_enhancement("re-test"),
            requirement_ids=("a", "b"),
            relationships=(
                RequirementRelationship(
                    relationship_id="r1",
                    source_requirement_id="a",
                    target_requirement_id="b",
                    relationship_type=RelationshipType.DEPENDS_ON,
                    rationale="test",
                ),
                RequirementRelationship(
                    relationship_id="r2",
                    source_requirement_id="b",
                    target_requirement_id="a",
                    relationship_type=RelationshipType.DEPENDS_ON,
                    rationale="test",
                ),
            ),
        )
        observations = engine._generate_observations(
            enhancement_id=RequirementEnhancementId.for_run("an-1", "ex-1"),
            requirements=(req_a, req_b),
            graph=graph,
        )
        cycle_observations = [
            o
            for o in observations
            if o.category == ObservationCategory.CONSISTENCY
            and o.severity == EnhancementSeverity.CRITICAL
        ]
        assert len(cycle_observations) == 1
        assert set(cycle_observations[0].subject_requirement_ids) == {"a", "b"}

    def test_cycle_detection_is_deterministic(self) -> None:
        engine = _engine()
        graph = RelationshipGraph(
            graph_id=RelationshipGraphId.for_enhancement("re-test"),
            requirement_ids=("a", "b"),
            relationships=(
                RequirementRelationship(
                    relationship_id="r1",
                    source_requirement_id="a",
                    target_requirement_id="b",
                    relationship_type=RelationshipType.DEPENDS_ON,
                    rationale="test",
                ),
                RequirementRelationship(
                    relationship_id="r2",
                    source_requirement_id="b",
                    target_requirement_id="a",
                    relationship_type=RelationshipType.DEPENDS_ON,
                    rationale="test",
                ),
            ),
        )
        assert engine._find_depends_on_cycle(graph) == engine._find_depends_on_cycle(graph)

    def test_observation_generation_disabled_yields_none(self, golden_pipeline: Any) -> None:
        base = default_enhancement_policy()
        policy = base.model_copy(
            update={
                "capability_switches": base.capability_switches.model_copy(
                    update={"enable_observation_generation": False}
                )
            }
        )
        analysis_result = _with_requirements(
            golden_pipeline,
            {"functional_requirements": ["Alpha unrelated.", "Beta unconnected."]},
        )
        result = _engine(policy=policy).enhance(
            golden_pipeline.engineering_context, analysis_result
        )
        assert result.observations == ()
        assert result.findings == ()

    def test_enabled_categories_restricts_observation_output(self, golden_pipeline: Any) -> None:
        base = default_enhancement_policy()
        policy = base.model_copy(
            update={
                "observation_rules": base.observation_rules.model_copy(
                    update={"enabled_categories": (ObservationCategory.DUPLICATION,)}
                )
            }
        )
        analysis_result = _with_requirements(
            golden_pipeline,
            {"functional_requirements": ["Same text.", "Same text.", "Alpha unrelated."]},
        )
        result = _engine(policy=policy).enhance(
            golden_pipeline.engineering_context, analysis_result
        )
        categories = {o.category for o in result.observations}
        assert categories == {ObservationCategory.DUPLICATION}

    def test_observation_ids_are_unique(self, golden_pipeline: Any) -> None:
        analysis_result = _with_requirements(
            golden_pipeline,
            {"functional_requirements": ["Alpha.", "Beta.", "Alpha.", "Gamma unrelated."]},
        )
        result = _engine().enhance(golden_pipeline.engineering_context, analysis_result)
        ids = [o.observation_id for o in result.observations]
        assert len(ids) == len(set(ids))

    def test_max_observations_per_requirement_is_respected(self, golden_pipeline: Any) -> None:
        base = default_enhancement_policy()
        policy = base.model_copy(
            update={
                "observation_rules": base.observation_rules.model_copy(
                    update={"max_observations_per_requirement": 1}
                )
            }
        )
        # This single, unconnected requirement triggers BOTH isolated (no edges) and
        # missing-dependency (keyword present, unresolved) — two single-subject
        # observations for the same requirement; the bound keeps only the first.
        analysis_result = _with_requirements(
            golden_pipeline,
            {"functional_requirements": ["Alpha requires something not listed."]},
        )
        result = _engine(policy=policy).enhance(
            golden_pipeline.engineering_context, analysis_result
        )
        subjects = [
            o for o in result.observations if o.subject_requirement_ids == ("functional-001",)
        ]
        assert len(subjects) == 1

    def test_observation_round_trips(self, golden_pipeline: Any) -> None:
        from requirement_intelligence.enhancement.models.observations import RequirementObservation

        analysis_result = _with_requirements(
            golden_pipeline, {"functional_requirements": ["Alpha unrelated."]}
        )
        result = _engine().enhance(golden_pipeline.engineering_context, analysis_result)
        observation = result.observations[0]
        dumped = observation.model_dump(mode="json", by_alias=True)
        assert RequirementObservation.model_validate(dumped) == observation

    def test_observations_are_deterministic_across_two_runs(self, golden_pipeline: Any) -> None:
        analysis_result = _with_requirements(
            golden_pipeline,
            {"functional_requirements": ["Alpha.", "Beta unrelated.", "Alpha."]},
        )
        engine = _engine(clock=_FIXED_CLOCK)
        r1 = engine.enhance(golden_pipeline.engineering_context, analysis_result)
        r2 = engine.enhance(golden_pipeline.engineering_context, analysis_result)
        assert r1.observations == r2.observations


# ===========================================================================
# Findings
# ===========================================================================


@pytest.mark.unit
class TestFindings:
    def test_info_observations_produce_no_finding(self, golden_pipeline: Any) -> None:
        analysis_result = _with_requirements(
            golden_pipeline,
            {
                "functional_requirements": [
                    "Base widget must render.",
                    "Extended widget depends on Base widget must render. for layout.",
                ]
            },
        )
        result = _engine().enhance(golden_pipeline.engineering_context, analysis_result)
        # Only the orphan (INFO) observation is produced here — no finding.
        assert result.findings == ()

    def test_warning_observation_produces_a_finding(self, golden_pipeline: Any) -> None:
        analysis_result = _with_requirements(
            golden_pipeline, {"functional_requirements": ["Same text.", "Same text."]}
        )
        result = _engine().enhance(golden_pipeline.engineering_context, analysis_result)
        assert len(result.findings) == 1

    def test_finding_id_is_a_function_of_observation_id(self, golden_pipeline: Any) -> None:
        analysis_result = _with_requirements(
            golden_pipeline, {"functional_requirements": ["Same text.", "Same text."]}
        )
        result = _engine().enhance(golden_pipeline.engineering_context, analysis_result)
        finding = result.findings[0]
        assert finding.finding_id == f"ef-{finding.observation_id}"

    def test_finding_has_no_subject_requirement_ids_field(self, golden_pipeline: Any) -> None:
        analysis_result = _with_requirements(
            golden_pipeline, {"functional_requirements": ["Same text.", "Same text."]}
        )
        result = _engine().enhance(golden_pipeline.engineering_context, analysis_result)
        finding = result.findings[0]
        assert not hasattr(finding, "subject_requirement_ids")

    def test_finding_severity_and_category_match_the_source_observation(
        self, golden_pipeline: Any
    ) -> None:
        analysis_result = _with_requirements(
            golden_pipeline, {"functional_requirements": ["Same text.", "Same text."]}
        )
        result = _engine().enhance(golden_pipeline.engineering_context, analysis_result)
        observation = next(
            o for o in result.observations if o.observation_id == result.findings[0].observation_id
        )
        assert result.findings[0].severity == observation.severity
        assert result.findings[0].category == observation.category

    def test_findings_count_matches_surfaced_observations(self, golden_pipeline: Any) -> None:
        analysis_result = _with_requirements(
            golden_pipeline,
            {"functional_requirements": ["Alpha.", "Beta unrelated.", "Alpha."]},
        )
        result = _engine().enhance(golden_pipeline.engineering_context, analysis_result)
        surfaced = [
            o
            for o in result.observations
            if o.severity in (EnhancementSeverity.WARNING, EnhancementSeverity.CRITICAL)
        ]
        assert len(result.findings) == len(surfaced)

    def test_findings_are_deterministic_across_two_runs(self, golden_pipeline: Any) -> None:
        analysis_result = _with_requirements(
            golden_pipeline, {"functional_requirements": ["Same text.", "Same text."]}
        )
        engine = _engine(clock=_FIXED_CLOCK)
        r1 = engine.enhance(golden_pipeline.engineering_context, analysis_result)
        r2 = engine.enhance(golden_pipeline.engineering_context, analysis_result)
        assert r1.findings == r2.findings


# ===========================================================================
# Metrics & summary
# ===========================================================================


@pytest.mark.unit
class TestMetricsAndSummary:
    def test_relationship_density_computed_correctly(self, golden_pipeline: Any) -> None:
        analysis_result = _with_requirements(
            golden_pipeline, {"functional_requirements": ["Same text.", "Same text."]}
        )
        result = _engine().enhance(golden_pipeline.engineering_context, analysis_result)
        assert result.metrics.relationship_density == 1 / 2

    def test_observation_rate_computed_correctly(self, golden_pipeline: Any) -> None:
        analysis_result = _with_requirements(
            golden_pipeline, {"functional_requirements": ["Alpha unrelated."]}
        )
        result = _engine().enhance(golden_pipeline.engineering_context, analysis_result)
        assert result.metrics.observation_rate == len(result.observations) / 1

    def test_metrics_all_zero_for_empty_result(self, golden_pipeline: Any) -> None:
        analysis_result = _with_requirements(golden_pipeline, {})
        result = _engine().enhance(golden_pipeline.engineering_context, analysis_result)
        assert result.metrics.enrichment_coverage == 0.0
        assert result.metrics.relationship_density == 0.0
        assert result.metrics.observation_rate == 0.0

    def test_summary_counts_match_actual_content(self, golden_pipeline: Any) -> None:
        analysis_result = _with_requirements(
            golden_pipeline, {"functional_requirements": ["Same text.", "Same text."]}
        )
        result = _engine().enhance(golden_pipeline.engineering_context, analysis_result)
        assert result.summary.total_requirements_enhanced == len(result.enhanced_requirements)
        assert result.summary.total_relationships == len(result.relationship_graph.relationships)
        assert result.summary.total_observations == len(result.observations)
        assert result.summary.total_findings == len(result.findings)

    def test_summary_distribution_excludes_zero_count_categories(
        self, golden_pipeline: Any
    ) -> None:
        analysis_result = _with_requirements(
            golden_pipeline, {"functional_requirements": ["Same text.", "Same text."]}
        )
        result = _engine().enhance(golden_pipeline.engineering_context, analysis_result)
        for entry in result.summary.observation_distribution:
            assert entry.count > 0

    def test_summary_distribution_follows_enum_order(self, golden_pipeline: Any) -> None:
        analysis_result = _with_requirements(
            golden_pipeline,
            {"functional_requirements": ["Same text.", "Same text.", "Alpha unrelated."]},
        )
        result = _engine().enhance(golden_pipeline.engineering_context, analysis_result)
        categories = [entry.category for entry in result.summary.observation_distribution]
        canonical = [c for c in ObservationCategory if c in categories]
        assert categories == canonical

    def test_summary_headline_reports_counts(self, golden_pipeline: Any) -> None:
        analysis_result = _with_requirements(
            golden_pipeline, {"functional_requirements": ["Same text.", "Same text."]}
        )
        result = _engine().enhance(golden_pipeline.engineering_context, analysis_result)
        assert "2 requirement(s) enhanced" in result.summary.headline

    def test_summary_policy_identity_matches_the_governing_policy(
        self, golden_pipeline: Any
    ) -> None:
        policy = default_enhancement_policy()
        analysis_result = _with_requirements(
            golden_pipeline, {"functional_requirements": ["Alpha."]}
        )
        result = _engine(policy=policy).enhance(
            golden_pipeline.engineering_context, analysis_result
        )
        assert result.summary.policy_id == policy.policy_id
        assert result.summary.policy_version == policy.policy_version

    def test_metrics_and_summary_are_deterministic(self, golden_pipeline: Any) -> None:
        analysis_result = _with_requirements(
            golden_pipeline, {"functional_requirements": ["Same text.", "Same text."]}
        )
        engine = _engine(clock=_FIXED_CLOCK)
        r1 = engine.enhance(golden_pipeline.engineering_context, analysis_result)
        r2 = engine.enhance(golden_pipeline.engineering_context, analysis_result)
        assert r1.metrics == r2.metrics
        assert r1.summary == r2.summary


# ===========================================================================
# PlatformContext integration
# ===========================================================================


@pytest.mark.unit
class TestPlatformContextIntegration:
    def test_service_uses_the_governed_default_catalog_and_policy(
        self, golden_pipeline: Any
    ) -> None:
        analysis_result = _with_requirements(
            golden_pipeline, {"functional_requirements": ["Same text.", "Same text."]}
        )
        service = PlatformContext().create_requirement_enhancement_service()
        result = service.enhance(golden_pipeline.engineering_context, analysis_result)
        # The default catalogue's duplicate-detection rule is active by default.
        assert len(result.relationship_graph.relationships) == 1

    def test_cli_obtains_the_service_only_from_platform_context(self) -> None:
        """CAP-081C wires the CLI to the service — but only via PlatformContext.

        The CLI's ``run_requirement_enhancement_phase`` is pure orchestration glue:
        it must construct nothing itself, obtaining the single service from the
        composition root, exactly mirroring Grounding/Quality Governance (ADR-0018 §D9).
        """
        cli_script = _REPO_ROOT / "scripts" / "run_requirement_analysis.py"
        source = cli_script.read_text(encoding="utf-8")
        assert "create_requirement_enhancement_service" in source
        assert "DeterministicRequirementEnhancementService(" not in source
        assert "DeterministicRequirementEnhancementEngine(" not in source


# ===========================================================================
# Architecture / containment
# ===========================================================================


@pytest.mark.unit
class TestEngineContainment:
    def test_engine_imports_no_peer_subsystem_implementation(self) -> None:
        source = (_ENHANCEMENT_PKG / "engine.py").read_text(encoding="utf-8")
        forbidden = (
            "GroundingService",
            "GroundingPipeline",
            "ResponseValidator",
            "CP1Service",
            "QualityGovernanceService",
            "QualityGovernancePipeline",
        )
        for line in source.splitlines():
            if line.strip().startswith(("import ", "from ")):
                for token in forbidden:
                    assert token not in line, f"engine.py must not import {token!r}"

    def test_engine_imports_no_execution_package(self) -> None:
        source = (_ENHANCEMENT_PKG / "engine.py").read_text(encoding="utf-8")
        assert "requirement_intelligence.execution" not in source

    def test_rules_package_is_self_contained(self) -> None:
        forbidden = (
            "requirement_intelligence.grounding",
            "requirement_intelligence.validation",
            "requirement_intelligence.cp1",
            "requirement_intelligence.quality_governance",
        )
        for path in (_ENHANCEMENT_PKG / "rules").rglob("*.py"):
            source = path.read_text(encoding="utf-8")
            for line in source.splitlines():
                if line.strip().startswith(("import ", "from ")):
                    for token in forbidden:
                        assert token not in line, f"{path.name} imports {token}"

    def test_engine_consumes_only_the_two_input_contracts_directly(self) -> None:
        source = (_ENHANCEMENT_PKG / "engine.py").read_text(encoding="utf-8")
        assert (
            "from requirement_intelligence.analysis.analysis_models import AnalysisResult" in source
        )
        assert (
            "from requirement_intelligence.context_orchestration.models.engineering_context import"
            in source
        )


# ===========================================================================
# Determinism
# ===========================================================================


@pytest.mark.unit
class TestDeterminism:
    def test_full_result_is_byte_identical_with_a_fixed_clock(self, golden_pipeline: Any) -> None:
        analysis_result = _with_requirements(
            golden_pipeline,
            {
                "functional_requirements": ["Same text.", "Same text.", "Alpha unrelated."],
                "security_requirements": [
                    "Base must hold.",
                    "Extended depends on Base must hold. now.",
                ],
            },
        )
        engine = _engine(clock=_FIXED_CLOCK)
        r1 = engine.enhance(golden_pipeline.engineering_context, analysis_result)
        r2 = engine.enhance(golden_pipeline.engineering_context, analysis_result)
        assert r1 == r2

    def test_two_fresh_engine_instances_agree(self, golden_pipeline: Any) -> None:
        analysis_result = _with_requirements(
            golden_pipeline, {"functional_requirements": ["Same text.", "Same text."]}
        )
        r1 = _engine(clock=_FIXED_CLOCK).enhance(
            golden_pipeline.engineering_context, analysis_result
        )
        r2 = _engine(clock=_FIXED_CLOCK).enhance(
            golden_pipeline.engineering_context, analysis_result
        )
        assert r1 == r2

    def test_result_id_and_enhancement_id_are_pure_functions_of_the_run(
        self, golden_pipeline: Any
    ) -> None:
        analysis_result = _with_requirements(
            golden_pipeline, {"functional_requirements": ["Alpha."]}
        )
        r1 = _engine().enhance(golden_pipeline.engineering_context, analysis_result)
        r2 = _engine().enhance(golden_pipeline.engineering_context, analysis_result)
        assert r1.result_id == r2.result_id

    def test_result_round_trips_through_json(self, golden_pipeline: Any) -> None:
        from requirement_intelligence.enhancement.models.result import (
            RequirementEnhancementResult,
        )

        analysis_result = _with_requirements(
            golden_pipeline, {"functional_requirements": ["Same text.", "Same text."]}
        )
        result = _engine().enhance(golden_pipeline.engineering_context, analysis_result)
        dumped = result.model_dump(mode="json", by_alias=True)
        assert RequirementEnhancementResult.model_validate(dumped) == result

    def test_no_randomness_across_many_repeated_runs(self, golden_pipeline: Any) -> None:
        analysis_result = _with_requirements(
            golden_pipeline,
            {"functional_requirements": ["Alpha.", "Beta unrelated.", "Alpha."]},
        )
        engine = _engine(clock=_FIXED_CLOCK)
        results = [
            engine.enhance(golden_pipeline.engineering_context, analysis_result) for _ in range(5)
        ]
        assert all(r == results[0] for r in results)
