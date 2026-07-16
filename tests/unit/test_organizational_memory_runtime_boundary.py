"""Runtime-boundary tests for Organizational Memory's CAP-085C activation
(ADR-0027 §D19).

Covers the frozen pipeline order documented in the CLI, round-trip stability
across more than one result shape, the composition-root discipline the
Execution Package must observe post-activation, and self-containment of the
new serializer package. Complements
``test_organizational_memory_execution_integration.py``,
``test_organizational_memory_manifest_purity_boundary.py``, and
``test_organizational_memory_serialization.py`` rather than duplicating them.
Unlike ``test_knowledge_graph_runtime_boundary.py``, there is no
``HistoricalDatasetProvider``/minting-helper section here: Organizational
Memory consumes the two already-completed Layer 2 peer results directly
(ADR-0025 §Stage 7/8's fan-in exception), so there is nothing of that shape to
isolate or unit-test.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from requirement_intelligence.organizational_memory.models.result import OrganizationalMemoryResult
from requirement_intelligence.organizational_memory.organizational_memory_service import (
    DeterministicOrganizationalMemoryService,
)
from requirement_intelligence.organizational_memory.serialization import (
    OrganizationalMemorySerializer,
)
from requirement_intelligence.platform.platform_context import PlatformContext
from tests.productization.conftest import _run_golden_pipeline

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT = _REPO_ROOT / "scripts" / "run_requirement_analysis.py"
_ORGANIZATIONAL_MEMORY_PKG = _REPO_ROOT / "requirement_intelligence" / "organizational_memory"
_EXECUTION_PKG = _REPO_ROOT / "requirement_intelligence" / "execution"


@pytest.mark.unit
class TestPipelineOrderDocumentation:
    def test_cli_module_docstring_and_phase_reflect_the_frozen_order(self) -> None:
        """The CLI documents Organizational Memory immediately after Knowledge Graph."""
        source = _SCRIPT.read_text(encoding="utf-8")
        phase_doc_start = source.index("def run_organizational_memory_phase(")
        phase_doc = source[phase_doc_start : phase_doc_start + 900]
        kg_pos = phase_doc.index("Knowledge Graph")
        om_pos = phase_doc.index("Organizational Memory", kg_pos)
        ep_pos = phase_doc.index("Execution Package", om_pos)
        assert kg_pos < om_pos < ep_pos

    def test_run_organizational_memory_phase_docstring_names_the_frozen_position(self) -> None:
        source = _SCRIPT.read_text(encoding="utf-8")
        start = source.index("def run_organizational_memory_phase(")
        end = source.index('"""', source.index('"""', start) + 3)
        docstring = source[start:end]
        assert "CAP-085C" in docstring
        assert "Knowledge Graph" in docstring


@pytest.mark.unit
class TestEngineIsolationAcrossRoots:
    def test_organizational_memory_engine_never_named_in_execution_package(self) -> None:
        """The deterministic engine never crosses into the Execution Package."""
        needle = "DeterministicOrganizationalMemoryEngine"
        offenders: list[Path] = []
        for path in _EXECUTION_PKG.rglob("*.py"):
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip().startswith(("import ", "from ")) and needle in line:
                    offenders.append(path.relative_to(_REPO_ROOT))
        assert offenders == []

    def test_organizational_memory_engine_never_named_in_the_cli_script(self) -> None:
        """The CLI orchestrates through the service only, never the engine directly."""
        source = _SCRIPT.read_text(encoding="utf-8")
        assert "DeterministicOrganizationalMemoryEngine" not in source


@pytest.mark.unit
class TestServiceCompositionRootPostActivation:
    def test_cli_obtains_the_service_only_from_platform_context(self) -> None:
        source = _SCRIPT.read_text(encoding="utf-8")
        assert "context.create_organizational_memory_service()" in source

    def test_platform_context_still_returns_the_deterministic_service(self) -> None:
        """CAP-085C activates the pipeline; it does not change what PlatformContext builds."""
        service = PlatformContext().create_organizational_memory_service()
        assert isinstance(service, DeterministicOrganizationalMemoryService)


@pytest.mark.unit
class TestRoundTripAcrossResultShapes:
    def test_golden_result_round_trips_through_the_serializer_and_the_model(
        self, tmp_path: Path
    ) -> None:
        pipeline = _run_golden_pipeline(tmp_path)
        result = pipeline.organizational_memory_result
        assert result is not None
        dumped = OrganizationalMemorySerializer().render_json(result)
        assert OrganizationalMemoryResult.model_validate(dumped) == result

    def test_disabled_policy_result_round_trips_too(self) -> None:
        """The policy-disabled empty-result path (engine's own short-circuit) round-trips.

        Exercises the same serializer/model round-trip invariant against the
        engine's ``_empty_result`` path (``enable_experience_capture=False``),
        never just the ordinary path — the projection-only invariant must hold
        for every shape the engine can produce.
        """
        from requirement_intelligence.continuous_improvement.engine import (
            DeterministicContinuousImprovementEngine,
        )
        from requirement_intelligence.continuous_improvement.models import (
            HistoricalDatasetReference as CIHistoricalDatasetReference,
        )
        from requirement_intelligence.continuous_improvement.policy import (
            default_improvement_policy,
        )
        from requirement_intelligence.continuous_improvement.rules import (
            default_improvement_rule_catalog,
        )
        from requirement_intelligence.knowledge_graph.engine import (
            DeterministicKnowledgeGraphEngine,
        )
        from requirement_intelligence.knowledge_graph.models import (
            HistoricalDatasetReference as KGHistoricalDatasetReference,
        )
        from requirement_intelligence.knowledge_graph.policy import default_knowledge_graph_policy
        from requirement_intelligence.knowledge_graph.rules import (
            default_knowledge_graph_rule_catalog,
        )
        from requirement_intelligence.organizational_memory.engine import (
            DeterministicOrganizationalMemoryEngine,
        )
        from requirement_intelligence.organizational_memory.policy import (
            default_organizational_memory_policy,
        )

        now = datetime(2026, 7, 16, tzinfo=UTC)
        ci_engine = DeterministicContinuousImprovementEngine(
            policy=default_improvement_policy(),
            rule_catalog=default_improvement_rule_catalog(),
            clock=lambda: now,
        )
        ci_result = ci_engine.improve(
            CIHistoricalDatasetReference(
                dataset_id="ds-disabled",
                dataset_version="1.0.0",
                first_execution_id="ex-1",
                last_execution_id="ex-1",
                execution_count=1,
                history_window=1,
                generated_at=now,
            )
        )
        kg_engine = DeterministicKnowledgeGraphEngine(
            policy=default_knowledge_graph_policy(),
            rule_catalog=default_knowledge_graph_rule_catalog(),
            clock=lambda: now,
        )
        kg_result = kg_engine.build(
            KGHistoricalDatasetReference(
                dataset_id="ds-disabled",
                dataset_version="1.0.0",
                first_execution_id="ex-1",
                last_execution_id="ex-1",
                execution_count=1,
                history_window=1,
                generated_at=now,
            )
        )

        base_policy = default_organizational_memory_policy()
        disabled_policy = base_policy.model_copy(
            update={
                "capability_switches": base_policy.capability_switches.model_copy(
                    update={"enable_experience_capture": False}
                )
            }
        )
        engine = DeterministicOrganizationalMemoryEngine(policy=disabled_policy, clock=lambda: now)
        result = engine.build(ci_result, kg_result)
        assert result.experiences == ()
        dumped = OrganizationalMemorySerializer().render_json(result)
        assert OrganizationalMemoryResult.model_validate(dumped) == result
        # The disabled-policy shape still renders valid, non-empty artifacts.
        report = OrganizationalMemorySerializer().render_report(result)
        metrics = OrganizationalMemorySerializer().render_metrics(result)
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
        for path in (_ORGANIZATIONAL_MEMORY_PKG / "serialization").rglob("*.py"):
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip().startswith(("import ", "from ")):
                    for token in layer_1:
                        assert token not in line, f"{path.name} imports {token}: {line!r}"

    def test_serialization_package_imports_neither_consumed_peer_directly(self) -> None:
        """The serializer projects the result only — it never re-imports either
        consumed Layer 2 peer's own models."""
        for path in (_ORGANIZATIONAL_MEMORY_PKG / "serialization").rglob("*.py"):
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip().startswith(("import ", "from ")):
                    assert "continuous_improvement" not in line, (
                        f"{path.name} imports continuous_improvement: {line!r}"
                    )
                    assert "knowledge_graph" not in line, (
                        f"{path.name} imports knowledge_graph: {line!r}"
                    )

    def test_serialization_package_exports_only_the_serializer(self) -> None:
        import requirement_intelligence.organizational_memory.serialization as pkg

        assert pkg.__all__ == ["OrganizationalMemorySerializer"]


@pytest.mark.unit
class TestManifestArtifactInventoryConsistency:
    def test_generated_artifacts_list_includes_exactly_the_three_organizational_memory_files(
        self, tmp_path: Path
    ) -> None:
        pipeline = _run_golden_pipeline(tmp_path)
        names = {
            entry["name"]
            for entry in pipeline.write_result.manifest["generatedArtifacts"]
            if entry["name"].startswith("organizational_memory")
        }
        assert names == {
            "organizational_memory_result.json",
            "organizational_memory_report.md",
            "organizational_memory_metrics.md",
        }

    def test_every_organizational_memory_artifact_has_a_positive_byte_count(
        self, tmp_path: Path
    ) -> None:
        pipeline = _run_golden_pipeline(tmp_path)
        entries = {
            entry["name"]: entry for entry in pipeline.write_result.manifest["generatedArtifacts"]
        }
        for name in (
            "organizational_memory_result.json",
            "organizational_memory_report.md",
            "organizational_memory_metrics.md",
        ):
            assert entries[name]["bytes"] > 0
