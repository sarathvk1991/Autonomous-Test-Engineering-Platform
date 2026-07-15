"""Architecture-only tests for the manifest purity boundary (CAP-082C, ADR-0019 §D9/§D10).

These tests add no behaviour and change nothing about the pipeline. They exist to keep
the boundary permanently enforced: the manifest owns package metadata and the artifact
inventory only; ``RecommendationResult`` (and its projection
``recommendation_result.json``) is the sole owner of every recommendation runtime
concept — the recommendations, the groups, the priorities, the confidence, the
metrics, and the summary. Nothing downstream of it may duplicate that ownership.
Mirrors ``test_manifest_purity_boundary.py`` (CAP-080D.1, ADR-0017 §D31).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from requirement_intelligence.execution.manifest_builder import ManifestBuilder
from tests.productization.conftest import _run_golden_pipeline

_REPO_ROOT = Path(__file__).resolve().parents[2]
_EXECUTION_DIR = _REPO_ROOT / "requirement_intelligence" / "execution"

#: Recommendation runtime tokens the Execution Package must never import. Mirrors the
#: forbidden list already enforced for the serializer in ``TestSerializationBoundary``
#: (``test_recommendation_serialization.py``) — the same containment rule, applied to
#: the manifest and writer instead of the serializer.
_FORBIDDEN_RECOMMENDATION_RUNTIME_TOKENS = (
    "recommendation.engine",
    "recommendation.recommendation_service",
    "recommendation.policy",
    "recommendation.rules",
    "DeterministicRecommendationEngine",
    "DeterministicRecommendationService",
    "RecommendationService",
    "RecommendationPolicy",
    "RecommendationRuleCatalog",
)

#: Manifest keys that would represent runtime state duplicated out of
#: ``RecommendationResult`` — a priority, a count, a summary, a decision, a group, or a
#: metric value. None of these may ever appear on the manifest; the manifest may only
#: reference the artifact.
_FORBIDDEN_RUNTIME_STATE_KEYS = (
    "recommendationPriority",
    "recommendationCounts",
    "recommendationSummary",
    "recommendationDecisions",
    "recommendationGroups",
    "recommendationMetricsValues",
    "recommendationConfidence",
)

#: The only recommendation keys the manifest may ever carry — a flag and two artifact
#: filenames. Package metadata / artifact inventory, never runtime state.
_ALLOWED_RECOMMENDATION_KEYS = frozenset(
    {
        "recommendationExecuted",
        "recommendationReport",
        "recommendationMetrics",
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
class TestManifestImportsNoRecommendationRuntime:
    """ManifestBuilder must never import a recommendation runtime implementation class."""

    @pytest.mark.parametrize(
        "filename", ["manifest_builder.py", "execution_data.py", "execution_writer.py"]
    )
    def test_no_forbidden_import(self, filename: str) -> None:
        for line in _import_lines(_source_of(filename)):
            for token in _FORBIDDEN_RECOMMENDATION_RUNTIME_TOKENS:
                assert token not in line, f"{filename} must not import {token!r}: {line!r}"


@pytest.mark.unit
class TestManifestContainsNoRuntimeState:
    """The manifest's recommendation keys are package metadata only — never runtime state."""

    def test_manifest_source_names_no_forbidden_key(self) -> None:
        """The builder's source code never assigns a forbidden runtime-state manifest key."""
        source = _source_of("manifest_builder.py")
        for key in _FORBIDDEN_RUNTIME_STATE_KEYS:
            assert f'"{key}"' not in source, f"manifest_builder.py must not set {key!r}"

    def test_built_manifest_carries_metadata_keys_only(self, tmp_path: Path) -> None:
        """A real recommendation run produces a manifest with exactly the allowed keys."""
        pipeline = _run_golden_pipeline(tmp_path)
        assert pipeline.recommendation_result is not None

        manifest = ManifestBuilder().build(
            pipeline.execution_data,
            started_timestamp="2026-01-01T00:00:00Z",
            completed_timestamp="2026-01-01T00:00:01Z",
            generated_artifacts=[],
        )
        recommendation_keys = {key for key in manifest if key.startswith("recommendation")}
        assert recommendation_keys == _ALLOWED_RECOMMENDATION_KEYS
        for key in _FORBIDDEN_RUNTIME_STATE_KEYS:
            assert key not in manifest


@pytest.mark.unit
class TestExecutionPackageIsProjectionOnly:
    """The Execution Package (writer + manifest) never generates, prioritizes, or groups."""

    def test_writer_imports_only_the_projection_serializer(self) -> None:
        """``execution_writer.py`` may import the recommendation *serializer*, nothing deeper."""
        source = _source_of("execution_writer.py")
        for line in _import_lines(source):
            if "recommendation" not in line:
                continue
            allowed = "recommendation.serialization" in line or "RecommendationSerializer" in line
            assert allowed, (
                f"execution_writer.py may only import the recommendation serializer, "
                f"found: {line!r}"
            )
