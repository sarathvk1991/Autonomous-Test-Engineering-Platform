"""Architecture-only tests for the manifest purity boundary (CAP-084C, ADR-0023 §D11/§D12).

These tests add no behaviour and change nothing about the pipeline. They exist to keep
the boundary permanently enforced: the manifest owns package metadata and the artifact
inventory only; ``KnowledgeGraphResult`` (and its projection
``knowledge_graph_result.json``) is the sole owner of every Knowledge Graph runtime
concept — the nodes, the edges, the subgraphs, the observations, the findings, the
metrics, and the summary. Nothing downstream of it may duplicate that ownership.
Mirrors ``test_continuous_improvement_manifest_purity_boundary.py`` (CAP-083C,
ADR-0022 §D10/§D11).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from requirement_intelligence.execution.manifest_builder import ManifestBuilder
from tests.productization.conftest import _run_golden_pipeline

_REPO_ROOT = Path(__file__).resolve().parents[2]
_EXECUTION_DIR = _REPO_ROOT / "requirement_intelligence" / "execution"

#: Knowledge Graph runtime tokens the Execution Package must never import.
#: Mirrors the same containment rule enforced for the serializer
#: (``test_knowledge_graph_serialization.py``), applied to the manifest and
#: writer instead of the serializer.
_FORBIDDEN_KNOWLEDGE_GRAPH_RUNTIME_TOKENS = (
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
)

#: Manifest keys that would represent runtime state duplicated out of
#: ``KnowledgeGraphResult`` — a node, an edge, a subgraph, an observation, a
#: finding, a summary, or a metric value. None of these may ever appear on the
#: manifest; the manifest may only reference the artifact.
_FORBIDDEN_RUNTIME_STATE_KEYS = (
    "knowledgeGraphResult",
    "knowledgeGraphSummary",
    "knowledgeGraphNodes",
    "knowledgeGraphEdges",
    "knowledgeGraphSubgraphs",
    "knowledgeGraphObservations",
    "knowledgeGraphFindings",
    "knowledgeGraphMetricsValues",
)

#: The only Knowledge Graph keys the manifest may ever carry — a flag and two
#: artifact filenames. Package metadata / artifact inventory, never runtime state.
_ALLOWED_KNOWLEDGE_GRAPH_KEYS = frozenset(
    {
        "knowledgeGraphExecuted",
        "knowledgeGraphReport",
        "knowledgeGraphMetrics",
    }
)


def _source_of(*relative_paths: str) -> str:
    text = ""
    for relative_path in relative_paths:
        text += (_EXECUTION_DIR / relative_path).read_text(encoding="utf-8")
    return text


def _import_lines(source: str) -> list[str]:
    return [
        line.strip()
        for line in source.splitlines()
        if line.strip().startswith(("import ", "from "))
    ]


@pytest.mark.unit
class TestManifestImportsNoKnowledgeGraphRuntime:
    """ManifestBuilder must never import a Knowledge Graph runtime implementation class."""

    @pytest.mark.parametrize(
        "filename", ["manifest_builder.py", "execution_data.py", "execution_writer.py"]
    )
    def test_no_forbidden_import(self, filename: str) -> None:
        for line in _import_lines(_source_of(filename)):
            for token in _FORBIDDEN_KNOWLEDGE_GRAPH_RUNTIME_TOKENS:
                assert token not in line, f"{filename} must not import {token!r}: {line!r}"


@pytest.mark.unit
class TestManifestContainsNoRuntimeState:
    """The manifest's Knowledge Graph keys are package metadata only — never runtime state."""

    def test_manifest_source_names_no_forbidden_key(self) -> None:
        """The builder's source code never assigns a forbidden runtime-state manifest key."""
        source = _source_of("manifest_builder.py")
        for key in _FORBIDDEN_RUNTIME_STATE_KEYS:
            assert f'"{key}"' not in source, f"manifest_builder.py must not set {key!r}"

    def test_built_manifest_carries_metadata_keys_only(self, tmp_path: Path) -> None:
        """A real Knowledge Graph run produces a manifest with exactly the allowed keys."""
        pipeline = _run_golden_pipeline(tmp_path)
        assert pipeline.knowledge_graph_result is not None

        manifest = ManifestBuilder().build(
            pipeline.execution_data,
            started_timestamp="2026-01-01T00:00:00Z",
            completed_timestamp="2026-01-01T00:00:01Z",
            generated_artifacts=[],
        )
        knowledge_graph_keys = {key for key in manifest if key.startswith("knowledgeGraph")}
        assert knowledge_graph_keys == _ALLOWED_KNOWLEDGE_GRAPH_KEYS
        for key in _FORBIDDEN_RUNTIME_STATE_KEYS:
            assert key not in manifest


@pytest.mark.unit
class TestKnowledgeGraphAndContinuousImprovementKeysStayDisjoint:
    """The two Layer 2 capabilities' manifest keys never collide or leak into each other."""

    def test_knowledge_graph_keys_never_reuse_a_continuous_improvement_prefix(
        self, tmp_path: Path
    ) -> None:
        pipeline = _run_golden_pipeline(tmp_path)
        manifest = pipeline.write_result.manifest
        knowledge_graph_keys = {k for k in manifest if k.startswith("knowledgeGraph")}
        continuous_improvement_keys = {k for k in manifest if k.startswith("continuousImprovement")}
        assert knowledge_graph_keys.isdisjoint(continuous_improvement_keys)
        assert knowledge_graph_keys == _ALLOWED_KNOWLEDGE_GRAPH_KEYS

    def test_both_capabilities_executed_flags_are_independently_true(
        self, tmp_path: Path
    ) -> None:
        pipeline = _run_golden_pipeline(tmp_path)
        manifest = pipeline.write_result.manifest
        assert manifest["continuousImprovementExecuted"] is True
        assert manifest["knowledgeGraphExecuted"] is True


@pytest.mark.unit
class TestExecutionPackageIsProjectionOnly:
    """The Execution Package (writer + manifest) never projects, partitions, or detects."""

    def test_writer_imports_only_the_projection_serializer(self) -> None:
        """``execution_writer.py`` may import the Knowledge Graph *serializer*, never
        anything deeper."""
        source = _source_of("execution_writer.py")
        for line in _import_lines(source):
            if "knowledge_graph" not in line:
                continue
            allowed = (
                "knowledge_graph.serialization" in line or "KnowledgeGraphSerializer" in line
            )
            assert allowed, (
                f"execution_writer.py may only import the Knowledge Graph "
                f"serializer, found: {line!r}"
            )
