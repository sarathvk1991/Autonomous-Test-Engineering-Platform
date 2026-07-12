"""Contract and architecture-boundary tests for the QualityRuleEvaluator (CAP-080B).

CAP-080B replaces the dormant CAP-080A.1 evaluator with the real, deterministic
:class:`DeterministicQualityRuleEvaluator`. These tests assert the permanent contract,
the ``PlatformContext`` registration, and the containment/dependency invariants that the
architecture freeze fixes (ADR-0017 §D25). The evaluator's *behaviour* is exercised in
``test_deterministic_quality_rule_evaluator.py``.
"""

from __future__ import annotations

import inspect
from abc import ABC
from pathlib import Path

import pytest

from requirement_intelligence.platform.platform_context import PlatformContext
from requirement_intelligence.quality_governance.evaluation import (
    DeterministicQualityRuleEvaluator,
    QualityRuleEvaluator,
    RuleEvaluationResult,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_QG_PKG = _REPO_ROOT / "requirement_intelligence" / "quality_governance"
_EVAL_PKG = _QG_PKG / "evaluation"


@pytest.mark.unit
class TestEvaluatorContract:
    def test_contract_is_abstract(self) -> None:
        assert issubclass(QualityRuleEvaluator, ABC)
        with pytest.raises(TypeError):
            QualityRuleEvaluator()  # type: ignore[abstract]

    def test_deterministic_evaluator_carries_its_policy_and_catalog(self) -> None:
        ctx = PlatformContext()
        policy = ctx.create_quality_policy()
        catalog = ctx.create_quality_rule_catalog()
        evaluator = DeterministicQualityRuleEvaluator(policy=policy, catalog=catalog)
        assert evaluator.policy == policy
        assert evaluator.catalog == catalog

    def test_permanent_signature(self) -> None:
        params = list(inspect.signature(QualityRuleEvaluator.evaluate).parameters)
        assert params == ["self", "grounding_result", "validation_result", "cp1_result"]
        assert (
            inspect.signature(QualityRuleEvaluator.evaluate).return_annotation
            == "RuleEvaluationResult"
        )


@pytest.mark.unit
class TestPlatformContextRegistration:
    def test_create_returns_deterministic_evaluator(self) -> None:
        evaluator = PlatformContext().create_quality_rule_evaluator()
        assert isinstance(evaluator, QualityRuleEvaluator)
        assert isinstance(evaluator, DeterministicQualityRuleEvaluator)

    def test_platform_context_is_the_composition_root(self) -> None:
        """The evaluator is constructed with the governed policy and catalogue."""
        ctx = PlatformContext()
        evaluator = ctx.create_quality_rule_evaluator()
        assert isinstance(evaluator, DeterministicQualityRuleEvaluator)
        assert evaluator.policy == ctx.create_quality_policy()
        assert evaluator.catalog == ctx.create_quality_rule_catalog()


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

        It may import only the three frozen result contracts (and their enums). This
        guard watches imports, not docstrings.
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

    def test_evaluator_imports_no_downstream_governance_layer(self) -> None:
        """The evaluator depends on nothing downstream of its own boundary.

        Rule Catalogue → Evaluator → RuleEvaluationResult. It must not import
        Assessment, Decision, the Governance Service, or the Execution Package.
        """
        forbidden = (
            "quality_assessment_engine",
            "QualityAssessmentEngine",
            "quality_decision_engine",
            "QualityDecisionEngine",
            "quality_governance_service",
            "QualityGovernanceService",
        )
        source = (_EVAL_PKG / "quality_rule_evaluator.py").read_text(encoding="utf-8")
        for line in source.splitlines():
            if line.strip().startswith(("import ", "from ")):
                for token in forbidden:
                    assert token not in line, f"evaluator imports downstream {token}"

    def test_evaluator_consumes_only_the_three_result_contracts(self) -> None:
        source = (_EVAL_PKG / "quality_rule_evaluator.py").read_text(encoding="utf-8")
        assert "GroundingResult" in source
        assert "ValidationResult" in source
        assert "CP1Result" in source

    def test_evaluator_consumes_catalog_and_policy(self) -> None:
        source = (_EVAL_PKG / "quality_rule_evaluator.py").read_text(encoding="utf-8")
        assert "QualityRuleCatalog" in source
        assert "QualityPolicy" in source


@pytest.mark.unit
class TestResultContractSelfContained:
    def test_result_records_evaluator_identity(self) -> None:
        """The boundary names the evaluator that produced it, independently of versions."""
        assert "evaluator_name" in RuleEvaluationResult.model_fields
        assert "evaluator_version" in RuleEvaluationResult.model_fields
        assert "policy_version" in RuleEvaluationResult.model_fields
        assert "result_version" in RuleEvaluationResult.model_fields
