"""Reuse-first page-object orchestration PLUS the precise method-fit
discharge (`automation_engineering.generation.page_object_orchestrator`,
`automation_engineering.generation.method_fit`) -- proves, deterministically
and without any live call:

Part 1 (generation, mirrors the step-def proofs):
* NO_MATCH -> GENERATE: the stub generator IS called, a page object lands in
  `com.automation.pages`, extends `BasePage`, constructor-injected driver
  convention (ADR-0041 D5).
* TRUSTED_REUSE (specific method present) -> BIND, never regenerate: the
  stub generator is proven NOT called via its own spy.
* ESCALATION (reuse engine's own checks) -> neither generated nor bound,
  surfaced for review, untouched.
* customqa:* constraints are actually injected into what the generation seam
  receives.

Part 2 -- THE METHOD-FIT DISCHARGE (the D4-critical page-object proofs, now
REAL, not deferred):
* PRECISE method-fit ESCALATES on the insufficient case: a TRUSTED_REUSE
  page object that has SOME coarsely-compatible method but LACKS the
  specific one being called.
* PRECISE method-fit PASSES when the reused page object HAS the specific
  method, with a fitting signature.
* CONTRAST proof: the SAME candidate that clears the COARSE screen
  (`automation_engineering.reuse.engine.decide_reuse` itself returns
  `TrustedReuse`, not an `Escalation`) still fails the PRECISE check --
  showing the two halves catch different things, exactly as ADR-0044 D4's
  clarification note describes.

Builds on the real catalog shapes (`automation_engineering.catalog.models`),
the same discipline `tests/unit/test_automation_engineering_reuse_engine.py`
and `tests/unit/test_automation_engineering_reuse_method_fit.py` already
established, so this orchestration is proven against the SAME reuse-decision
data the engine actually produces.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from automation_engineering.catalog.models import (
    AssetCatalog,
    JavaMethod,
    JavaParameter,
    PageObjectAsset,
    StepCapture,
)
from automation_engineering.generation.method_fit import verify_specific_method_fit
from automation_engineering.generation.models import (
    BoundPageObjectMethod,
    EscalatedPageObjectMethodNeed,
    GeneratedPageObject,
    PageObjectMethodNeed,
)
from automation_engineering.generation.page_object_generator import StubPageObjectGenerator
from automation_engineering.generation.page_object_orchestrator import (
    DEFAULT_CUSTOMQA_PAGE_OBJECT_CONSTRAINTS,
    DEFAULT_PAGE_OBJECT_TARGET_PACKAGE,
    derive_page_object_class_name,
    generate_page_object_methods,
    orchestrate_page_object_method,
)
from automation_engineering.reuse.engine import decide_reuse
from automation_engineering.reuse.matcher import StubSemanticMatcher
from automation_engineering.reuse.models import (
    EscalationCheck,
    GherkinStepNeed,
    MatchCandidate,
    TrustedReuse,
)

pytestmark = pytest.mark.unit

_LOGIN_ASSET_ID = "PAGE-loginfixture01"
_CURRENT_HASH = "current-hash-abc123"
_STALE_HASH = "stale-hash-000000"


def _page_object(
    asset_id: str = _LOGIN_ASSET_ID,
    class_name: str = "com.automation.pages.LoginPage",
    methods: tuple[JavaMethod, ...] = (),
    content_hash: str = _CURRENT_HASH,
) -> PageObjectAsset:
    return PageObjectAsset(
        asset_id=asset_id,
        class_name=class_name,
        extends="BasePage",
        fields=(),
        locators=(),
        methods=methods,
        source_file="com/automation/pages/LoginPage.java",
        content_hash=content_hash,
    )


def _catalog(*assets: PageObjectAsset) -> AssetCatalog:
    return AssetCatalog(baseline_root="test-suite-baseline", page_objects=tuple(assets))


def _method_need(
    action_text: str = "click the forgot password link",
    method_name: str = "clickForgotPasswordLink",
) -> PageObjectMethodNeed:
    return PageObjectMethodNeed(
        need=GherkinStepNeed(text=action_text, step_type="PageAction", captures=()),
        method_name=method_name,
    )


# ---------------------------------------------------------------------------
# NO_MATCH -> generate
# ---------------------------------------------------------------------------


class TestNoMatchGenerates:
    def test_generates_a_page_object_in_com_automation_pages(self) -> None:
        method_need = _method_need()
        catalog = _catalog()  # empty -- nothing to reuse
        matcher = StubSemanticMatcher({method_need.need.text: ()})
        canned_java = (
            "package com.automation.pages;\n\n"
            "import com.automation.base.BasePage;\n"
            "import org.openqa.selenium.By;\n"
            "import org.openqa.selenium.WebDriver;\n\n"
            "public class ForgotPasswordLinkPage extends BasePage {\n"
            "    private final By link = By.id(\"forgot-password\");\n\n"
            "    public ForgotPasswordLinkPage(WebDriver driver) {\n"
            "        super(driver);\n"
            "    }\n\n"
            "    public void clickForgotPasswordLink() {\n"
            "        driver.findElement(link).click();\n"
            "    }\n"
            "}\n"
        )
        generator = StubPageObjectGenerator({method_need.need.text: canned_java})

        outcome = orchestrate_page_object_method(method_need, catalog, matcher, generator)

        assert isinstance(outcome, GeneratedPageObject)
        assert outcome.method_need == method_need
        assert outcome.java_source == canned_java
        assert "extends BasePage" in outcome.java_source
        assert "WebDriver driver" in outcome.java_source
        assert (
            outcome.target_package
            == DEFAULT_PAGE_OBJECT_TARGET_PACKAGE
            == "com.automation.pages"
        )
        assert outcome.class_name == "ForgotPasswordLinkPage"
        assert generator.call_count == 1

    def test_generator_is_called_exactly_once_per_no_match_need(self) -> None:
        method_need = _method_need()
        catalog = _catalog()
        matcher = StubSemanticMatcher({method_need.need.text: ()})
        generator = StubPageObjectGenerator(
            {method_need.need.text: "package com.automation.pages;\n"}
        )

        orchestrate_page_object_method(method_need, catalog, matcher, generator)

        assert generator.call_count == 1


# ---------------------------------------------------------------------------
# TRUSTED_REUSE (specific method present) -> bind, never regenerate
# ---------------------------------------------------------------------------


class TestTrustedReuseWithSufficientMethodBindsWithoutRegenerating:
    def test_binds_to_the_existing_asset(self) -> None:
        asset = _page_object(
            methods=(JavaMethod(name="clickForgotPasswordLink", parameters=(), return_type="void"),)
        )
        catalog = _catalog(asset)
        method_need = _method_need()
        candidate = MatchCandidate(
            asset_id=_LOGIN_ASSET_ID, confidence=0.95, content_hash=_CURRENT_HASH
        )
        matcher = StubSemanticMatcher({method_need.need.text: (candidate,)})
        generator = StubPageObjectGenerator({})  # must never be called

        outcome = orchestrate_page_object_method(method_need, catalog, matcher, generator)

        assert isinstance(outcome, BoundPageObjectMethod)
        assert outcome.method_need == method_need
        assert outcome.asset is asset

    def test_generator_is_never_called_for_a_sufficient_trusted_reuse(self) -> None:
        """The spy proof this build's verification section requires: zero
        generation calls when a trusted reuse's specific method is present."""
        asset = _page_object(
            methods=(JavaMethod(name="clickForgotPasswordLink", parameters=(), return_type="void"),)
        )
        catalog = _catalog(asset)
        method_need = _method_need()
        candidate = MatchCandidate(
            asset_id=_LOGIN_ASSET_ID, confidence=0.95, content_hash=_CURRENT_HASH
        )
        matcher = StubSemanticMatcher({method_need.need.text: (candidate,)})
        generator = StubPageObjectGenerator({})

        orchestrate_page_object_method(method_need, catalog, matcher, generator)

        assert generator.call_count == 0
        assert generator.received_contexts == ()


