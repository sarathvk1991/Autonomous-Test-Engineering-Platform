"""Unit tests for the Knowledge Graph serialization layer (CAP-084C).

Covers the JSON round-trip invariant, deterministic Markdown/metrics rendering, the
ExecutionWriter integration (conditional artifacts + manifest registration + absence
when no KnowledgeGraphResult), the manifest purity boundary (the manifest references
the Knowledge Graph artifacts but never duplicates their content, ADR-0023
§D11/§D12), and the frozen boundaries (serializer imports no Knowledge Graph
runtime; the runtime contract imports no execution package). Mirrors
``test_continuous_improvement_serialization.py`` (CAP-083C).
"""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest

from requirement_intelligence.execution.execution_writer import ExecutionWriter
from requirement_intelligence.knowledge_graph.identity import (
    KnowledgeFindingId,
    KnowledgeGraphFrameworkVersion,
    KnowledgeGraphId,
    KnowledgeGraphResultId,
    KnowledgeNodeId,
    KnowledgePolicyId,
    KnowledgePolicyVersion,
)
from requirement_intelligence.knowledge_graph.knowledge_graph_service import (
    DeterministicKnowledgeGraphService,
)
from requirement_intelligence.knowledge_graph.models.enums import (
    KnowledgeFindingCategory,
    KnowledgeNodeType,
    KnowledgeSeverity,
)
from requirement_intelligence.knowledge_graph.models.finding import KnowledgeFinding
from requirement_intelligence.knowledge_graph.models.historical_dataset_reference import (
    HistoricalDatasetReference,
)
from requirement_intelligence.knowledge_graph.models.node import KnowledgeNode
from requirement_intelligence.knowledge_graph.models.result import KnowledgeGraphResult
from requirement_intelligence.knowledge_graph.models.summary import (
    KnowledgeMetrics,
    KnowledgeSummary,
)
from requirement_intelligence.knowledge_graph.policy import default_knowledge_graph_policy
from requirement_intelligence.knowledge_graph.rules import default_knowledge_graph_rule_catalog
from requirement_intelligence.knowledge_graph.serialization import KnowledgeGraphSerializer
from tests.productization.conftest import _run_golden_pipeline

_REPO_ROOT = Path(__file__).resolve().parents[2]

_KNOWLEDGE_GRAPH_ARTIFACTS = (
    "knowledge_graph_result.json",
    "knowledge_graph_report.md",
    "knowledge_graph_metrics.md",
)

_NOW = datetime(2026, 7, 16, tzinfo=UTC)


def _reference(**overrides: object) -> HistoricalDatasetReference:
    defaults: dict[str, object] = dict(
        dataset_id="ds-serialization",
        dataset_version="1.0.0",
        first_execution_id="ex-1",
        last_execution_id="ex-1",
        execution_count=1,
        history_window=25,
        generated_at=_NOW,
    )
    defaults.update(overrides)
    return HistoricalDatasetReference(**defaults)  # type: ignore[arg-type]


def _empty_result() -> KnowledgeGraphResult:
    """A result built through the real engine — the ordinary, deterministic case."""
    service = DeterministicKnowledgeGraphService(
        policy=default_knowledge_graph_policy(), rule_catalog=default_knowledge_graph_rule_catalog()
    )
    return service.build(_reference())


