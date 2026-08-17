"""Proves ADR-0051 D2's regression gate: RELATIVE to a stored baseline,
never an absolute score threshold. A low-but-stable score PASSES; a
high-but-dropped score REGRESSES -- if this gate were absolute-threshold
based, both assertions below would be reversed for at least one case.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from eval_harness.baseline_store import EvalBaselineStore, check_regression
from eval_harness.models import (
    CaseResult,
    EvalScore,
    PropertyCheckOutcome,
    PropertyCheckResult,
    RegressionGateOutcome,
)
from eval_harness.scoring import score_eval_set
from requirement_intelligence.llm.generation_identity import GenerationIdentity

_IDENTITY_A = GenerationIdentity(
    prompt_id="generate_step_definitions",
    prompt_version="1.1.0",
    prompt_sha256="a" * 64,
    provider="gemini",
    model="gemini-3.5-flash",
)

_IDENTITY_B_MODEL_SWAP = GenerationIdentity(
    prompt_id="generate_step_definitions",
    prompt_version="1.1.0",
    prompt_sha256="a" * 64,
    provider="gemini",
    model="gemini-2.5-flash",
)


def _score(
    identity: GenerationIdentity,
    pass_rate: float,
    *,
    generator_id: str = "step_definition_generation",
) -> EvalScore:
    total = 4
    passed = round(pass_rate * total)
    outcomes = [PropertyCheckOutcome.PASSED] * passed + [PropertyCheckOutcome.FAILED] * (
        total - passed
    )
    case_results = [
        CaseResult(
            case_id="case-1",
            check_results=tuple(
                PropertyCheckResult(check_name=f"check_{i}", outcome=outcome)
                for i, outcome in enumerate(outcomes)
            ),
        )
    ]
    return score_eval_set(
        case_results, generator_id=generator_id, eval_set_version="1.0.0", identity=identity
    )


@pytest.fixture
def store(tmp_path: Path) -> EvalBaselineStore:
    return EvalBaselineStore(tmp_path / "eval_baselines")


class TestEvalBaselineStoreRoundTrip:
    def test_get_baseline_returns_none_before_anything_is_recorded(
        self, store: EvalBaselineStore
    ) -> None:
        assert store.get_baseline("step_definition_generation") is None

    def test_record_then_get_round_trips(self, store: EvalBaselineStore) -> None:
        recorded = _score(_IDENTITY_A, 1.0)
        store.record_baseline("step_definition_generation", recorded)
        fetched = store.get_baseline("step_definition_generation")
        assert fetched is not None
        assert fetched.pass_rate == recorded.pass_rate
        assert fetched.identity == recorded.identity

    def test_a_corrupt_baseline_file_degrades_to_none_not_a_crash(
        self, tmp_path: Path
    ) -> None:
        store_dir = tmp_path / "eval_baselines"
        store = EvalBaselineStore(store_dir)
        path = store_dir / "step_definition_generation.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{ not valid json", encoding="utf-8")
        assert store.get_baseline("step_definition_generation") is None


class TestCheckRegressionIsScoresFirst:
    def test_no_baseline_establishes_one_rather_than_pass_or_fail(
        self, store: EvalBaselineStore
    ) -> None:
        candidate = _score(_IDENTITY_A, 1.0)
        result = check_regression(candidate, store)
        assert result.outcome == RegressionGateOutcome.ESTABLISHED_BASELINE
        assert result.baseline_pass_rate is None


class TestCheckRegressionIsRelativeNotAbsolute:
    def test_a_low_but_stable_score_passes(self, store: EvalBaselineStore) -> None:
        """A 25% baseline compared against a 25% candidate PASSES -- an
        absolute-threshold gate calibrated anywhere above 25% would
        incorrectly fail this, the exact "pass-bias meaning-check" trap
        ADR-0051 D2 names as the reason to reject an absolute bar."""
        store.record_baseline("step_definition_generation", _score(_IDENTITY_A, 0.25))
        candidate = _score(_IDENTITY_B_MODEL_SWAP, 0.25)
        result = check_regression(candidate, store)
        assert result.outcome == RegressionGateOutcome.PASSED

    def test_a_high_but_dropped_score_regresses(self, store: EvalBaselineStore) -> None:
        """A 100% baseline compared against a 75% candidate REGRESSES -- an
        absolute-threshold gate calibrated anywhere at or below 75% would
        incorrectly pass this, even though real quality dropped. This is
        the mechanism shape of the real `gemini-2.5-flash` regression
        (`[[cap-compile-gap-closed]]`): the model swap alone (identity
        changes; the eval set and checks do not) is what the gate reacts
        to."""
        store.record_baseline("step_definition_generation", _score(_IDENTITY_A, 1.0))
        candidate = _score(_IDENTITY_B_MODEL_SWAP, 0.75)
        result = check_regression(candidate, store)
        assert result.outcome == RegressionGateOutcome.REGRESSED
        assert result.baseline_pass_rate == 1.0
        assert result.candidate_pass_rate == 0.75

    def test_an_improved_score_passes(self, store: EvalBaselineStore) -> None:
        store.record_baseline("step_definition_generation", _score(_IDENTITY_A, 0.5))
        candidate = _score(_IDENTITY_B_MODEL_SWAP, 0.75)
        result = check_regression(candidate, store)
        assert result.outcome == RegressionGateOutcome.PASSED