# ---------------------------------------------------------------------------
# ESCALATION (reuse engine's own checks) -> neither generated nor bound
# ---------------------------------------------------------------------------


class TestReuseEngineEscalationSurfacesForReview:
    def test_low_confidence_escalates_without_generating_or_binding(self) -> None:
        asset = _page_object(
            methods=(JavaMethod(name="clickForgotPasswordLink", parameters=(), return_type="void"),)
        )
        catalog = _catalog(asset)
        method_need = _method_need()
        # 0.72 -- inside the escalate band, not below the NO_MATCH/generate
        # floor (ADR-0044 D3/D4's additive note).
        candidate = MatchCandidate(
            asset_id=_LOGIN_ASSET_ID, confidence=0.72, content_hash=_CURRENT_HASH
        )
        matcher = StubSemanticMatcher({method_need.need.text: (candidate,)})
        generator = StubPageObjectGenerator({})

        outcome = orchestrate_page_object_method(method_need, catalog, matcher, generator)

        assert isinstance(outcome, EscalatedPageObjectMethodNeed)
        assert outcome.method_need == method_need
        assert outcome.escalation.check == EscalationCheck.CONFIDENCE
        assert outcome.escalation.candidate == candidate
        assert generator.call_count == 0

    def test_stale_content_hash_escalates_without_generating_or_binding(self) -> None:
        asset = _page_object(
            methods=(
                JavaMethod(name="clickForgotPasswordLink", parameters=(), return_type="void"),
            ),
            content_hash=_CURRENT_HASH,
        )
        catalog = _catalog(asset)
        method_need = _method_need()
        candidate = MatchCandidate(
            asset_id=_LOGIN_ASSET_ID, confidence=0.95, content_hash=_STALE_HASH
        )
        matcher = StubSemanticMatcher({method_need.need.text: (candidate,)})
        generator = StubPageObjectGenerator({})

        outcome = orchestrate_page_object_method(method_need, catalog, matcher, generator)

        assert isinstance(outcome, EscalatedPageObjectMethodNeed)
        assert outcome.escalation.check == EscalationCheck.CONTENT_HASH
        assert generator.call_count == 0

    def test_gross_coarse_incompatibility_escalates_without_generating_or_binding(self) -> None:
        """The COARSE screen's own job: a candidate whose class has NO
        method at all with a compatible shape (every method is zero-arg,
        the need requires one capture) escalates at decision time, before
        this build's own precise check is ever reached."""
        asset = _page_object(methods=(JavaMethod(name="open", parameters=(), return_type="void"),))
        catalog = _catalog(asset)

        method_need = PageObjectMethodNeed(
            need=GherkinStepNeed(
                text="log in with a username",
                step_type="PageAction",
                captures=(
                    StepCapture(index=0, style="cucumber_expression", expression_type="string"),
                ),
            ),
            method_name="loginWithUsername",
        )
        candidate = MatchCandidate(
            asset_id=_LOGIN_ASSET_ID, confidence=0.95, content_hash=_CURRENT_HASH
        )
        matcher = StubSemanticMatcher({method_need.need.text: (candidate,)})
        generator = StubPageObjectGenerator({})

        outcome = orchestrate_page_object_method(method_need, catalog, matcher, generator)

        assert isinstance(outcome, EscalatedPageObjectMethodNeed)
        assert outcome.escalation.check == EscalationCheck.METHOD_FIT
        assert generator.call_count == 0


