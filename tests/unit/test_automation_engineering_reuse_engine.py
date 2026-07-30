"""The reuse-safety decision (ADR-0044 D4) -- the three-check trust model.

Proves, deterministically and without any live call: a clean match trusts
the right asset; each of the three checks escalates INDEPENDENTLY when it
alone fails (the D4-critical proofs, especially the signature-mismatch
case D4 exists for); no single check can be silently bypassed by the other
two passing; the NO_MATCH/generate boundary; the empty-catalog bootstrap
(0% reuse, correctly, not an error, and with zero live calls); and
determinism of the whole decision given the same inputs.

Builds on the real catalog shapes (`automation_engineering.catalog.models`)
and the real capture/correlation machinery
(`automation_engineering.catalog.alignment.correlate`) so the signature-fit
proofs are checked against the SAME correlation data D4(c) actually uses,
not a hand-rolled stand-in.
"""

from __future__ import annotations

import pytest

from automation_engineering.catalog.alignment import correlate
from automation_engineering.catalog.models import (
    AssetCatalog,
    JavaParameter,
    StepCapture,
    StepDefinitionAsset,
)
from automation_engineering.reuse.embeddings import EmbeddingProvider
from automation_engineering.reuse.engine import DEFAULT_CONFIDENCE_THRESHOLD, decide_reuse
from automation_engineering.reuse.live_matcher import LiveSemanticMatcher
from automation_engineering.reuse.matcher import StubSemanticMatcher
from automation_engineering.reuse.models import (
    Escalation,
    EscalationCheck,
    GherkinStepNeed,
    MatchCandidate,
    NoMatch,
    TrustedReuse,
)

pytestmark = pytest.mark.unit

_LOGIN_PATTERN = "I log in as {string} with password {string}"
_LOGIN_ASSET_ID = "STEP-loginasfixture01"
_CURRENT_HASH = "current-hash-abc123"
_STALE_HASH = "stale-hash-000000"


def _login_step_definition(content_hash: str = _CURRENT_HASH) -> StepDefinitionAsset:
    """A step definition whose own annotation captures (2 `{string}`) and
    parameters (2 `String`) are self-aligned -- built via the real
    `correlate()` the catalog itself uses, not a hand-authored
    `SignatureAlignment`."""
    parameters = (
        JavaParameter(name="username", java_type="String"),
        JavaParameter(name="password", java_type="String"),
    )
    return StepDefinitionAsset(
        asset_id=_LOGIN_ASSET_ID,
        class_name="com.automation.steps.LoginSteps",
        method_name="iLogInAsWithPassword",
        step_type="When",
        pattern=_LOGIN_PATTERN,
        parameters=parameters,
        return_type="void",
        source_file="com/automation/steps/LoginSteps.java",
        content_hash=content_hash,
        signature_alignment=correlate(_LOGIN_PATTERN, parameters),
    )


def _catalog(*assets: StepDefinitionAsset) -> AssetCatalog:
    return AssetCatalog(baseline_root="test-suite-baseline", step_definitions=tuple(assets))


def _two_string_captures() -> tuple[StepCapture, ...]:
    return (
        StepCapture(index=0, style="cucumber_expression", expression_type="string"),
        StepCapture(index=1, style="cucumber_expression", expression_type="string"),
    )


def _fitting_need() -> GherkinStepNeed:
    return GherkinStepNeed(
        text='I log in as "alice" with password "secret"',
        step_type="When",
        captures=_two_string_captures(),
    )


class _NeverCalledEmbeddingProvider:
    """A spy `EmbeddingProvider` that fails the test if `.embed()` is ever
    invoked -- used to prove the empty-catalog bootstrap makes zero live
    calls."""

    def embed(self, texts: Sequence[str]) -> tuple[tuple[float, ...], ...]:
        raise AssertionError(
            "EmbeddingProvider.embed() must never be called for an empty catalog "
            "-- LiveSemanticMatcher must short-circuit before any live call."
        )


