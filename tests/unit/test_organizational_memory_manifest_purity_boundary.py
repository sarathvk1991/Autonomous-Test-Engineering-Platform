"""Architecture-only tests for the manifest purity boundary (CAP-085C, ADR-0027 §D18/§D19).

These tests add no behaviour and change nothing about the pipeline. They exist to keep
the boundary permanently enforced: the manifest owns package metadata and the artifact
inventory only; ``OrganizationalMemoryResult`` (and its projection
``organizational_memory_result.json``) is the sole owner of every Organizational Memory
runtime concept — the experiences, the lessons, the best practices, the promotions, the
lifecycles, the metrics, and the summary. Nothing downstream of it may duplicate that
ownership. Mirrors ``test_knowledge_graph_manifest_purity_boundary.py`` (CAP-084C,
ADR-0023 §D11/§D12).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from requirement_intelligence.execution.manifest_builder import ManifestBuilder
from tests.productization.conftest import _run_golden_pipeline

_REPO_ROOT = Path(__file__).resolve().parents[2]
_EXECUTION_DIR = _REPO_ROOT / "requirement_intelligence" / "execution"

#: Organizational Memory runtime tokens the Execution Package must never import.
#: Mirrors the same containment rule enforced for the serializer
#: (``test_organizational_memory_serialization.py``), applied to the manifest and
#: writer instead of the serializer.
_FORBIDDEN_ORGANIZATIONAL_MEMORY_RUNTIME_TOKENS = (
    "organizational_memory.engine",
    "organizational_memory_service",
    "organizational_memory.policy",
    "organizational_memory.rules",
    "DeterministicOrganizationalMemoryEngine",
    "DeterministicOrganizationalMemoryService",
    "OrganizationalMemoryPolicy",
    "PromotionRuleCatalog",
)

#: Manifest keys that would represent runtime state duplicated out of
#: ``OrganizationalMemoryResult`` — an experience, a lesson, a best practice, a
#: promotion, a lifecycle record, a summary, or a metric value. None of these may
#: ever appear on the manifest; the manifest may only reference the artifact.
_FORBIDDEN_RUNTIME_STATE_KEYS = (
    "organizationalMemoryResult",
    "organizationalMemorySummary",
    "organizationalMemoryExperiences",
    "organizationalMemoryLessons",
    "organizationalMemoryBestPractices",
    "organizationalMemoryPromotions",
    "organizationalMemoryLifecycles",
    "organizationalMemoryMetricsValues",
)

#: The only Organizational Memory keys the manifest may ever carry — a flag and
#: two artifact filenames. Package metadata / artifact inventory, never runtime
#: state.
_ALLOWED_ORGANIZATIONAL_MEMORY_KEYS = frozenset(
    {
        "organizationalMemoryExecuted",
        "organizationalMemoryReport",
        "organizationalMemoryMetrics",
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
class TestManifestImportsNoOrganizationalMemoryRuntime:
    """ManifestBuilder must never import an Organizational Memory runtime implementation class."""

    @pytest.mark.parametrize(
        "filename", ["manifest_builder.py", "execution_data.py", "execution_writer.py"]
    )
    def test_no_forbidden_import(self, filename: str) -> None:
        for line in _import_lines(_source_of(filename)):
            for token in _FORBIDDEN_ORGANIZATIONAL_MEMORY_RUNTIME_TOKENS:
                assert token not in line, f"{filename} must not import {token!r}: {line!r}"


@pytest.mark.unit
class TestManifestContainsNoRuntimeState:
    """The manifest's Organizational Memory keys are package metadata only — never runtime state."""

    def test_manifest_source_names_no_forbidden_key(self) -> None:
        """The builder's source code never assigns a forbidden runtime-state manifest key."""
        source = _source_of("manifest_builder.py")
        for key in _FORBIDDEN_RUNTIME_STATE_KEYS:
            assert f'"{key}"' not in source, f"manifest_builder.py must not set {key!r}"

    def test_built_manifest_carries_metadata_keys_only(self, tmp_path: Path) -> None:
        """A real Organizational Memory run produces a manifest with exactly the allowed keys."""
        pipeline = _run_golden_pipeline(tmp_path)
        assert pipeline.organizational_memory_result is not None

        manifest = ManifestBuilder().build(
            pipeline.execution_data,
            started_timestamp="2026-01-01T00:00:00Z",
            completed_timestamp="2026-01-01T00:00:01Z",
            generated_artifacts=[],
        )
        organizational_memory_keys = {
            key for key in manifest if key.startswith("organizationalMemory")
        }
        assert organizational_memory_keys == _ALLOWED_ORGANIZATIONAL_MEMORY_KEYS
        for key in _FORBIDDEN_RUNTIME_STATE_KEYS:
            assert key not in manifest


@pytest.mark.unit
class TestOrganizationalMemoryAndKnowledgeGraphKeysStayDisjoint:
    """The two peer capabilities' manifest keys never collide or leak into each other."""

    def test_organizational_memory_keys_never_reuse_a_knowledge_graph_prefix(
        self, tmp_path: Path
    ) -> None:
        pipeline = _run_golden_pipeline(tmp_path)
        manifest = pipeline.write_result.manifest
        organizational_memory_keys = {k for k in manifest if k.startswith("organizationalMemory")}
        knowledge_graph_keys = {k for k in manifest if k.startswith("knowledgeGraph")}
        assert organizational_memory_keys.isdisjoint(knowledge_graph_keys)
        assert organizational_memory_keys == _ALLOWED_ORGANIZATIONAL_MEMORY_KEYS

    def test_both_capabilities_executed_flags_are_independently_true(self, tmp_path: Path) -> None:
        pipeline = _run_golden_pipeline(tmp_path)
        manifest = pipeline.write_result.manifest
        assert manifest["knowledgeGraphExecuted"] is True
        assert manifest["organizationalMemoryExecuted"] is True


@pytest.mark.unit
class TestExecutionPackageIsProjectionOnly:
    """The Execution Package (writer + manifest) never captures, promotes, or records."""

    def test_writer_imports_only_the_projection_serializer(self) -> None:
        """``execution_writer.py`` may import the Organizational Memory *serializer*,
        never anything deeper."""
        source = _source_of("execution_writer.py")
        for line in _import_lines(source):
            if "organizational_memory" not in line:
                continue
            allowed = (
                "organizational_memory.serialization" in line
                or "OrganizationalMemorySerializer" in line
            )
            assert allowed, (
                f"execution_writer.py may only import the Organizational Memory "
                f"serializer, found: {line!r}"
            )
