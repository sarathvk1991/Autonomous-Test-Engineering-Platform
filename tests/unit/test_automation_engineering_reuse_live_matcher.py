"""`LiveSemanticMatcher` -- the embeddings-backed `SemanticMatcher`
(ADR-0044 D3's lean, resolved). Tested against a deterministic FAKE
`EmbeddingProvider` (canned vectors, no network) -- the same
"stub the seam one level down" discipline the engine's own tests use for
`SemanticMatcher` itself. Proves: one batched call per `match()`; cosine
similarity ranks candidates best-first; only step definitions are
considered; an empty catalog short-circuits before any embedding call.
"""

from __future__ import annotations

from collections.abc import Sequence

import pytest

from automation_engineering.catalog.alignment import correlate
from automation_engineering.catalog.models import (
    AssetCatalog,
    JavaParameter,
    PageObjectAsset,
    StepDefinitionAsset,
)
from automation_engineering.reuse.live_matcher import LiveSemanticMatcher
from automation_engineering.reuse.models import GherkinStepNeed

pytestmark = pytest.mark.unit


class _FakeEmbeddingProvider:
    """Deterministic stand-in for `EmbeddingProvider` -- returns pre-authored
    vectors keyed by input text order, no network call. Records every batch
    it was called with, for call-count/argument assertions."""

    def __init__(self, vectors_by_text: dict[str, tuple[float, ...]]) -> None:
        self._vectors_by_text = vectors_by_text
        self.calls: list[list[str]] = []

    def embed(self, texts: Sequence[str]) -> tuple[tuple[float, ...], ...]:
        self.calls.append(list(texts))
        return tuple(self._vectors_by_text[t] for t in texts)


def _step(asset_id: str, pattern: str, content_hash: str) -> StepDefinitionAsset:
    parameters = (
        (JavaParameter(name="username", java_type="String"),) if "{string}" in pattern else ()
    )
    return StepDefinitionAsset(
        asset_id=asset_id,
        class_name="com.automation.steps.Steps",
        method_name="m",
        step_type="When",
        pattern=pattern,
        parameters=parameters,
        return_type="void",
        source_file="com/automation/steps/Steps.java",
        content_hash=content_hash,
        signature_alignment=correlate(pattern, parameters),
    )


def test_ranks_candidates_best_first_by_cosine_similarity() -> None:
    login = _step("STEP-login", "I log in as {string}", "hash-login")
    logout = _step("STEP-logout", "I log out", "hash-logout")
    catalog = AssetCatalog(baseline_root="test-suite-baseline", step_definitions=(login, logout))
    need = GherkinStepNeed(text="I log in as alice", step_type="When")

    provider = _FakeEmbeddingProvider(
        {
            "I log in as alice": (1.0, 0.0),
            "I log in as {string}": (1.0, 0.0),  # identical direction -> similarity 1.0
            "I log out": (0.0, 1.0),  # orthogonal -> similarity 0.0
        }
    )
    matcher = LiveSemanticMatcher(provider)

    result = matcher.match(need, catalog)

    assert [c.asset_id for c in result] == ["STEP-login", "STEP-logout"]
    assert result[0].confidence == pytest.approx(1.0)
    assert result[1].confidence == pytest.approx(0.0)


def test_candidate_carries_the_content_hash_at_match_time() -> None:
    login = _step("STEP-login", "I log in as {string}", "hash-at-match-time")
    catalog = AssetCatalog(baseline_root="test-suite-baseline", step_definitions=(login,))
    need = GherkinStepNeed(text="I log in", step_type="When")
    provider = _FakeEmbeddingProvider({"I log in": (1.0, 0.0), "I log in as {string}": (1.0, 0.0)})
    matcher = LiveSemanticMatcher(provider)

    result = matcher.match(need, catalog)

    assert result[0].content_hash == "hash-at-match-time"


def test_makes_exactly_one_batched_embedding_call() -> None:
    login = _step("STEP-login", "I log in as {string}", "h1")
    logout = _step("STEP-logout", "I log out", "h2")
    catalog = AssetCatalog(baseline_root="test-suite-baseline", step_definitions=(login, logout))
    need = GherkinStepNeed(text="I log in", step_type="When")
    provider = _FakeEmbeddingProvider(
        {"I log in": (1.0, 0.0), "I log in as {string}": (1.0, 0.0), "I log out": (0.0, 1.0)}
    )
    matcher = LiveSemanticMatcher(provider)

    matcher.match(need, catalog)

    assert len(provider.calls) == 1
    assert provider.calls[0] == ["I log in", "I log in as {string}", "I log out"]


