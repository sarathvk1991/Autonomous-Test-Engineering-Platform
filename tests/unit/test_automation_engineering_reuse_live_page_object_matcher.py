"""`LivePageObjectSemanticMatcher` -- the page-object-scoped counterpart to
`LiveSemanticMatcher` (`automation_engineering/reuse/live_matcher.py`),
closing the blocker the stage-15 page-object wiring flagged (no live
`SemanticMatcher` correctly matches a page-object need against
`catalog.page_objects`). Tested against the SAME deterministic FAKE
`EmbeddingProvider` discipline
`test_automation_engineering_reuse_live_matcher.py` already uses -- no
network, no live LLM. Proves: the Protocol shape mirrors the step-def
matcher exactly (ranking, content-hash, batching, priming, empty-catalog
short-circuit); it is scoped to `catalog.page_objects` and never touches
`catalog.step_definitions` (no wrong-catalog match); and, composed with the
already-built reuse engine, a page-object need that matches an existing
tracked page object's real method BINDS while one that doesn't GENERATES.
"""

from __future__ import annotations

from collections.abc import Sequence

import pytest

from automation_engineering.catalog.alignment import correlate
from automation_engineering.catalog.models import (
    AssetCatalog,
    JavaMethod,
    PageObjectAsset,
    StepDefinitionAsset,
)
from automation_engineering.generation.models import (
    BoundPageObjectMethod,
    GeneratedPageObject,
    PageObjectMethodNeed,
)
from automation_engineering.generation.page_object_generator import StubPageObjectGenerator
from automation_engineering.generation.page_object_orchestrator import (
    orchestrate_page_object_method,
)
from automation_engineering.reuse.live_page_object_matcher import (
    LivePageObjectSemanticMatcher,
    page_object_embedding_text,
)
from automation_engineering.reuse.models import GherkinStepNeed

pytestmark = pytest.mark.unit


class _FakeEmbeddingProvider:
    """Deterministic stand-in for `EmbeddingProvider` -- returns pre-authored
    vectors keyed by input text, no network call. Records every batch it
    was called with, for call-count/argument assertions. Identical
    discipline to `test_automation_engineering_reuse_live_matcher.py`'s own
    fake."""

    def __init__(self, vectors_by_text: dict[str, tuple[float, ...]]) -> None:
        self._vectors_by_text = vectors_by_text
        self.calls: list[list[str]] = []

    def embed(self, texts: Sequence[str]) -> tuple[tuple[float, ...], ...]:
        self.calls.append(list(texts))
        return tuple(self._vectors_by_text[t] for t in texts)


def _page(
    asset_id: str,
    class_name: str,
    semantic_tags: tuple[str, ...],
    content_hash: str,
    *,
    methods: tuple[JavaMethod, ...] = (),
) -> PageObjectAsset:
    return PageObjectAsset(
        asset_id=asset_id,
        class_name=class_name,
        extends="BasePage",
        fields=(),
        locators=(),
        methods=methods,
        source_file="com/automation/pages/Page.java",
        content_hash=content_hash,
        semantic_tags=semantic_tags,
    )


# ---------------------------------------------------------------------------
# Protocol-shape mirror of LiveSemanticMatcher (ranking, hash, batching)
# ---------------------------------------------------------------------------


def test_ranks_candidates_best_first_by_cosine_similarity() -> None:
    login = _page("PAGE-login", "com.automation.pages.LoginPage", ("login", "page"), "hash-login")
    cart = _page("PAGE-cart", "com.automation.pages.CartPage", ("cart", "page"), "hash-cart")
    catalog = AssetCatalog(baseline_root="test-suite-baseline", page_objects=(login, cart))
    need = GherkinStepNeed(text="I am on the login page", step_type="Given")

    provider = _FakeEmbeddingProvider(
        {
            "I am on the login page": (1.0, 0.0),
            "login page": (1.0, 0.0),  # identical direction -> similarity 1.0
            "cart page": (0.0, 1.0),  # orthogonal -> similarity 0.0
        }
    )
    matcher = LivePageObjectSemanticMatcher(provider)

    result = matcher.match(need, catalog)

    assert [c.asset_id for c in result] == ["PAGE-login", "PAGE-cart"]
    assert result[0].confidence == pytest.approx(1.0)
    assert result[1].confidence == pytest.approx(0.0)


def test_candidate_carries_the_content_hash_at_match_time() -> None:
    login = _page(
        "PAGE-login", "com.automation.pages.LoginPage", ("login", "page"), "hash-at-match-time"
    )
    catalog = AssetCatalog(baseline_root="test-suite-baseline", page_objects=(login,))
    need = GherkinStepNeed(text="I am on the login page", step_type="Given")
    provider = _FakeEmbeddingProvider(
        {"I am on the login page": (1.0, 0.0), "login page": (1.0, 0.0)}
    )
    matcher = LivePageObjectSemanticMatcher(provider)

    result = matcher.match(need, catalog)

    assert result[0].content_hash == "hash-at-match-time"


