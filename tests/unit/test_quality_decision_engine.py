"""Unit tests for the dormant QualityDecisionEngine and its architecture boundaries.

CAP-080A.3 is a pure architecture freeze: the engine is dormant, registered but
unconsumed, is the sole owner of the release decision, and consumes only
QualityAssessmentResult. These tests assert the dormant contract, the PlatformContext
registration, and the containment/dependency invariants (ADR-0017 §D23).
"""

from __future__ import annotations

import inspect
from abc import ABC
from pathlib import Path

import pytest

from requirement_intelligence.platform.platform_context import PlatformContext
from requirement_intelligence.quality_governance.decision import (
    DecisionPolicy,
    DormantQualityDecisionEngine,
    QualityDecisionEngine,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_QG_PKG = _REPO_ROOT / "requirement_intelligence" / "quality_governance"
_DECISION_PKG = _QG_PKG / "decision"


@pytest.mark.unit
class TestDormantEngine:
    def test_contract_is_abstract(self) -> None:
        assert issubclass(QualityDecisionEngine, ABC)
        with pytest.raises(TypeError):
            QualityDecisionEngine()  # type: ignore[abstract]

    def test_decide_is_dormant(self) -> None:
        engine = DormantQualityDecisionEngine(policy=PlatformContext().create_decision_policy())
        with pytest.raises(NotImplementedError):
            engine.decide(None)  # type: ignore[arg-type]

    def test_engine_carries_its_policy(self) -> None:
        policy = PlatformContext().create_decision_policy()
        assert DormantQualityDecisionEngine(policy=policy).policy == policy

    def test_permanent_signature(self) -> None:
        sig = inspect.signature(QualityDecisionEngine.decide)
        assert list(sig.parameters) == ["self", "quality_assessment_result"]
        assert sig.return_annotation == "QualityDecisionResult"


@pytest.mark.unit
class TestPlatformContextRegistration:
    def test_create_decision_policy(self) -> None:
        assert isinstance(PlatformContext().create_decision_policy(), DecisionPolicy)

    def test_create_engine_returns_dormant(self) -> None:
        engine = PlatformContext().create_quality_decision_engine()
        assert isinstance(engine, QualityDecisionEngine)
        assert isinstance(engine, DormantQualityDecisionEngine)


@pytest.mark.unit
class TestRuntimeContainment:
    def test_only_platform_context_names_the_engine_externally(self) -> None:
        roots = (
            _REPO_ROOT / "requirement_intelligence",
            _REPO_ROOT / "scripts",
            _REPO_ROOT / "app",
        )
        needle = "QualityDecisionEngine"
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
    def test_decision_imports_no_execution_package(self) -> None:
        for path in _DECISION_PKG.rglob("*.py"):
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip().startswith(("import ", "from ")):
                    assert "execution" not in line.lower(), f"{path.name} imports execution"

    def test_decision_consumes_only_the_assessment_result(self) -> None:
        """Decision reads only QualityAssessmentResult — never the earlier boundaries.

        ADR-0017 Recommendation 1: never RuleEvaluationResult, GroundingResult,
        ValidationResult, or CP1Result. Docstrings may name them for explanation; this
        guard watches imports.
        """
        forbidden = (
            "RuleEvaluationResult",
            "GroundingResult",
            "ValidationResult",
            "CP1Result",
        )
        for path in _DECISION_PKG.rglob("*.py"):
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip().startswith(("import ", "from ")):
                    for token in forbidden:
                        assert token not in line, f"{path.name} imports {token}"

    def test_decision_imports_no_upstream_or_downstream_implementation(self) -> None:
        forbidden_impl = (
            "GroundingStrategy",
            "GroundingService",
            "SupportClassificationEngine",
            "ConfidenceCalculator",
            "ResponseValidator",
            "CP1Service",
            "CP1Engine",
            "EngineeringContextOrchestrator",
            "QualityRuleEvaluator",
            "DormantQualityRuleEvaluator",
            "QualityAssessmentEngine",
            "DormantQualityAssessmentEngine",
            "QualityGovernanceService",
            "DormantQualityGovernanceService",
            "RequirementPromptBuilder",
        )
        for path in _DECISION_PKG.rglob("*.py"):
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip().startswith(("import ", "from ")):
                    for token in forbidden_impl:
                        assert token not in line, f"{path.name} imports {token}"

    def test_decision_imports_no_subsystem_outside_quality_governance(self) -> None:
        forbidden_subsystems = (
            "requirement_intelligence.grounding",
            "requirement_intelligence.validation",
            "requirement_intelligence.cp1",
            "requirement_intelligence.analysis",
            "requirement_intelligence.context_orchestration",
        )
        for path in _DECISION_PKG.rglob("*.py"):
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip().startswith(("import ", "from ")):
                    for token in forbidden_subsystems:
                        assert token not in line, f"{path.name} imports {token}"

    def test_engine_consumes_only_assessment_result(self) -> None:
        source = (_DECISION_PKG / "quality_decision_engine.py").read_text(encoding="utf-8")
        import_lines = [
            line for line in source.splitlines() if line.strip().startswith(("import ", "from "))
        ]
        blob = "\n".join(import_lines)
        assert "QualityAssessmentResult" in blob
        assert "QualityDecisionResult" in blob
        assert "DecisionPolicy" in blob
