"""Contract and architecture-boundary tests for the QualityAssessmentEngine (CAP-080B.1).

CAP-080B.1 replaces the dormant CAP-080A.2 engine with the real, deterministic
:class:`DeterministicQualityAssessmentEngine`. These tests assert the permanent
contract, the ``PlatformContext`` registration, and the containment/dependency
invariants (ADR-0017 §D21/§D26). Behaviour is exercised in
``test_deterministic_quality_assessment_engine.py``.
"""

from __future__ import annotations

import inspect
from abc import ABC
from pathlib import Path

import pytest

from requirement_intelligence.platform.platform_context import PlatformContext
from requirement_intelligence.quality_governance.assessment import (
    AssessmentPolicy,
    DeterministicQualityAssessmentEngine,
    QualityAssessmentEngine,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_QG_PKG = _REPO_ROOT / "requirement_intelligence" / "quality_governance"
_ASSESS_PKG = _QG_PKG / "assessment"


@pytest.mark.unit
class TestEngineContract:
    def test_contract_is_abstract(self) -> None:
        assert issubclass(QualityAssessmentEngine, ABC)
        with pytest.raises(TypeError):
            QualityAssessmentEngine()  # type: ignore[abstract]

    def test_engine_carries_its_policy(self) -> None:
        policy = PlatformContext().create_assessment_policy()
        assert DeterministicQualityAssessmentEngine(policy=policy).policy == policy

    def test_permanent_signature(self) -> None:
        sig = inspect.signature(QualityAssessmentEngine.assess)
        assert list(sig.parameters) == ["self", "rule_evaluation_result"]
        assert sig.return_annotation == "QualityAssessmentResult"


@pytest.mark.unit
class TestPlatformContextRegistration:
    def test_create_assessment_policy(self) -> None:
        assert isinstance(PlatformContext().create_assessment_policy(), AssessmentPolicy)

    def test_create_engine_returns_deterministic(self) -> None:
        engine = PlatformContext().create_quality_assessment_engine()
        assert isinstance(engine, QualityAssessmentEngine)
        assert isinstance(engine, DeterministicQualityAssessmentEngine)

    def test_engine_constructed_with_policy_only(self) -> None:
        ctx = PlatformContext()
        engine = ctx.create_quality_assessment_engine()
        assert isinstance(engine, DeterministicQualityAssessmentEngine)
        assert engine.policy == ctx.create_assessment_policy()


@pytest.mark.unit
class TestRuntimeContainment:
    def test_only_platform_context_names_the_engine_externally(self) -> None:
        roots = (
            _REPO_ROOT / "requirement_intelligence",
            _REPO_ROOT / "scripts",
            _REPO_ROOT / "app",
        )
        needle = "QualityAssessmentEngine"
        permitted = {Path("requirement_intelligence/platform/platform_context.py")}
        external: set[Path] = set()
        for root in roots:
            if not root.exists():
                continue
            for path in root.rglob("*.py"):
                if "tests" in path.parts or path.is_relative_to(_QG_PKG):
                    continue
                if needle in path.read_text(encoding="utf-8"):
                    external.add(path.relative_to(_REPO_ROOT))
        assert external == permitted


@pytest.mark.unit
class TestDependencyBoundaries:
    def test_assessment_imports_no_execution_package(self) -> None:
        for path in _ASSESS_PKG.rglob("*.py"):
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip().startswith(("import ", "from ")):
                    assert "execution" not in line.lower(), f"{path.name} imports execution"

    def test_assessment_imports_no_upstream_or_downstream_implementation(self) -> None:
        """Assessment imports no Grounding/Validation/CP1/evaluator/decision/governance impl."""
        forbidden_impl = (
            "GroundingStrategy",
            "GroundingService",
            "GroundingPipeline",
            "SupportClassificationEngine",
            "ConfidenceCalculator",
            "GroundingMetricsBuilder",
            "ResponseValidator",
            "CP1Service",
            "CP1Engine",
            "EngineeringContextOrchestrator",
            "QualityRuleEvaluator",
            "DeterministicQualityRuleEvaluator",
            "QualityDecisionEngine",
            "QualityGovernanceService",
            "DormantQualityGovernanceService",
            "RequirementPromptBuilder",
        )
        for path in _ASSESS_PKG.rglob("*.py"):
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip().startswith(("import ", "from ")):
                    for token in forbidden_impl:
                        assert token not in line, f"{path.name} imports {token}"

    def test_assessment_imports_no_raw_upstream_results(self) -> None:
        """Assessment never reads Grounding/Validation/CP1 results directly (ADR-0017 §D21)."""
        forbidden = ("GroundingResult", "ValidationResult", "CP1Result")
        for path in _ASSESS_PKG.rglob("*.py"):
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip().startswith(("import ", "from ")):
                    for token in forbidden:
                        assert token not in line, f"{path.name} imports {token}"

    def test_assessment_imports_no_subsystem_outside_quality_governance(self) -> None:
        forbidden_subsystems = (
            "requirement_intelligence.grounding",
            "requirement_intelligence.validation",
            "requirement_intelligence.cp1",
            "requirement_intelligence.analysis",
            "requirement_intelligence.context_orchestration",
        )
        for path in _ASSESS_PKG.rglob("*.py"):
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip().startswith(("import ", "from ")):
                    for token in forbidden_subsystems:
                        assert token not in line, f"{path.name} imports {token}"

    def test_engine_consumes_only_rule_evaluation_result(self) -> None:
        source = (_ASSESS_PKG / "quality_assessment_engine.py").read_text(encoding="utf-8")
        assert "RuleEvaluationResult" in source
        assert "QualityAssessmentResult" in source
        assert "AssessmentPolicy" in source
