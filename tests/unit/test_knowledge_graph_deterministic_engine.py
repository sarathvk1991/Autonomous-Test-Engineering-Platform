"""End-to-end tests for ``DeterministicKnowledgeGraphEngine`` (CAP-084B).

Exercises the full pipeline — Historical Dataset resolution through node/edge
projection, subgraph detection, observation/finding analysis, and result
assembly — via the public ``build`` contract only. Covers determinism,
explainability, policy gating, provider injection, and containment, mirroring
``test_continuous_improvement_engine.py``'s coverage of its own deterministic
engine.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from requirement_intelligence.knowledge_graph.engine.deterministic_engine import (
    DeterministicKnowledgeGraphEngine,
)
from requirement_intelligence.knowledge_graph.engine.historical_dataset import (
    HistoricalDataset,
    HistoricalDatasetProvider,
    HistoricalExecutionRecord,
)
from requirement_intelligence.knowledge_graph.identity import (
    KnowledgeGraphId,
    KnowledgeGraphResultId,
)
from requirement_intelligence.knowledge_graph.models.historical_dataset_reference import (
    HistoricalDatasetReference,
)
from requirement_intelligence.knowledge_graph.models.result import KnowledgeGraphResult
from requirement_intelligence.knowledge_graph.policy import (
    KnowledgeGraphPolicy,
    default_knowledge_graph_policy,
)
from requirement_intelligence.knowledge_graph.rules import default_knowledge_graph_rule_catalog

_REPO_ROOT = Path(__file__).resolve().parents[2]
_KNOWLEDGE_GRAPH_PKG = _REPO_ROOT / "requirement_intelligence" / "knowledge_graph"
_FIXED_CLOCK = lambda: datetime(2026, 7, 15, tzinfo=UTC)  # noqa: E731


def _reference(**overrides: object) -> HistoricalDatasetReference:
    defaults: dict[str, object] = dict(
        dataset_id="ds-engine",
        dataset_version="1.0.0",
        first_execution_id="ex-1",
        last_execution_id="ex-25",
        execution_count=25,
        history_window=25,
        generated_at=datetime(2026, 7, 15, tzinfo=UTC),
    )
    defaults.update(overrides)
    return HistoricalDatasetReference(**defaults)  # type: ignore[arg-type]


class _FakeProvider(HistoricalDatasetProvider):
    """A controllable stub — hands the engine a fixed, hand-built dataset."""

    def __init__(self, dataset: HistoricalDataset) -> None:
        self._dataset = dataset

    def resolve(self, historical_dataset: HistoricalDatasetReference) -> HistoricalDataset:
        return self._dataset


def _engine(
    policy: KnowledgeGraphPolicy | None = None,
    provider: HistoricalDatasetProvider | None = None,
    clock=_FIXED_CLOCK,
) -> DeterministicKnowledgeGraphEngine:
    return DeterministicKnowledgeGraphEngine(
        policy=policy or default_knowledge_graph_policy(),
        rule_catalog=default_knowledge_graph_rule_catalog(),
        provider=provider,
        clock=clock,
    )


@pytest.mark.unit
class TestDeterminism:
    def test_identical_input_produces_identical_content(self) -> None:
        reference = _reference()
        r1 = _engine().build(reference)
        r2 = _engine().build(reference)
        assert r1.nodes == r2.nodes
        assert r1.edges == r2.edges
        assert r1.subgraphs == r2.subgraphs
        assert r1.observations == r2.observations
        assert r1.findings == r2.findings
        assert r1.summary == r2.summary
        assert r1.metrics == r2.metrics
        assert r1.result_id == r2.result_id
        assert r1.graph_id == r2.graph_id

    def test_fixed_clock_produces_fully_equal_results(self) -> None:
        reference = _reference()
        assert _engine().build(reference) == _engine().build(reference)

    def test_different_datasets_produce_different_graphs(self) -> None:
        r1 = _engine().build(_reference(dataset_id="ds-a"))
        r2 = _engine().build(_reference(dataset_id="ds-b"))
        assert r1.graph_id != r2.graph_id

    def test_result_id_is_pure_function_of_graph_id(self) -> None:
        reference = _reference()
        result = _engine().build(reference)
        expected_graph_id = KnowledgeGraphId.for_dataset(reference.dataset_id)
        assert result.graph_id == expected_graph_id
        assert result.result_id == KnowledgeGraphResultId.for_graph(str(expected_graph_id))


@pytest.mark.unit
class TestExplainability:
    def test_every_edge_endpoint_exists_among_nodes(self) -> None:
        result = _engine().build(_reference())
        node_ids = {node.node_id for node in result.nodes}
        for edge in result.edges:
            assert edge.source_node_id in node_ids
            assert edge.target_node_id in node_ids

    def test_every_finding_references_a_node_or_edge(self) -> None:
        result = _engine().build(_reference())
        for finding in result.findings:
            assert finding.subject_node_ids or finding.subject_edge_ids

    def test_every_subgraph_node_exists_in_top_level_nodes(self) -> None:
        result = _engine().build(_reference())
        node_ids = {node.node_id for node in result.nodes}
        for subgraph in result.subgraphs:
            assert set(subgraph.node_ids) <= node_ids

    def test_returns_a_real_knowledge_graph_result(self) -> None:
        result = _engine().build(_reference())
        assert isinstance(result, KnowledgeGraphResult)
        assert result.historical_dataset.dataset_id == "ds-engine"


@pytest.mark.unit
class TestPolicyGating:
    def test_master_switch_disabled_yields_empty_result(self) -> None:
        base = default_knowledge_graph_policy()
        disabled = base.model_copy(
            update={
                "capability_switches": base.capability_switches.model_copy(
                    update={"enable_deterministic_engine": False}
                )
            }
        )
        result = _engine(policy=disabled).build(_reference())
        assert result.nodes == ()
        assert result.edges == ()
        assert result.findings == ()
        assert "disabled by policy" in result.summary.headline

    def test_master_switch_disabled_result_still_round_trips(self) -> None:
        base = default_knowledge_graph_policy()
        disabled = base.model_copy(
            update={
                "capability_switches": base.capability_switches.model_copy(
                    update={"enable_deterministic_engine": False}
                )
            }
        )
        result = _engine(policy=disabled).build(_reference())
        dumped = result.model_dump(mode="json", by_alias=True)
        assert KnowledgeGraphResult.model_validate(dumped) == result

    def test_node_ingestion_disabled_yields_no_nodes_or_edges(self) -> None:
        base = default_knowledge_graph_policy()
        policy = base.model_copy(
            update={
                "capability_switches": base.capability_switches.model_copy(
                    update={"enable_node_ingestion": False}
                )
            }
        )
        result = _engine(policy=policy).build(_reference())
        assert result.nodes == ()
        assert result.edges == ()

    def test_finding_detection_disabled_yields_no_findings(self) -> None:
        base = default_knowledge_graph_policy()
        policy = base.model_copy(
            update={
                "capability_switches": base.capability_switches.model_copy(
                    update={"enable_finding_detection": False}
                )
            }
        )
        result = _engine(policy=policy).build(_reference())
        assert result.findings == ()
        assert result.nodes != ()


@pytest.mark.unit
class TestProviderInjection:
    def test_accepts_an_explicit_provider(self) -> None:
        dataset = HistoricalDataset(
            dataset_id="ds-custom",
            executions=(
                HistoricalExecutionRecord(
                    execution_id="ex-only",
                    ordinal=0,
                    requirement_id="req-only",
                    recommendation_id=None,
                    finding_id=None,
                    capability_id=None,
                    document_id=None,
                    depends_on_previous=False,
                ),
            ),
        )
        result = _engine(provider=_FakeProvider(dataset)).build(_reference())
        assert any(node.referenced_id == "req-only" for node in result.nodes)

    def test_default_provider_is_deterministic_hash_based(self) -> None:
        result = _engine().build(_reference(execution_count=1))
        assert len(result.nodes) > 0


@pytest.mark.unit
class TestContainment:
    def test_engine_module_imports_only_its_own_collaborators(self) -> None:
        source = (
            _KNOWLEDGE_GRAPH_PKG / "engine" / "deterministic_engine.py"
        ).read_text(encoding="utf-8")
        forbidden = (
            "requirement_intelligence.enhancement",
            "requirement_intelligence.grounding",
            "requirement_intelligence.validation",
            "requirement_intelligence.cp1",
            "requirement_intelligence.quality_governance",
            "requirement_intelligence.recommendation",
            "requirement_intelligence.continuous_improvement",
            "requirement_intelligence.execution",
            "PlatformContext",
        )
        for line in source.splitlines():
            if line.strip().startswith(("import ", "from ")):
                for token in forbidden:
                    assert token not in line, f"deterministic_engine.py imports {token}: {line!r}"

    def test_result_builder_is_the_only_result_constructor_in_the_engine(self) -> None:
        """No engine module other than result_builder.py constructs KnowledgeGraphResult."""
        engine_dir = _KNOWLEDGE_GRAPH_PKG / "engine"
        offenders = []
        for path in engine_dir.rglob("*.py"):
            if path.name == "result_builder.py":
                continue
            if "KnowledgeGraphResult(" in path.read_text(encoding="utf-8"):
                offenders.append(path.name)
        assert offenders == []
