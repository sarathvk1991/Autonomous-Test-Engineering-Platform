"""Promotion's decision (ADR-0045 D2/D3).

Proves, deterministically and without any live call: a clean, gate-passing,
non-duplicate candidate auto-promotes; each of D2(a)'s three gates (CP2,
CP3, CP4) blocks INDEPENDENTLY when it alone fails; a duplicate of an
existing tracked-baseline asset blocks even when every gate passed; a gate
failure is reported ahead of a duplicate when both are true (checks run in
order, D2(a) then D2(b)); and an already-escalated reuse decision is carried
through unedited, never re-decided, by `evaluate_escalated_promotion`.

**Per-asset CP3 decomposition (ADR-0045 D2 additive note, 2026-08-06).**
`AssetGateOutcomes.cp3_verdict` (a bare `ValidationVerdict`) became
`cp3_result` (a full `Cp3Result`) so `evaluate_promotion` can decompose CP3
down to THIS candidate's own class -- `TestPerAssetCp3Decomposition` proves
a per-class criterion (`direct_webdriver_action`/`long_method`) failing for
ONE class does not block a DIFFERENT clean class in the same batch, a
per-asset criterion (`duplicate_steps`) failing for one asset_id does not
block a different asset_id, and the whole-project `sonar_quality_gate`
still blocks every candidate alike (it has no file/class attribution to
decompose by -- `automation_engineering.promotion.cp3_decomposition`'s own
module docstring).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from automation_engineering.catalog.alignment import correlate
from automation_engineering.catalog.models import AssetCatalog, StepDefinitionAsset
from automation_engineering.cp3.models import (
    CP3_CRITERIA,
    Cp3CriterionResult,
    Cp3Result,
    Cp3ReuseReport,
)
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
_REUSE_REPORT = Cp3ReuseReport(reused=0, generated=1, escalated=0, reuse_percentage=0.0)


def _cp3_result(**overrides: tuple[str, ...]) -> Cp3Result:
    """A whole-batch `Cp3Result` -- every criterion PASS by default;
    `overrides` maps a criterion name to FAIL messages for that criterion
    alone (e.g. `_cp3_result(long_method=("SomeClass.someMethod: ...",))`)."""
    criteria = tuple(
        Cp3CriterionResult(
            criterion=name,
            verdict=ValidationVerdict.FAIL if name in overrides else ValidationVerdict.PASS,
            messages=overrides.get(name, ()),
        )
        for name in CP3_CRITERIA
    )
    overall = ValidationVerdict.FAIL if overrides else ValidationVerdict.PASS
    return Cp3Result(overall_verdict=overall, criteria=criteria, reuse=_REUSE_REPORT)


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
        cp3_result=_cp3_result(),
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
            cp3_result=_cp3_result(),
            cp4_verdict=ValidationVerdict.PASS,
        )
        decision = evaluate_promotion(_candidate(), gates, _empty_baseline())

        assert isinstance(decision, NotPromotable)
        assert decision.reason is PromotionBlockReason.CP2_FAILED

    def test_cp3_failure_blocks(self) -> None:
        """A whole-project Sonar FAIL (no file/class attribution to
        decompose by) blocks every candidate, including this one -- the one
        CP3 criterion that stays genuinely batch-wide under the per-asset
        design (`cp3_decomposition`'s own module docstring)."""
        gates = AssetGateOutcomes(
            cp2_verdict=ValidationVerdict.PASS,
            cp3_result=_cp3_result(sonar_quality_gate=("server reported ERROR",)),
            cp4_verdict=ValidationVerdict.PASS,
        )
        decision = evaluate_promotion(_candidate(), gates, _empty_baseline())

        assert isinstance(decision, NotPromotable)
        assert decision.reason is PromotionBlockReason.CP3_FAILED

    def test_cp4_failure_blocks(self) -> None:
        gates = AssetGateOutcomes(
            cp2_verdict=ValidationVerdict.PASS,
            cp3_result=_cp3_result(),
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
            cp3_result=_cp3_result(sonar_quality_gate=("server reported ERROR",)),
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


class TestPerAssetCp3Decomposition:
    """ADR-0045 D2 additive note: CP3's own batch verdict is decomposed
    per-candidate, not applied uniformly. This is the exact mechanism the
    confirming live run's own gap (30 clean binds promoted 0 because 30
    unrelated needs escalated, failing one shared whole-run gate) required."""

    _OTHER_CLASS = "com.automation.steps.OtherUnrelatedSteps"
    _OWN_CLASS = "com.automation.steps.SearchProductSteps"  # matches _candidate()

    def test_a_per_class_violation_on_a_different_class_does_not_block(self) -> None:
        gates = AssetGateOutcomes(
            cp2_verdict=ValidationVerdict.PASS,
            cp3_result=_cp3_result(
                direct_webdriver_action=(
                    f"{self._OTHER_CLASS}: imports org.openqa.selenium.WebDriver directly",
                )
            ),
            cp4_verdict=ValidationVerdict.PASS,
        )
        decision = evaluate_promotion(_candidate(), gates, _empty_baseline())

        assert isinstance(decision, Promoted)

    def test_a_per_class_violation_on_this_class_blocks(self) -> None:
        gates = AssetGateOutcomes(
            cp2_verdict=ValidationVerdict.PASS,
            cp3_result=_cp3_result(
                long_method=(f"{self._OWN_CLASS}.iSearchForAProduct: 47 lines, over the limit",)
            ),
            cp4_verdict=ValidationVerdict.PASS,
        )
        decision = evaluate_promotion(_candidate(), gates, _empty_baseline())

        assert isinstance(decision, NotPromotable)
        assert decision.reason is PromotionBlockReason.CP3_FAILED
        assert "47 lines" in decision.detail

    def test_a_duplicate_steps_collision_naming_a_different_asset_does_not_block(self) -> None:
        gates = AssetGateOutcomes(
            cp2_verdict=ValidationVerdict.PASS,
            cp3_result=_cp3_result(
                duplicate_steps=(
                    "pattern 'I do something else' bound by 2 step-definition assets: "
                    "STEP-other-one (com.automation.steps.OtherSteps#a), "
                    "STEP-other-two (com.automation.steps.OtherSteps#b)",
                )
            ),
            cp4_verdict=ValidationVerdict.PASS,
        )
        decision = evaluate_promotion(_candidate(), gates, _empty_baseline())

        assert isinstance(decision, Promoted)

    def test_a_duplicate_steps_collision_naming_this_asset_blocks(self) -> None:
        gates = AssetGateOutcomes(
            cp2_verdict=ValidationVerdict.PASS,
            cp3_result=_cp3_result(
                duplicate_steps=(
                    f"pattern {_PATTERN!r} bound by 2 step-definition assets: "
                    "STEP-searchproduct01 "
                    "(com.automation.steps.SearchProductSteps#iSearchForAProduct), "
                    "STEP-searchproduct02 "
                    "(com.automation.steps.SearchProductStepsTwo#iSearchForAProduct)",
                )
            ),
            cp4_verdict=ValidationVerdict.PASS,
        )
        decision = evaluate_promotion(_candidate(), gates, _empty_baseline())

        assert isinstance(decision, NotPromotable)
        assert decision.reason is PromotionBlockReason.CP3_FAILED

    def test_a_coverage_family_failure_from_an_unrelated_escalated_need_does_not_block(
        self,
    ) -> None:
        """The exact confirming-run mechanism: an unrelated need's own
        escalation fails step_coverage/scenario_coverage/unmapped_steps in
        the WHOLE-RUN Cp3Result, but this candidate's own need already
        resolved (it reached `evaluate_promotion` as a candidate at all) --
        the coverage family is excluded from a resolved candidate's own
        gate (`cp3_decomposition`'s own module docstring)."""
        gates = AssetGateOutcomes(
            cp2_verdict=ValidationVerdict.PASS,
            cp3_result=_cp3_result(
                step_coverage=("1/4 steps unmapped (75.0% step coverage)",),
                scenario_coverage=("@SCN-002 ('Some other scenario'): 1/1 steps unmapped",),
                unmapped_steps=(
                    "@SCN-002 ('Some other scenario'): 'some other step' -- "
                    "escalated, no automatic binding",
                ),
            ),
            cp4_verdict=ValidationVerdict.PASS,
        )
        decision = evaluate_promotion(_candidate(), gates, _empty_baseline())

        assert isinstance(decision, Promoted)

    def test_sonar_whole_project_failure_still_blocks_every_candidate(self) -> None:
        """Sonar has no file/class attribution to decompose by -- a
        whole-project FAIL is applied uniformly, unlike the three
        per-class/per-asset criteria above."""
        gates = AssetGateOutcomes(
            cp2_verdict=ValidationVerdict.PASS,
            cp3_result=_cp3_result(sonar_quality_gate=("new_coverage: ERROR",)),
            cp4_verdict=ValidationVerdict.PASS,
        )
        decision = evaluate_promotion(_candidate(), gates, _empty_baseline())

        assert isinstance(decision, NotPromotable)
        assert decision.reason is PromotionBlockReason.CP3_FAILED
        assert "new_coverage" in decision.detail
