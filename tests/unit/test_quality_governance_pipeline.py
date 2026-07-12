"""Orchestration tests for the Quality Governance runtime (CAP-080C).

Exercises the private :class:`QualityGovernancePipeline`, the thin
:class:`DefaultQualityGovernanceService`, and the assembly-only
:class:`QualityGovernanceResultBuilder`: frozen execution order, delegation-only
service, deterministic construction, immutability, the private-pipeline and
composition-root invariants, and the runtime/execution containment boundaries
(ADR-0017 §D29).
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

import requirement_intelligence.quality_governance as qg_pkg
from requirement_intelligence.cp1.models.cp1_result import CP1Result
from requirement_intelligence.grounding.models import GroundingResult
from requirement_intelligence.platform.platform_context import PlatformContext
from requirement_intelligence.quality_governance import (
    DefaultQualityGovernanceService,
    QualityGovernanceResult,
    QualityGovernanceResultBuilder,
)
from requirement_intelligence.quality_governance.assessment.models import QualityAssessmentResult
from requirement_intelligence.quality_governance.assessment.quality_assessment_engine import (
    QualityAssessmentEngine,
)
from requirement_intelligence.quality_governance.decision.models import QualityDecisionResult
from requirement_intelligence.quality_governance.decision.quality_decision_engine import (
    QualityDecisionEngine,
)
from requirement_intelligence.quality_governance.evaluation.models import RuleEvaluationResult
from requirement_intelligence.quality_governance.evaluation.quality_rule_evaluator import (
    QualityRuleEvaluator,
)
from requirement_intelligence.quality_governance.pipeline import QualityGovernancePipeline
from requirement_intelligence.validation.models.validation_result import ValidationResult
from tests.unit.quality_governance_helpers import (
    make_cp1_result,
    make_grounding_result,
    make_validation_result,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_QG_PKG = _REPO_ROOT / "requirement_intelligence" / "quality_governance"
_FIXED = datetime(2026, 7, 12, 12, 0, 0, tzinfo=UTC)


def _inputs(
    *, grounding_score: int = 40
) -> tuple[GroundingResult, ValidationResult, CP1Result]:
    return (
        make_grounding_result(grounding_score=grounding_score),
        make_validation_result(),
        make_cp1_result(),
    )


def _pipeline(ctx: PlatformContext, *, clock=None, log: list[str] | None = None):  # type: ignore[no-untyped-def]
    evaluator: QualityRuleEvaluator = ctx.create_quality_rule_evaluator()
    assessor: QualityAssessmentEngine = ctx.create_quality_assessment_engine()
    decider: QualityDecisionEngine = ctx.create_quality_decision_engine()
    builder = QualityGovernanceResultBuilder()
    if log is not None:
        evaluator = _RecordingEvaluator(evaluator, log)
        assessor = _RecordingAssessor(assessor, log)
        decider = _RecordingDecider(decider, log)
        builder = _RecordingBuilder(log)
    return QualityGovernancePipeline(
        policy=ctx.create_quality_policy(),
        rule_evaluator=evaluator,
        assessment_engine=assessor,
        decision_engine=decider,
        result_builder=builder,
        clock=clock,
    )


class _RecordingEvaluator(QualityRuleEvaluator):
    def __init__(self, inner: QualityRuleEvaluator, log: list[str]) -> None:
        self._inner = inner
        self._log = log

    def evaluate(
        self, g: GroundingResult, v: ValidationResult, c: CP1Result
    ) -> RuleEvaluationResult:
        self._log.append("evaluate")
        return self._inner.evaluate(g, v, c)


class _RecordingAssessor(QualityAssessmentEngine):
    def __init__(self, inner: QualityAssessmentEngine, log: list[str]) -> None:
        self._inner = inner
        self._log = log

    def assess(self, rule_evaluation_result: RuleEvaluationResult) -> QualityAssessmentResult:
        self._log.append("assess")
        return self._inner.assess(rule_evaluation_result)


class _RecordingDecider(QualityDecisionEngine):
    def __init__(self, inner: QualityDecisionEngine, log: list[str]) -> None:
        self._inner = inner
        self._log = log

    def decide(self, quality_assessment_result: QualityAssessmentResult) -> QualityDecisionResult:
        self._log.append("decide")
        return self._inner.decide(quality_assessment_result)


class _RecordingBuilder(QualityGovernanceResultBuilder):
    def __init__(self, log: list[str]) -> None:
        self._log = log

    def build(self, **kwargs: object) -> QualityGovernanceResult:  # type: ignore[override]
        self._log.append("build")
        return super().build(**kwargs)  # type: ignore[arg-type]


@pytest.mark.unit
class TestExecutionOrder:
    def test_stages_run_in_the_frozen_order(self) -> None:
        log: list[str] = []
        pipeline = _pipeline(PlatformContext(), clock=lambda: _FIXED, log=log)
        pipeline.execute(*_inputs())
        assert log == ["evaluate", "assess", "decide", "build"]

    def test_execute_returns_a_governance_result(self) -> None:
        result = _pipeline(PlatformContext(), clock=lambda: _FIXED).execute(*_inputs())
        assert isinstance(result, QualityGovernanceResult)


@pytest.mark.unit
class TestServiceDelegation:
    def test_service_delegates_to_the_pipeline(self) -> None:
        ctx = PlatformContext()
        pipeline = _pipeline(ctx, clock=lambda: _FIXED)
        service = DefaultQualityGovernanceService(pipeline=pipeline)
        inputs = _inputs()
        assert service.evaluate(*inputs) == pipeline.execute(*inputs)

    def test_service_body_only_delegates(self) -> None:
        source = (_QG_PKG / "quality_governance_service.py").read_text(encoding="utf-8")
        assert "self._pipeline.execute" in source
        # The service performs none of the stages itself.
        for token in (".evaluate(", ".assess(", ".decide(", ".build("):
            assert f"self._rule{token}" not in source


@pytest.mark.unit
class TestDeterminism:
    def test_fixed_clock_yields_identical_results(self) -> None:
        ctx = PlatformContext()
        pipeline = _pipeline(ctx, clock=lambda: _FIXED)
        first = pipeline.execute(*_inputs())
        second = pipeline.execute(*_inputs())
        assert first == second
        assert first.model_dump(mode="json", by_alias=True) == second.model_dump(
            mode="json", by_alias=True
        )

    def test_result_round_trips(self) -> None:
        result = _pipeline(PlatformContext(), clock=lambda: _FIXED).execute(*_inputs())
        dumped = result.model_dump(mode="json", by_alias=True)
        assert QualityGovernanceResult.model_validate(dumped) == result


@pytest.mark.unit
class TestBuilderAssembly:
    def test_result_is_immutable(self) -> None:
        from pydantic import ValidationError

        result = _pipeline(PlatformContext(), clock=lambda: _FIXED).execute(*_inputs())
        with pytest.raises(ValidationError):
            result.analysis_id = "other"  # type: ignore[misc]

    def test_consumed_inputs_record_all_three_sources(self) -> None:
        result = _pipeline(PlatformContext(), clock=lambda: _FIXED).execute(*_inputs())
        sources = {ref.source for ref in result.consumed_inputs}
        assert sources == {"grounding", "validation", "cp1"}

    def test_decision_and_findings_are_consistent(self) -> None:
        result = _pipeline(PlatformContext(), clock=lambda: _FIXED).execute(
            *_inputs(grounding_score=40)
        )
        assert result.assessment.summary.total_findings == len(result.assessment.findings)
        assert result.assessment.decision == result.assessment.summary.decision


@pytest.mark.unit
class TestArchitecturalBoundaries:
    def test_pipeline_is_private_not_exported(self) -> None:
        assert "QualityGovernancePipeline" not in qg_pkg.__all__

    def test_pipeline_imports_no_execution_cli_or_serialization(self) -> None:
        source = (_QG_PKG / "pipeline.py").read_text(encoding="utf-8")
        for line in source.splitlines():
            if line.strip().startswith(("import ", "from ")):
                lowered = line.lower()
                for token in ("execution", "cli", "serial", "report", "manifest"):
                    assert token not in lowered, f"pipeline imports {token}"

    def test_builder_imports_no_engine_implementation(self) -> None:
        source = (_QG_PKG / "builder.py").read_text(encoding="utf-8")
        for line in source.splitlines():
            if line.strip().startswith(("import ", "from ")):
                for token in (
                    "quality_rule_evaluator",
                    "quality_assessment_engine",
                    "quality_decision_engine",
                    "pipeline",
                    "QualityRuleEvaluator",
                    "QualityAssessmentEngine",
                    "QualityDecisionEngine",
                ):
                    assert token not in line, f"builder imports engine {token}"

    def test_service_imports_no_engine_implementation(self) -> None:
        source = (_QG_PKG / "quality_governance_service.py").read_text(encoding="utf-8")
        for line in source.splitlines():
            if line.strip().startswith(("import ", "from ")):
                for token in (
                    "quality_rule_evaluator",
                    "quality_assessment_engine",
                    "quality_decision_engine",
                    "builder",
                ):
                    assert token not in line, f"service imports {token}"

    def test_platform_context_is_the_only_external_composition_root(self) -> None:
        needle = "QualityGovernancePipeline"
        permitted = {Path("requirement_intelligence/platform/platform_context.py")}
        external: set[Path] = set()
        for root in (_REPO_ROOT / "requirement_intelligence",):
            for path in root.rglob("*.py"):
                if "tests" in path.parts or path.is_relative_to(_QG_PKG):
                    continue
                if needle in path.read_text(encoding="utf-8"):
                    external.add(path.relative_to(_REPO_ROOT))
        assert external == permitted