def test_makes_exactly_one_batched_embedding_call() -> None:
    login = _page("PAGE-login", "com.automation.pages.LoginPage", ("login", "page"), "h1")
    cart = _page("PAGE-cart", "com.automation.pages.CartPage", ("cart", "page"), "h2")
    catalog = AssetCatalog(baseline_root="test-suite-baseline", page_objects=(login, cart))
    need = GherkinStepNeed(text="I am on the login page", step_type="Given")
    provider = _FakeEmbeddingProvider(
        {"I am on the login page": (1.0, 0.0), "login page": (1.0, 0.0), "cart page": (0.0, 1.0)}
    )
    matcher = LivePageObjectSemanticMatcher(provider)

    matcher.match(need, catalog)

    assert len(provider.calls) == 1
    assert provider.calls[0] == ["I am on the login page", "login page", "cart page"]


def test_empty_catalog_short_circuits_before_any_embedding_call() -> None:
    catalog = AssetCatalog(baseline_root="test-suite-baseline")
    need = GherkinStepNeed(text="I am on the login page", step_type="Given")
    provider = _FakeEmbeddingProvider({})
    matcher = LivePageObjectSemanticMatcher(provider)

    result = matcher.match(need, catalog)

    assert result == ()
    assert provider.calls == []


def test_prime_then_match_for_several_needs_makes_exactly_one_call() -> None:
    login = _page("PAGE-login", "com.automation.pages.LoginPage", ("login", "page"), "h1")
    cart = _page("PAGE-cart", "com.automation.pages.CartPage", ("cart", "page"), "h2")
    catalog = AssetCatalog(baseline_root="test-suite-baseline", page_objects=(login, cart))
    needs = [
        GherkinStepNeed(text="I am on the login page", step_type="Given"),
        GherkinStepNeed(text="I check out", step_type="When"),
    ]
    provider = _FakeEmbeddingProvider(
        {
            "I am on the login page": (1.0, 0.0),
            "I check out": (0.5, 0.5),
            "login page": (1.0, 0.0),
            "cart page": (0.0, 1.0),
        }
    )
    matcher = LivePageObjectSemanticMatcher(provider)

    matcher.prime(needs, catalog)
    for need in needs:
        matcher.match(need, catalog)

    assert len(provider.calls) == 1
    assert set(provider.calls[0]) == {
        "I am on the login page",
        "I check out",
        "login page",
        "cart page",
    }


def test_prime_with_nothing_new_to_embed_makes_no_call() -> None:
    catalog = AssetCatalog(baseline_root="test-suite-baseline")
    provider = _FakeEmbeddingProvider({})
    matcher = LivePageObjectSemanticMatcher(provider)

    matcher.prime([], catalog)

    assert provider.calls == []


def test_match_without_priming_still_embeds_on_demand_unchanged() -> None:
    login = _page("PAGE-login", "com.automation.pages.LoginPage", ("login", "page"), "h1")
    catalog = AssetCatalog(baseline_root="test-suite-baseline", page_objects=(login,))
    need = GherkinStepNeed(text="I am on the login page", step_type="Given")
    provider = _FakeEmbeddingProvider(
        {"I am on the login page": (1.0, 0.0), "login page": (1.0, 0.0)}
    )
    matcher = LivePageObjectSemanticMatcher(provider)

    result = matcher.match(need, catalog)

    assert [c.asset_id for c in result] == ["PAGE-login"]
    assert len(provider.calls) == 1


# ---------------------------------------------------------------------------
# Scoping: page_objects only, never step_definitions -- no wrong-catalog match
# ---------------------------------------------------------------------------


def test_only_page_objects_are_considered_not_step_definitions() -> None:
    """The mirror image of `test_only_step_definitions_are_considered_not_
    page_objects` in the step-def matcher's own test file -- this matcher
    reads `catalog.page_objects` exclusively; a step-definition asset in
    the SAME catalog is never embedded, never returned, and never even
    inspected (no `StepDefinitionAsset`-shaped attribute access that could
    raise)."""
    login_page = _page("PAGE-login", "com.automation.pages.LoginPage", ("login", "page"), "hp1")
    login_step = StepDefinitionAsset(
        asset_id="STEP-login",
        class_name="com.automation.steps.LoginSteps",
        method_name="iAmOnTheLoginPage",
        step_type="Given",
        pattern="I am on the login page",
        parameters=(),
        return_type="void",
        source_file="com/automation/steps/LoginSteps.java",
        content_hash="hs1",
        signature_alignment=correlate("I am on the login page", ()),
    )
    catalog = AssetCatalog(
        baseline_root="test-suite-baseline",
        step_definitions=(login_step,),
        page_objects=(login_page,),
    )
    need = GherkinStepNeed(text="I am on the login page", step_type="Given")
    provider = _FakeEmbeddingProvider(
        {"I am on the login page": (1.0, 0.0), "login page": (1.0, 0.0)}
    )
    matcher = LivePageObjectSemanticMatcher(provider)

    result = matcher.match(need, catalog)

    assert [c.asset_id for c in result] == ["PAGE-login"]
    # The step-definition's own pattern text was never sent to the
    # provider -- proof this matcher never even looked at it.
    assert provider.calls[0] == ["I am on the login page", "login page"]