def test_empty_catalog_short_circuits_before_any_embedding_call() -> None:
    catalog = AssetCatalog(baseline_root="test-suite-baseline")
    need = GherkinStepNeed(text="I log in", step_type="When")
    provider = _FakeEmbeddingProvider({})
    matcher = LiveSemanticMatcher(provider)

    result = matcher.match(need, catalog)

    assert result == ()
    assert provider.calls == []


def test_prime_then_match_for_several_needs_makes_exactly_one_call() -> None:
    """FIX 1 verification: the whole-run batching lever. Without `prime()`,
    N needs make N `embed()` calls (one per `match()`, each re-embedding the
    unchanged catalog). With `prime()` called once up front, every
    subsequent `match()` call is a pure cache hit -- zero further calls."""
    login = _step("STEP-login", "I log in as {string}", "h1")
    logout = _step("STEP-logout", "I log out", "h2")
    catalog = AssetCatalog(baseline_root="test-suite-baseline", step_definitions=(login, logout))
    needs = [
        GherkinStepNeed(text="I log in", step_type="When"),
        GherkinStepNeed(text="I check out", step_type="When"),
        GherkinStepNeed(text="I browse", step_type="When"),
    ]
    provider = _FakeEmbeddingProvider(
        {
            "I log in": (1.0, 0.0),
            "I check out": (0.5, 0.5),
            "I browse": (0.0, 1.0),
            "I log in as {string}": (1.0, 0.0),
            "I log out": (0.0, 1.0),
        }
    )
    matcher = LiveSemanticMatcher(provider)

    matcher.prime(needs, catalog)
    for need in needs:
        matcher.match(need, catalog)

    assert len(provider.calls) == 1
    assert set(provider.calls[0]) == {
        "I log in",
        "I check out",
        "I browse",
        "I log in as {string}",
        "I log out",
    }


def test_prime_deduplicates_repeated_texts_within_one_call() -> None:
    login = _step("STEP-login", "I log in as {string}", "h1")
    catalog = AssetCatalog(baseline_root="test-suite-baseline", step_definitions=(login,))
    needs = [
        GherkinStepNeed(text="I log in", step_type="When"),
        GherkinStepNeed(text="I log in", step_type="When"),  # duplicate on purpose
    ]
    provider = _FakeEmbeddingProvider(
        {"I log in": (1.0, 0.0), "I log in as {string}": (1.0, 0.0)}
    )
    matcher = LiveSemanticMatcher(provider)

    matcher.prime(needs, catalog)

    assert len(provider.calls) == 1
    assert provider.calls[0] == ["I log in", "I log in as {string}"]


def test_prime_with_nothing_new_to_embed_makes_no_call() -> None:
    catalog = AssetCatalog(baseline_root="test-suite-baseline")
    provider = _FakeEmbeddingProvider({})
    matcher = LiveSemanticMatcher(provider)

    matcher.prime([], catalog)

    assert provider.calls == []


def test_match_without_priming_still_embeds_on_demand_unchanged() -> None:
    """Backward compatibility: a caller that never calls `prime()` (every
    pre-existing test above) gets exactly the old behavior -- `match()`
    embeds on its own cache miss."""
    login = _step("STEP-login", "I log in as {string}", "h1")
    catalog = AssetCatalog(baseline_root="test-suite-baseline", step_definitions=(login,))
    need = GherkinStepNeed(text="I log in", step_type="When")
    provider = _FakeEmbeddingProvider(
        {"I log in": (1.0, 0.0), "I log in as {string}": (1.0, 0.0)}
    )
    matcher = LiveSemanticMatcher(provider)

    result = matcher.match(need, catalog)

    assert [c.asset_id for c in result] == ["STEP-login"]
    assert len(provider.calls) == 1


def test_only_step_definitions_are_considered_not_page_objects() -> None:
    login = _step("STEP-login", "I log in as {string}", "h1")
    page = PageObjectAsset(
        asset_id="PAGE-login",
        class_name="com.automation.pages.LoginPage",
        extends="BasePage",
        fields=(),
        locators=(),
        methods=(),
        source_file="com/automation/pages/LoginPage.java",
        content_hash="hp1",
    )
    catalog = AssetCatalog(
        baseline_root="test-suite-baseline", step_definitions=(login,), page_objects=(page,)
    )
    need = GherkinStepNeed(text="I log in", step_type="When")
    provider = _FakeEmbeddingProvider({"I log in": (1.0, 0.0), "I log in as {string}": (1.0, 0.0)})
    matcher = LiveSemanticMatcher(provider)

    result = matcher.match(need, catalog)

    assert [c.asset_id for c in result] == ["STEP-login"]
    assert provider.calls[0] == ["I log in", "I log in as {string}"]