# ---------------------------------------------------------------------------
# TRUSTED path
# ---------------------------------------------------------------------------


def test_trusted_reuse_binds_the_right_asset() -> None:
    asset = _login_step_definition()
    catalog = _catalog(asset)
    need = _fitting_need()
    candidate = MatchCandidate(
        asset_id=_LOGIN_ASSET_ID, confidence=0.95, content_hash=_CURRENT_HASH
    )
    matcher = StubSemanticMatcher({need.text: (candidate,)})

    decision = decide_reuse(need, catalog, matcher)

    assert isinstance(decision, TrustedReuse)
    assert decision.asset is asset
    assert decision.asset.asset_id == _LOGIN_ASSET_ID
    assert decision.candidate == candidate


def test_trusted_reuse_only_considers_the_best_ranked_candidate() -> None:
    """The engine trusts only the top-ranked (best-first) candidate -- a
    lower-ranked candidate's own properties are irrelevant to the decision,
    even if it would otherwise have passed."""
    asset = _login_step_definition()
    catalog = _catalog(asset)
    need = _fitting_need()
    best = MatchCandidate(asset_id=_LOGIN_ASSET_ID, confidence=0.95, content_hash=_CURRENT_HASH)
    second = MatchCandidate(asset_id="STEP-other", confidence=0.99, content_hash="whatever")
    matcher = StubSemanticMatcher({need.text: (best, second)})

    decision = decide_reuse(need, catalog, matcher)

    assert isinstance(decision, TrustedReuse)
    assert decision.candidate == best


# ---------------------------------------------------------------------------
# The three ESCALATION modes, proven independently (D4-critical)
# ---------------------------------------------------------------------------


def test_low_confidence_escalates_even_when_otherwise_fine() -> None:
    """(a) fails alone: hash current, signature fits, confidence below
    threshold -> ESCALATE(confidence)."""
    asset = _login_step_definition()
    catalog = _catalog(asset)
    need = _fitting_need()
    candidate = MatchCandidate(
        asset_id=_LOGIN_ASSET_ID,
        confidence=DEFAULT_CONFIDENCE_THRESHOLD - 0.01,
        content_hash=_CURRENT_HASH,
    )
    matcher = StubSemanticMatcher({need.text: (candidate,)})

    decision = decide_reuse(need, catalog, matcher)

    assert isinstance(decision, Escalation)
    assert decision.check is EscalationCheck.CONFIDENCE
    assert decision.candidate == candidate


def test_stale_content_hash_escalates_even_with_high_confidence_and_fitting_signature() -> None:
    """(b) fails alone: confidence high, signature fits, but the candidate's
    own content-hash (what the match was computed against) no longer matches
    a fresh catalog lookup -> ESCALATE(stale), NOT trusted. Proves (b) fires
    even when (a) and (c) would pass -- advisory-until-verified (ADR-0044
    D4's own discipline)."""
    asset = _login_step_definition(content_hash=_CURRENT_HASH)
    catalog = _catalog(asset)
    need = _fitting_need()
    candidate = MatchCandidate(asset_id=_LOGIN_ASSET_ID, confidence=0.95, content_hash=_STALE_HASH)
    matcher = StubSemanticMatcher({need.text: (candidate,)})

    decision = decide_reuse(need, catalog, matcher)

    assert isinstance(decision, Escalation)
    assert decision.check is EscalationCheck.CONTENT_HASH
    assert _STALE_HASH in decision.detail
    assert _CURRENT_HASH in decision.detail


