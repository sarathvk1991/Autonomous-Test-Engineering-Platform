"""Architecture-only tests for the manifest purity boundary (CAP-086C, ADR-0029 §D28/§D29).

These tests add no behaviour and change nothing about the pipeline. They exist to keep
the boundary permanently enforced: the manifest owns package metadata and the artifact
inventory only; ``LearningResult`` (and its projection ``learning_result.json``) is the
sole owner of every Learning runtime concept — the candidates, the validations, the
learnings, the confidences, the lifecycles, the metrics, and the summary. Nothing
downstream of it may duplicate that ownership. Mirrors
``test_organizational_memory_manifest_purity_boundary.py`` (CAP-085C, ADR-0027 §D18/§D19).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from requirement_intelligence.execution.manifest_builder import ManifestBuilder
from tests.productization.conftest import _run_golden_pipeline

_REPO_ROOT = Path(__file__).resolve().parents[2]
_EXECUTION_DIR = _REPO_ROOT / "requirement_intelligence" / "execution"

#: Learning runtime tokens the Execution Package must never import. Mirrors the
#: same containment rule enforced for the serializer
#: (``test_learning_serialization.py``), applied to the manifest and writer
#: instead of the serializer.
_FORBIDDEN_LEARNING_RUNTIME_TOKENS = (
    "learning.engine",
    "learning_service",
    "learning.policy",
    "learning.rules",
    "DeterministicLearningEngine",
    "DeterministicLearningService",
    "LearningPolicy",
    "LearningRuleCatalog",
)

#: Manifest keys that would represent runtime state duplicated out of
#: ``LearningResult`` — a candidate, a validation, a learning, a confidence, a
#: lifecycle record, a summary, or a metric value. None of these may ever appear
#: on the manifest; the manifest may only reference the artifact.
_FORBIDDEN_RUNTIME_STATE_KEYS = (
    "learningResult",
    "learningSummary",
    "learningCandidates",
    "learningValidations",
    "learnings",
    "learningConfidences",
    "learningLifecycles",
    "learningMetricsValues",
)

#: The only Learning keys the manifest may ever carry — a flag and two artifact
#: filenames. Package metadata / artifact inventory, never runtime state.
_ALLOWED_LEARNING_KEYS = frozenset(
    {
        "learningExecuted",
        "learningReport",
        "learningMetrics",
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
class TestManifestImportsNoLearningRuntime:
    """ManifestBuilder must never import a Learning runtime implementation class."""

    @pytest.mark.parametrize(
        "filename", ["manifest_builder.py", "execution_data.py", "execution_writer.py"]
    )
    def test_no_forbidden_import(self, filename: str) -> None:
        for line in _import_lines(_source_of(filename)):
            for token in _FORBIDDEN_LEARNING_RUNTIME_TOKENS:
                assert token not in line, f"{filename} must not import {token!r}: {line!r}"


@pytest.mark.unit
class TestManifestContainsNoRuntimeState:
    """The manifest's Learning keys are package metadata only — never runtime state."""

    def test_manifest_source_names_no_forbidden_key(self) -> None:
        """The builder's source code never assigns a forbidden runtime-state manifest key."""
        source = _source_of("manifest_builder.py")
        for key in _FORBIDDEN_RUNTIME_STATE_KEYS:
            assert f'"{key}"' not in source, f"manifest_builder.py must not set {key!r}"

    def test_built_manifest_carries_metadata_keys_only(self, tmp_path: Path) -> None:
        """A real Learning run produces a manifest with exactly the allowed keys."""
        pipeline = _run_golden_pipeline(tmp_path)
        assert pipeline.learning_result is not None

        manifest = ManifestBuilder().build(
            pipeline.execution_data,
            started_timestamp="2026-01-01T00:00:00Z",
            completed_timestamp="2026-01-01T00:00:01Z",
            generated_artifacts=[],
        )
        learning_keys = {key for key in manifest if key.startswith("learning")}
        assert learning_keys == _ALLOWED_LEARNING_KEYS
        for key in _FORBIDDEN_RUNTIME_STATE_KEYS:
            assert key not in manifest


@pytest.mark.unit
class TestLearningAndOrganizationalMemoryKeysStayDisjoint:
    """The two adjacent capabilities' manifest keys never collide or leak into each other."""

    def test_learning_keys_never_reuse_an_organizational_memory_prefix(
        self, tmp_path: Path
    ) -> None:
        pipeline = _run_golden_pipeline(tmp_path)
        manifest = pipeline.write_result.manifest
        learning_keys = {k for k in manifest if k.startswith("learning")}
        organizational_memory_keys = {k for k in manifest if k.startswith("organizationalMemory")}
        assert learning_keys.isdisjoint(organizational_memory_keys)
        assert learning_keys == _ALLOWED_LEARNING_KEYS

    def test_both_capabilities_executed_flags_are_independently_true(self, tmp_path: Path) -> None:
        pipeline = _run_golden_pipeline(tmp_path)
        manifest = pipeline.write_result.manifest
        assert manifest["organizationalMemoryExecuted"] is True
        assert manifest["learningExecuted"] is True


@pytest.mark.unit
class TestExecutionPackageIsProjectionOnly:
    """The Execution Package (writer + manifest) never collects, validates, or generates."""

    def test_writer_imports_only_the_projection_serializer(self) -> None:
        """``execution_writer.py`` may import the Learning *serializer*, never
        anything deeper."""
        source = _source_of("execution_writer.py")
        for line in _import_lines(source):
            if "learning" not in line:
                continue
            allowed = "learning.serialization" in line or "LearningSerializer" in line
            assert allowed, (
                f"execution_writer.py may only import the Learning serializer, "
                f"found: {line!r}"
            )
