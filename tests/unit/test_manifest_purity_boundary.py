"""Architecture-only tests for the manifest purity boundary (CAP-080D.1, ADR-0017 §D31).

These tests add no behaviour and change nothing about the pipeline. They exist to keep the
boundary permanently enforced: the manifest owns package metadata and the artifact inventory
only; ``QualityGovernanceResult`` (and its projection ``quality_governance_result.json``) is
the sole owner of every governance runtime concept — the decision, the score, the findings,
the assessment, the recommendations, and release readiness. Nothing downstream of it may
duplicate that ownership.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from requirement_intelligence.execution.manifest_builder import ManifestBuilder
from tests.productization.conftest import _run_golden_pipeline

_REPO_ROOT = Path(__file__).resolve().parents[2]
_EXECUTION_DIR = _REPO_ROOT / "requirement_intelligence" / "execution"

#: Governance runtime tokens the Execution Package must never import. Mirrors the forbidden
#: list already enforced for the serializer in ``TestSerializationBoundary`` — the same
#: containment rule, applied to the manifest and writer instead of the serializer.
_FORBIDDEN_GOVERNANCE_RUNTIME_TOKENS = (
    "quality_governance.evaluation",
    "quality_governance.assessment",
    "quality_governance.decision",
    "quality_governance.pipeline",
    "quality_governance.builder",
    "quality_governance.policy",
    "quality_governance.rules",
    "quality_governance_service",
    "QualityGovernancePipeline",
    "QualityRuleEvaluator",
    "QualityAssessmentEngine",
    "QualityDecisionEngine",
    "QualityGovernanceService",
)

#: Manifest keys that would represent runtime state duplicated out of ``QualityGovernanceResult``
#: — the decision, a score, findings, recommendations, or a versioned decision axis. None of
#: these may ever appear on the manifest; the manifest may only reference the artifact.
_FORBIDDEN_RUNTIME_STATE_KEYS = (
    "qualityGovernanceDecision",
    "qualityGovernanceDecisionVersion",
    "qualityGovernanceScore",
    "qualityGovernanceFindings",
    "qualityGovernanceRecommendations",
    "qualityGovernanceAssessment",
)

#: The only governance keys the manifest may ever carry — a flag and two artifact filenames.
#: Package metadata / artifact inventory, never runtime state.
_ALLOWED_GOVERNANCE_KEYS = frozenset(
    {
        "qualityGovernanceExecuted",
        "qualityGovernanceReport",
        "qualityGovernanceSummary",
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
class TestManifestImportsNoGovernanceRuntime:
    """ManifestBuilder must never import a governance runtime implementation class."""

    @pytest.mark.parametrize(
        "filename", ["manifest_builder.py", "execution_data.py", "execution_writer.py"]
    )
    def test_no_forbidden_import(self, filename: str) -> None:
        for line in _import_lines(_source_of(filename)):
            for token in _FORBIDDEN_GOVERNANCE_RUNTIME_TOKENS:
                assert token not in line, f"{filename} must not import {token!r}: {line!r}"

@pytest.mark.unit
class TestManifestContainsNoRuntimeState:
    """The manifest's governance keys are package metadata only — never runtime state."""

    def test_manifest_source_names_no_forbidden_key(self) -> None:
        """The builder's source code never assigns a forbidden runtime-state manifest key."""
        source = _source_of("manifest_builder.py")
        for key in _FORBIDDEN_RUNTIME_STATE_KEYS:
            assert f'"{key}"' not in source, f"manifest_builder.py must not set {key!r}"

    def test_built_manifest_carries_metadata_keys_only(self, tmp_path: Path) -> None:
        """A real governance run produces a manifest with exactly the allowed governance keys."""
        pipeline = _run_golden_pipeline(tmp_path)
        assert pipeline.quality_governance_result is not None

        manifest = ManifestBuilder().build(
            pipeline.execution_data,
            started_timestamp="2026-01-01T00:00:00Z",
            completed_timestamp="2026-01-01T00:00:01Z",
            generated_artifacts=[],
        )
        governance_keys = {key for key in manifest if key.startswith("qualityGovernance")}
        assert governance_keys == _ALLOWED_GOVERNANCE_KEYS
        for key in _FORBIDDEN_RUNTIME_STATE_KEYS:
            assert key not in manifest


@pytest.mark.unit
class TestExecutionPackageIsProjectionOnly:
    """The Execution Package (writer + manifest) never evaluates, assesses, or decides."""

    def test_writer_imports_only_the_projection_serializer(self) -> None:
        """``execution_writer.py`` may import the governance *serializer*, nothing deeper."""
        source = _source_of("execution_writer.py")
        for line in _import_lines(source):
            if "quality_governance" not in line:
                continue
            allowed = (
                "quality_governance.serialization" in line
                or "QualityGovernanceSerializer" in line
            )
            assert allowed, f"execution_writer.py may only import the serializer, found: {line!r}"