# ---------------------------------------------------------------------------
# customqa:* constraint injection
# ---------------------------------------------------------------------------


class TestCustomqaConstraintsAreInjectedIntoGeneration:
    def test_default_constraints_reach_the_generation_seam(self) -> None:
        method_need = _method_need()
        catalog = _catalog()
        matcher = StubSemanticMatcher({method_need.need.text: ()})
        generator = StubPageObjectGenerator(
            {method_need.need.text: "package com.automation.pages;\n"}
        )

        orchestrate_page_object_method(method_need, catalog, matcher, generator)

        assert generator.call_count == 1
        received = generator.received_contexts[0]
        assert received.customqa_constraints == DEFAULT_CUSTOMQA_PAGE_OBJECT_CONSTRAINTS
        assert any("customqa:direct-webdriver-action" in c for c in received.customqa_constraints)
        assert any("customqa:long-method" in c for c in received.customqa_constraints)

    def test_caller_supplied_constraints_reach_the_generation_seam(self) -> None:
        method_need = _method_need()
        catalog = _catalog()
        matcher = StubSemanticMatcher({method_need.need.text: ()})
        generator = StubPageObjectGenerator(
            {method_need.need.text: "package com.automation.pages;\n"}
        )
        custom_constraints = ("custom-rule-one", "custom-rule-two")

        orchestrate_page_object_method(
            method_need, catalog, matcher, generator, customqa_constraints=custom_constraints
        )

        received = generator.received_contexts[0]
        assert received.customqa_constraints == custom_constraints

    def test_target_package_reaches_the_generation_seam(self) -> None:
        method_need = _method_need()
        catalog = _catalog()
        matcher = StubSemanticMatcher({method_need.need.text: ()})
        generator = StubPageObjectGenerator(
            {method_need.need.text: "package com.automation.pages;\n"}
        )

        orchestrate_page_object_method(
            method_need, catalog, matcher, generator, target_package="com.custom.pages"
        )

        received = generator.received_contexts[0]
        assert received.target_package == "com.custom.pages"