def _with_a_finding() -> KnowledgeGraphResult:
    """A hand-built result carrying at least one finding, for report content assertions.

    Triggering ``ISOLATED_NODE`` organically through the deterministic provider
    requires disabling exactly one governed edge rule while its corresponding
    node rule stays enabled — a policy-shape exercise belonging to
    ``test_knowledge_graph_deterministic_engine.py``, not this serializer test.
    Hand-building the result directly (the same discipline the CAP-084A freeze
    test used before an engine existed) keeps this test focused on rendering,
    not finding-trigger conditions.
    """
    node = KnowledgeNode(
        node_id=KnowledgeNodeId.for_entity("requirement", "req-1"),
        node_type=KnowledgeNodeType.REQUIREMENT,
        referenced_id="req-1",
        label="Requirement 1",
    )
    finding = KnowledgeFinding(
        finding_id=KnowledgeFindingId.for_ordinal("kg-serialization", 0),
        category=KnowledgeFindingCategory.ISOLATED_NODE,
        severity=KnowledgeSeverity.WARNING,
        subject_node_ids=(node.node_id,),
        subject_edge_ids=(),
        message="node has no incident edges",
    )
    return KnowledgeGraphResult(
        result_id=KnowledgeGraphResultId.for_graph("kg-serialization"),
        graph_id=KnowledgeGraphId.for_dataset("ds-serialization"),
        historical_dataset=_reference(),
        nodes=(node,),
        edges=(),
        subgraphs=(),
        observations=(),
        findings=(finding,),
        summary=KnowledgeSummary(
            policy_id=KnowledgePolicyId("default-knowledge-graph-policy"),
            policy_version=KnowledgePolicyVersion(1, 1, 0),
            total_nodes=1,
            total_edges=0,
            total_subgraphs=0,
            total_observations=0,
            total_findings=1,
            headline="1 node(s), 1 finding(s).",
        ),
        metrics=KnowledgeMetrics(
            node_count=1,
            edge_count=0,
            subgraph_count=0,
            connected_component_count=1,
            average_degree=0.0,
            orphan_node_count=1,
        ),
        policy_id=KnowledgePolicyId("default-knowledge-graph-policy"),
        policy_version=KnowledgePolicyVersion(1, 1, 0),
        framework_version=KnowledgeGraphFrameworkVersion(1, 0, 0),
        started_at=_NOW,
        completed_at=_NOW,
    )


@pytest.mark.unit
class TestJsonProjection:
    def test_round_trip_equals_original(self) -> None:
        result = _with_a_finding()
        dumped = KnowledgeGraphSerializer().render_json(result)
        assert KnowledgeGraphResult.model_validate(dumped) == result

    def test_json_is_camel_case_and_carries_versions(self) -> None:
        dumped = KnowledgeGraphSerializer().render_json(_with_a_finding())
        assert "resultVersion" in dumped
        assert "frameworkVersion" in dumped
        assert "historicalDataset" in dumped
        assert "policyVersion" in dumped

    def test_json_is_deterministic_for_the_same_result(self) -> None:
        serializer = KnowledgeGraphSerializer()
        result = _with_a_finding()
        assert json.dumps(serializer.render_json(result)) == json.dumps(
            serializer.render_json(result)
        )


@pytest.mark.unit
class TestMarkdownProjection:
    def test_report_is_deterministic_and_has_sections(self) -> None:
        serializer = KnowledgeGraphSerializer()
        result = _with_a_finding()
        report = serializer.render_report(result)
        assert report == serializer.render_report(result)
        for section in (
            "# Knowledge Graph Report",
            "## Summary",
            "## Historical Dataset",
            "## Nodes",
            "## Edges",
            "## Subgraphs",
            "## Observations",
            "## Findings",
        ):
            assert section in report

    def test_metrics_is_deterministic_and_has_headline(self) -> None:
        serializer = KnowledgeGraphSerializer()
        result = _with_a_finding()
        rendered = serializer.render_metrics(result)
        assert rendered == serializer.render_metrics(result)
        assert "# Knowledge Graph Metrics" in rendered
        assert "Average degree" in rendered

    def test_report_surfaces_a_finding_verbatim(self) -> None:
        # The projection never derives a finding — it renders exactly what the
        # KnowledgeGraphResult already recorded.
        serializer = KnowledgeGraphSerializer()
        result = _with_a_finding()
        assert result.findings
        report = serializer.render_report(result)
        assert str(result.findings[0].finding_id) in report
        assert result.findings[0].message in report

    def test_result_with_no_findings_still_renders_valid_sections(self) -> None:
        serializer = KnowledgeGraphSerializer()
        result = _empty_result()
        assert result.findings == ()
        report = serializer.render_report(result)
        assert "_None_" in report
        metrics = serializer.render_metrics(result)
        assert "0.000" in metrics or "Orphan nodes" in metrics