def test_embedding_text_is_the_semantic_tags_only_no_pattern_field_exists() -> None:
    page = _page(
        "PAGE-login",
        "com.automation.pages.LoginPage",
        ("login", "page", "attempt", "username", "password"),
        "h1",
    )
    assert page_object_embedding_text(page) == "login page attempt username password"


# ---------------------------------------------------------------------------
# Type-correctness: a page-object candidate resolves to a PageObjectAsset,
# never a StepDefinitionAsset -- no wrong-catalog TypeError downstream.
# ---------------------------------------------------------------------------


def test_matched_candidate_resolves_to_a_page_object_asset_in_the_catalog() -> None:
    login_page = _page("PAGE-login", "com.automation.pages.LoginPage", ("login", "page"), "h1")
    catalog = AssetCatalog(baseline_root="test-suite-baseline", page_objects=(login_page,))
    need = GherkinStepNeed(text="I am on the login page", step_type="Given")
    provider = _FakeEmbeddingProvider(
        {"I am on the login page": (1.0, 0.0), "login page": (1.0, 0.0)}
    )
    matcher = LivePageObjectSemanticMatcher(provider)

    candidate = matcher.match(need, catalog)[0]
    resolved = catalog.get(candidate.asset_id)

    assert isinstance(resolved, PageObjectAsset)


# ---------------------------------------------------------------------------
# End-to-end reuse loop, composed with the already-built orchestrator:
# BIND on a real structural match, GENERATE FRESH on NoMatch.
# ---------------------------------------------------------------------------


def test_bind_when_the_matched_page_object_has_the_specific_method_needed() -> None:
    """A page-object need whose class-level SEMANTIC match (this module)
    resolves to a page object that also has the SPECIFIC method requested
    (the already-built, unchanged coarse + precise structural checks) BINDS
    -- never regenerates."""
    login_page = _page(
        "PAGE-login",
        "com.automation.pages.LoginPage",
        ("login", "page", "enter", "username"),
        "h1",
        methods=(JavaMethod(name="enterUsername", parameters=(), return_type="void"),),
    )
    catalog = AssetCatalog(baseline_root="test-suite-baseline", page_objects=(login_page,))
    step_need = GherkinStepNeed(text="I am on the login page", step_type="Given")
    method_need = PageObjectMethodNeed(
        need=step_need, method_name="enterUsername", class_name_override="LoginPage"
    )
    provider = _FakeEmbeddingProvider(
        {"I am on the login page": (1.0, 0.0), "login page enter username": (1.0, 0.0)}
    )
    matcher = LivePageObjectSemanticMatcher(provider)
    generator = StubPageObjectGenerator({})  # never called -- proof the BIND path never generates

    outcome = orchestrate_page_object_method(method_need, catalog, matcher, generator)

    assert isinstance(outcome, BoundPageObjectMethod)
    assert outcome.asset.asset_id == "PAGE-login"
    assert generator.call_count == 0


def test_generate_fresh_when_no_page_object_matches_at_all() -> None:
    """An empty `catalog.page_objects` (or, equivalently, nothing
    plausible) is NoMatch -- generates fresh, exactly the step-definition
    reuse engine's own NO_MATCH/generate boundary (ADR-0044 D3), now
    exercised for page objects through a real live-shaped matcher."""
    catalog = AssetCatalog(baseline_root="test-suite-baseline", page_objects=())
    step_need = GherkinStepNeed(text="I am on the login page", step_type="Given")
    method_need = PageObjectMethodNeed(
        need=step_need, method_name="enterUsername", class_name_override="LoginPage"
    )
    provider = _FakeEmbeddingProvider({})
    matcher = LivePageObjectSemanticMatcher(provider)
    generated_java = (
        "package com.automation.pages;\n\n"
        "import com.automation.base.BasePage;\n"
        "import org.openqa.selenium.WebDriver;\n\n"
        "public class LoginPage extends BasePage {\n"
        "    public LoginPage(WebDriver driver) { super(driver); }\n"
        "    public void enterUsername(String username) { }\n"
        "}\n"
    )
    generator = StubPageObjectGenerator({"I am on the login page": generated_java})

    outcome = orchestrate_page_object_method(method_need, catalog, matcher, generator)

    assert isinstance(outcome, GeneratedPageObject)
    assert generator.call_count == 1
