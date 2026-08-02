"""Promotion's decision (ADR-0045 D2/D3).

Proves, deterministically and without any live call: a clean, gate-passing,
non-duplicate candidate auto-promotes; each of D2(a)'s three gates (CP2,
CP3, CP4) blocks INDEPENDENTLY when it alone fails; a duplicate of an
existing tracked-baseline asset blocks even when every gate passed; a gate
failure is reported ahead of a duplicate when both are true (checks run in
order, D2(a) then D2(b)); and an already-escalated reuse decision is carried
through unedited, never re-decided, by `evaluate_escalated_promotion`.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from automation_engineering.catalog.alignment import correlate
from automation_engineering.catalog.models import AssetCatalog, StepDefinitionAsset
from automation_engineering.promotion.gate import evaluate_escalated_promotion, evaluate_promotion
from automation_engineering.promotion.models import (
    AssetGateOutcomes,
    NotPromotable,
    Promoted,
    PromotionBlockReason,
    PromotionCandidate,
    PromotionEscalated,
)
from automation_engineering.reuse.models import (
    Escalation,
    EscalationCheck,
    GherkinStepNeed,
    MatchCandidate,
)
from shared.enums.base import ValidationVerdict

pytestmark = pytest.mark.unit

_CONTENT_HASH = "content-hash-of-search-product-steps"
_PATTERN = "I search for a product"


def _candidate(content_hash: str = _CONTENT_HASH) -> PromotionCandidate:
    asset = StepDefinitionAsset(
        asset_id="STEP-searchproduct01",
        class_name="com.automation.steps.SearchProductSteps",
        method_name="iSearchForAProduct",
        step_type="When",
        pattern=_PATTERN,
        parameters=(),
        return_type="void",
        source_file="com/automation/steps/SearchProductSteps.java",
        content_hash=content_hash,
        signature_alignment=correlate(_PATTERN, ()),
    )
    return PromotionCandidate(
        java_source="// fixture -- gate.py tests operate on the resolved asset only",
        asset=asset,
        relative_path=Path("com/automation/steps/SearchProductSteps.java"),
    )


def _all_pass() -> AssetGateOutcomes:
    return AssetGateOutcomes(
        cp2_verdict=ValidationVerdict.PASS,
        cp3_verdict=ValidationVerdict.PASS,
        cp4_verdict=ValidationVerdict.PASS,
    )


def _empty_baseline() -> AssetCatalog:
    return AssetCatalog(baseline_root="test-suite-baseline")


def _baseline_with_duplicate(content_hash: str = _CONTENT_HASH) -> AssetCatalog:
    existing = StepDefinitionAsset(
        asset_id="STEP-alreadyinbaseline01",
        class_name="com.automation.steps.ExistingSteps",
        method_name="existingMethod",
        step_type="When",
        pattern=_PATTERN,
        parameters=(),
        return_type="void",
        source_file="com/automation/steps/ExistingSteps.java",
        content_hash=content_hash,
        signature_alignment=correlate(_PATTERN, ()),
    )
    return AssetCatalog(baseline_root="test-suite-baseline", step_definitions=(existing,))


class TestCleanCandidatePromotes:
    def test_all_gates_pass_and_no_duplicate_promotes(self) -> None:
        decision = evaluate_promotion(_candidate(), _all_pass(), _empty_baseline())

        assert isinstance(decision, Promoted)
        assert decision.candidate.asset.content_hash == _CONTENT_HASH


class TestEachGateBlocksIndependently:
    def test_cp2_failure_blocks(self) -> None:
        gates = AssetGateOutcomes(
            cp2_verdict=ValidationVerdict.FAIL,
            cp3_verdict=ValidationVerdict.PASS,
            cp4_verdict=ValidationVerdict.PASS,
        )
        decision = evaluate_promotion(_candidate(), gates, _empty_baseline())

        assert isinstance(decision, NotPromotable)
        assert decision.reason is PromotionBlockReason.CP2_FAILED

    def test_cp3_failure_blocks(self) -> None:
        gates = AssetGateOutcomes(
            cp2_verdict=ValidationVerdict.PASS,
            cp3_verdict=ValidationVerdict.FAIL,
            cp4_verdict=ValidationVerdict.PASS,
        )
        decision = evaluate_promotion(_candidate(), gates, _empty_baseline())

        assert isinstance(decision, NotPromotable)
        assert decision.reason is PromotionBlockReason.CP3_FAILED

    def test_cp4_failure_blocks(self) -> None:
        gates = AssetGateOutcomes(
            cp2_verdict=ValidationVerdict.PASS,
            cp3_verdict=ValidationVerdict.PASS,
            cp4_verdict=ValidationVerdict.FAIL,
        )
        decision = evaluate_promotion(_candidate(), gates, _empty_baseline())

        assert isinstance(decision, NotPromotable)
        assert decision.reason is PromotionBlockReason.CP4_FAILED

    def test_duplicate_of_existing_baseline_asset_blocks(self) -> None:
        decision = evaluate_promotion(_candidate(), _all_pass(), _baseline_with_duplicate())

        assert isinstance(decision, NotPromotable)
        assert decision.reason is PromotionBlockReason.DUPLICATE
        assert "STEP-alreadyinbaseline01" in decision.detail

    def test_non_matching_content_hash_is_not_a_duplicate(self) -> None:
        """A baseline asset with a DIFFERENT content-hash never blocks --
        D2(b) is an exact-identity check, not a fuzzy one."""
        decision = evaluate_promotion(
            _candidate(content_hash="a-completely-different-hash"),
            _all_pass(),
            _baseline_with_duplicate(content_hash=_CONTENT_HASH),
        )

        assert isinstance(decision, Promoted)


class TestGateFailureOutranksDuplicateCheck:
    def test_gate_failure_is_reported_even_when_also_a_duplicate(self) -> None:
        """D2(a) is checked before D2(b) (module docstring) -- a candidate
        that is BOTH gate-failing and a duplicate is reported for the gate
        failure, never silently for the duplicate instead."""
        gates = AssetGateOutcomes(
            cp2_verdict=ValidationVerdict.PASS,
            cp3_verdict=ValidationVerdict.FAIL,
            cp4_verdict=ValidationVerdict.PASS,
        )
        decision = evaluate_promotion(_candidate(), gates, _baseline_with_duplicate())

        assert isinstance(decision, NotPromotable)
        assert decision.reason is PromotionBlockReason.CP3_FAILED


class TestEscalationPassesThroughUnedited:
    def test_escalated_promotion_carries_the_same_escalation_object(self) -> None:
        need = GherkinStepNeed(text=_PATTERN, step_type="When")
        candidate = MatchCandidate(asset_id="STEP-x", confidence=0.2, content_hash="h")
        escalation = Escalation(
            need=need,
            check=EscalationCheck.CONFIDENCE,
            candidate=candidate,
            detail="match confidence 0.2 is below the configured threshold 0.75",
        )

        decision = evaluate_escalated_promotion(escalation)

        assert isinstance(decision, PromotionEscalated)
        assert decision.escalation is escalation  # same object, never re-decided
