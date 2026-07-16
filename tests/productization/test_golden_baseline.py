"""CAP-070 — Golden End-to-End Validation Baseline.

Productization tests that validate the complete Requirement Intelligence pipeline
against a deterministic golden dataset.  Every subsystem must execute; every
governed artifact must be generated; manifests must be internally consistent;
and two consecutive pipeline runs must produce identical findings and verdicts
(excluding run-specific provenance such as IDs and timestamps).

Test organisation
-----------------
Phase 3  — Pipeline execution  (every subsystem fires)
Phase 4  — Output verification (artifacts, manifest, cross-references, checksums)
Phase 5  — Determinism         (run twice; compare content, not provenance)
Phase 6  — Productization assertions (structured per-layer contract checks)
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from requirement_intelligence.models.enums import SourceCategory
from requirement_intelligence.normalization.models.normalization_result import NormalizationResult
from requirement_intelligence.validation.models.validation_enums import ValidationVerdict
from tests.productization.conftest import PipelineResult, _run_golden_pipeline
from tests.productization.fixtures.golden_dataset import (
    EXPECTED_CONSOLIDATED_COUNT,
    EXPECTED_FUNCTIONAL_REQUIREMENTS_COUNT,
    EXPECTED_MODULE,
    EXPECTED_QUALITY_REQUIREMENTS_COUNT,
    EXPECTED_RECOMMENDATIONS_COUNT,
    EXPECTED_RISKS_COUNT,
    EXPECTED_SECURITY_REQUIREMENTS_COUNT,
    GOLDEN_DATASET_VERSION,
    GOLDEN_SOURCE_ARTIFACTS,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_CORE_ARTIFACTS = frozenset(
    {
        "consolidated_artifact.json",
        "engineering_context.json",
        "prompt.txt",
        "llm_request.json",
    }
)
_RESULT_ARTIFACTS = frozenset(
    {
        "analysis_result.json",
        "raw_llm_response.json",
        "execution_summary.md",
        "baseline_metrics.md",
        "review.md",
    }
)
_VALIDATION_ARTIFACTS = frozenset({"validation_result.json", "validation_report.md"})
_CP1_ARTIFACTS = frozenset({"cp1_report.md"})
_GROUNDING_ARTIFACTS = frozenset(
    {"grounding_result.json", "grounding_report.md", "grounding_metrics.md"}
)
_QUALITY_GOVERNANCE_ARTIFACTS = frozenset(
    {
        "quality_governance_result.json",
        "quality_governance_report.md",
        "quality_governance_summary.md",
    }
)
_REQUIREMENT_ENHANCEMENT_ARTIFACTS = frozenset(
    {
        "requirement_enhancement_result.json",
        "requirement_enhancement_report.md",
        "requirement_enhancement_metrics.md",
    }
)
_RECOMMENDATION_ARTIFACTS = frozenset(
    {
        "recommendation_result.json",
        "recommendation_report.md",
        "recommendation_metrics.md",
    }
)
_CONTINUOUS_IMPROVEMENT_ARTIFACTS = frozenset(
    {
        "continuous_improvement_result.json",
        "continuous_improvement_report.md",
        "continuous_improvement_metrics.md",
    }
)
_KNOWLEDGE_GRAPH_ARTIFACTS = frozenset(
    {
        "knowledge_graph_result.json",
        "knowledge_graph_report.md",
        "knowledge_graph_metrics.md",
    }
)
_ORGANIZATIONAL_MEMORY_ARTIFACTS = frozenset(
    {
        "organizational_memory_result.json",
        "organizational_memory_report.md",
        "organizational_memory_metrics.md",
    }
)
_ALL_ARTIFACTS = (
    _CORE_ARTIFACTS
    | _RESULT_ARTIFACTS
    | _VALIDATION_ARTIFACTS
    | _CP1_ARTIFACTS
    | _GROUNDING_ARTIFACTS
    | _QUALITY_GOVERNANCE_ARTIFACTS
    | _REQUIREMENT_ENHANCEMENT_ARTIFACTS
    | _RECOMMENDATION_ARTIFACTS
    | _CONTINUOUS_IMPROVEMENT_ARTIFACTS
    | _KNOWLEDGE_GRAPH_ARTIFACTS
    | _ORGANIZATIONAL_MEMORY_ARTIFACTS
    | {"manifest.json"}
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _parsed_response_structure(result: PipelineResult) -> dict:
    """Extract the deterministic structure from the normalization result."""
    pr = result.normalization_result.parsed_response
    if pr is None:
        return {}
    normalized = pr.normalized_structure
    if normalized is None:
        return {}
    return dict(normalized)


# ===========================================================================
# PHASE 3 — Pipeline Execution
# ===========================================================================


class TestPhase3PipelineExecution:
    """Every subsystem in the governed pipeline must execute successfully."""

    @pytest.mark.productization
    def test_source_artifacts_loaded(self, golden_pipeline_result: PipelineResult) -> None:
        """All nine golden source artifacts are loaded."""
        assert golden_pipeline_result.source_artifact_count == len(GOLDEN_SOURCE_ARTIFACTS)
        assert golden_pipeline_result.source_artifact_count == 9

    @pytest.mark.productization
    def test_consolidation_produces_single_group(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """All artifacts share component='authentication' → one ConsolidatedArtifact."""
        assert len(golden_pipeline_result.consolidated_artifacts) == EXPECTED_CONSOLIDATED_COUNT

    @pytest.mark.productization
    def test_consolidated_artifact_module(self, golden_pipeline_result: PipelineResult) -> None:
        """The consolidated module name matches the golden dataset's component."""
        assert golden_pipeline_result.selected.module == EXPECTED_MODULE

    @pytest.mark.productization
    def test_consolidated_artifact_has_all_categories(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """The consolidated artifact carries functional, security, and quality artifacts."""
        selected = golden_pipeline_result.selected
        assert len(selected.functional_artifacts) > 0, "Expected functional artifacts"
        assert len(selected.security_artifacts) > 0, "Expected security artifacts"
        assert len(selected.quality_artifacts) > 0, "Expected quality artifacts"

    @pytest.mark.productization
    def test_consolidated_functional_count(self, golden_pipeline_result: PipelineResult) -> None:
        """Four JIRA functional artifacts (1 epic + 3 stories)."""
        assert len(golden_pipeline_result.selected.functional_artifacts) == 4

    @pytest.mark.productization
    def test_consolidated_security_count(self, golden_pipeline_result: PipelineResult) -> None:
        """Three OWASP ZAP security artifacts."""
        assert len(golden_pipeline_result.selected.security_artifacts) == 3

    @pytest.mark.productization
    def test_consolidated_quality_count(self, golden_pipeline_result: PipelineResult) -> None:
        """Two SonarQube quality artifacts."""
        assert len(golden_pipeline_result.selected.quality_artifacts) == 2

    @pytest.mark.productization
    def test_orchestrator_produced_an_engineering_context(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """EngineeringContextOrchestrator produced the context the prompt was built from."""
        assert golden_pipeline_result.engineering_context is not None

    @pytest.mark.productization
    def test_default_orchestration_policy_is_active(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """CAP-076D: the runtime executes DefaultOrchestrationPolicy."""
        orchestration = golden_pipeline_result.engineering_context.orchestration
        assert str(orchestration.policy_id) == "coverage"
        assert str(orchestration.policy_version) == "1.0.0"

    @pytest.mark.productization
    def test_context_draws_on_the_only_group_the_golden_dataset_produces(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """The golden dataset consolidates to one group, so one group contributes."""
        provenance = golden_pipeline_result.engineering_context.provenance
        assert provenance.contributing_group_count == 1
        assert provenance.contributing_consolidated_ids == (
            golden_pipeline_result.selected.consolidated_id,
        )

    @pytest.mark.productization
    def test_context_carries_every_artifact_of_the_contributing_group(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """Nothing is dropped: the whole group fits inside the policy's budget.

        Compared as multisets, not sequences — the active policy orders evidence by
        risk, so a positional comparison would test the ordering rule rather than
        the completeness claim this test makes. Ordering is tested separately.
        """
        selected = golden_pipeline_result.selected
        evidence = golden_pipeline_result.engineering_context.evidence
        assert sorted(a.source_record_id for a in evidence.functional_artifacts) == sorted(
            a.source_record_id for a in selected.functional_artifacts
        )
        assert sorted(a.source_record_id for a in evidence.security_artifacts) == sorted(
            a.source_record_id for a in selected.security_artifacts
        )
        assert sorted(a.source_record_id for a in evidence.quality_artifacts) == sorted(
            a.source_record_id for a in selected.quality_artifacts
        )

    @pytest.mark.productization
    def test_all_three_evidence_domains_reach_the_reasoner(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """The CAP-074B repair, asserted against the golden baseline."""
        coverage = golden_pipeline_result.engineering_context.coverage
        assert coverage.all_present_categories_represented is True
        assert coverage.rule_satisfied is True
        assert [str(c) for c in coverage.represented_categories] == [
            "functional",
            "security",
            "quality",
        ]

    @pytest.mark.productization
    def test_active_policy_orders_evidence_by_risk_then_record_id(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """The ordering rule is the one behaviour the golden dataset can isolate."""
        from requirement_intelligence.consolidation.consolidation_rules import artifact_risk

        rank = {"low": 0, "medium": 1, "high": 2, "critical": 3}
        security = golden_pipeline_result.engineering_context.evidence.security_artifacts
        keys = [(-rank[str(artifact_risk(a))], a.source_record_id) for a in security]
        assert keys == sorted(keys)

    @pytest.mark.productization
    def test_the_evidence_budget_did_not_bind_this_dataset(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """Nine artifacts sit far inside a 25-per-domain budget; nothing was truncated."""
        budget = golden_pipeline_result.engineering_context.evidence_budget
        assert budget.truncated is False
        assert budget.total_used == 9

    @pytest.mark.productization
    def test_analysis_result_exists(self, golden_pipeline_result: PipelineResult) -> None:
        """RequirementAnalysisService produced an AnalysisResult."""
        assert golden_pipeline_result.analysis_result is not None

    @pytest.mark.productization
    def test_analysis_result_has_llm_response(self, golden_pipeline_result: PipelineResult) -> None:
        """AnalysisResult carries the stub provider's LLMResponse."""
        assert golden_pipeline_result.analysis_result.llm_response is not None
        assert golden_pipeline_result.analysis_result.llm_response.generated_text != ""

    @pytest.mark.productization
    def test_normalization_result_exists(self, golden_pipeline_result: PipelineResult) -> None:
        """ResponseNormalizer produced a NormalizationResult."""
        assert isinstance(golden_pipeline_result.normalization_result, NormalizationResult)

    @pytest.mark.productization
    def test_normalization_produced_parsed_response(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """NormalizationResult carries a populated ParsedResponse."""
        assert golden_pipeline_result.normalization_result.parsed_response is not None

    @pytest.mark.productization
    def test_validation_result_exists(self, golden_pipeline_result: PipelineResult) -> None:
        """ResponseValidator produced a ValidationResult."""
        assert golden_pipeline_result.validation_result is not None

    @pytest.mark.productization
    def test_cp1_result_exists(self, golden_pipeline_result: PipelineResult) -> None:
        """CP1 Service produced a CP1Result (gate must be open for golden response)."""
        assert golden_pipeline_result.cp1_result is not None, (
            "CP1Result is None — the Validation → CP1 gate was closed. "
            f"Validation verdict: {golden_pipeline_result.validation_result.overall_verdict}"
        )

    @pytest.mark.productization
    def test_quality_governance_result_exists(self, golden_pipeline_result: PipelineResult) -> None:
        """Quality Governance ran after CP1 (CAP-080D) and produced a QualityGovernanceResult."""
        assert golden_pipeline_result.quality_governance_result is not None, (
            "QualityGovernanceResult is None — governance did not run despite CP1 completing."
        )

    @pytest.mark.productization
    def test_quality_governance_runs_strictly_after_cp1(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """The frozen order: governance only exists because all three peer results do.

        Governance consumes exactly GroundingResult + ValidationResult + CP1Result, and its
        recorded provenance names those three consumed inputs — never a prompt, an
        EngineeringContext, or a Gemini response.
        """
        governance = golden_pipeline_result.quality_governance_result
        assert golden_pipeline_result.grounding_result is not None
        assert golden_pipeline_result.validation_result is not None
        assert golden_pipeline_result.cp1_result is not None
        consumed = {str(ref.source) for ref in governance.consumed_inputs}
        assert consumed == {"grounding", "validation", "cp1"}
        # Governance completes after the CP1 result it consumed was produced.
        assert governance.started_at <= governance.completed_at

    @pytest.mark.productization
    def test_recommendation_result_exists(self, golden_pipeline_result: PipelineResult) -> None:
        """Recommendation ran after Quality Governance (CAP-082C) and produced a result."""
        assert golden_pipeline_result.recommendation_result is not None, (
            "RecommendationResult is None — recommendation did not run despite "
            "governance completing."
        )

    @pytest.mark.productization
    def test_recommendation_runs_strictly_after_quality_governance(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """The frozen order: recommendation only exists because all five peer results do.

        Recommendation consumes exactly RequirementEnhancementResult + GroundingResult +
        ValidationResult + CP1Result + QualityGovernanceResult, and its recorded
        provenance names those five consumed inputs.
        """
        recommendation = golden_pipeline_result.recommendation_result
        assert golden_pipeline_result.requirement_enhancement_result is not None
        assert golden_pipeline_result.grounding_result is not None
        assert golden_pipeline_result.validation_result is not None
        assert golden_pipeline_result.cp1_result is not None
        assert golden_pipeline_result.quality_governance_result is not None
        consumed = {str(ref.source) for ref in recommendation.consumed_inputs}
        assert consumed == {"enhancement", "grounding", "validation", "cp1", "quality_governance"}
        # Recommendation completes after the governance result it consumed was produced.
        assert recommendation.started_at <= recommendation.completed_at

    @pytest.mark.productization
    def test_recommendation_produces_the_golden_datasets_known_shape(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """A long-term regression guard: the golden dataset's fixed, deterministic shape.

        The golden dataset's single enhancement observation (a dependency gap on
        one requirement) deterministically produces exactly one recommendation in
        exactly one group. A change to this count is a genuine regression signal —
        either in Requirement Enhancement's observation generation or in the
        Recommendation engine's dispatch/policy — and must be re-baselined
        deliberately, never silently.
        """
        recommendation = golden_pipeline_result.recommendation_result
        assert recommendation.summary.total_recommendations == 1
        assert recommendation.summary.total_groups == 1
        rec = recommendation.recommendations[0]
        assert str(rec.recommendation_source) == "enhancement"
        assert str(rec.recommendation_type) == "clarify_requirement"
        assert str(rec.priority) == "medium"

    @pytest.mark.productization
    def test_continuous_improvement_result_exists(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """Continuous Improvement ran after Recommendation (CAP-083C) and produced a result."""
        assert golden_pipeline_result.continuous_improvement_result is not None, (
            "ContinuousImprovementResult is None — continuous improvement did not run "
            "despite recommendation completing."
        )

    @pytest.mark.productization
    def test_continuous_improvement_runs_strictly_after_recommendation(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """The frozen order: continuous improvement only exists once recommendation does.

        Continuous Improvement consumes exactly one ``HistoricalDatasetReference`` —
        never a Layer 1 peer result (Recommendation 1, ADR-0022) — minted from this
        run's own ``AnalysisResult`` (no real, multi-execution Historical Dataset
        implementation exists yet, ADR-0021 §Stage 6).
        """
        continuous_improvement = golden_pipeline_result.continuous_improvement_result
        assert golden_pipeline_result.recommendation_result is not None
        reference = continuous_improvement.historical_dataset
        assert reference.first_execution_id == golden_pipeline_result.analysis_result.execution_id
        assert reference.last_execution_id == golden_pipeline_result.analysis_result.execution_id
        # Continuous Improvement completes after the reference it consumed was minted.
        assert continuous_improvement.started_at <= continuous_improvement.completed_at

    @pytest.mark.productization
    def test_continuous_improvement_produces_the_golden_datasets_known_shape(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """A long-term regression guard: the golden dataset's fixed, deterministic shape.

        The reference this milestone mints spans exactly one execution
        (``execution_count=1``), and the governed default policy requires at least
        three recurring executions before it emits a finding and at least two data
        points before it emits a trend (ADR-0022 §D9). A single-execution reference
        can satisfy neither floor, so the golden dataset deterministically observes
        nothing — an empty, but genuine, ``ContinuousImprovementResult``. A change to
        this shape is a genuine regression signal and must be re-baselined
        deliberately, never silently.
        """
        continuous_improvement = golden_pipeline_result.continuous_improvement_result
        assert continuous_improvement.findings == ()
        assert continuous_improvement.trends == ()
        assert continuous_improvement.opportunities == ()
        assert continuous_improvement.summary.total_findings == 0
        assert continuous_improvement.summary.total_trends == 0
        assert continuous_improvement.summary.total_opportunities == 0

    @pytest.mark.productization
    def test_knowledge_graph_result_exists(self, golden_pipeline_result: PipelineResult) -> None:
        """Knowledge Graph ran after Continuous Improvement (CAP-084C) and produced a result."""
        assert golden_pipeline_result.knowledge_graph_result is not None, (
            "KnowledgeGraphResult is None — Knowledge Graph did not run despite "
            "continuous improvement completing."
        )

    @pytest.mark.productization
    def test_knowledge_graph_runs_strictly_after_continuous_improvement(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """The frozen order: Knowledge Graph only exists once continuous improvement does.

        Knowledge Graph consumes exactly one ``HistoricalDatasetReference`` — never
        a Layer 1 peer result, and never ``ContinuousImprovementResult``
        (Recommendation 1/9, ADR-0023) — minted from this run's own
        ``AnalysisResult`` via the same deterministic single-execution strategy
        CAP-083C introduced (no real, multi-execution Historical Dataset
        implementation exists yet, ADR-0021 §Stage 6).
        """
        knowledge_graph = golden_pipeline_result.knowledge_graph_result
        assert golden_pipeline_result.continuous_improvement_result is not None
        reference = knowledge_graph.historical_dataset
        assert reference.first_execution_id == golden_pipeline_result.analysis_result.execution_id
        assert reference.last_execution_id == golden_pipeline_result.analysis_result.execution_id
        # Knowledge Graph completes after the reference it consumed was minted.
        assert knowledge_graph.started_at <= knowledge_graph.completed_at

    @pytest.mark.productization
    def test_knowledge_graph_produces_the_golden_datasets_known_shape(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """A long-term regression guard: the golden dataset's structurally bounded shape.

        Unlike Continuous Improvement's single-execution reference (which can
        satisfy neither the recurrence nor trend floor, so the golden dataset
        always observes exactly zero of everything), Knowledge Graph's CAP-084B
        deterministic provider synthesizes a requirement, an execution, and a
        dataset node **unconditionally** from every reference — the base shape —
        plus up to four more node types (recommendation, finding, capability,
        document) **conditionally**, gated by a SHA-256 digest of the reference's
        own ``dataset_id`` (which embeds this run's randomly minted
        ``execution_id``, ADR-0021 §Stage 6 — no real Historical Dataset exists
        yet). That conditional presence is *reproducible for a fixed reference*
        (proven by ``test_knowledge_graph_execution_integration.py``'s
        same-input-same-output tests) but *legitimately varies* across two golden
        pipeline runs, each of which mints its own fresh, random reference. This
        test therefore asserts the invariant bounds and node/edge types that
        *are* stable for every possible execution-count-1 reference, never an
        exact count. A value outside these bounds is a genuine regression signal.

        Findings are *usually* empty at ``execution_count=1``, with exactly one
        documented exception: when both ``capability`` and ``document`` nodes
        are present for the same execution, ``EdgeProjector`` draws
        ``IMPLEMENTS`` (requirement → capability), ``USES`` (capability →
        document), and ``REFERENCES`` (document → requirement) — a genuine
        3-node directed cycle the deterministic, iterative cycle detector
        correctly reports as a single ``CYCLE`` finding. This is a real,
        reproducible structural property of the CAP-084B engine (not a defect
        introduced by this test), so the assertion below allows at most one
        finding, and only of that category — never a silent, unexplained one.
        """
        knowledge_graph = golden_pipeline_result.knowledge_graph_result
        node_types = {str(node.node_type) for node in knowledge_graph.nodes}
        assert {"execution", "requirement", "dataset"} <= node_types
        assert 3 <= len(knowledge_graph.nodes) <= 7
        assert 2 <= len(knowledge_graph.edges) <= 8
        # Every conditional node type (recommendation/finding/capability/document)
        # is always linked back to the requirement node by an edge the moment it
        # is present (EdgeProjector), so a single-execution reference can never
        # produce an isolated node or a broken lineage. A cycle is possible —
        # see the docstring above — but only the one documented shape.
        assert knowledge_graph.subgraphs and len(knowledge_graph.subgraphs) == 1
        assert len(knowledge_graph.observations) == 3
        assert len(knowledge_graph.findings) <= 1
        if knowledge_graph.findings:
            assert str(knowledge_graph.findings[0].category) == "cycle"
        assert knowledge_graph.summary.total_findings == len(knowledge_graph.findings)
        assert knowledge_graph.metrics.connected_component_count == 1

    @pytest.mark.productization
    def test_organizational_memory_result_exists(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """Organizational Memory ran after Knowledge Graph (CAP-085C) and produced a result."""
        assert golden_pipeline_result.organizational_memory_result is not None, (
            "OrganizationalMemoryResult is None — Organizational Memory did not run "
            "despite Continuous Improvement and Knowledge Graph completing."
        )

    @pytest.mark.productization
    def test_organizational_memory_runs_strictly_after_knowledge_graph(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """The frozen order: Organizational Memory only exists once both peers do.

        Organizational Memory consumes exactly the two already-completed Layer 2
        peer results — never a ``HistoricalDatasetReference`` (unlike its two
        peers, ADR-0025 §Stage 7/8's fan-in exception).
        """
        organizational_memory = golden_pipeline_result.organizational_memory_result
        assert golden_pipeline_result.continuous_improvement_result is not None
        assert golden_pipeline_result.knowledge_graph_result is not None
        assert organizational_memory.continuous_improvement_result_id == str(
            golden_pipeline_result.continuous_improvement_result.result_id
        )
        assert organizational_memory.knowledge_graph_result_id == str(
            golden_pipeline_result.knowledge_graph_result.result_id
        )
        assert organizational_memory.started_at <= organizational_memory.completed_at

    @pytest.mark.productization
    def test_organizational_memory_produces_the_golden_datasets_known_shape(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """A long-term regression guard: the golden dataset's structurally bounded shape.

        Continuous Improvement's single-execution reference always yields zero
        findings/trends/opportunities (see
        ``test_continuous_improvement_produces_no_findings_at_execution_count_one``
        above), so ``ExperienceCollector`` captures nothing from that side.
        Knowledge Graph's own golden shape is bounded but not exact (see
        ``test_knowledge_graph_produces_the_golden_datasets_known_shape``): exactly
        3 observations and exactly 1 subgraph unconditionally, plus 0 or 1 finding
        digest-gated on the reference. ``ExperienceCollector`` captures one
        Experience per Knowledge Graph observation/subgraph/finding, so this
        golden run captures 4 or 5 experiences. ``ExperienceClusterer`` groups by
        exact ``(source_layer, description)`` equality, and these descriptions are
        all structurally distinct, so no cluster ever reaches the governed
        ``minimum_experiences_for_lesson`` floor of 3 — this golden dataset
        therefore never promotes a lesson, best practice, or promotion record. A
        value outside these bounds is a genuine regression signal.
        """
        organizational_memory = golden_pipeline_result.organizational_memory_result
        assert 4 <= len(organizational_memory.experiences) <= 5
        assert organizational_memory.lessons == ()
        assert organizational_memory.best_practices == ()
        assert organizational_memory.promotions == ()
        assert len(organizational_memory.lifecycles) == len(organizational_memory.experiences)
        assert organizational_memory.summary.total_experiences == len(
            organizational_memory.experiences
        )
        assert organizational_memory.metrics.active_count == len(organizational_memory.lifecycles)

    @pytest.mark.productization
    def test_execution_package_written(self, golden_pipeline_result: PipelineResult) -> None:
        """ExecutionWriter completed without raising."""
        assert golden_pipeline_result.write_result is not None
        assert golden_pipeline_result.output_dir.is_dir()


# ===========================================================================
# PHASE 4 — Output Verification
# ===========================================================================


class TestPhase4OutputVerification:
    """Every governed artifact must be present, internally consistent, and checksummed."""

    # --- Artifact presence -------------------------------------------------

    @pytest.mark.productization
    def test_all_core_artifacts_present(self, golden_pipeline_result: PipelineResult) -> None:
        for name in _CORE_ARTIFACTS:
            path = golden_pipeline_result.output_dir / name
            assert path.exists(), f"Core artifact missing: {name}"
            assert path.stat().st_size > 0, f"Core artifact is empty: {name}"

    @pytest.mark.productization
    def test_all_result_artifacts_present(self, golden_pipeline_result: PipelineResult) -> None:
        for name in _RESULT_ARTIFACTS:
            path = golden_pipeline_result.output_dir / name
            assert path.exists(), f"Result artifact missing: {name}"
            assert path.stat().st_size > 0, f"Result artifact is empty: {name}"

    @pytest.mark.productization
    def test_validation_artifacts_present(self, golden_pipeline_result: PipelineResult) -> None:
        for name in _VALIDATION_ARTIFACTS:
            path = golden_pipeline_result.output_dir / name
            assert path.exists(), f"Validation artifact missing: {name}"
            assert path.stat().st_size > 0, f"Validation artifact is empty: {name}"

    @pytest.mark.productization
    def test_cp1_report_present(self, golden_pipeline_result: PipelineResult) -> None:
        path = golden_pipeline_result.output_dir / "cp1_report.md"
        assert path.exists(), "cp1_report.md missing"
        assert path.stat().st_size > 0, "cp1_report.md is empty"

    @pytest.mark.productization
    def test_grounding_artifacts_present(self, golden_pipeline_result: PipelineResult) -> None:
        """Grounding ran (CAP-077F.2), so all three grounding artifacts are written."""
        for name in _GROUNDING_ARTIFACTS:
            path = golden_pipeline_result.output_dir / name
            assert path.exists(), f"Grounding artifact missing: {name}"
            assert path.stat().st_size > 0, f"Grounding artifact is empty: {name}"

    @pytest.mark.productization
    def test_grounding_result_json_round_trips(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """grounding_result.json is a verbatim, round-trippable projection."""
        from requirement_intelligence.grounding import GroundingResult

        on_disk = _load_json(golden_pipeline_result.output_dir / "grounding_result.json")
        assert GroundingResult.model_validate(on_disk) == golden_pipeline_result.grounding_result

    @pytest.mark.productization
    def test_quality_governance_artifacts_present(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """Quality Governance ran (CAP-080D), so all three governance artifacts are written."""
        for name in _QUALITY_GOVERNANCE_ARTIFACTS:
            path = golden_pipeline_result.output_dir / name
            assert path.exists(), f"Quality Governance artifact missing: {name}"
            assert path.stat().st_size > 0, f"Quality Governance artifact is empty: {name}"

    @pytest.mark.productization
    def test_quality_governance_result_json_round_trips(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """quality_governance_result.json is a verbatim, round-trippable projection."""
        from requirement_intelligence.quality_governance import QualityGovernanceResult

        on_disk = _load_json(golden_pipeline_result.output_dir / "quality_governance_result.json")
        assert (
            QualityGovernanceResult.model_validate(on_disk)
            == golden_pipeline_result.quality_governance_result
        )

    @pytest.mark.productization
    def test_requirement_enhancement_artifacts_present(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """Requirement Enhancement ran (CAP-081C), so all three artifacts are written."""
        for name in _REQUIREMENT_ENHANCEMENT_ARTIFACTS:
            path = golden_pipeline_result.output_dir / name
            assert path.exists(), f"Requirement Enhancement artifact missing: {name}"
            assert path.stat().st_size > 0, f"Requirement Enhancement artifact is empty: {name}"

    @pytest.mark.productization
    def test_requirement_enhancement_result_json_round_trips(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """requirement_enhancement_result.json is a verbatim, round-trippable projection."""
        from requirement_intelligence.enhancement import RequirementEnhancementResult

        on_disk = _load_json(
            golden_pipeline_result.output_dir / "requirement_enhancement_result.json"
        )
        assert (
            RequirementEnhancementResult.model_validate(on_disk)
            == golden_pipeline_result.requirement_enhancement_result
        )

    @pytest.mark.productization
    def test_recommendation_artifacts_present(self, golden_pipeline_result: PipelineResult) -> None:
        """Recommendation ran (CAP-082C), so all three artifacts are written."""
        for name in _RECOMMENDATION_ARTIFACTS:
            path = golden_pipeline_result.output_dir / name
            assert path.exists(), f"Recommendation artifact missing: {name}"
            assert path.stat().st_size > 0, f"Recommendation artifact is empty: {name}"

    @pytest.mark.productization
    def test_recommendation_result_json_round_trips(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """recommendation_result.json is a verbatim, round-trippable projection."""
        from requirement_intelligence.recommendation import RecommendationResult

        on_disk = _load_json(golden_pipeline_result.output_dir / "recommendation_result.json")
        assert (
            RecommendationResult.model_validate(on_disk)
            == golden_pipeline_result.recommendation_result
        )

    @pytest.mark.productization
    def test_continuous_improvement_artifacts_present(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """Continuous Improvement ran (CAP-083C), so all three artifacts are written."""
        for name in _CONTINUOUS_IMPROVEMENT_ARTIFACTS:
            path = golden_pipeline_result.output_dir / name
            assert path.exists(), f"Continuous Improvement artifact missing: {name}"
            assert path.stat().st_size > 0, f"Continuous Improvement artifact is empty: {name}"

    @pytest.mark.productization
    def test_continuous_improvement_result_json_round_trips(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """continuous_improvement_result.json is a verbatim, round-trippable projection."""
        from requirement_intelligence.continuous_improvement.models import (
            ContinuousImprovementResult,
        )

        on_disk = _load_json(
            golden_pipeline_result.output_dir / "continuous_improvement_result.json"
        )
        assert (
            ContinuousImprovementResult.model_validate(on_disk)
            == golden_pipeline_result.continuous_improvement_result
        )

    @pytest.mark.productization
    def test_knowledge_graph_artifacts_present(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """Knowledge Graph ran (CAP-084C), so all three artifacts are written."""
        for name in _KNOWLEDGE_GRAPH_ARTIFACTS:
            path = golden_pipeline_result.output_dir / name
            assert path.exists(), f"Knowledge Graph artifact missing: {name}"
            assert path.stat().st_size > 0, f"Knowledge Graph artifact is empty: {name}"

    @pytest.mark.productization
    def test_knowledge_graph_result_json_round_trips(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """knowledge_graph_result.json is a verbatim, round-trippable projection."""
        from requirement_intelligence.knowledge_graph.models import KnowledgeGraphResult

        on_disk = _load_json(golden_pipeline_result.output_dir / "knowledge_graph_result.json")
        assert (
            KnowledgeGraphResult.model_validate(on_disk)
            == golden_pipeline_result.knowledge_graph_result
        )

    @pytest.mark.productization
    def test_organizational_memory_artifacts_present(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """Organizational Memory ran (CAP-085C), so all three artifacts are written."""
        for name in _ORGANIZATIONAL_MEMORY_ARTIFACTS:
            path = golden_pipeline_result.output_dir / name
            assert path.exists(), f"Organizational Memory artifact missing: {name}"
            assert path.stat().st_size > 0, f"Organizational Memory artifact is empty: {name}"

    @pytest.mark.productization
    def test_organizational_memory_result_json_round_trips(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """organizational_memory_result.json is a verbatim, round-trippable projection."""
        from requirement_intelligence.organizational_memory.models import (
            OrganizationalMemoryResult,
        )

        on_disk = _load_json(
            golden_pipeline_result.output_dir / "organizational_memory_result.json"
        )
        assert (
            OrganizationalMemoryResult.model_validate(on_disk)
            == golden_pipeline_result.organizational_memory_result
        )

    @pytest.mark.productization
    def test_manifest_present(self, golden_pipeline_result: PipelineResult) -> None:
        path = golden_pipeline_result.output_dir / "manifest.json"
        assert path.exists(), "manifest.json missing"
        assert path.stat().st_size > 0, "manifest.json is empty"

    # --- AnalysisResult verification ---------------------------------------

    @pytest.mark.productization
    def test_analysis_result_json_parseable(self, golden_pipeline_result: PipelineResult) -> None:
        data = _load_json(golden_pipeline_result.output_dir / "analysis_result.json")
        assert "analysisId" in data
        assert "executionId" in data
        assert "provider" in data
        assert "llmResponse" in data

    @pytest.mark.productization
    def test_raw_llm_response_json_parseable(self, golden_pipeline_result: PipelineResult) -> None:
        data = _load_json(golden_pipeline_result.output_dir / "raw_llm_response.json")
        assert "generatedText" in data or "generated_text" in data

    # --- EngineeringContext artifact verification --------------------------

    @pytest.mark.productization
    def test_engineering_context_artifact_records_identity_and_policy(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """engineering_context.json names the context and the rules that composed it."""
        data = _load_json(golden_pipeline_result.output_dir / "engineering_context.json")
        context = golden_pipeline_result.engineering_context
        assert data["contextId"] == str(context.context_id)
        assert data["orchestration"]["policyId"] == "coverage"
        assert data["orchestration"]["policyVersion"] == "1.0.0"
        assert data["orchestration"]["selectionStrategy"] == "coverage_guaranteed"
        assert data["orchestrationReason"] == context.orchestration_reason

    @pytest.mark.productization
    def test_engineering_context_artifact_records_evidence_counts(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """Evidence counts in the artifact match the nine golden source artifacts."""
        data = _load_json(golden_pipeline_result.output_dir / "engineering_context.json")
        counts = data["evidenceCounts"]
        assert counts == {"functional": 4, "security": 3, "quality": 2, "total": 9}
        assert data["provenance"]["sourceArtifactCount"] == 9

    @pytest.mark.productization
    def test_engineering_context_artifact_explains_every_contribution(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """Every contributing group carries a non-empty, documented inclusion reason."""
        data = _load_json(golden_pipeline_result.output_dir / "engineering_context.json")
        contributions = data["provenance"]["contributions"]
        assert contributions, "No contribution was recorded"
        for contribution in contributions:
            assert contribution["consolidatedId"]
            assert contribution["inclusionReason"].strip()
            assert contribution["consolidationReason"].strip()
            assert contribution["rank"] >= 1
            assert contribution["artifactCount"] == contribution["candidateArtifactCount"]

    @pytest.mark.productization
    def test_engineering_context_artifact_summarises_every_evidence_item(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """Each evidence artifact is traceable to its origin record."""
        data = _load_json(golden_pipeline_result.output_dir / "engineering_context.json")
        summary = data["evidenceSummary"]
        items = summary["functional"] + summary["security"] + summary["quality"]
        assert len(items) == data["evidenceCounts"]["total"]
        for item in items:
            assert item["sourceSystem"] and item["sourceRecordId"] and item["title"]

    # --- NormalizationResult verification ----------------------------------

    @pytest.mark.productization
    def test_parsed_response_has_required_keys(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """ParsedResponse normalized_structure carries all required JSON contract keys."""
        structure = _parsed_response_structure(golden_pipeline_result)
        for key in (
            "summary",
            "functional_requirements",
            "security_requirements",
            "quality_requirements",
            "risks",
            "recommendations",
        ):
            assert key in structure, f"ParsedResponse is missing key: {key}"

    @pytest.mark.productization
    def test_functional_requirements_count(self, golden_pipeline_result: PipelineResult) -> None:
        structure = _parsed_response_structure(golden_pipeline_result)
        assert len(structure["functional_requirements"]) == EXPECTED_FUNCTIONAL_REQUIREMENTS_COUNT

    @pytest.mark.productization
    def test_security_requirements_count(self, golden_pipeline_result: PipelineResult) -> None:
        structure = _parsed_response_structure(golden_pipeline_result)
        assert len(structure["security_requirements"]) == EXPECTED_SECURITY_REQUIREMENTS_COUNT

    @pytest.mark.productization
    def test_quality_requirements_count(self, golden_pipeline_result: PipelineResult) -> None:
        structure = _parsed_response_structure(golden_pipeline_result)
        assert len(structure["quality_requirements"]) == EXPECTED_QUALITY_REQUIREMENTS_COUNT

    @pytest.mark.productization
    def test_risks_count(self, golden_pipeline_result: PipelineResult) -> None:
        structure = _parsed_response_structure(golden_pipeline_result)
        assert len(structure["risks"]) == EXPECTED_RISKS_COUNT

    @pytest.mark.productization
    def test_recommendations_count(self, golden_pipeline_result: PipelineResult) -> None:
        structure = _parsed_response_structure(golden_pipeline_result)
        assert len(structure["recommendations"]) == EXPECTED_RECOMMENDATIONS_COUNT

    # --- ValidationResult verification -------------------------------------

    @pytest.mark.productization
    def test_validation_result_json_parseable(self, golden_pipeline_result: PipelineResult) -> None:
        data = _load_json(golden_pipeline_result.output_dir / "validation_result.json")
        assert "overallVerdict" in data
        assert "validationSummary" in data

    @pytest.mark.productization
    def test_validation_verdict_is_passing(self, golden_pipeline_result: PipelineResult) -> None:
        """Golden response must pass validation (prerequisite for CP1 gate opening)."""
        verdict = golden_pipeline_result.validation_result.overall_verdict
        assert verdict in (ValidationVerdict.PASSED, ValidationVerdict.PASSED_WITH_WARNINGS), (
            f"Expected PASSED or PASSED_WITH_WARNINGS; got {verdict}. "
            "The golden response did not satisfy the validation rules."
        )

    # --- CP1Result verification --------------------------------------------

    @pytest.mark.productization
    def test_cp1_verdict_is_pass(self, golden_pipeline_result: PipelineResult) -> None:
        """CP1-0001 must PASS: the golden response contains ≥1 requirement in all categories."""
        result = golden_pipeline_result.cp1_result
        assert result is not None
        verdict_value = str(getattr(result.overall_verdict, "value", result.overall_verdict))
        assert verdict_value.upper() == "PASS", (
            f"Expected CP1 verdict PASS; got {verdict_value}. "
            "CP1-0001 failed: the golden response must contain at least one requirement."
        )

    @pytest.mark.productization
    def test_cp1_no_fail_findings(self, golden_pipeline_result: PipelineResult) -> None:
        """No CP1 findings with FAIL contribution (golden response is engineering-ready)."""
        result = golden_pipeline_result.cp1_result
        assert result is not None
        fail_findings = [
            f
            for f in result.findings
            if str(getattr(f.verdict_contribution, "value", f.verdict_contribution)).upper()
            == "FAIL"
        ]
        assert len(fail_findings) == 0, (
            f"Found {len(fail_findings)} FAIL finding(s) in the golden CP1 result: "
            + str([f.criterion_id for f in fail_findings])
        )

    # --- Manifest verification ---------------------------------------------

    @pytest.mark.productization
    def test_manifest_schema_version(self, golden_pipeline_result: PipelineResult) -> None:
        manifest = _load_json(golden_pipeline_result.output_dir / "manifest.json")
        assert manifest["manifestSchemaVersion"] == "1.0.0"

    @pytest.mark.productization
    def test_manifest_platform_version(self, golden_pipeline_result: PipelineResult) -> None:
        manifest = _load_json(golden_pipeline_result.output_dir / "manifest.json")
        assert manifest["platformVersion"] == "1.0.0"

    @pytest.mark.productization
    def test_manifest_execution_mode(self, golden_pipeline_result: PipelineResult) -> None:
        manifest = _load_json(golden_pipeline_result.output_dir / "manifest.json")
        assert manifest["executionMode"] == "live"
        assert manifest["dryRun"] is False

    @pytest.mark.productization
    def test_manifest_cp1_executed(self, golden_pipeline_result: PipelineResult) -> None:
        manifest = _load_json(golden_pipeline_result.output_dir / "manifest.json")
        assert manifest.get("cp1Executed") is True
        assert manifest.get("cp1Verdict") is not None
        assert manifest.get("cp1Report") == "cp1_report.md"

    @pytest.mark.productization
    def test_manifest_references_quality_governance_artifacts_only(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """manifest.json indexes the governance artifacts; it never duplicates the verdict.

        Manifest purity (ADR-0017 §D31): the manifest owns package metadata and the
        artifact inventory only. The canonical ``QualityDecision`` is the sole runtime
        state and lives exclusively on ``QualityGovernanceResult`` / the artifact
        ``quality_governance_result.json`` — never re-surfaced as a manifest key.
        """
        manifest = _load_json(golden_pipeline_result.output_dir / "manifest.json")
        governance = golden_pipeline_result.quality_governance_result
        assert manifest.get("qualityGovernanceExecuted") is True
        assert manifest.get("qualityGovernanceReport") == "quality_governance_report.md"
        assert manifest.get("qualityGovernanceSummary") == "quality_governance_summary.md"
        assert "qualityGovernanceDecision" not in manifest
        assert "qualityGovernanceScore" not in manifest
        assert "qualityGovernanceDecisionVersion" not in manifest

        on_disk = _load_json(golden_pipeline_result.output_dir / "quality_governance_result.json")
        decision = governance.assessment.decision
        assert on_disk["assessment"]["decision"] == str(getattr(decision, "value", decision))

    @pytest.mark.productization
    def test_manifest_references_requirement_enhancement_artifacts_only(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """manifest.json indexes the enhancement artifacts; it never duplicates runtime state.

        Manifest purity (ADR-0017 §D31, applied here from the outset per ADR-0018
        §D8): the manifest owns package metadata and the artifact inventory only. The
        canonical enhanced requirements, relationship graph, observations, findings,
        metrics, and summary are the sole runtime state and live exclusively on
        ``RequirementEnhancementResult`` / the artifact
        ``requirement_enhancement_result.json`` — never re-surfaced as manifest keys.
        """
        manifest = _load_json(golden_pipeline_result.output_dir / "manifest.json")
        result = golden_pipeline_result.requirement_enhancement_result
        assert manifest.get("requirementEnhancementExecuted") is True
        assert manifest.get("requirementEnhancementReport") == "requirement_enhancement_report.md"
        assert manifest.get("requirementEnhancementMetrics") == "requirement_enhancement_metrics.md"
        for forbidden_key in (
            "requirementEnhancementCoverage",
            "requirementEnhancementSummary",
            "requirementEnhancementFindings",
            "requirementEnhancementRelationshipCount",
            "requirementEnhancementObservationCount",
        ):
            assert forbidden_key not in manifest

        on_disk = _load_json(
            golden_pipeline_result.output_dir / "requirement_enhancement_result.json"
        )
        assert on_disk["summary"]["totalRequirementsEnhanced"] == (
            result.summary.total_requirements_enhanced
        )

    @pytest.mark.productization
    def test_manifest_references_recommendation_artifacts_only(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """manifest.json indexes the recommendation artifacts; it never duplicates runtime state.

        Manifest purity (ADR-0017 §D31, applied here per ADR-0019 §D9/§D10): the
        manifest owns package metadata and the artifact inventory only. The canonical
        recommendations, groups, priorities, confidence, metrics, and summary are the
        sole runtime state and live exclusively on ``RecommendationResult`` / the
        artifact ``recommendation_result.json`` — never re-surfaced as manifest keys.
        """
        manifest = _load_json(golden_pipeline_result.output_dir / "manifest.json")
        result = golden_pipeline_result.recommendation_result
        assert manifest.get("recommendationExecuted") is True
        assert manifest.get("recommendationReport") == "recommendation_report.md"
        assert manifest.get("recommendationMetrics") == "recommendation_metrics.md"
        for forbidden_key in (
            "recommendationPriority",
            "recommendationCounts",
            "recommendationSummary",
            "recommendationDecisions",
            "recommendationGroups",
            "recommendationMetricsValues",
        ):
            assert forbidden_key not in manifest

        on_disk = _load_json(golden_pipeline_result.output_dir / "recommendation_result.json")
        assert on_disk["summary"]["totalRecommendations"] == result.summary.total_recommendations

    @pytest.mark.productization
    def test_manifest_checksums_the_recommendation_result(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """recommendation_result.json is checksummed by the same mechanism as every other."""
        manifest = _load_json(golden_pipeline_result.output_dir / "manifest.json")
        entries = {a["name"]: a for a in manifest["generatedArtifacts"]}
        entry = entries["recommendation_result.json"]
        path = golden_pipeline_result.output_dir / "recommendation_result.json"
        assert entry["sha256"] == _sha256(path)
        assert entry["bytes"] == path.stat().st_size

    @pytest.mark.productization
    def test_recommendation_report_contains_the_summary_headline(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """recommendation_report.md is a projection — it shows the result's own headline."""
        report = (golden_pipeline_result.output_dir / "recommendation_report.md").read_text(
            encoding="utf-8"
        )
        assert golden_pipeline_result.recommendation_result.summary.headline in report

    @pytest.mark.productization
    def test_recommendation_metrics_contains_the_recommendation_density(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """recommendation_metrics.md is a projection — it shows the result's own metrics."""
        metrics_md = (golden_pipeline_result.output_dir / "recommendation_metrics.md").read_text(
            encoding="utf-8"
        )
        density = golden_pipeline_result.recommendation_result.metrics.recommendation_density
        assert f"{density:.3f}" in metrics_md

    @pytest.mark.productization
    def test_execution_data_recommendation_result_matches_pipeline_result(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """The object transported into the Execution Package is the same one returned."""
        assert (
            golden_pipeline_result.execution_data.recommendation_result
            is golden_pipeline_result.recommendation_result
        )

    @pytest.mark.productization
    def test_manifest_references_continuous_improvement_artifacts_only(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """manifest.json indexes the continuous improvement artifacts; it never duplicates state.

        Manifest purity (ADR-0017 §D31, applied here per ADR-0022 §D10/§D11): the
        manifest owns package metadata and the artifact inventory only. The canonical
        findings, trends, opportunities, metrics, and summary are the sole runtime
        state and live exclusively on ``ContinuousImprovementResult`` / the artifact
        ``continuous_improvement_result.json`` — never re-surfaced as manifest keys.
        """
        manifest = _load_json(golden_pipeline_result.output_dir / "manifest.json")
        result = golden_pipeline_result.continuous_improvement_result
        assert manifest.get("continuousImprovementExecuted") is True
        assert manifest.get("continuousImprovementReport") == "continuous_improvement_report.md"
        assert manifest.get("continuousImprovementMetrics") == "continuous_improvement_metrics.md"
        for forbidden_key in (
            "continuousImprovementResult",
            "continuousImprovementSummary",
            "continuousImprovementFindings",
            "continuousImprovementTrends",
            "continuousImprovementOpportunities",
        ):
            assert forbidden_key not in manifest

        on_disk = _load_json(
            golden_pipeline_result.output_dir / "continuous_improvement_result.json"
        )
        assert on_disk["summary"]["totalFindings"] == result.summary.total_findings

    @pytest.mark.productization
    def test_manifest_checksums_the_continuous_improvement_result(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """continuous_improvement_result.json is checksummed like every other artifact."""
        manifest = _load_json(golden_pipeline_result.output_dir / "manifest.json")
        entries = {a["name"]: a for a in manifest["generatedArtifacts"]}
        entry = entries["continuous_improvement_result.json"]
        path = golden_pipeline_result.output_dir / "continuous_improvement_result.json"
        assert entry["sha256"] == _sha256(path)
        assert entry["bytes"] == path.stat().st_size

    @pytest.mark.productization
    def test_continuous_improvement_report_contains_the_summary_headline(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """continuous_improvement_report.md is a projection — it shows the result's own headline."""
        report = (golden_pipeline_result.output_dir / "continuous_improvement_report.md").read_text(
            encoding="utf-8"
        )
        assert golden_pipeline_result.continuous_improvement_result.summary.headline in report

    @pytest.mark.productization
    def test_continuous_improvement_metrics_contains_the_finding_density(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """continuous_improvement_metrics.md is a projection — it shows the result's own metrics."""
        metrics_md = (
            golden_pipeline_result.output_dir / "continuous_improvement_metrics.md"
        ).read_text(encoding="utf-8")
        density = golden_pipeline_result.continuous_improvement_result.metrics.finding_density
        assert f"{density:.3f}" in metrics_md

    @pytest.mark.productization
    def test_execution_data_continuous_improvement_result_matches_pipeline_result(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """The object transported into the Execution Package is the same one returned."""
        assert (
            golden_pipeline_result.execution_data.continuous_improvement_result
            is golden_pipeline_result.continuous_improvement_result
        )

    @pytest.mark.productization
    def test_manifest_references_knowledge_graph_artifacts_only(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """manifest.json indexes the Knowledge Graph artifacts; it never duplicates state.

        Manifest purity (ADR-0017 §D31, applied here per ADR-0023 §D11/§D12): the
        manifest owns package metadata and the artifact inventory only. The
        canonical nodes, edges, subgraphs, observations, findings, metrics, and
        summary are the sole runtime state and live exclusively on
        ``KnowledgeGraphResult`` / the artifact ``knowledge_graph_result.json`` —
        never re-surfaced as manifest keys.
        """
        manifest = _load_json(golden_pipeline_result.output_dir / "manifest.json")
        result = golden_pipeline_result.knowledge_graph_result
        assert manifest.get("knowledgeGraphExecuted") is True
        assert manifest.get("knowledgeGraphReport") == "knowledge_graph_report.md"
        assert manifest.get("knowledgeGraphMetrics") == "knowledge_graph_metrics.md"
        for forbidden_key in (
            "knowledgeGraphResult",
            "knowledgeGraphSummary",
            "knowledgeGraphNodes",
            "knowledgeGraphEdges",
            "knowledgeGraphFindings",
        ):
            assert forbidden_key not in manifest

        on_disk = _load_json(golden_pipeline_result.output_dir / "knowledge_graph_result.json")
        assert on_disk["summary"]["totalNodes"] == result.summary.total_nodes

    @pytest.mark.productization
    def test_manifest_references_organizational_memory_artifacts_only(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """manifest.json indexes the Organizational Memory artifacts; it never duplicates state.

        Manifest purity (ADR-0017 §D31, applied here per ADR-0027 §D18/§D19): the
        manifest owns package metadata and the artifact inventory only. The
        canonical experiences, lessons, best practices, promotions, lifecycles,
        metrics, and summary are the sole runtime state and live exclusively on
        ``OrganizationalMemoryResult`` / the artifact
        ``organizational_memory_result.json`` — never re-surfaced as manifest keys.
        """
        manifest = _load_json(golden_pipeline_result.output_dir / "manifest.json")
        result = golden_pipeline_result.organizational_memory_result
        assert manifest.get("organizationalMemoryExecuted") is True
        assert manifest.get("organizationalMemoryReport") == "organizational_memory_report.md"
        assert manifest.get("organizationalMemoryMetrics") == "organizational_memory_metrics.md"
        for forbidden_key in (
            "organizationalMemoryResult",
            "organizationalMemorySummary",
            "organizationalMemoryExperiences",
            "organizationalMemoryLessons",
            "organizationalMemoryBestPractices",
            "organizationalMemoryPromotions",
            "organizationalMemoryLifecycles",
        ):
            assert forbidden_key not in manifest

        on_disk = _load_json(
            golden_pipeline_result.output_dir / "organizational_memory_result.json"
        )
        assert on_disk["summary"]["totalExperiences"] == result.summary.total_experiences

    @pytest.mark.productization
    def test_manifest_checksums_the_organizational_memory_result(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """organizational_memory_result.json is checksummed like every other artifact."""
        manifest = _load_json(golden_pipeline_result.output_dir / "manifest.json")
        entries = {a["name"]: a for a in manifest["generatedArtifacts"]}
        entry = entries["organizational_memory_result.json"]
        path = golden_pipeline_result.output_dir / "organizational_memory_result.json"
        assert entry["sha256"] == _sha256(path)
        assert entry["bytes"] == path.stat().st_size

    @pytest.mark.productization
    def test_organizational_memory_report_contains_the_summary_headline(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """organizational_memory_report.md is a projection — it shows the result's own headline."""
        report = (golden_pipeline_result.output_dir / "organizational_memory_report.md").read_text(
            encoding="utf-8"
        )
        assert golden_pipeline_result.organizational_memory_result.summary.headline in report

    @pytest.mark.productization
    def test_organizational_memory_metrics_contains_the_experience_count(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """organizational_memory_metrics.md is a projection — it shows the result's own metrics."""
        metrics_md = (
            golden_pipeline_result.output_dir / "organizational_memory_metrics.md"
        ).read_text(encoding="utf-8")
        experience_count = (
            golden_pipeline_result.organizational_memory_result.metrics.experience_count
        )
        assert str(experience_count) in metrics_md

    @pytest.mark.productization
    def test_execution_data_organizational_memory_result_matches_pipeline_result(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """The object transported into the Execution Package is the same one returned."""
        assert (
            golden_pipeline_result.execution_data.organizational_memory_result
            is golden_pipeline_result.organizational_memory_result
        )

    @pytest.mark.productization
    def test_organizational_memory_artifacts_are_written_after_knowledge_graph_artifacts(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """Artifact write order mirrors the frozen pipeline order (Knowledge
        Graph, then Organizational Memory)."""
        names = [
            entry["name"]
            for entry in golden_pipeline_result.write_result.manifest["generatedArtifacts"]
        ]
        last_kg_index = max(
            index for index, name in enumerate(names) if name.startswith("knowledge_graph")
        )
        first_om_index = min(
            index for index, name in enumerate(names) if name.startswith("organizational_memory")
        )
        assert last_kg_index < first_om_index

    @pytest.mark.productization
    def test_organizational_memory_result_is_explainable_solely_from_the_result(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """Every experience/lesson/promotion/lifecycle the golden run produced traces
        to the result alone.

        No re-run of the engine, the service, or either consumed peer result is
        required — the explainability invariant ADR-0027 §D18/§D19 certifies.
        """
        result = golden_pipeline_result.organizational_memory_result
        known_experience_ids = {experience.experience_id for experience in result.experiences}
        known_subject_ids = (
            {str(i) for i in known_experience_ids}
            | {str(lesson.lesson_id) for lesson in result.lessons}
            | {str(bp.best_practice_id) for bp in result.best_practices}
        )
        for lesson in result.lessons:
            assert set(lesson.source_experience_ids) <= known_experience_ids
        for lifecycle in result.lifecycles:
            assert lifecycle.subject_id in known_subject_ids

    @pytest.mark.productization
    def test_manifest_checksums_the_knowledge_graph_result(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """knowledge_graph_result.json is checksummed like every other artifact."""
        manifest = _load_json(golden_pipeline_result.output_dir / "manifest.json")
        entries = {a["name"]: a for a in manifest["generatedArtifacts"]}
        entry = entries["knowledge_graph_result.json"]
        path = golden_pipeline_result.output_dir / "knowledge_graph_result.json"
        assert entry["sha256"] == _sha256(path)
        assert entry["bytes"] == path.stat().st_size

    @pytest.mark.productization
    def test_knowledge_graph_report_contains_the_summary_headline(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """knowledge_graph_report.md is a projection — it shows the result's own headline."""
        report = (golden_pipeline_result.output_dir / "knowledge_graph_report.md").read_text(
            encoding="utf-8"
        )
        assert golden_pipeline_result.knowledge_graph_result.summary.headline in report

    @pytest.mark.productization
    def test_knowledge_graph_metrics_contains_the_average_degree(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """knowledge_graph_metrics.md is a projection — it shows the result's own metrics."""
        metrics_md = (golden_pipeline_result.output_dir / "knowledge_graph_metrics.md").read_text(
            encoding="utf-8"
        )
        average_degree = golden_pipeline_result.knowledge_graph_result.metrics.average_degree
        assert f"{average_degree:.3f}" in metrics_md

    @pytest.mark.productization
    def test_execution_data_knowledge_graph_result_matches_pipeline_result(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """The object transported into the Execution Package is the same one returned."""
        assert (
            golden_pipeline_result.execution_data.knowledge_graph_result
            is golden_pipeline_result.knowledge_graph_result
        )

    @pytest.mark.productization
    def test_knowledge_graph_artifacts_are_written_after_continuous_improvement_artifacts(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """Artifact write order mirrors the frozen pipeline order (Continuous
        Improvement, then Knowledge Graph)."""
        names = [
            entry["name"]
            for entry in golden_pipeline_result.write_result.manifest["generatedArtifacts"]
        ]
        last_ci_index = max(
            index for index, name in enumerate(names) if name.startswith("continuous_improvement")
        )
        first_kg_index = min(
            index for index, name in enumerate(names) if name.startswith("knowledge_graph")
        )
        assert last_ci_index < first_kg_index

    @pytest.mark.productization
    def test_knowledge_graph_result_is_explainable_solely_from_the_result(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """Every node/edge/observation the golden run produced traces to the result alone.

        No re-run of the engine, the provider, or the service is required — the
        explainability invariant ADR-0023 §D11/§D12 certifies.
        """
        result = golden_pipeline_result.knowledge_graph_result
        known_node_ids = {node.node_id for node in result.nodes}
        known_edge_ids = {edge.edge_id for edge in result.edges}
        for edge in result.edges:
            assert edge.source_node_id in known_node_ids
            assert edge.target_node_id in known_node_ids
        for observation in result.observations:
            assert set(observation.subject_node_ids) <= known_node_ids
            assert set(observation.subject_edge_ids) <= known_edge_ids

    @pytest.mark.productization
    def test_manifest_registers_the_engineering_context(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """manifest.json names the artifact and the policy that produced it."""
        manifest = _load_json(golden_pipeline_result.output_dir / "manifest.json")
        context = golden_pipeline_result.engineering_context
        assert manifest["engineeringContextArtifact"] == "engineering_context.json"
        assert manifest["engineeringContextId"] == str(context.context_id)
        assert manifest["orchestrationPolicyId"] == "coverage"
        assert manifest["orchestrationPolicyVersion"] == "1.0.0"
        assert manifest["selectionStrategy"] == "coverage_guaranteed"
        assert manifest["candidateGroupCount"] == 1
        assert manifest["contributingGroupCount"] == 1
        assert manifest["contributingConsolidatedIds"] == list(
            context.provenance.contributing_consolidated_ids
        )
        assert manifest["coverageComplete"] is True
        assert manifest["evidenceDomainsRepresented"] == ["functional", "security", "quality"]
        assert manifest["contextArtifactCount"] == 9

    @pytest.mark.productization
    def test_manifest_checksums_the_engineering_context(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """The new artifact is checksummed by the same mechanism as every other."""
        manifest = _load_json(golden_pipeline_result.output_dir / "manifest.json")
        entries = {a["name"]: a for a in manifest["generatedArtifacts"]}
        entry = entries["engineering_context.json"]
        path = golden_pipeline_result.output_dir / "engineering_context.json"
        assert entry["sha256"] == _sha256(path)
        assert entry["bytes"] == path.stat().st_size

    @pytest.mark.productization
    def test_manifest_generated_artifacts_list(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        manifest = _load_json(golden_pipeline_result.output_dir / "manifest.json")
        names = {a["name"] for a in manifest["generatedArtifacts"]}
        # Every governed artifact must appear in the manifest listing.
        for expected in _ALL_ARTIFACTS - {"manifest.json"}:
            assert expected in names, f"Artifact missing from manifest listing: {expected}"

    @pytest.mark.productization
    def test_manifest_checksums_match_files(self, golden_pipeline_result: PipelineResult) -> None:
        """sha256 in manifest.generatedArtifacts must match on-disk content."""
        manifest = _load_json(golden_pipeline_result.output_dir / "manifest.json")
        for entry in manifest["generatedArtifacts"]:
            name = entry["name"]
            expected_sha = entry["sha256"]
            actual_sha = _sha256(golden_pipeline_result.output_dir / name)
            assert actual_sha == expected_sha, (
                f"Checksum mismatch for {name}: manifest={expected_sha!r} file={actual_sha!r}"
            )

    @pytest.mark.productization
    def test_manifest_byte_counts_match_files(self, golden_pipeline_result: PipelineResult) -> None:
        """bytes in manifest.generatedArtifacts must match on-disk file size."""
        manifest = _load_json(golden_pipeline_result.output_dir / "manifest.json")
        for entry in manifest["generatedArtifacts"]:
            name = entry["name"]
            expected_bytes = entry["bytes"]
            actual_bytes = (golden_pipeline_result.output_dir / name).stat().st_size
            assert actual_bytes == expected_bytes, (
                f"Byte count mismatch for {name}: manifest={expected_bytes} file={actual_bytes}"
            )

    @pytest.mark.productization
    def test_manifest_analysis_id_cross_reference(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """manifest.analysisId matches the AnalysisResult written to disk."""
        manifest = _load_json(golden_pipeline_result.output_dir / "manifest.json")
        analysis_data = _load_json(golden_pipeline_result.output_dir / "analysis_result.json")
        assert manifest["analysisId"] == analysis_data["analysisId"]

    @pytest.mark.productization
    def test_manifest_execution_id_cross_reference(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """manifest.executionId matches the AnalysisResult written to disk."""
        manifest = _load_json(golden_pipeline_result.output_dir / "manifest.json")
        analysis_data = _load_json(golden_pipeline_result.output_dir / "analysis_result.json")
        assert manifest["executionId"] == analysis_data["executionId"]

    @pytest.mark.productization
    def test_manifest_prompt_sha256_matches_prompt_txt(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """manifest.promptSha256 is the SHA-256 of the full prompt (system + user)."""
        manifest = _load_json(golden_pipeline_result.output_dir / "manifest.json")
        full_prompt = golden_pipeline_result.execution_data.full_prompt
        import hashlib

        expected = hashlib.sha256(full_prompt.encode("utf-8")).hexdigest()
        assert manifest["promptSha256"] == expected

    @pytest.mark.productization
    def test_manifest_response_sha256_matches_generated_text(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """manifest.responseSha256 is the SHA-256 of the raw LLM response text."""
        manifest = _load_json(golden_pipeline_result.output_dir / "manifest.json")
        generated_text = golden_pipeline_result.execution_data.generated_text
        import hashlib

        expected = hashlib.sha256(generated_text.encode("utf-8")).hexdigest()
        assert manifest["responseSha256"] == expected

    # --- Execution summary verification ------------------------------------

    @pytest.mark.productization
    def test_execution_summary_contains_cp1_section(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        content = (golden_pipeline_result.output_dir / "execution_summary.md").read_text()
        assert "Engineering Readiness" in content
        assert "cp1_report.md" in content

    # --- Baseline metrics verification -------------------------------------

    @pytest.mark.productization
    def test_baseline_metrics_source_artifact_count(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        content = (golden_pipeline_result.output_dir / "baseline_metrics.md").read_text()
        assert "9" in content  # Source Artifacts Processed = 9


# ===========================================================================
# PHASE 5 — Determinism
# ===========================================================================


class TestPhase5Determinism:
    """Two consecutive identical pipeline runs must produce the same findings and verdicts."""

    @pytest.mark.productization
    def test_determinism_validation_verdict(
        self,
        golden_pipeline_result: PipelineResult,
        tmp_path: Path,
    ) -> None:
        """Two runs produce identical Validation verdicts."""
        run2 = _run_golden_pipeline(tmp_path)
        v1 = str(golden_pipeline_result.validation_result.overall_verdict)
        v2 = str(run2.validation_result.overall_verdict)
        assert v1 == v2, f"Validation verdict differs: run1={v1!r} run2={v2!r}"

    @pytest.mark.productization
    def test_determinism_validation_issue_count(
        self,
        golden_pipeline_result: PipelineResult,
        tmp_path: Path,
    ) -> None:
        """Two runs produce the same number of validation issues."""
        run2 = _run_golden_pipeline(tmp_path)
        n1 = len(golden_pipeline_result.validation_result.validation_issues)
        n2 = len(run2.validation_result.validation_issues)
        assert n1 == n2, f"Validation issue count differs: run1={n1} run2={n2}"

    @pytest.mark.productization
    def test_determinism_validation_issue_rules(
        self,
        golden_pipeline_result: PipelineResult,
        tmp_path: Path,
    ) -> None:
        """Two runs report the same rule IDs (order-independent)."""
        run2 = _run_golden_pipeline(tmp_path)
        rules1 = sorted(
            i.rule_id for i in golden_pipeline_result.validation_result.validation_issues
        )
        rules2 = sorted(i.rule_id for i in run2.validation_result.validation_issues)
        assert rules1 == rules2, f"Rule IDs differ: run1={rules1} run2={rules2}"

    @pytest.mark.productization
    def test_determinism_cp1_verdict(
        self,
        golden_pipeline_result: PipelineResult,
        tmp_path: Path,
    ) -> None:
        """Two runs produce identical CP1 verdicts."""
        run2 = _run_golden_pipeline(tmp_path)
        r1 = golden_pipeline_result.cp1_result
        r2 = run2.cp1_result
        assert (r1 is None) == (r2 is None), "CP1 gate open/closed differs between runs"
        if r1 is not None and r2 is not None:
            v1 = str(getattr(r1.overall_verdict, "value", r1.overall_verdict))
            v2 = str(getattr(r2.overall_verdict, "value", r2.overall_verdict))
            assert v1 == v2, f"CP1 verdict differs: run1={v1!r} run2={v2!r}"

    @pytest.mark.productization
    def test_determinism_cp1_finding_count(
        self,
        golden_pipeline_result: PipelineResult,
        tmp_path: Path,
    ) -> None:
        """Two runs produce the same number of CP1 findings."""
        run2 = _run_golden_pipeline(tmp_path)
        r1 = golden_pipeline_result.cp1_result
        r2 = run2.cp1_result
        if r1 is None and r2 is None:
            return  # both skipped — consistent
        assert r1 is not None and r2 is not None
        assert len(r1.findings) == len(r2.findings), (
            f"CP1 finding count differs: run1={len(r1.findings)} run2={len(r2.findings)}"
        )

    @pytest.mark.productization
    def test_determinism_cp1_criterion_ids(
        self,
        golden_pipeline_result: PipelineResult,
        tmp_path: Path,
    ) -> None:
        """Two runs report the same CP1 criterion IDs (order-independent)."""
        run2 = _run_golden_pipeline(tmp_path)
        r1 = golden_pipeline_result.cp1_result
        r2 = run2.cp1_result
        if r1 is None and r2 is None:
            return
        assert r1 is not None and r2 is not None
        cids1 = sorted(f.criterion_id for f in r1.findings)
        cids2 = sorted(f.criterion_id for f in r2.findings)
        assert cids1 == cids2, f"CP1 criterion IDs differ: run1={cids1} run2={cids2}"

    @pytest.mark.productization
    def test_determinism_grounding_classification_distribution(
        self,
        golden_pipeline_result: PipelineResult,
        tmp_path: Path,
    ) -> None:
        """Two runs produce the same grounding verdicts (content, not provenance)."""
        run2 = _run_golden_pipeline(tmp_path)
        g1 = golden_pipeline_result.grounding_result.assessment
        g2 = run2.grounding_result.assessment
        dist1 = [(str(e.classification), e.count) for e in g1.metrics.support_distribution]
        dist2 = [(str(e.classification), e.count) for e in g2.metrics.support_distribution]
        assert dist1 == dist2, f"Grounding distribution differs: {dist1} vs {dist2}"

    @pytest.mark.productization
    def test_determinism_grounding_score_and_findings(
        self,
        golden_pipeline_result: PipelineResult,
        tmp_path: Path,
    ) -> None:
        """Two runs produce the same grounding score, coverage, and finding ids."""
        run2 = _run_golden_pipeline(tmp_path)
        g1 = golden_pipeline_result.grounding_result.assessment
        g2 = run2.grounding_result.assessment
        assert g1.metrics.grounding_score == g2.metrics.grounding_score
        assert g1.metrics.hallucination_rate == g2.metrics.hallucination_rate
        assert sorted(f.finding_id for f in g1.findings) == sorted(
            f.finding_id for f in g2.findings
        )

    @pytest.mark.productization
    def test_determinism_grounding_requirement_ids(
        self,
        golden_pipeline_result: PipelineResult,
        tmp_path: Path,
    ) -> None:
        """Grounded requirement ids are deterministic (minted from domain + text)."""
        run2 = _run_golden_pipeline(tmp_path)
        ids1 = sorted(
            str(r.requirement_id)
            for r in golden_pipeline_result.grounding_result.assessment.grounded_requirements
        )
        ids2 = sorted(
            str(r.requirement_id) for r in run2.grounding_result.assessment.grounded_requirements
        )
        assert ids1 == ids2

    @pytest.mark.productization
    def test_determinism_quality_governance_decision_and_findings(
        self,
        golden_pipeline_result: PipelineResult,
        tmp_path: Path,
    ) -> None:
        """Two runs produce the same QualityDecision, score, counts and finding ids.

        The determinism boundary is the canonical QualityGovernanceResult content, never
        the Markdown formatting or the provenance timestamps — exactly mirroring Grounding
        (ADR-0017 §D30, Recommendation 5).
        """
        run2 = _run_golden_pipeline(tmp_path)
        a1 = golden_pipeline_result.quality_governance_result.assessment
        a2 = run2.quality_governance_result.assessment
        assert str(a1.decision) == str(a2.decision)
        assert a1.summary.overall_quality_score == a2.summary.overall_quality_score
        assert a1.summary.total_findings == a2.summary.total_findings
        assert a1.summary.warning_count == a2.summary.warning_count
        assert a1.summary.failure_count == a2.summary.failure_count
        assert sorted(f.finding_id for f in a1.findings) == sorted(
            f.finding_id for f in a2.findings
        )

    @pytest.mark.productization
    def test_determinism_quality_governance_serialization(
        self,
        golden_pipeline_result: PipelineResult,
        tmp_path: Path,
    ) -> None:
        """Serializer output is deterministic on the governed content, excluding provenance.

        The runtime mints run-specific provenance — analysis/execution ids, the derived
        result/assessment ids, consumed-input ids, and the started/completed timestamps —
        exactly as Grounding does. The determinism boundary is the governed content, not
        that provenance (ADR-0017 §D30, Recommendation 5). The summary projection carries no
        provenance and so is byte-identical across runs; the JSON projection is identical
        once provenance is dropped; and each projection is a pure function of its input.
        """
        from requirement_intelligence.quality_governance.serialization import (
            QualityGovernanceSerializer,
        )

        run2 = _run_golden_pipeline(tmp_path)
        serializer = QualityGovernanceSerializer()
        g1 = golden_pipeline_result.quality_governance_result
        g2 = run2.quality_governance_result

        # The summary carries no provenance — byte-identical across two runs.
        assert serializer.render_summary(g1) == serializer.render_summary(g2)

        # The JSON projection is identical once run-specific provenance is dropped.
        def _strip_provenance(dumped: dict) -> dict:
            for key in ("resultId", "analysisId", "executionId", "startedAt", "completedAt"):
                dumped.pop(key, None)
            dumped.pop("consumedInputs", None)
            assessment = dict(dumped["assessment"])
            for key in ("assessmentId", "analysisId", "executionId"):
                assessment.pop(key, None)
            dumped["assessment"] = assessment
            return dumped

        assert _strip_provenance(serializer.render_json(g1)) == _strip_provenance(
            serializer.render_json(g2)
        )

        # Each projection is a pure function of its input — same result, same bytes.
        assert serializer.render_report(g1) == serializer.render_report(g1)
        assert serializer.render_json(g1) == serializer.render_json(g1)

    @pytest.mark.productization
    def test_determinism_manifest_governance_keys_stay_metadata_only(
        self,
        golden_pipeline_result: PipelineResult,
        tmp_path: Path,
    ) -> None:
        """manifest governance keys are identical package metadata across two runs.

        Decision determinism itself is proven at the runtime-contract boundary by
        ``test_determinism_quality_governance_decision_and_findings`` (ADR-0017 §D31): the
        golden regression compares ``QualityGovernanceResult`` content, never the manifest.
        This test only confirms the manifest's package-metadata keys are stable and that no
        runtime-state key has leaked back into the manifest.
        """
        run2 = _run_golden_pipeline(tmp_path)
        m1 = _load_json(golden_pipeline_result.output_dir / "manifest.json")
        m2 = _load_json(run2.output_dir / "manifest.json")
        assert m1.get("qualityGovernanceExecuted") == m2.get("qualityGovernanceExecuted")
        assert m1.get("qualityGovernanceReport") == m2.get("qualityGovernanceReport")
        assert m1.get("qualityGovernanceSummary") == m2.get("qualityGovernanceSummary")
        assert "qualityGovernanceDecision" not in m1
        assert "qualityGovernanceDecision" not in m2

    @pytest.mark.productization
    def test_determinism_requirement_enhancement_result_content(
        self,
        golden_pipeline_result: PipelineResult,
        tmp_path: Path,
    ) -> None:
        """Two runs produce the same enhanced requirements, relationships, and findings.

        The determinism boundary is the canonical ``RequirementEnhancementResult``
        content, never Markdown formatting or provenance timestamps — exactly
        mirroring Grounding and Quality Governance (ADR-0018 §D8/§D9).

        ``EnhancedRequirementId`` / ``RequirementObservationId`` / the finding id /
        ``result_id`` are each a pure function of the run's ``enhancement_id`` (in
        turn minted from ``analysis_id``/``execution_id``) — run-scoped provenance,
        exactly like ``QualityAssessmentId`` / ``QualityGovernanceResultId`` (ADR-0017
        §D5). Two independent runs mint fresh execution ids even over byte-identical
        content, so this test compares stable *content* (requirement ids, the
        content-only ``relationship_id`` — a pure function of source/target/type,
        Recommendation 5 — and finding category/severity/message), never those
        run-scoped ids.
        """
        run2 = _run_golden_pipeline(tmp_path)
        r1 = golden_pipeline_result.requirement_enhancement_result
        r2 = run2.requirement_enhancement_result
        assert r1.summary.total_requirements_enhanced == r2.summary.total_requirements_enhanced
        assert r1.summary.total_relationships == r2.summary.total_relationships
        assert r1.summary.total_observations == r2.summary.total_observations
        assert r1.summary.total_findings == r2.summary.total_findings
        assert r1.metrics == r2.metrics
        assert sorted(str(req.requirement_id) for req in r1.enhanced_requirements) == sorted(
            str(req.requirement_id) for req in r2.enhanced_requirements
        )
        # relationship_id is content-derived (source + target + type only), never
        # enhancement_id-derived, so it is directly comparable across runs.
        assert sorted(edge.relationship_id for edge in r1.relationship_graph.relationships) == (
            sorted(edge.relationship_id for edge in r2.relationship_graph.relationships)
        )

        def _finding_content(finding: Any) -> tuple[str, str, str]:
            return (str(finding.category), str(finding.severity), finding.message)

        assert sorted(_finding_content(f) for f in r1.findings) == sorted(
            _finding_content(f) for f in r2.findings
        )

    @pytest.mark.productization
    def test_determinism_requirement_enhancement_serialization(
        self,
        golden_pipeline_result: PipelineResult,
        tmp_path: Path,
    ) -> None:
        """Serializer output is deterministic on the enhancement content, excluding provenance.

        The runtime mints run-specific provenance — analysis/execution ids, the
        derived result id, consumed-input ids, and the started/completed timestamps —
        exactly as Grounding and Quality Governance do. Because ``EnhancedRequirementId``
        / ``RequirementObservationId`` / the finding id are each a pure function of the
        run's ``enhancement_id`` (in turn minted from ``analysis_id``/``execution_id``),
        they too are run-scoped provenance and are stripped alongside the top-level ids
        before comparing, along with the governed "traceability" attribute (which
        embeds ``analysis_id:execution_id`` verbatim by design). ``relationshipId`` is
        content-derived (source + target + type only, Recommendation 5) and is left in
        place. The determinism boundary is the enhancement content, not that provenance.
        """
        from requirement_intelligence.enhancement.serialization import EnhancementSerializer

        run2 = _run_golden_pipeline(tmp_path)
        serializer = EnhancementSerializer()
        r1 = golden_pipeline_result.requirement_enhancement_result
        r2 = run2.requirement_enhancement_result

        def _strip_provenance(dumped: dict) -> dict:
            dumped = dict(dumped)
            for key in ("resultId", "analysisId", "executionId", "startedAt", "completedAt"):
                dumped.pop(key, None)
            dumped.pop("consumedInputs", None)
            if "relationshipGraph" in dumped:
                graph = dict(dumped["relationshipGraph"])
                graph.pop("graphId", None)
                dumped["relationshipGraph"] = graph
            if "enhancedRequirements" in dumped:
                dumped["enhancedRequirements"] = [
                    {
                        k: (
                            # The governed "traceability" attribute embeds
                            # analysis_id:execution_id verbatim in its value — run
                            # provenance by design (ER-ENR-003) — so it is excluded
                            # too; "provenance" (domain:position) is stable content.
                            [a for a in v if a.get("key") != "traceability"]
                            if k == "attributes"
                            else v
                        )
                        for k, v in item.items()
                        if k not in ("enhancedRequirementId", "observationIds")
                    }
                    for item in dumped["enhancedRequirements"]
                ]
            if "observations" in dumped:
                dumped["observations"] = [
                    {k: v for k, v in item.items() if k != "observationId"}
                    for item in dumped["observations"]
                ]
            if "findings" in dumped:
                dumped["findings"] = [
                    {k: v for k, v in item.items() if k not in ("findingId", "observationId")}
                    for item in dumped["findings"]
                ]
            return dumped

        assert _strip_provenance(serializer.render_json(r1)) == _strip_provenance(
            serializer.render_json(r2)
        )

        # Each projection is a pure function of its input — same result, same bytes.
        assert serializer.render_report(r1) == serializer.render_report(r1)
        assert serializer.render_metrics(r1) == serializer.render_metrics(r1)
        assert serializer.render_json(r1) == serializer.render_json(r1)

    @pytest.mark.productization
    def test_determinism_manifest_enhancement_keys_stay_metadata_only(
        self,
        golden_pipeline_result: PipelineResult,
        tmp_path: Path,
    ) -> None:
        """manifest enhancement keys are identical package metadata across two runs.

        Content determinism itself is proven at the runtime-contract boundary by
        ``test_determinism_requirement_enhancement_result_content``: the golden
        regression compares ``RequirementEnhancementResult`` content, never the
        manifest. This test only confirms the manifest's package-metadata keys are
        stable and that no runtime-state key has leaked back into the manifest.
        """
        run2 = _run_golden_pipeline(tmp_path)
        m1 = _load_json(golden_pipeline_result.output_dir / "manifest.json")
        m2 = _load_json(run2.output_dir / "manifest.json")
        assert m1.get("requirementEnhancementExecuted") == m2.get("requirementEnhancementExecuted")
        assert m1.get("requirementEnhancementReport") == m2.get("requirementEnhancementReport")
        assert m1.get("requirementEnhancementMetrics") == m2.get("requirementEnhancementMetrics")
        assert "requirementEnhancementCoverage" not in m1
        assert "requirementEnhancementCoverage" not in m2

    @pytest.mark.productization
    def test_determinism_recommendation_result_content(
        self,
        golden_pipeline_result: PipelineResult,
        tmp_path: Path,
    ) -> None:
        """Two runs produce the same recommendations, groups, and metrics.

        The determinism boundary is the canonical ``RecommendationResult`` content,
        never Markdown formatting or provenance timestamps — exactly mirroring
        Requirement Enhancement (ADR-0019 §D9/§D10). ``RecommendationId`` /
        ``RecommendationGroupId`` / ``result_id`` are each a pure function of the
        run's ``execution_id`` — run-scoped provenance, exactly like
        ``EnhancedRequirementId`` (ADR-0018 §D5). Two independent runs mint fresh
        execution ids even over byte-identical content, so this test compares stable
        *content* (recommendation type/priority/effort/confidence/title/description/
        source, and group category/label/size), never those run-scoped ids.
        """
        run2 = _run_golden_pipeline(tmp_path)
        r1 = golden_pipeline_result.recommendation_result
        r2 = run2.recommendation_result
        assert r1.summary.total_recommendations == r2.summary.total_recommendations
        assert r1.summary.total_groups == r2.summary.total_groups
        assert r1.metrics == r2.metrics

        def _recommendation_content(rec: Any) -> tuple[str, str, str, float, str, str, str]:
            return (
                str(rec.recommendation_type),
                str(rec.priority),
                str(rec.effort),
                rec.confidence,
                rec.title,
                rec.description,
                str(rec.recommendation_source),
            )

        assert sorted(_recommendation_content(r) for r in r1.recommendations) == sorted(
            _recommendation_content(r) for r in r2.recommendations
        )

        def _group_content(group: Any) -> tuple[str, str, int]:
            return (str(group.category), group.label, len(group.recommendation_ids))

        assert sorted(_group_content(g) for g in r1.groups) == sorted(
            _group_content(g) for g in r2.groups
        )

    @pytest.mark.productization
    def test_determinism_recommendation_serialization(
        self,
        golden_pipeline_result: PipelineResult,
        tmp_path: Path,
    ) -> None:
        """Serializer output is deterministic on the recommendation content, excluding provenance.

        The runtime mints run-specific provenance — analysis/execution ids, the
        derived result id, consumed-input ids, and the started/completed timestamps —
        exactly as Requirement Enhancement does. Because ``RecommendationId`` /
        ``RecommendationGroupId`` / a reference's ``referencedId`` are each a pure
        function of the run's ``execution_id`` (or an upstream finding minted from
        it), they too are run-scoped provenance and are stripped before comparing.
        The determinism boundary is the recommendation content, not that provenance.
        """
        from requirement_intelligence.recommendation.serialization import (
            RecommendationSerializer,
        )

        run2 = _run_golden_pipeline(tmp_path)
        serializer = RecommendationSerializer()
        r1 = golden_pipeline_result.recommendation_result
        r2 = run2.recommendation_result

        def _strip_provenance(dumped: dict) -> dict:
            dumped = dict(dumped)
            for key in ("resultId", "analysisId", "executionId", "startedAt", "completedAt"):
                dumped.pop(key, None)
            dumped.pop("consumedInputs", None)
            if "recommendations" in dumped:
                dumped["recommendations"] = [
                    {
                        k: (
                            [
                                {rk: rv for rk, rv in ref.items() if rk != "referencedId"}
                                for ref in v
                            ]
                            if k == "references"
                            else v
                        )
                        for k, v in item.items()
                        if k not in ("recommendationId", "rationale")
                    }
                    for item in dumped["recommendations"]
                ]
            if "groups" in dumped:
                dumped["groups"] = [
                    {k: v for k, v in item.items() if k not in ("groupId", "recommendationIds")}
                    for item in dumped["groups"]
                ]
            return dumped

        assert _strip_provenance(serializer.render_json(r1)) == _strip_provenance(
            serializer.render_json(r2)
        )

        # Each projection is a pure function of its input — same result, same bytes.
        assert serializer.render_report(r1) == serializer.render_report(r1)
        assert serializer.render_metrics(r1) == serializer.render_metrics(r1)
        assert serializer.render_json(r1) == serializer.render_json(r1)

    @pytest.mark.productization
    def test_determinism_manifest_recommendation_keys_stay_metadata_only(
        self,
        golden_pipeline_result: PipelineResult,
        tmp_path: Path,
    ) -> None:
        """manifest recommendation keys are identical package metadata across two runs.

        Content determinism itself is proven at the runtime-contract boundary by
        ``test_determinism_recommendation_result_content``: the golden regression
        compares ``RecommendationResult`` content, never the manifest. This test only
        confirms the manifest's package-metadata keys are stable and that no
        runtime-state key has leaked back into the manifest.
        """
        run2 = _run_golden_pipeline(tmp_path)
        m1 = _load_json(golden_pipeline_result.output_dir / "manifest.json")
        m2 = _load_json(run2.output_dir / "manifest.json")
        assert m1.get("recommendationExecuted") == m2.get("recommendationExecuted")
        assert m1.get("recommendationReport") == m2.get("recommendationReport")
        assert m1.get("recommendationMetrics") == m2.get("recommendationMetrics")
        assert "recommendationPriority" not in m1
        assert "recommendationPriority" not in m2

    @pytest.mark.productization
    def test_determinism_continuous_improvement_result_content(
        self,
        golden_pipeline_result: PipelineResult,
        tmp_path: Path,
    ) -> None:
        """Two runs produce the same findings, trends, opportunities, and metrics.

        The determinism boundary is the canonical ``ContinuousImprovementResult``
        content, never Markdown formatting or provenance timestamps/ids — exactly
        mirroring Recommendation (ADR-0019 §D9/§D10). Two independent runs mint a
        fresh, execution-scoped ``HistoricalDatasetReference`` (a random
        ``execution_id``) even over byte-identical golden input, so this test
        compares stable *content* (counts and metrics), never the run-scoped
        reference or any id derived from it.
        """
        run2 = _run_golden_pipeline(tmp_path)
        r1 = golden_pipeline_result.continuous_improvement_result
        r2 = run2.continuous_improvement_result
        assert r1.summary.total_findings == r2.summary.total_findings
        assert r1.summary.total_trends == r2.summary.total_trends
        assert r1.summary.total_opportunities == r2.summary.total_opportunities
        assert r1.metrics == r2.metrics

    @pytest.mark.productization
    def test_determinism_continuous_improvement_serialization(
        self,
        golden_pipeline_result: PipelineResult,
        tmp_path: Path,
    ) -> None:
        """Serializer output is deterministic on the continuous improvement content.

        The runtime mints run-specific provenance — the result id, the referenced
        dataset's identity/execution ids, and the started/completed timestamps —
        exactly as Recommendation does. The determinism boundary is the content,
        not that provenance.
        """
        from requirement_intelligence.continuous_improvement.serialization import (
            ContinuousImprovementSerializer,
        )

        run2 = _run_golden_pipeline(tmp_path)
        serializer = ContinuousImprovementSerializer()
        r1 = golden_pipeline_result.continuous_improvement_result
        r2 = run2.continuous_improvement_result

        def _strip_provenance(dumped: dict) -> dict:
            dumped = dict(dumped)
            for key in ("resultId", "startedAt", "completedAt"):
                dumped.pop(key, None)
            dumped.pop("historicalDataset", None)
            return dumped

        assert _strip_provenance(serializer.render_json(r1)) == _strip_provenance(
            serializer.render_json(r2)
        )

        # Each projection is a pure function of its input — same result, same bytes.
        assert serializer.render_report(r1) == serializer.render_report(r1)
        assert serializer.render_metrics(r1) == serializer.render_metrics(r1)
        assert serializer.render_json(r1) == serializer.render_json(r1)

    @pytest.mark.productization
    def test_determinism_manifest_continuous_improvement_keys_stay_metadata_only(
        self,
        golden_pipeline_result: PipelineResult,
        tmp_path: Path,
    ) -> None:
        """manifest continuous improvement keys are identical package metadata across two runs.

        Content determinism itself is proven at the runtime-contract boundary by
        ``test_determinism_continuous_improvement_result_content``: the golden
        regression compares ``ContinuousImprovementResult`` content, never the
        manifest. This test only confirms the manifest's package-metadata keys are
        stable and that no runtime-state key has leaked back into the manifest.
        """
        run2 = _run_golden_pipeline(tmp_path)
        m1 = _load_json(golden_pipeline_result.output_dir / "manifest.json")
        m2 = _load_json(run2.output_dir / "manifest.json")
        assert m1.get("continuousImprovementExecuted") == m2.get("continuousImprovementExecuted")
        assert m1.get("continuousImprovementReport") == m2.get("continuousImprovementReport")
        assert m1.get("continuousImprovementMetrics") == m2.get("continuousImprovementMetrics")
        assert "continuousImprovementSummary" not in m1
        assert "continuousImprovementSummary" not in m2

    @pytest.mark.productization
    def test_determinism_knowledge_graph_result_content(
        self,
        golden_pipeline_result: PipelineResult,
    ) -> None:
        """The same ``HistoricalDatasetReference``, built twice, yields the same content.

        Unlike Continuous Improvement's always-empty single-execution result,
        Knowledge Graph's CAP-084B deterministic provider gates several node/edge
        types on a SHA-256 digest of the reference's own ``dataset_id`` — which
        embeds this golden run's randomly minted ``execution_id``. Comparing two
        *independent* golden pipeline runs would therefore compare two different
        random inputs, not test determinism. The actual determinism contract this
        engine makes (ADR-0023 §D10, ``test_knowledge_graph_historical_dataset.py``)
        is *same reference in, same result out* — proven here by resolving the
        exact reference this golden run already consumed a second time, directly
        through ``KnowledgeGraphService.build``, and comparing content (never the
        wall-clock ``startedAt``/``completedAt`` timestamps or the fresh
        ``resultId``, since that id is minted from the graph id via
        ``ResultBuilder`` but the object itself is rebuilt, not cached).
        """
        from requirement_intelligence.platform.platform_context import PlatformContext

        r1 = golden_pipeline_result.knowledge_graph_result
        r2 = PlatformContext().create_knowledge_graph_service().build(r1.historical_dataset)
        assert r1.nodes == r2.nodes
        assert r1.edges == r2.edges
        assert r1.subgraphs == r2.subgraphs
        assert r1.observations == r2.observations
        assert r1.findings == r2.findings
        assert r1.summary.total_nodes == r2.summary.total_nodes
        assert r1.summary.total_edges == r2.summary.total_edges
        assert r1.metrics == r2.metrics
        assert r1.graph_id == r2.graph_id
        assert r1.result_id == r2.result_id

    @pytest.mark.productization
    def test_determinism_knowledge_graph_serialization(
        self,
        golden_pipeline_result: PipelineResult,
    ) -> None:
        """Serializer output is a pure function of a ``KnowledgeGraphResult`` — no re-derivation.

        The runtime mints run-specific provenance on the ``startedAt``/
        ``completedAt`` fields (wall clock); the serializer must render the exact
        same bytes given the exact same result object, exactly as every other
        subsystem serializer in this platform does.
        """
        from requirement_intelligence.knowledge_graph.serialization import (
            KnowledgeGraphSerializer,
        )

        serializer = KnowledgeGraphSerializer()
        r1 = golden_pipeline_result.knowledge_graph_result

        assert serializer.render_report(r1) == serializer.render_report(r1)
        assert serializer.render_metrics(r1) == serializer.render_metrics(r1)
        assert serializer.render_json(r1) == serializer.render_json(r1)

    @pytest.mark.productization
    def test_determinism_manifest_knowledge_graph_keys_stay_metadata_only(
        self,
        golden_pipeline_result: PipelineResult,
        tmp_path: Path,
    ) -> None:
        """manifest Knowledge Graph keys are identical package metadata across two runs.

        Content determinism itself is proven at the runtime-contract boundary by
        ``test_determinism_knowledge_graph_result_content``: the golden regression
        compares ``KnowledgeGraphResult`` content, never the manifest. This test
        only confirms the manifest's package-metadata keys are stable and that no
        runtime-state key has leaked back into the manifest.
        """
        run2 = _run_golden_pipeline(tmp_path)
        m1 = _load_json(golden_pipeline_result.output_dir / "manifest.json")
        m2 = _load_json(run2.output_dir / "manifest.json")
        assert m1.get("knowledgeGraphExecuted") == m2.get("knowledgeGraphExecuted")
        assert m1.get("knowledgeGraphReport") == m2.get("knowledgeGraphReport")
        assert m1.get("knowledgeGraphMetrics") == m2.get("knowledgeGraphMetrics")
        assert "knowledgeGraphSummary" not in m1
        assert "knowledgeGraphSummary" not in m2

    @pytest.mark.productization
    def test_determinism_organizational_memory_result_content(
        self,
        golden_pipeline_result: PipelineResult,
    ) -> None:
        """The same two consumed Layer 2 results, built twice, yield the same content.

        Unlike its two peers, Organizational Memory consumes no
        ``HistoricalDatasetReference`` — it consumes the two already-completed
        Layer 2 peer results directly (ADR-0025 §Stage 7/8's fan-in exception).
        The determinism contract (ADR-0027 §D18/§D19) is *same two results in,
        same result out* — proven here by rebuilding directly through
        ``OrganizationalMemoryService.build`` from the exact two results this
        golden run already consumed, and comparing content (never the wall-clock
        ``startedAt``/``completedAt`` timestamps or the fresh ``resultId``, since
        that id is minted from the memory id but the object itself is rebuilt,
        not cached).
        """
        from requirement_intelligence.platform.platform_context import PlatformContext

        r1 = golden_pipeline_result.organizational_memory_result
        r2 = (
            PlatformContext()
            .create_organizational_memory_service()
            .build(
                golden_pipeline_result.continuous_improvement_result,
                golden_pipeline_result.knowledge_graph_result,
            )
        )
        assert r1.experiences == r2.experiences
        assert r1.lessons == r2.lessons
        assert r1.best_practices == r2.best_practices
        assert r1.promotions == r2.promotions
        assert r1.lifecycles == r2.lifecycles
        assert r1.summary.total_experiences == r2.summary.total_experiences
        assert r1.metrics == r2.metrics
        assert r1.memory_id == r2.memory_id
        assert r1.result_id == r2.result_id

    @pytest.mark.productization
    def test_determinism_organizational_memory_serialization(
        self,
        golden_pipeline_result: PipelineResult,
    ) -> None:
        """Serializer output is a pure function of an ``OrganizationalMemoryResult`` —
        no re-derivation.

        The runtime mints run-specific provenance on the ``startedAt``/
        ``completedAt`` fields (wall clock); the serializer must render the exact
        same bytes given the exact same result object, exactly as every other
        subsystem serializer in this platform does.
        """
        from requirement_intelligence.organizational_memory.serialization import (
            OrganizationalMemorySerializer,
        )

        serializer = OrganizationalMemorySerializer()
        r1 = golden_pipeline_result.organizational_memory_result

        assert serializer.render_report(r1) == serializer.render_report(r1)
        assert serializer.render_metrics(r1) == serializer.render_metrics(r1)
        assert serializer.render_json(r1) == serializer.render_json(r1)

    @pytest.mark.productization
    def test_determinism_manifest_organizational_memory_keys_stay_metadata_only(
        self,
        golden_pipeline_result: PipelineResult,
        tmp_path: Path,
    ) -> None:
        """manifest Organizational Memory keys are identical package metadata across two runs.

        Content determinism itself is proven at the runtime-contract boundary by
        ``test_determinism_organizational_memory_result_content``: the golden
        regression compares ``OrganizationalMemoryResult`` content, never the
        manifest. This test only confirms the manifest's package-metadata keys
        are stable and that no runtime-state key has leaked back into the
        manifest.
        """
        run2 = _run_golden_pipeline(tmp_path)
        m1 = _load_json(golden_pipeline_result.output_dir / "manifest.json")
        m2 = _load_json(run2.output_dir / "manifest.json")
        assert m1.get("organizationalMemoryExecuted") == m2.get("organizationalMemoryExecuted")
        assert m1.get("organizationalMemoryReport") == m2.get("organizationalMemoryReport")
        assert m1.get("organizationalMemoryMetrics") == m2.get("organizationalMemoryMetrics")
        assert "organizationalMemorySummary" not in m1
        assert "organizationalMemorySummary" not in m2

    @pytest.mark.productization
    def test_determinism_normalization_outcome(
        self,
        golden_pipeline_result: PipelineResult,
        tmp_path: Path,
    ) -> None:
        """Two runs produce identical normalization outcomes."""
        run2 = _run_golden_pipeline(tmp_path)
        pr1 = golden_pipeline_result.normalization_result.parsed_response
        pr2 = run2.normalization_result.parsed_response
        assert (pr1 is None) == (pr2 is None), "ParsedResponse presence differs"
        if pr1 is not None and pr2 is not None:
            outcome1 = str(getattr(pr1.normalization_outcome, "value", pr1.normalization_outcome))
            outcome2 = str(getattr(pr2.normalization_outcome, "value", pr2.normalization_outcome))
            assert outcome1 == outcome2, (
                f"Normalization outcome differs: run1={outcome1!r} run2={outcome2!r}"
            )

    @pytest.mark.productization
    def test_determinism_parsed_response_structure(
        self,
        golden_pipeline_result: PipelineResult,
        tmp_path: Path,
    ) -> None:
        """Two runs produce identical ParsedResponse normalized structures."""
        run2 = _run_golden_pipeline(tmp_path)
        s1 = _parsed_response_structure(golden_pipeline_result)
        s2 = _parsed_response_structure(run2)
        assert s1 == s2, "ParsedResponse.normalized_structure differs between runs"

    @pytest.mark.productization
    def test_determinism_consolidated_artifact_count(
        self,
        golden_pipeline_result: PipelineResult,
        tmp_path: Path,
    ) -> None:
        """Two runs produce the same number of consolidated artifacts."""
        run2 = _run_golden_pipeline(tmp_path)
        n1 = len(golden_pipeline_result.consolidated_artifacts)
        n2 = len(run2.consolidated_artifacts)
        assert n1 == n2, f"Consolidated artifact count differs: run1={n1} run2={n2}"

    @pytest.mark.productization
    def test_determinism_consolidated_module_name(
        self,
        golden_pipeline_result: PipelineResult,
        tmp_path: Path,
    ) -> None:
        """Two runs select the identical consolidated module."""
        run2 = _run_golden_pipeline(tmp_path)
        assert golden_pipeline_result.selected.module == run2.selected.module

    @pytest.mark.productization
    def test_determinism_manifest_cp1_verdict_field(
        self,
        golden_pipeline_result: PipelineResult,
        tmp_path: Path,
    ) -> None:
        """manifest.cp1Verdict is identical across two runs."""
        run2 = _run_golden_pipeline(tmp_path)
        m1 = _load_json(golden_pipeline_result.output_dir / "manifest.json")
        m2 = _load_json(run2.output_dir / "manifest.json")
        assert m1.get("cp1Verdict") == m2.get("cp1Verdict"), (
            f"manifest.cp1Verdict differs: run1={m1.get('cp1Verdict')!r} "
            f"run2={m2.get('cp1Verdict')!r}"
        )

    @pytest.mark.productization
    def test_determinism_response_sha256(
        self,
        golden_pipeline_result: PipelineResult,
        tmp_path: Path,
    ) -> None:
        """The raw LLM response text (and its SHA-256) is identical across runs."""
        run2 = _run_golden_pipeline(tmp_path)
        text1 = golden_pipeline_result.execution_data.generated_text
        text2 = run2.execution_data.generated_text
        assert text1 == text2, "Generated text differs between runs"

    @pytest.mark.productization
    def test_determinism_engineering_context_id(
        self,
        golden_pipeline_result: PipelineResult,
        tmp_path: Path,
    ) -> None:
        """The context identity is a pure function of its inputs — never a uuid or clock."""
        run2 = _run_golden_pipeline(tmp_path)
        id1 = str(golden_pipeline_result.engineering_context.context_id)
        id2 = str(run2.engineering_context.context_id)
        assert id1 == id2, f"Context id differs: run1={id1!r} run2={id2!r}"

    @pytest.mark.productization
    def test_determinism_engineering_context_artifact_bytes(
        self,
        golden_pipeline_result: PipelineResult,
        tmp_path: Path,
    ) -> None:
        """engineering_context.json is byte-identical across two runs."""
        run2 = _run_golden_pipeline(tmp_path)
        sha1 = _sha256(golden_pipeline_result.output_dir / "engineering_context.json")
        sha2 = _sha256(run2.output_dir / "engineering_context.json")
        assert sha1 == sha2, "engineering_context.json differs between runs"

    @pytest.mark.productization
    def test_determinism_prompt_sha256(
        self,
        golden_pipeline_result: PipelineResult,
        tmp_path: Path,
    ) -> None:
        """The orchestrated prompt is byte-identical across two runs."""
        run2 = _run_golden_pipeline(tmp_path)
        m1 = _load_json(golden_pipeline_result.output_dir / "manifest.json")
        m2 = _load_json(run2.output_dir / "manifest.json")
        assert m1["promptSha256"] == m2["promptSha256"]


# ===========================================================================
# PHASE 6 — Productization Assertions
# ===========================================================================


class TestPhase6ProductizationAssertions:
    """Structured per-layer contract checks that serve as long-term regression guards."""

    # --- Dataset integrity -------------------------------------------------

    @pytest.mark.productization
    def test_dataset_version(self) -> None:
        """The golden dataset declares a version."""
        assert GOLDEN_DATASET_VERSION == "1.7.0"

    @pytest.mark.productization
    def test_dataset_covers_all_categories(self) -> None:
        """Dataset includes at least one artifact in each governed category."""
        categories = {a.source_category for a in GOLDEN_SOURCE_ARTIFACTS}
        assert SourceCategory.FUNCTIONAL in categories
        assert SourceCategory.SECURITY in categories
        assert SourceCategory.QUALITY in categories

    @pytest.mark.productization
    def test_dataset_artifact_ids_unique(self) -> None:
        """All artifact IDs in the golden dataset are unique."""
        ids = [a.artifact_id for a in GOLDEN_SOURCE_ARTIFACTS]
        assert len(ids) == len(set(ids)), "Duplicate artifact IDs in golden dataset"

    # --- Pipeline contract -------------------------------------------------

    @pytest.mark.productization
    def test_analysis_result_prompt_version(self, golden_pipeline_result: PipelineResult) -> None:
        """AnalysisResult carries the governed prompt version."""
        assert golden_pipeline_result.analysis_result.prompt_version == "1.0.0"

    @pytest.mark.productization
    def test_analysis_result_reasoning_contract_version(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """AnalysisResult carries the governed reasoning contract version."""
        assert golden_pipeline_result.analysis_result.reasoning_contract_version == "1.0.0"

    @pytest.mark.productization
    def test_normalization_statistics_populated(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """NormalizationResult statistics are populated."""
        stats = golden_pipeline_result.normalization_result.normalization_statistics
        assert stats is not None
        assert stats.responsibilities_executed >= 0

    @pytest.mark.productization
    def test_validation_statistics_rules_executed(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """ValidationResult statistics show at least one rule was executed."""
        stats = golden_pipeline_result.validation_result.validation_statistics
        assert stats.rules_executed > 0, "No validation rules were executed"

    @pytest.mark.productization
    def test_cp1_framework_metadata_present(self, golden_pipeline_result: PipelineResult) -> None:
        """CP1Result carries framework metadata."""
        result = golden_pipeline_result.cp1_result
        assert result is not None
        assert result.framework_metadata is not None

    @pytest.mark.productization
    def test_cp1_input_cross_references_validation(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """CP1Input.validation_id matches the ValidationResult.validation_id."""
        cp1_result = golden_pipeline_result.cp1_result
        validation_result = golden_pipeline_result.validation_result
        assert cp1_result is not None
        assert cp1_result.validation_id == validation_result.validation_id

    @pytest.mark.productization
    def test_execution_data_no_dry_run(self, golden_pipeline_result: PipelineResult) -> None:
        """Execution data records a live (non-dry-run) execution."""
        assert golden_pipeline_result.execution_data.dry_run is False

    @pytest.mark.productization
    def test_write_result_json_valid(self, golden_pipeline_result: PipelineResult) -> None:
        """ExecutionWriter confirms the LLM response is valid JSON."""
        assert golden_pipeline_result.write_result.json_valid is True

    @pytest.mark.productization
    def test_manifest_all_version_fields_present(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """manifest.json contains every governed version field."""
        manifest = _load_json(golden_pipeline_result.output_dir / "manifest.json")
        for key in (
            "manifestSchemaVersion",
            "platformVersion",
            "baselineVersion",
            "executionPackageVersion",
            "connectorRegistryVersion",
            "mapperVersion",
            "consolidationEngineVersion",
            "promptFrameworkVersion",
            "llmFrameworkVersion",
            "analysisServiceVersion",
            "executionWriterVersion",
            "platformCapabilitiesVersion",
        ):
            assert key in manifest, f"Version field missing from manifest: {key}"
            assert manifest[key], f"Version field is empty in manifest: {key}"

    @pytest.mark.productization
    def test_validation_report_contains_verdict(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """validation_report.md renders the overall verdict."""
        content = (golden_pipeline_result.output_dir / "validation_report.md").read_text()
        assert "PASSED" in content.upper()

    @pytest.mark.productization
    def test_cp1_report_contains_verdict(self, golden_pipeline_result: PipelineResult) -> None:
        """cp1_report.md renders the CP1 overall verdict."""
        content = (golden_pipeline_result.output_dir / "cp1_report.md").read_text()
        assert "PASS" in content.upper()

    # --- Explainability (CAP-076C Stage 9) ---------------------------------

    @pytest.mark.productization
    def test_context_carries_an_orchestration_reason(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """Every EngineeringContext explains, in one sentence, why it was composed."""
        reason = golden_pipeline_result.engineering_context.orchestration_reason
        assert reason.strip()
        assert golden_pipeline_result.engineering_context.subject.label in reason

    @pytest.mark.productization
    def test_every_contributing_group_has_an_inclusion_reason(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """No group is present without a recorded reason naming the policy that admitted it."""
        provenance = golden_pipeline_result.engineering_context.provenance
        policy_id = str(golden_pipeline_result.engineering_context.orchestration.policy_id)
        for contribution in provenance.contributions:
            assert contribution.inclusion_reason.strip()
            assert policy_id in contribution.inclusion_reason

    @pytest.mark.productization
    def test_provenance_records_every_candidate_the_policy_ranked(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """Selection is falsifiable: the context records what it was chosen *from*."""
        provenance = golden_pipeline_result.engineering_context.provenance
        assert provenance.candidate_group_count == len(
            golden_pipeline_result.consolidated_artifacts
        )

    @pytest.mark.productization
    def test_every_evidence_artifact_is_traceable_to_its_source_record(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """No evidence item is anonymous: each carries its origin system and record id."""
        evidence = golden_pipeline_result.engineering_context.evidence
        artifacts = (
            *evidence.functional_artifacts,
            *evidence.security_artifacts,
            *evidence.quality_artifacts,
        )
        assert len(artifacts) == evidence.total_count
        for artifact in artifacts:
            assert artifact.source_system and artifact.source_record_id


# ===========================================================================
# CAP-076D — EngineeringContext as a first-class governed execution artifact
# ===========================================================================


class TestEngineeringContextGovernance:
    """The Golden Baseline verifies the *context*, not a single selected group.

    Before CAP-076D the baseline pinned the ConsolidatedArtifact the runtime
    selected. That was the right subject when a context was a single group. It no
    longer is: the context is the complete reasoning input, and the group is one
    of its contributors. These tests govern the context and every orchestration
    decision recorded inside it.
    """

    @pytest.mark.productization
    def test_context_artifact_records_the_full_ranking(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """Every candidate group appears, with the score it was ranked on."""
        data = _load_json(golden_pipeline_result.output_dir / "engineering_context.json")
        context = golden_pipeline_result.engineering_context
        ranking = data["ranking"]
        assert ranking["keys"] == list(context.ranking.keys)
        assert ranking["tieBreaker"] == context.ranking.tie_breaker
        assert len(ranking["entries"]) == context.provenance.candidate_group_count
        for entry in ranking["entries"]:
            assert entry["decisionReason"].strip()
            assert len(entry["score"]) == len(ranking["keys"])

    @pytest.mark.productization
    def test_context_artifact_partitions_selected_and_excluded_groups(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """Both halves of the ranking are named; an exclusion is never implicit."""
        data = _load_json(golden_pipeline_result.output_dir / "engineering_context.json")
        selected = data["selectedGroups"]
        excluded = data["excludedGroups"]
        assert len(selected) + len(excluded) == data["candidateGroupCount"]
        assert len(selected) == data["contributingGroupCount"]
        for group in selected:
            assert group["inclusionReason"].strip()
        for group in excluded:
            assert group["exclusionReason"].strip()

    @pytest.mark.productization
    def test_context_artifact_records_coverage_per_domain(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        data = _load_json(golden_pipeline_result.output_dir / "engineering_context.json")
        coverage = data["coverage"]
        assert coverage["mode"] == "all_present_categories"
        assert coverage["ruleSatisfied"] is True
        assert coverage["allPresentCategoriesRepresented"] is True
        assert [d["category"] for d in coverage["domains"]] == [
            "functional",
            "security",
            "quality",
        ]
        for domain in coverage["domains"]:
            assert domain["reason"].strip()

    @pytest.mark.productization
    def test_context_artifact_records_the_evidence_budget(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        data = _load_json(golden_pipeline_result.output_dir / "engineering_context.json")
        budget = data["evidenceBudget"]
        assert budget["maxArtifactsPerDomain"] == 25
        assert budget["maxArtifactsTotal"] == 60
        assert budget["totalUsed"] == 9
        assert budget["truncated"] is False
        assert sum(d["used"] for d in budget["domains"]) == budget["totalUsed"]

    @pytest.mark.productization
    def test_context_artifact_records_grounding_metadata(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """Grounding names the domains, the counts and the systems the evidence came from."""
        data = _load_json(golden_pipeline_result.output_dir / "engineering_context.json")
        grounding = data["groundingMetadata"]
        assert grounding["evidenceDomains"] == ["functional", "security", "quality"]
        assert grounding["evidenceCounts"] == {
            "functional": 4,
            "security": 3,
            "quality": 2,
            "total": 9,
        }
        assert grounding["coverageAchieved"] is True
        systems = {e["sourceSystem"]: e["artifactCount"] for e in grounding["sourceDistribution"]}
        assert systems == {"jira": 4, "owasp_zap": 3, "sonarqube": 2}
        assert sum(systems.values()) == grounding["evidenceCounts"]["total"]

    @pytest.mark.productization
    def test_context_artifact_declares_its_contract_version(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        data = _load_json(golden_pipeline_result.output_dir / "engineering_context.json")
        assert data["engineeringContextArtifactVersion"] == "2.0.0"
        assert data["contextModelVersion"] == "1.2"


class TestPolicyComparison:
    """Legacy versus Default over the identical candidate set (CAP-076D Stage 9).

    The golden dataset consolidates to one group carrying all three domains, so it
    isolates exactly one difference between the policies: the order evidence is
    presented in. Every other output must be identical, and that is the point —
    a difference anywhere else would mean the policy flip changed something the
    policy does not govern.
    """

    @pytest.mark.productization
    def test_both_policies_select_the_same_group(
        self,
        golden_pipeline_result: PipelineResult,
        legacy_pipeline_result: PipelineResult,
    ) -> None:
        assert (
            golden_pipeline_result.selected.consolidated_id
            == legacy_pipeline_result.selected.consolidated_id
        )

    @pytest.mark.productization
    def test_both_policies_deliver_the_same_evidence_for_this_dataset(
        self,
        golden_pipeline_result: PipelineResult,
        legacy_pipeline_result: PipelineResult,
    ) -> None:
        """One group, whole, under both policies — only the ordering differs."""
        active = golden_pipeline_result.engineering_context.evidence
        legacy = legacy_pipeline_result.engineering_context.evidence
        assert active.total_count == legacy.total_count == 9
        assert sorted(a.source_record_id for a in active.security_artifacts) == sorted(
            a.source_record_id for a in legacy.security_artifacts
        )

    @pytest.mark.productization
    def test_the_policies_disagree_only_where_the_policy_says_they_should(
        self,
        golden_pipeline_result: PipelineResult,
        legacy_pipeline_result: PipelineResult,
    ) -> None:
        """Same context identity and subject; different recorded policy and ordering."""
        active = golden_pipeline_result.engineering_context
        legacy = legacy_pipeline_result.engineering_context
        assert active.context_id == legacy.context_id  # same subject, same groups
        assert str(active.orchestration.policy_id) == "coverage"
        assert str(legacy.orchestration.policy_id) == "legacy-single-largest"
        assert active.coverage.selection_strategy == "coverage_guaranteed"
        assert legacy.coverage.selection_strategy == "single_largest"

    @pytest.mark.productization
    def test_both_policies_produce_identical_validation_and_cp1_outcomes(
        self,
        golden_pipeline_result: PipelineResult,
        legacy_pipeline_result: PipelineResult,
    ) -> None:
        """Validation and CP1 are unchanged by CAP-076D and must not react to the policy."""
        assert (
            golden_pipeline_result.validation_result.overall_verdict
            == legacy_pipeline_result.validation_result.overall_verdict
        )
        assert golden_pipeline_result.cp1_result is not None
        assert legacy_pipeline_result.cp1_result is not None
        assert (
            golden_pipeline_result.cp1_result.overall_verdict
            == legacy_pipeline_result.cp1_result.overall_verdict
        )

    @pytest.mark.productization
    def test_the_legacy_policy_still_reproduces_the_pre_cap_076_selection(
        self, legacy_pipeline_result: PipelineResult
    ) -> None:
        """The control arm is only a control if it still controls."""
        context = legacy_pipeline_result.engineering_context
        assert context.provenance.contributing_group_count == 1
        assert context.coverage.rule_satisfied is True
        evidence = context.evidence
        selected = legacy_pipeline_result.selected
        assert list(evidence.functional_artifacts) == selected.functional_artifacts
        assert list(evidence.security_artifacts) == selected.security_artifacts
        assert list(evidence.quality_artifacts) == selected.quality_artifacts