# ---------------------------------------------------------------------------
# PART 2 -- THE METHOD-FIT DISCHARGE
# ---------------------------------------------------------------------------


class TestPreciseMethodFitEscalatesTheInsufficientCase:
    """The case the COARSE decision-time check structurally could NOT catch
    (ADR-0044 D4's own clarification-note example, reproduced almost
    verbatim): a `LoginPage` reused for a step needing
    `clickForgotPasswordLink()`, where `LoginPage` merely happens to have
    some OTHER zero-arg method (`open()`)."""

    def test_reuse_engine_itself_returns_trusted_reuse_not_an_escalation(self) -> None:
        """First, prove the COARSE screen genuinely passes -- this is not a
        contrived case the engine would have caught anyway."""
        asset = _page_object(methods=(JavaMethod(name="open", parameters=(), return_type="void"),))
        catalog = _catalog(asset)
        method_need = _method_need()  # needs clickForgotPasswordLink -- absent
        candidate = MatchCandidate(
            asset_id=_LOGIN_ASSET_ID, confidence=0.95, content_hash=_CURRENT_HASH
        )
        matcher = StubSemanticMatcher({method_need.need.text: (candidate,)})

        decision = decide_reuse(method_need.need, catalog, matcher)

        assert isinstance(decision, TrustedReuse)
        assert decision.asset is asset

    def test_orchestration_escalates_despite_the_coarse_pass(self) -> None:
        """Then prove the FULL orchestration -- coarse pass included --
        still escalates, because the PRECISE check catches what the coarse
        one could not. THIS is the obligation discharged."""
        asset = _page_object(methods=(JavaMethod(name="open", parameters=(), return_type="void"),))
        catalog = _catalog(asset)
        method_need = _method_need()
        candidate = MatchCandidate(
            asset_id=_LOGIN_ASSET_ID, confidence=0.95, content_hash=_CURRENT_HASH
        )
        matcher = StubSemanticMatcher({method_need.need.text: (candidate,)})
        generator = StubPageObjectGenerator({})  # must never be called

        outcome = orchestrate_page_object_method(method_need, catalog, matcher, generator)

        assert isinstance(outcome, EscalatedPageObjectMethodNeed)
        assert outcome.escalation.check == EscalationCheck.METHOD_FIT
        assert "clickForgotPasswordLink" in outcome.escalation.detail
        assert "open" in outcome.escalation.detail  # names what IS available
        assert generator.call_count == 0  # not bound, not generated -- surfaced only

    def test_method_fit_verify_function_directly_escalates_on_absent_method(self) -> None:
        """Unit-level proof of :func:`verify_specific_method_fit` itself,
        independent of the orchestrator wiring around it."""
        asset = _page_object(methods=(JavaMethod(name="open", parameters=(), return_type="void"),))
        candidate = MatchCandidate(
            asset_id=_LOGIN_ASSET_ID, confidence=0.95, content_hash=_CURRENT_HASH
        )

        escalation = verify_specific_method_fit(
            _method_need().need, asset, candidate, "clickForgotPasswordLink"
        )

        assert escalation is not None
        assert escalation.check == EscalationCheck.METHOD_FIT

    def test_method_present_but_wrong_signature_also_escalates(self) -> None:
        """Present by name, but the wrong parameter shape (arity, here) --
        also fails the precise check, not merely a name-membership test."""
        asset = _page_object(
            methods=(
                JavaMethod(
                    name="clickForgotPasswordLink",
                    parameters=(JavaParameter(name="unexpected", java_type="int"),),
                    return_type="void",
                ),
            )
        )
        candidate = MatchCandidate(
            asset_id=_LOGIN_ASSET_ID, confidence=0.95, content_hash=_CURRENT_HASH
        )
        need = GherkinStepNeed(
            text="click the forgot password link", step_type="PageAction", captures=()
        )

        escalation = verify_specific_method_fit(need, asset, candidate, "clickForgotPasswordLink")

        assert escalation is not None
        assert escalation.check == EscalationCheck.METHOD_FIT
        assert "wrong" in escalation.detail.lower() or "does not fit" in escalation.detail.lower()


