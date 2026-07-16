"""Runtime-boundary tests for Knowledge Graph's CAP-084C activation (ADR-0023 §D12).

Covers provider isolation across every root the platform searches (not just the
``knowledge_graph`` package itself), the frozen pipeline order documented in the
CLI, round-trip stability across more than one result shape, and the
composition-root discipline the Execution Package must observe post-activation.
Complements ``test_knowledge_graph_execution_integration.py``,
``test_knowledge_graph_manifest_purity_boundary.py``, and
``test_knowledge_graph_serialization.py`` rather than duplicating them.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from requirement_intelligence.knowledge_graph.knowledge_graph_service import (
    DeterministicKnowledgeGraphService,
)
from requirement_intelligence.knowledge_graph.models.result import KnowledgeGraphResult
from requirement_intelligence.knowledge_graph.serialization import KnowledgeGraphSerializer
from requirement_intelligence.platform.platform_context import PlatformContext
from tests.productization.conftest import _run_golden_pipeline

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT = _REPO_ROOT / "scripts" / "run_requirement_analysis.py"
_KNOWLEDGE_GRAPH_PKG = _REPO_ROOT / "requirement_intelligence" / "knowledge_graph"
_CONTINUOUS_IMPROVEMENT_PKG = _REPO_ROOT / "requirement_intelligence" / "continuous_improvement"
_EXECUTION_PKG = _REPO_ROOT / "requirement_intelligence" / "execution"


@pytest.mark.unit
class TestPipelineOrderDocumentation:
    def test_cli_module_docstring_and_phase_reflect_the_frozen_order(self) -> None:
        """The CLI documents Knowledge Graph immediately after Continuous Improvement."""
        source = _SCRIPT.read_text(encoding="utf-8")
        phase_doc_start = source.index("def run_knowledge_graph_phase(")
        phase_doc = source[phase_doc_start : phase_doc_start + 800]
        ci_pos = phase_doc.index("Continuous Improvement")
        kg_pos = phase_doc.index("Knowledge Graph", ci_pos)
        ep_pos = phase_doc.index("Execution Package", kg_pos)
        assert ci_pos < kg_pos < ep_pos

    def test_run_knowledge_graph_phase_docstring_names_the_frozen_position(self) -> None:
        source = _SCRIPT.read_text(encoding="utf-8")
        start = source.index("def run_knowledge_graph_phase(")
        end = source.index('"""', source.index('"""', start) + 3)
        docstring = source[start:end]
        assert "CAP-084C" in docstring
        assert "Continuous Improvement" in docstring


@pytest.mark.unit
class TestProviderIsolationAcrossRoots:
    def test_knowledge_graph_provider_never_named_in_execution_package(self) -> None:
        """``HistoricalDatasetProvider`` (KG's) never crosses into the Execution Package."""
        needle = "HistoricalDatasetProvider"
        offenders: list[Path] = []
        for path in _EXECUTION_PKG.rglob("*.py"):
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip().startswith(("import ", "from ")) and needle in line:
                    offenders.append(path.relative_to(_REPO_ROOT))
        assert offenders == []

    def test_knowledge_graph_provider_never_named_in_the_cli_script(self) -> None:
        source = _SCRIPT.read_text(encoding="utf-8")
        for token in ("HistoricalDatasetProvider", "DeterministicHistoricalDatasetProvider"):
            assert token not in source

    def test_knowledge_graph_engine_never_named_in_the_cli_script(self) -> None:
        """The CLI orchestrates through the service only, never the engine directly."""
        source = _SCRIPT.read_text(encoding="utf-8")
        assert "DeterministicKnowledgeGraphEngine" not in source

    def test_continuous_improvement_and_knowledge_graph_providers_stay_disjoint(self) -> None:
        """Neither Layer 2 capability's provider is importable from the other's package.

        Both packages independently reuse the identical, generic
        ``HistoricalDatasetProvider`` name for two unrelated private classes
        (ADR-0023 §D10, ADR-0024 Stage 0) — this guard proves neither ever
        imports the other's.
        """
        needle = "HistoricalDatasetProvider"
        for path in _KNOWLEDGE_GRAPH_PKG.rglob("*.py"):
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip().startswith(("import ", "from ")):
                    assert "continuous_improvement" not in line, (
                        f"{path.name} imports from continuous_improvement: {line!r}"
                    )
        for path in _CONTINUOUS_IMPROVEMENT_PKG.rglob("*.py"):
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip().startswith(("import ", "from ")):
                    assert "knowledge_graph" not in line, (
                        f"{path.name} imports from knowledge_graph: {line!r}"
                    )
        assert needle  # the constant documents intent; the two loops above enforce it


@pytest.mark.unit
class TestServiceCompositionRootPostActivation:
    def test_cli_obtains_the_service_only_from_platform_context(self) -> None:
        source = _SCRIPT.read_text(encoding="utf-8")
        assert "context.create_knowledge_graph_service()" in source

    def test_platform_context_still_returns_the_deterministic_service(self) -> None:
        """CAP-084C activates the pipeline; it does not change what PlatformContext builds."""
        service = PlatformContext().create_knowledge_graph_service()
        assert isinstance(service, DeterministicKnowledgeGraphService)


@pytest.mark.unit
class TestRoundTripAcrossResultShapes:
    def test_golden_result_round_trips_through_the_serializer_and_the_model(
        self, tmp_path: Path
    ) -> None:
        pipeline = _run_golden_pipeline(tmp_path)
        result = pipeline.knowledge_graph_result
        assert result is not None
        dumped = KnowledgeGraphSerializer().render_json(result)
        assert KnowledgeGraphResult.model_validate(dumped) == result

    def test_disabled_policy_result_round_trips_too(self) -> None:
        """The policy-disabled empty-result path (engine's own short-circuit) round-trips.

        Exercises the same serializer/model round-trip invariant against the
        engine's ``_empty_result`` path (``enable_deterministic_engine=False``),
        never just the ordinary path — the projection-only invariant must hold
        for every shape the engine can produce.
        """
        from datetime import UTC, datetime

        from requirement_intelligence.knowledge_graph.engine import (
            DeterministicKnowledgeGraphEngine,
        )
        from requirement_intelligence.knowledge_graph.models.historical_dataset_reference import (
            HistoricalDatasetReference,
        )
        from requirement_intelligence.knowledge_graph.policy import default_knowledge_graph_policy

        base_policy = default_knowledge_graph_policy()
        disabled_policy = base_policy.model_copy(
            update={
                "capability_switches": base_policy.capability_switches.model_copy(
                    update={"enable_deterministic_engine": False}
                )
            }
        )
        engine = DeterministicKnowledgeGraphEngine(policy=disabled_policy)
        reference = HistoricalDatasetReference(
            dataset_id="ds-disabled",
            dataset_version="1.0.0",
            first_execution_id="ex-1",
            last_execution_id="ex-1",
            execution_count=1,
            history_window=1,
            generated_at=datetime(2026, 7, 16, tzinfo=UTC),
        )
        result = engine.build(reference)
        assert result.nodes == ()
        dumped = KnowledgeGraphSerializer().render_json(result)
        assert KnowledgeGraphResult.model_validate(dumped) == result
        # The disabled-policy shape still renders valid, non-empty artifacts.
        report = KnowledgeGraphSerializer().render_report(result)
        metrics = KnowledgeGraphSerializer().render_metrics(result)
        assert report
        assert metrics


@pytest.mark.unit
class TestSerializationPackageIsSelfContained:
    def test_serialization_package_imports_no_layer_1_subsystem(self) -> None:
        layer_1 = (
            "requirement_intelligence.enhancement",
            "requirement_intelligence.grounding",
            "requirement_intelligence.validation",
            "requirement_intelligence.cp1",
            "requirement_intelligence.quality_governance",
            "requirement_intelligence.recommendation",
            "requirement_intelligence.analysis",
            "requirement_intelligence.context_orchestration",
        )
        for path in (_KNOWLEDGE_GRAPH_PKG / "serialization").rglob("*.py"):
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip().startswith(("import ", "from ")):
                    for token in layer_1:
                        assert token not in line, f"{path.name} imports {token}: {line!r}"

    def test_serialization_package_imports_no_continuous_improvement(self) -> None:
        """Knowledge Graph's serializer never imports Continuous Improvement's own."""
        for path in (_KNOWLEDGE_GRAPH_PKG / "serialization").rglob("*.py"):
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip().startswith(("import ", "from ")):
                    assert "continuous_improvement" not in line, (
                        f"{path.name} imports continuous_improvement: {line!r}"
                    )

    def test_serialization_package_exports_only_the_serializer(self) -> None:
        import requirement_intelligence.knowledge_graph.serialization as pkg

        assert pkg.__all__ == ["KnowledgeGraphSerializer"]


@pytest.mark.unit
class TestKnowledgeGraphReferenceMinting:
    def test_minting_helper_produces_a_valid_single_execution_reference(self) -> None:
        """Direct unit coverage of the CLI's KG-specific minting helper (not just text-scan)."""
        import importlib.util
        from datetime import UTC, datetime
        from types import SimpleNamespace

        spec = importlib.util.spec_from_file_location("run_requirement_analysis", _SCRIPT)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        fake_result = SimpleNamespace(
            execution_id="ex-mint-test",
            completed_at=datetime(2026, 7, 16, tzinfo=UTC),
        )
        reference = module._knowledge_graph_historical_dataset_reference_for_execution(
            fake_result
        )
        assert reference.first_execution_id == "ex-mint-test"
        assert reference.last_execution_id == "ex-mint-test"
        assert reference.execution_count == 1
        assert reference.history_window == 1
        assert reference.generated_at == fake_result.completed_at
        assert reference.dataset_id == "single-execution:ex-mint-test"


@pytest.mark.unit
class TestManifestArtifactInventoryConsistency:
    def test_generated_artifacts_list_includes_exactly_the_three_knowledge_graph_files(
        self, tmp_path: Path
    ) -> None:
        pipeline = _run_golden_pipeline(tmp_path)
        names = {
            entry["name"]
            for entry in pipeline.write_result.manifest["generatedArtifacts"]
            if entry["name"].startswith("knowledge_graph")
        }
        assert names == {
            "knowledge_graph_result.json",
            "knowledge_graph_report.md",
            "knowledge_graph_metrics.md",
        }

    def test_every_knowledge_graph_artifact_has_a_positive_byte_count(
        self, tmp_path: Path
    ) -> None:
        pipeline = _run_golden_pipeline(tmp_path)
        entries = {
            entry["name"]: entry for entry in pipeline.write_result.manifest["generatedArtifacts"]
        }
        for name in (
            "knowledge_graph_result.json",
            "knowledge_graph_report.md",
            "knowledge_graph_metrics.md",
        ):
            assert entries[name]["bytes"] > 0
