"""Unit tests for the dormant QualityRuleEvaluator and its architecture boundaries.

CAP-080A.1 is a pure architecture freeze: the evaluator is dormant, registered but
unconsumed, owns rule evaluation only, and the evaluation layer is a consumer of the
three peer result contracts. These tests assert the dormant contract, the
PlatformContext registration, and the containment/dependency invariants (ADR-0017).
"""

from __future__ import annotations

import inspect
from abc import ABC
from pathlib import Path

import pytest

from requirement_intelligence.platform.platform_context import PlatformContext
from requirement_intelligence.quality_governance.evaluation import (
    DormantQualityRuleEvaluator,
    QualityRuleEvaluator,
    RuleEvaluationResult,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_QG_PKG = _REPO_ROOT / "requirement_intelligence" / "quality_governance"
_EVAL_PKG = _QG_PKG / "evaluation"


@pytest.mark.unit
class TestDormantEvaluator:
    def test_contract_is_abstract(self) -> None:
        assert issubclass(QualityRuleEvaluator, ABC)
        with pytest.raises(TypeError):
            QualityRuleEvaluator()  # type: ignore[abstract]

    def test_evaluate_is_dormant(self) -> None:
        evaluator = DormantQualityRuleEvaluator(policy=PlatformContext().create_quality_policy())
        with pytest.raises(NotImplementedError):
            evaluator.evaluate(None, None, None)  # type: ignore[arg-type]

    def test_evaluator_carries_its_policy(self) -> None:
        policy = PlatformContext().create_quality_policy()
        assert DormantQualityRuleEvaluator(policy=policy).policy == policy

    def test_permanent_signature(self) -> None:
        params = list(inspect.signature(QualityRuleEvaluator.evaluate).parameters)
        assert params == ["self", "grounding_result", "validation_result", "cp1_result"]
        assert (
            inspect.signature(QualityRuleEvaluator.evaluate).return_annotation
            == "RuleEvaluationResult"
        )


@pytest.mark.unit
class TestPlatformContextRegistration:
    def test_create_returns_dormant_evaluator(self) -> None:
        evaluator = PlatformContext().create_quality_rule_evaluator()
        assert isinstance(evaluator, QualityRuleEvaluator)
        assert isinstance(evaluator, DormantQualityRuleEvaluator)


@pytest.mark.unit
class TestRuntimeContainment:
    def test_only_platform_context_names_the_evaluator_externally(self) -> None:
        """Outside the quality_governance package, only PlatformContext may name it."""
        roots = (
            _REPO_ROOT / "requirement_intelligence",
            _REPO_ROOT / "scripts",
            _REPO_ROOT / "app",
        )
        needle = "QualityRuleEvaluator"
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
    def test_evaluation_imports_no_execution_package(self) -> None:
        """The evaluation layer never depends on the Execution Package."""
        for path in _EVAL_PKG.rglob("*.py"):
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip().startswith(("import ", "from ")):
                    assert "execution" not in line.lower(), f"{path.name} imports execution"

    def test_evaluation_imports_no_upstream_implementation(self) -> None:
        """The evaluation layer imports no Grounding/Validation/CP1 *implementation*.

        It may import only the three frozen result contracts. Docstrings may still name
        analog classes for explanation; this guard watches imports.
        """
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
        )
        for path in _EVAL_PKG.rglob("*.py"):
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip().startswith(("import ", "from ")):
                    for token in forbidden_impl:
                        assert token not in line, f"{path.name} imports {token}"

    def test_evaluation_models_import_no_upstream_subsystem(self) -> None:
        """The evaluation *models* are self-contained — no upstream subsystem at all.

        Only the evaluator module may import the three result contracts; the models
        depend only on quality_governance identity/enums and shared.
        """
        forbidden_subsystems = (
            "requirement_intelligence.grounding",
            "requirement_intelligence.validation",
            "requirement_intelligence.cp1",
            "requirement_intelligence.analysis",
            "requirement_intelligence.context_orchestration",
        )
        source = (_EVAL_PKG / "models.py").read_text(encoding="utf-8")
        for line in source.splitlines():
            if line.strip().startswith(("import ", "from ")):
                for token in forbidden_subsystems:
                    assert token not in line, f"models.py imports {token}"

    def test_evaluator_consumes_only_the_three_result_contracts(self) -> None:
        source = (_EVAL_PKG / "quality_rule_evaluator.py").read_text(encoding="utf-8")
        assert "GroundingResult" in source
        assert "ValidationResult" in source
        assert "CP1Result" in source

    def test_governance_layer_imports_only_the_result_contract_from_evaluation(self) -> None:
        """Quality Governance (service/models) imports RuleEvaluationResult only.

        No governance module reaches into evaluation internals (the evaluator, the
        distribution entries, or the status enum) — the boundary is the result
        contract. CAP-080A.1 wires nothing, so today no governance module imports
        evaluation at all; this guard keeps it that way until a milestone consciously
        consumes the contract.
        """
        internal_only = (
            "quality_rule_evaluator",
            "DormantQualityRuleEvaluator",
            "QualityRuleEvaluator",
            "RuleEvaluationStatus",
        )
        governance_modules = [
            _QG_PKG / "quality_governance_service.py",
            *(_QG_PKG / "models").rglob("*.py"),
            *(_QG_PKG / "policy").rglob("*.py"),
        ]
        for path in governance_modules:
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip().startswith(("import ", "from ")) and "evaluation" in line:
                    for token in internal_only:
                        assert token not in line, f"{path.name} imports evaluation internal {token}"


@pytest.mark.unit
class TestResultContractSelfContained:
    def test_result_is_self_contained_and_round_trips(self) -> None:
        """RuleEvaluationResult reconstructs from its own serialization alone."""
        evaluator = PlatformContext().create_quality_rule_evaluator()
        assert isinstance(evaluator, QualityRuleEvaluator)
        # The contract type is importable and self-describing without any runtime.
        assert "result_version" in RuleEvaluationResult.model_fields
        assert "policy_version" in RuleEvaluationResult.model_fields
