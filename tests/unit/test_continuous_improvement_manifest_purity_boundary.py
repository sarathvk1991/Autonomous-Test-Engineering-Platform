"""Architecture-only tests for the manifest purity boundary (CAP-083C, ADR-0022 §D10/§D11).

These tests add no behaviour and change nothing about the pipeline. They exist to keep
the boundary permanently enforced: the manifest owns package metadata and the artifact
inventory only; ``ContinuousImprovementResult`` (and its projection
``continuous_improvement_result.json``) is the sole owner of every continuous
improvement runtime concept — the findings, the trends, the opportunities, the
metrics, and the summary. Nothing downstream of it may duplicate that ownership.
Mirrors ``test_recommendation_manifest_purity_boundary.py`` (CAP-082C, ADR-0019 §D9/§D10).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from requirement_intelligence.execution.manifest_builder import ManifestBuilder
from tests.productization.conftest import _run_golden_pipeline

_REPO_ROOT = Path(__file__).resolve().parents[2]
_EXECUTION_DIR = _REPO_ROOT / "requirement_intelligence" / "execution"

#: Continuous Improvement runtime tokens the Execution Package must never import.
#: Mirrors the same containment rule enforced for the serializer
#: (``test_continuous_improvement_serialization.py``), applied to the manifest and
#: writer instead of the serializer.
_FORBIDDEN_CONTINUOUS_IMPROVEMENT_RUNTIME_TOKENS = (
    "continuous_improvement.engine",
    "continuous_improvement_service",
    "continuous_improvement.policy",
    "continuous_improvement.rules",
    "DeterministicContinuousImprovementEngine",
    "DeterministicContinuousImprovementService",
    "ContinuousImprovementService",
    "ImprovementPolicy",
    "ImprovementRuleCatalog",
    "HistoricalDatasetProvider",
)

#: Manifest keys that would represent runtime state duplicated out of
#: ``ContinuousImprovementResult`` — a finding, a trend, an opportunity, a summary, or
#: a metric value. None of these may ever appear on the manifest; the manifest may
#: only reference the artifact.
_FORBIDDEN_RUNTIME_STATE_KEYS = (
    "continuousImprovementResult",
    "continuousImprovementSummary",
    "continuousImprovementFindings",
    "continuousImprovementTrends",
    "continuousImprovementOpportunities",
    "continuousImprovementDecision",
    "continuousImprovementScore",
)

#: The only continuous improvement keys the manifest may ever carry — a flag and two
#: artifact filenames. Package metadata / artifact inventory, never runtime state.
_ALLOWED_CONTINUOUS_IMPROVEMENT_KEYS = frozenset(
    {
        "continuousImprovementExecuted",
        "continuousImprovementReport",
        "continuousImprovementMetrics",
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
class TestManifestImportsNoContinuousImprovementRuntime:
    """ManifestBuilder must never import a continuous improvement runtime implementation class."""

    @pytest.mark.parametrize(
        "filename", ["manifest_builder.py", "execution_data.py", "execution_writer.py"]
    )
    def test_no_forbidden_import(self, filename: str) -> None:
        for line in _import_lines(_source_of(filename)):
            for token in _FORBIDDEN_CONTINUOUS_IMPROVEMENT_RUNTIME_TOKENS:
                assert token not in line, f"{filename} must not import {token!r}: {line!r}"


@pytest.mark.unit
class TestManifestContainsNoRuntimeState:
    """The manifest's continuous improvement keys are package metadata only — never runtime
    state."""

    def test_manifest_source_names_no_forbidden_key(self) -> None:
        """The builder's source code never assigns a forbidden runtime-state manifest key."""
        source = _source_of("manifest_builder.py")
        for key in _FORBIDDEN_RUNTIME_STATE_KEYS:
            assert f'"{key}"' not in source, f"manifest_builder.py must not set {key!r}"

    def test_built_manifest_carries_metadata_keys_only(self, tmp_path: Path) -> None:
        """A real continuous improvement run produces a manifest with exactly the allowed keys."""
        pipeline = _run_golden_pipeline(tmp_path)
        assert pipeline.continuous_improvement_result is not None

        manifest = ManifestBuilder().build(
            pipeline.execution_data,
            started_timestamp="2026-01-01T00:00:00Z",
            completed_timestamp="2026-01-01T00:00:01Z",
            generated_artifacts=[],
        )
        continuous_improvement_keys = {
            key for key in manifest if key.startswith("continuousImprovement")
        }
        assert continuous_improvement_keys == _ALLOWED_CONTINUOUS_IMPROVEMENT_KEYS
        for key in _FORBIDDEN_RUNTIME_STATE_KEYS:
            assert key not in manifest


@pytest.mark.unit
class TestExecutionPackageIsProjectionOnly:
    """The Execution Package (writer + manifest) never observes, detects, or generates."""

    def test_writer_imports_only_the_projection_serializer(self) -> None:
        """``execution_writer.py`` may import the continuous improvement *serializer*, never
        anything deeper."""
        source = _source_of("execution_writer.py")
        for line in _import_lines(source):
            if "continuous_improvement" not in line:
                continue
            allowed = (
                "continuous_improvement.serialization" in line
                or "ContinuousImprovementSerializer" in line
            )
            assert allowed, (
                f"execution_writer.py may only import the continuous improvement "
                f"serializer, found: {line!r}"
            )