class TestPreciseMethodFitPassesTheSufficientCase:
    def test_method_present_with_fitting_signature_verifies_clean(self) -> None:
        asset = _page_object(
            methods=(JavaMethod(name="clickForgotPasswordLink", parameters=(), return_type="void"),)
        )
        candidate = MatchCandidate(
            asset_id=_LOGIN_ASSET_ID, confidence=0.95, content_hash=_CURRENT_HASH
        )

        escalation = verify_specific_method_fit(
            _method_need().need, asset, candidate, "clickForgotPasswordLink"
        )

        assert escalation is None

    def test_orchestration_binds_when_the_specific_method_is_present(self) -> None:
        asset = _page_object(
            methods=(JavaMethod(name="clickForgotPasswordLink", parameters=(), return_type="void"),)
        )
        catalog = _catalog(asset)
        method_need = _method_need()
        candidate = MatchCandidate(
            asset_id=_LOGIN_ASSET_ID, confidence=0.95, content_hash=_CURRENT_HASH
        )
        matcher = StubSemanticMatcher({method_need.need.text: (candidate,)})
        generator = StubPageObjectGenerator({})

        outcome = orchestrate_page_object_method(method_need, catalog, matcher, generator)

        assert isinstance(outcome, BoundPageObjectMethod)
        assert generator.call_count == 0


class TestCoarseAndPreciseCatchDifferentThings:
    """The contrast proof this build's verification section names
    explicitly: the SAME candidate that clears the coarse screen still
    fails the precise one -- the two halves are not redundant."""

    def test_same_candidate_clears_coarse_but_fails_precise(self) -> None:
        asset = _page_object(methods=(JavaMethod(name="open", parameters=(), return_type="void"),))
        catalog = _catalog(asset)
        method_need = _method_need()
        candidate = MatchCandidate(
            asset_id=_LOGIN_ASSET_ID, confidence=0.95, content_hash=_CURRENT_HASH
        )
        matcher = StubSemanticMatcher({method_need.need.text: (candidate,)})

        # COARSE (the reuse engine's own decision): passes.
        coarse_decision = decide_reuse(method_need.need, catalog, matcher)
        assert isinstance(coarse_decision, TrustedReuse)
        assert isinstance(coarse_decision.asset, PageObjectAsset)

        # PRECISE (this build's discharge): fails, on the SAME asset/candidate.
        precise_escalation = verify_specific_method_fit(
            method_need.need,
            coarse_decision.asset,
            coarse_decision.candidate,
            "clickForgotPasswordLink",
        )
        assert precise_escalation is not None
        assert precise_escalation.check == EscalationCheck.METHOD_FIT

    def test_a_different_need_naming_an_existing_method_passes_both(self) -> None:
        """Contrast the other direction: the SAME class, a need that asks
        for the method it ACTUALLY has, passes both halves -- proving the
        precise check does not simply reject every reuse, only the specific
        mismatch case."""
        asset = _page_object(methods=(JavaMethod(name="open", parameters=(), return_type="void"),))
        catalog = _catalog(asset)
        method_need = _method_need(action_text="open the login page", method_name="open")
        candidate = MatchCandidate(
            asset_id=_LOGIN_ASSET_ID, confidence=0.95, content_hash=_CURRENT_HASH
        )
        matcher = StubSemanticMatcher({method_need.need.text: (candidate,)})
        generator = StubPageObjectGenerator({})

        outcome = orchestrate_page_object_method(method_need, catalog, matcher, generator)

        assert isinstance(outcome, BoundPageObjectMethod)


