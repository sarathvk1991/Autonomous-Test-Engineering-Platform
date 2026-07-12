"""Architecture-only tests for the CAP-080B.1.1 QualityAssessmentResult freeze.

These assert the *runtime contract* invariants — not behaviour (behaviour lives in
``test_deterministic_quality_assessment_engine.py``). They cover the independent
runtime-contract version, serialization round-trip / immutability / equality, the
explainability invariant (the result is self-contained), and the frozen runtime vs
Execution-Package and Assessment→Decision boundaries (ADR-0017 §D27).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from requirement_intelligence.quality_governance.assessment import (
    QUALITY_ASSESSMENT_RESULT_VERSION,
    QualityAssessmentResult,
    default_assessment_policy,
)
from requirement_intelligence.quality_governance.assessment.quality_assessment_engine import (
    DeterministicQualityAssessmentEngine,
)
from requirement_intelligence.quality_governance.evaluation import (
    DeterministicQualityRuleEvaluator,
)
from requirement_intelligence.quality_governance.identity import (
    AssessmentOutcomeVersion,
    AssessmentPolicyVersion,
    QualityAssessmentResultVersion,
)
from requirement_intelligence.quality_governance.policy import default_quality_policy
from requirement_intelligence.quality_governance.rules import default_quality_rule_catalog
from tests.unit.quality_governance_helpers import (
    make_cp1_result,
    make_grounding_result,
    make_validation_result,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_QG_PKG = _REPO_ROOT / "requirement_intelligence" / "quality_governance"
_ASSESS_PKG = _QG_PKG / "assessment"


def _result(*, grounding_score: int = 40) -> QualityAssessmentResult:
    evaluator = DeterministicQualityRuleEvaluator(
        policy=default_quality_policy(), catalog=default_quality_rule_catalog()
    )
    rule_result = evaluator.evaluate(
        make_grounding_result(grounding_score=grounding_score),
        make_validation_result(),
        make_cp1_result(),
    )
    return DeterministicQualityAssessmentEngine(policy=default_assessment_policy()).assess(
        rule_result
    )


@pytest.mark.unit
class TestRuntimeContractVersion:
    def test_result_version_defaults_to_the_contract_version(self) -> None:
        assert _result().result_version == QUALITY_ASSESSMENT_RESULT_VERSION

    def test_result_version_is_its_own_type(self) -> None:
        assert isinstance(QUALITY_ASSESSMENT_RESULT_VERSION, QualityAssessmentResultVersion)

    def test_runtime_version_is_independent_of_other_axes(self) -> None:
        """The runtime-contract version is a distinct axis from outcome/policy versions."""
        assert not issubclass(QualityAssessmentResultVersion, AssessmentOutcomeVersion)
        assert not issubclass(QualityAssessmentResultVersion, AssessmentPolicyVersion)
        result = _result()
        # The contract version is carried independently of the governing policy version.
        assert result.result_version == QUALITY_ASSESSMENT_RESULT_VERSION
        assert result.policy_version == default_assessment_policy().policy_version


@pytest.mark.unit
class TestSelfContainedContract:
    def test_round_trips_from_serialization_alone(self) -> None:
        result = _result()
        dumped = result.model_dump(mode="json", by_alias=True)
        assert QualityAssessmentResult.model_validate(dumped) == result

    def test_deterministic_equality(self) -> None:
        assert _result() == _result()

    def test_is_immutable(self) -> None:
        result = _result()
        with pytest.raises(ValidationError):
            result.analysis_id = "other"  # type: ignore[misc]

    def test_explainable_from_contract_fields_alone(self) -> None:
        """Every observation lives in references/statistics/summary/outcome — nothing external."""
        assert _result() is not None  # the contract constructs from an evaluation alone
        fields = set(QualityAssessmentResult.model_fields)
        assert {
            "references",
            "assessment_summary",
            "assessment_statistics",
            "overall_assessment",
        } <= fields
        # The contract references its input by id; it never embeds the RuleEvaluationResult.
        assert "rule_evaluation_result" not in fields
        assert "rule_evaluation_result_id" in fields

    def test_carries_no_release_decision_or_score(self) -> None:
        fields = set(QualityAssessmentResult.model_fields)
        assert "decision" not in fields
        assert "quality_decision" not in fields
        assert "quality_score" not in fields
        assert "governance_summary" not in fields


@pytest.mark.unit
class TestRuntimeAndExecutionBoundary:
    def test_assessment_imports_no_execution_package(self) -> None:
        """The runtime Assessment layer never depends on the Execution Package."""
        for path in _ASSESS_PKG.rglob("*.py"):
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip().startswith(("import ", "from ")):
                    assert "execution" not in line.lower(), f"{path.name} imports execution"

    def test_assessment_models_import_no_runtime_engine(self) -> None:
        """The QualityAssessmentResult model imports no engine, evaluator, or renderer."""
        source = (_ASSESS_PKG / "models.py").read_text(encoding="utf-8")
        for token in (
            "DeterministicQualityAssessmentEngine",
            "QualityAssessmentEngine",
            "DeterministicQualityRuleEvaluator",
            "QualityDecisionEngine",
            "QualityGovernanceService",
        ):
            for line in source.splitlines():
                if line.strip().startswith(("import ", "from ")):
                    assert token not in line, f"models.py imports {token}"

    def test_no_execution_package_consumes_assessment_runtime(self) -> None:
        """No Execution Package re-runs Assessment: the engine is named only by PlatformContext.

        A projection reads a ``QualityAssessmentResult``; it never invokes the engine.
        Guards the serialization invariant before any assessment renderer exists.
        """
        needle = "DeterministicQualityAssessmentEngine"
        permitted = {
            Path("requirement_intelligence/platform/platform_context.py"),
        }
        external: set[Path] = set()
        for root in (_REPO_ROOT / "requirement_intelligence",):
            for path in root.rglob("*.py"):
                if "tests" in path.parts or path.is_relative_to(_QG_PKG):
                    continue
                if needle in path.read_text(encoding="utf-8"):
                    external.add(path.relative_to(_REPO_ROOT))
        assert external == permitted