def test_signature_mismatch_escalates_even_with_high_confidence_and_current_hash() -> None:
    """(c) fails alone: confidence high, hash current, but the Gherkin
    step-need needs only 1 capture while the candidate declares 2
    (the 1-capture-step -> 2-param-method case D4 exists for) ->
    ESCALATE(signature), NOT trusted. This is the plausible-but-wrong match
    caught structurally, not by confidence."""
    asset = _login_step_definition()
    catalog = _catalog(asset)
    need = GherkinStepNeed(
        text='I log in as "alice"',
        step_type="When",
        captures=(StepCapture(index=0, style="cucumber_expression", expression_type="string"),),
    )
    candidate = MatchCandidate(
        asset_id=_LOGIN_ASSET_ID, confidence=0.95, content_hash=_CURRENT_HASH
    )
    matcher = StubSemanticMatcher({need.text: (candidate,)})

    decision = decide_reuse(need, catalog, matcher)

    assert isinstance(decision, Escalation)
    assert decision.check is EscalationCheck.SIGNATURE_FIT
    assert "capture-count mismatch" in decision.detail
    assert "needs 1" in decision.detail
    assert "declares 2" in decision.detail


def test_signature_type_mismatch_escalates() -> None:
    """(c) also fires on a same-count, wrong-TYPE capture -- not only arity."""
    asset = _login_step_definition()
    catalog = _catalog(asset)
    need = GherkinStepNeed(
        text='I log in as 12345 with password "secret"',
        step_type="When",
        captures=(
            StepCapture(index=0, style="cucumber_expression", expression_type="int"),
            StepCapture(index=1, style="cucumber_expression", expression_type="string"),
        ),
    )
    candidate = MatchCandidate(
        asset_id=_LOGIN_ASSET_ID, confidence=0.95, content_hash=_CURRENT_HASH
    )
    matcher = StubSemanticMatcher({need.text: (candidate,)})

    decision = decide_reuse(need, catalog, matcher)

    assert isinstance(decision, Escalation)
    assert decision.check is EscalationCheck.SIGNATURE_FIT
    assert "capture #0 type mismatch" in decision.detail


def test_candidates_own_self_misaligned_signature_never_trusted() -> None:
    """A candidate whose OWN annotation-to-parameter alignment is already
    broken (its own `signature_alignment.is_aligned` is False) can never be
    trusted as a binding target, regardless of confidence or hash."""
    parameters = (JavaParameter(name="username", java_type="String"),)
    misaligned = StepDefinitionAsset(
        asset_id=_LOGIN_ASSET_ID,
        class_name="com.automation.steps.LoginSteps",
        method_name="iLogInAsWithPassword",
        step_type="When",
        pattern=_LOGIN_PATTERN,  # declares 2 captures
        parameters=parameters,  # but only 1 parameter -- arity mismatch, self-misaligned
        return_type="void",
        source_file="com/automation/steps/LoginSteps.java",
        content_hash=_CURRENT_HASH,
        signature_alignment=correlate(_LOGIN_PATTERN, parameters),
    )
    catalog = _catalog(misaligned)
    need = _fitting_need()
    candidate = MatchCandidate(
        asset_id=_LOGIN_ASSET_ID, confidence=0.95, content_hash=_CURRENT_HASH
    )
    matcher = StubSemanticMatcher({need.text: (candidate,)})

    decision = decide_reuse(need, catalog, matcher)

    assert isinstance(decision, Escalation)
    assert decision.check is EscalationCheck.SIGNATURE_FIT
    assert "not self-aligned" in decision.detail


