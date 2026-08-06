"""THE LOOP-CLOSING PROOF (ADR-0045's own point, D4/Problem): promotion in
run N is reuse in run N+1.

Runs the real pipeline -- catalog reconciliation
(:mod:`automation_engineering.catalog`), the reuse-safety decision
(:mod:`automation_engineering.reuse`), reuse-first generation orchestration
(:mod:`automation_engineering.generation`), and promotion (:mod:`.gate`,
:mod:`.mechanism`) -- twice, against the SAME tracked-baseline directory,
proving end to end:

* **Run 1**, against an EMPTY baseline: reconciliation finds nothing (0%
  reuse, correctly -- ADR-0044 D5's own bootstrap case, not a failure); the
  reuse engine returns `NoMatch`; a step definition is generated; it clears
  a (supplied) clean CP2/CP3/CP4 gate outcome; it is not a duplicate of
  anything in the (empty) baseline; it PROMOTES; the promoted file is
  written into the tracked baseline and STAGED (git-visible, never
  committed -- D5).
* **Run 2**, against the NOW-non-empty baseline: reconciliation finds the
  promoted asset (proving `reconcile()` reads the WORKING TREE, not git's
  commit history -- a staged-but-uncommitted file is already visible); for
  the SAME step-need, the reuse engine now returns `TrustedReuse` against
  that promoted asset; the step-def orchestrator BINDS instead of
  generating (the generator is a spy that fails the test if ever called);
  reuse for this need goes from 0% (run 1) to 100% (run 2).

Only the semantic matcher is stubbed (`StubSemanticMatcher` -- the ONE
seam ADR-0044 D3 always leaves behind an interface for, matching this
platform's own "stub now, live peer alongside it" convention everywhere
else). Catalog reconciliation, the reuse-safety decision, promotion's own
gate, and its git mechanics are all real, unstubbed code, run against a
real temporary git repository -- proving the loop closes structurally, not
merely that each piece unit-tests correctly in isolation.

CP3/CP4 verdicts are supplied directly as a clean `AssetGateOutcomes`,
rather than invoking the real CP3/CP4 gates (which need a live SonarQube
server and a real Maven project respectively) -- CP3's and CP4's OWN
correctness is already proven by their own test suites
(`test_automation_engineering_cp3_gate.py`, `test_automation_engineering_
cp4_gate.py`); this test proves PROMOTION's behavior given a gate outcome,
not CP3/CP4's own internals.
"""

from __future__ import annotations

import subprocess
import textwrap
from pathlib import Path

import pytest

from automation_engineering.catalog.scanner import reconcile
from automation_engineering.cp3.models import (
    CP3_CRITERIA,
    Cp3CriterionResult,
    Cp3Result,
    Cp3ReuseReport,
)
from automation_engineering.generation.models import BoundStepDefinition, GeneratedStepDefinition
from automation_engineering.generation.orchestrator import orchestrate_step_definition
from automation_engineering.generation.step_definition_generator import (
    StepDefinitionGenerationContext,
)
from automation_engineering.promotion.mechanism import apply_promotion, stage_promoted_assets
from automation_engineering.promotion.models import AssetGateOutcomes, Promoted
from automation_engineering.promotion.outcomes import promote_outcome
from automation_engineering.reuse.matcher import StubSemanticMatcher
from automation_engineering.reuse.models import GherkinStepNeed, MatchCandidate
from shared.enums.base import ValidationVerdict

pytestmark = pytest.mark.unit

_NEED_TEXT = "I search for a product"

_GENERATED_STEP_SOURCE = textwrap.dedent(
    """\
    package com.automation.steps;

    import io.cucumber.java.en.When;

    /** Generated step definition -- searches for a product. */
    public class SearchProductSteps {

        @When("I search for a product")
        public void iSearchForAProduct() {
            // generated fixture body
        }
    }
    """
)


class _NeverCalledGenerator:
    """A spy step-definition generator that fails the test if `.generate()`
    is ever invoked -- proves run 2 BINDS the promoted asset rather than
    regenerating it."""

    def __init__(self) -> None:
        self.call_count = 0

    def generate(self, context: StepDefinitionGenerationContext) -> str:
        self.call_count += 1
        raise AssertionError(
            "the generator must never be called once the reuse engine trusts a "
            "binding -- if this fires, run 2 regenerated instead of reusing "
            "run 1's promoted asset"
        )


def _run_git(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )


def _init_git_repo(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    _run_git("init", "--quiet", cwd=root)
    _run_git("config", "user.email", "test@example.com", cwd=root)
    _run_git("config", "user.name", "Test", cwd=root)
    (root / ".gitkeep").write_text("", encoding="utf-8")
    _run_git("add", ".gitkeep", cwd=root)
    _run_git("commit", "--quiet", "-m", "initial baseline", cwd=root)


def _clean_cp3_result() -> Cp3Result:
    criteria = tuple(
        Cp3CriterionResult(criterion=name, verdict=ValidationVerdict.PASS) for name in CP3_CRITERIA
    )
    return Cp3Result(
        overall_verdict=ValidationVerdict.PASS,
        criteria=criteria,
        reuse=Cp3ReuseReport(reused=0, generated=1, escalated=0, reuse_percentage=0.0),
    )


def _clean_gates() -> AssetGateOutcomes:
    return AssetGateOutcomes(
        cp2_verdict=ValidationVerdict.PASS,
        cp3_result=_clean_cp3_result(),
        cp4_verdict=ValidationVerdict.PASS,
    )


def test_promotion_in_run_one_becomes_reuse_in_run_two(tmp_path: Path) -> None:
    baseline_root = tmp_path / "test-suite-baseline"
    _init_git_repo(baseline_root)
    need = GherkinStepNeed(text=_NEED_TEXT, step_type="When")

    # ------------------------------------------------------------------
    # RUN 1 -- empty baseline, generate, promote.
    # ------------------------------------------------------------------
    run1_catalog = reconcile(baseline_root)
    assert run1_catalog.all_assets() == ()  # bootstrap: 0% reuse, correctly

    run1_matcher = StubSemanticMatcher({_NEED_TEXT: ()})  # nothing to match yet
    run1_generator = _RecordingGenerator({_NEED_TEXT: _GENERATED_STEP_SOURCE})

    run1_outcome = orchestrate_step_definition(need, run1_catalog, run1_matcher, run1_generator)
    assert isinstance(run1_outcome, GeneratedStepDefinition)  # NO_MATCH -> generate
    assert run1_generator.call_count == 1

    run1_decision = promote_outcome(run1_outcome, _clean_gates(), run1_catalog)
    assert isinstance(run1_decision, Promoted)

    written_path = apply_promotion(run1_decision, baseline_root)
    stage_promoted_assets([written_path], baseline_root)

    # Git-visible (D5), but never committed -- the mechanism's own resolved
    # choice (stage-for-review, `mechanism.py`'s module docstring).
    status = _run_git("status", "--porcelain", cwd=baseline_root)
    assert "A  src/test/java/com/automation/steps/SearchProductSteps.java" in status.stdout
    log_after_run1 = _run_git("log", "--oneline", cwd=baseline_root).stdout
    assert log_after_run1.strip().count("\n") == 0  # still exactly the initial commit

    # ------------------------------------------------------------------
    # RUN 2 -- the SAME baseline, now non-empty. Catalog reconciliation
    # reads the WORKING TREE (reconcile() never consults git history), so
    # the staged-but-uncommitted file from run 1 is already visible.
    # ------------------------------------------------------------------
    run2_catalog = reconcile(baseline_root)
    assert len(run2_catalog.step_definitions) == 1
    promoted_asset = run2_catalog.step_definitions[0]
    assert promoted_asset.content_hash == run1_decision.candidate.asset.content_hash
    assert promoted_asset.asset_id == run1_decision.candidate.asset.asset_id

    # The semantic matcher (the one stubbed seam) now recognizes the SAME
    # step-need as matching the promoted asset -- everything else (the
    # reuse-safety decision, the orchestrator's bind-vs-generate routing)
    # is real, unstubbed code.
    run2_match_candidate = MatchCandidate(
        asset_id=promoted_asset.asset_id,
        confidence=0.95,
        content_hash=promoted_asset.content_hash,
    )
    run2_matcher = StubSemanticMatcher({_NEED_TEXT: (run2_match_candidate,)})
    run2_generator = _NeverCalledGenerator()

    run2_outcome = orchestrate_step_definition(need, run2_catalog, run2_matcher, run2_generator)

    assert isinstance(run2_outcome, BoundStepDefinition)  # TRUSTED_REUSE -> bind, not generate
    assert run2_outcome.asset.asset_id == promoted_asset.asset_id
    assert run2_generator.call_count == 0  # never regenerated

    # The loop closed: run 1's 0%-reuse bootstrap generated and promoted one
    # asset; run 2's reuse for the SAME need is 100% -- bound, not generated.


class _RecordingGenerator:
    """Deterministic, fixture-driven step-definition generator (mirrors
    `StubStepDefinitionGenerator`) that also records its own call count --
    used for run 1's own generation, kept separate from `_NeverCalledGenerator`
    so each run's own expectation (called once vs. never) is unambiguous."""

    def __init__(self, java_source_by_step_text: dict[str, str]) -> None:
        self._canned = java_source_by_step_text
        self.call_count = 0

    def generate(self, context: StepDefinitionGenerationContext) -> str:
        self.call_count += 1
        return self._canned[context.need.text]