@pytest.mark.unit
class TestExecutionWriterIntegration:
    def test_no_knowledge_graph_result_produces_no_artifacts(self, tmp_path: Path) -> None:
        pipeline = _run_golden_pipeline(tmp_path / "golden")
        data = replace(pipeline.execution_data, knowledge_graph_result=None)
        target = tmp_path / "no_knowledge_graph"
        target.mkdir()
        write_result = ExecutionWriter().write(target, data)
        for name in _KNOWLEDGE_GRAPH_ARTIFACTS:
            assert not (target / name).exists()
        assert all("knowledge_graph" not in n for n in write_result.generated_artifacts)
        manifest = write_result.manifest
        assert "knowledgeGraphExecuted" not in manifest
        assert "knowledgeGraphReport" not in manifest

    def test_knowledge_graph_result_produces_three_artifacts_and_manifest_entries(
        self, tmp_path: Path
    ) -> None:
        pipeline = _run_golden_pipeline(tmp_path / "golden")
        result = pipeline.knowledge_graph_result
        data = replace(pipeline.execution_data, knowledge_graph_result=result)
        target = tmp_path / "with_knowledge_graph"
        target.mkdir()
        write_result = ExecutionWriter().write(target, data)
        for name in _KNOWLEDGE_GRAPH_ARTIFACTS:
            assert (target / name).exists()
            assert name in write_result.generated_artifacts
        manifest_names = {a["name"] for a in write_result.manifest["generatedArtifacts"]}
        assert set(_KNOWLEDGE_GRAPH_ARTIFACTS) <= manifest_names
        # Manifest purity (ADR-0023 §D11/§D12): the manifest is package metadata
        # only — it names the artifact, it never carries Knowledge Graph content.
        # The canonical nodes/edges/subgraphs/observations/findings live
        # exclusively in knowledge_graph_result.json / KnowledgeGraphResult.
        assert write_result.manifest["knowledgeGraphExecuted"] is True
        assert "knowledgeGraphSummary" not in write_result.manifest
        assert "knowledgeGraphNodes" not in write_result.manifest
        result_path = target / "knowledge_graph_result.json"
        on_disk = json.loads(result_path.read_text(encoding="utf-8"))
        assert on_disk["summary"]["totalNodes"] == result.summary.total_nodes

    def test_artifacts_are_reproducible_from_knowledge_graph_result_alone(
        self, tmp_path: Path
    ) -> None:
        pipeline = _run_golden_pipeline(tmp_path / "golden")
        result = pipeline.knowledge_graph_result
        data = replace(pipeline.execution_data, knowledge_graph_result=result)
        target = tmp_path / "repro"
        target.mkdir()
        ExecutionWriter().write(target, data)
        serializer = KnowledgeGraphSerializer()
        assert (target / "knowledge_graph_report.md").read_text(encoding="utf-8") == (
            serializer.render_report(result)
        )
        assert (target / "knowledge_graph_metrics.md").read_text(encoding="utf-8") == (
            serializer.render_metrics(result)
        )
        assert json.loads(
            (target / "knowledge_graph_result.json").read_text(encoding="utf-8")
        ) == serializer.render_json(result)


@pytest.mark.unit
class TestSerializationBoundary:
    def test_serializer_imports_no_knowledge_graph_runtime(self) -> None:
        source = (
            _REPO_ROOT
            / "requirement_intelligence"
            / "knowledge_graph"
            / "serialization"
            / "knowledge_graph_serializer.py"
        ).read_text(encoding="utf-8")
        forbidden = (
            "knowledge_graph.engine",
            "knowledge_graph_service",
            "knowledge_graph.policy",
            "knowledge_graph.rules",
            "DeterministicKnowledgeGraphEngine",
            "DeterministicKnowledgeGraphService",
            "KnowledgeGraphService",
            "KnowledgeGraphPolicy",
            "KnowledgeGraphRuleCatalog",
            "HistoricalDatasetProvider",
            "PlatformContext",
        )
        for line in source.splitlines():
            if line.strip().startswith(("import ", "from ")):
                for token in forbidden:
                    assert token not in line, f"serializer must not import {token!r}"

    def test_runtime_contract_imports_no_execution_package(self) -> None:
        """KnowledgeGraphResult must never depend on the Execution Package."""
        source = (
            _REPO_ROOT / "requirement_intelligence" / "knowledge_graph" / "models" / "result.py"
        ).read_text(encoding="utf-8")
        assert "requirement_intelligence.execution" not in source
