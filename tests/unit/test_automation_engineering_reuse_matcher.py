"""The `SemanticMatcher` seam and its deterministic stub (ADR-0044 D3's
matching mechanism, the only nondeterministic part of the reuse engine).

Proves `StubSemanticMatcher`'s own scripted-response discipline: a
registered step text returns exactly its canned candidates, in order,
every call; an unscripted step text raises rather than silently
inventing a match or a non-match -- the same discipline
`StubFeatureRemediator` already established.
"""

from __future__ import annotations

import pytest

from automation_engineering.catalog.models import AssetCatalog
from automation_engineering.reuse.matcher import SemanticMatcher, StubSemanticMatcher
from automation_engineering.reuse.models import GherkinStepNeed, MatchCandidate

pytestmark = pytest.mark.unit

_EMPTY_CATALOG = AssetCatalog(baseline_root="test-suite-baseline")


def test_stub_conforms_to_seam() -> None:
    matcher: SemanticMatcher = StubSemanticMatcher({})
    assert hasattr(matcher, "match")


def test_stub_returns_the_canned_candidates_for_a_registered_step_text() -> None:
    candidate = MatchCandidate(asset_id="STEP-abc", confidence=0.9, content_hash="h1")
    matcher = StubSemanticMatcher({"I log in": (candidate,)})
    need = GherkinStepNeed(text="I log in", step_type="When")

    result = matcher.match(need, _EMPTY_CATALOG)

    assert result == (candidate,)


def test_stub_returns_empty_tuple_when_scripted_as_no_match() -> None:
    matcher = StubSemanticMatcher({"nothing similar": ()})
    need = GherkinStepNeed(text="nothing similar", step_type="Given")

    assert matcher.match(need, _EMPTY_CATALOG) == ()


def test_stub_raises_on_unscripted_step_text() -> None:
    matcher = StubSemanticMatcher({"I log in": ()})
    need = GherkinStepNeed(text="an unregistered step", step_type="Given")

    with pytest.raises(KeyError, match="unregistered step"):
        matcher.match(need, _EMPTY_CATALOG)


def test_stub_call_count_tracks_invocations() -> None:
    matcher = StubSemanticMatcher({"step one": (), "step two": ()})
    matcher.match(GherkinStepNeed(text="step one", step_type="Given"), _EMPTY_CATALOG)
    matcher.match(GherkinStepNeed(text="step two", step_type="Given"), _EMPTY_CATALOG)

    assert matcher.call_count == 2


def test_stub_is_deterministic_across_repeated_calls_for_the_same_need() -> None:
    candidate = MatchCandidate(asset_id="STEP-abc", confidence=0.9, content_hash="h1")
    matcher = StubSemanticMatcher({"I log in": (candidate,)})
    need = GherkinStepNeed(text="I log in", step_type="When")

    results = [matcher.match(need, _EMPTY_CATALOG) for _ in range(3)]

    assert all(r == (candidate,) for r in results)