# ---------------------------------------------------------------------------
# No single check can be bypassed -- the combinatorial proof
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("confidence", "content_hash", "need_captures", "expected_check"),
    [
        pytest.param(
            DEFAULT_CONFIDENCE_THRESHOLD - 0.01,
            _CURRENT_HASH,
            _two_string_captures(),
            EscalationCheck.CONFIDENCE,
            id="only-confidence-fails",
        ),
        pytest.param(
            0.95,
            _STALE_HASH,
            _two_string_captures(),
            EscalationCheck.CONTENT_HASH,
            id="only-hash-fails",
        ),
        pytest.param(
            0.95,
            _CURRENT_HASH,
            (StepCapture(index=0, style="cucumber_expression", expression_type="string"),),
            EscalationCheck.SIGNATURE_FIT,
            id="only-signature-fails",
        ),
    ],
)
def test_no_single_check_is_ever_bypassed_by_the_other_two_passing(
    confidence: float,
    content_hash: str,
    need_captures: tuple[StepCapture, ...],
    expected_check: EscalationCheck,
) -> None:
    """ADR-0044 D4's own 'all three, every time' made verifiable: for each
    of the three checks, a candidate that fails EXACTLY that one check --
    with the other two passing -- always escalates, and always names the
    failing check. No combination of two passing checks ever compensates
    for the third."""
    asset = _login_step_definition()
    catalog = _catalog(asset)
    need = GherkinStepNeed(text="scripted step text", step_type="When", captures=need_captures)
    candidate = MatchCandidate(
        asset_id=_LOGIN_ASSET_ID, confidence=confidence, content_hash=content_hash
    )
    matcher = StubSemanticMatcher({need.text: (candidate,)})

    decision = decide_reuse(need, catalog, matcher)

    assert isinstance(decision, Escalation)
    assert decision.check is expected_check
    assert not isinstance(decision, TrustedReuse)


# ---------------------------------------------------------------------------
# NO_MATCH / generate boundary
# ---------------------------------------------------------------------------


def test_no_candidates_at_all_returns_no_match_not_escalation_not_error() -> None:
    catalog = _catalog(_login_step_definition())
    need = GherkinStepNeed(text="a step nothing resembles", step_type="Given")
    matcher = StubSemanticMatcher({need.text: ()})

    decision = decide_reuse(need, catalog, matcher)

    assert isinstance(decision, NoMatch)
    assert decision.need is need


def test_empty_catalog_bootstrap_is_generate_all_not_error_and_makes_no_live_call() -> None:
    """ADR-0044 D5's own bootstrap case: an empty catalog -> every
    asset-need -> NO_MATCH -> generate everything (0% reuse, correctly).
    Uses the REAL `LiveSemanticMatcher` (not the stub) wired to a spy
    `EmbeddingProvider` that fails if ever called -- proving the engine's
    decision logic, and the live matcher's own short-circuit, make zero live
    calls for the empty-catalog case."""
    empty_catalog = AssetCatalog(baseline_root="test-suite-baseline")
    need = GherkinStepNeed(text='I log in as "alice" with password "secret"', step_type="When")
    never_called_provider: EmbeddingProvider = _NeverCalledEmbeddingProvider()
    live_matcher = LiveSemanticMatcher(never_called_provider)

    decision = decide_reuse(need, empty_catalog, live_matcher)

    assert isinstance(decision, NoMatch)


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


def test_same_inputs_and_stub_always_produce_the_same_decision() -> None:
    asset = _login_step_definition()
    catalog = _catalog(asset)
    need = _fitting_need()
    candidate = MatchCandidate(
        asset_id=_LOGIN_ASSET_ID, confidence=0.95, content_hash=_CURRENT_HASH
    )
    matcher = StubSemanticMatcher({need.text: (candidate,)})

    decisions = [decide_reuse(need, catalog, matcher) for _ in range(5)]

    assert all(d == decisions[0] for d in decisions)
    assert isinstance(decisions[0], TrustedReuse)


def test_confidence_threshold_is_configurable() -> None:
    """The threshold is a tunable parameter, not a hardcoded constant baked
    into the decision logic -- a lower threshold trusts a match the default
    would have escalated."""
    asset = _login_step_definition()
    catalog = _catalog(asset)
    need = _fitting_need()
    low_confidence = 0.5
    candidate = MatchCandidate(
        asset_id=_LOGIN_ASSET_ID, confidence=low_confidence, content_hash=_CURRENT_HASH
    )
    matcher = StubSemanticMatcher({need.text: (candidate,)})

    escalated = decide_reuse(need, catalog, matcher)
    assert isinstance(escalated, Escalation)

    trusted = decide_reuse(need, catalog, matcher, confidence_threshold=0.4)
    assert isinstance(trusted, TrustedReuse)