# ---------------------------------------------------------------------------
# Deterministic class-name derivation
# ---------------------------------------------------------------------------


class TestDerivePageObjectClassName:
    def test_strips_a_leading_verb_and_stopwords(self) -> None:
        assert derive_page_object_class_name("click the forgot password link") == (
            "ForgotPasswordLinkPage"
        )

    def test_appends_page_suffix_when_absent(self) -> None:
        assert derive_page_object_class_name("the checkout page") == "CheckoutPage"

    def test_does_not_double_the_page_suffix(self) -> None:
        assert derive_page_object_class_name("open smoke page").endswith("Page")
        assert not derive_page_object_class_name("open smoke page").endswith("PagePage")

    def test_deterministic_across_calls(self) -> None:
        first = derive_page_object_class_name("click the forgot password link")
        second = derive_page_object_class_name("click the forgot password link")
        assert first == second


# ---------------------------------------------------------------------------
# Batch orchestration, determinism, and no live LLM call anywhere here
# ---------------------------------------------------------------------------


class TestBatchOrchestration:
    def test_generate_page_object_methods_processes_each_need_independently_in_order(
        self,
    ) -> None:
        asset = _page_object(
            methods=(JavaMethod(name="clickForgotPasswordLink", parameters=(), return_type="void"),)
        )
        bind_need = _method_need()
        generate_need = _method_need(action_text="open the checkout page", method_name="open")
        escalate_need = _method_need(
            action_text="an ambiguous page action", method_name="doSomethingAmbiguous"
        )
        catalog = _catalog(asset)
        bind_candidate = MatchCandidate(
            asset_id=_LOGIN_ASSET_ID, confidence=0.95, content_hash=_CURRENT_HASH
        )
        # 0.72 -- inside the escalate band, not below the NO_MATCH/generate
        # floor.
        escalate_candidate = MatchCandidate(
            asset_id=_LOGIN_ASSET_ID, confidence=0.72, content_hash=_CURRENT_HASH
        )
        matcher = StubSemanticMatcher(
            {
                bind_need.need.text: (bind_candidate,),
                generate_need.need.text: (),
                escalate_need.need.text: (escalate_candidate,),
            }
        )
        generator = StubPageObjectGenerator(
            {generate_need.need.text: "package com.automation.pages;\n"}
        )

        outcomes = generate_page_object_methods(
            [bind_need, generate_need, escalate_need], catalog, matcher, generator
        )

        assert len(outcomes) == 3
        assert isinstance(outcomes[0], BoundPageObjectMethod)
        assert isinstance(outcomes[1], GeneratedPageObject)
        assert isinstance(outcomes[2], EscalatedPageObjectMethodNeed)
        assert generator.call_count == 1  # only the NO_MATCH need generated


class TestDeterminism:
    def test_same_inputs_yield_the_same_outcome(self) -> None:
        method_need = _method_need()
        catalog = _catalog()
        matcher = StubSemanticMatcher({method_need.need.text: ()})
        canned = "package com.automation.pages;\n"

        first = orchestrate_page_object_method(
            method_need, catalog, matcher, StubPageObjectGenerator({method_need.need.text: canned})
        )
        second = orchestrate_page_object_method(
            method_need, catalog, matcher, StubPageObjectGenerator({method_need.need.text: canned})
        )

        assert first == second


class TestNoLiveLlmInvolvementInOrchestration:
    def test_orchestrator_module_never_imports_llm_factory_or_an_embedding_provider(
        self,
    ) -> None:
        for module_name in ("page_object_orchestrator.py", "method_fit.py"):
            source = Path(f"automation_engineering/generation/{module_name}").read_text(
                encoding="utf-8"
            )
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        assert "llm_factory" not in alias.name
                        assert "embeddings" not in alias.name
                elif isinstance(node, ast.ImportFrom) and node.module:
                    assert "llm_factory" not in node.module
                    assert "embeddings" not in node.module
