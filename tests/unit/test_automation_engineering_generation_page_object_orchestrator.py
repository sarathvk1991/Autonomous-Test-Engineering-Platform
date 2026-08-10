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
    orchestrate_page_object_class,
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
            '    private final By link = By.id("forgot-password");\n\n'
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
            outcome.target_package == DEFAULT_PAGE_OBJECT_TARGET_PACKAGE == "com.automation.pages"
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


class TestDerivedReturnTypeReachesGeneration:
    """Defect-4 fix: `PageObjectMethodNeed.return_type` (caller-supplied,
    e.g. by `page_object_reference_derivation`) reaches
    `PageObjectGenerationContext.return_type` -- the exact same passthrough
    `method_name` already gets (defect-1's own fix)."""

    def test_orchestrate_page_object_method_passes_return_type_through(self) -> None:
        method_need = PageObjectMethodNeed(
            need=GherkinStepNeed(text="the page is displayed", step_type="PageAction"),
            method_name="isDisplayed",
            return_type="boolean",
        )
        catalog = _catalog()
        matcher = StubSemanticMatcher({method_need.need.text: ()})
        generator = StubPageObjectGenerator(
            {method_need.need.text: "package com.automation.pages;\n"}
        )

        orchestrate_page_object_method(method_need, catalog, matcher, generator)

        assert generator.received_contexts[0].return_type == "boolean"

    def test_defaults_to_none_when_the_need_carries_no_derived_return_type(self) -> None:
        method_need = _method_need()  # return_type defaults to None
        catalog = _catalog()
        matcher = StubSemanticMatcher({method_need.need.text: ()})
        generator = StubPageObjectGenerator(
            {method_need.need.text: "package com.automation.pages;\n"}
        )

        orchestrate_page_object_method(method_need, catalog, matcher, generator)

        assert generator.received_contexts[0].return_type is None

    def test_orchestrate_page_object_class_passes_the_primarys_return_type_through(self) -> None:
        primary = PageObjectMethodNeed(
            need=GherkinStepNeed(text="the page is displayed", step_type="PageAction"),
            method_name="isDisplayed",
            return_type="boolean",
        )
        sibling = PageObjectMethodNeed(
            need=GherkinStepNeed(text="click continue", step_type="PageAction"),
            method_name="clickContinue",
            return_type="void",
        )
        catalog = _catalog()
        matcher = StubSemanticMatcher({primary.need.text: (), sibling.need.text: ()})
        generator = StubPageObjectGenerator({primary.need.text: "package com.automation.pages;\n"})

        orchestrate_page_object_class([primary, sibling], catalog, matcher, generator)

        received = generator.received_contexts[0]
        assert received.return_type == "boolean"
        assert [n.return_type for n in received.additional_method_needs] == ["void"]


class TestDerivedParametersReachGeneration:
    """The captures-arity fix: `PageObjectMethodNeed.parameters`
    (caller-supplied, e.g. the call-site-derived arity from
    `page_object_reference_derivation`) reaches
    `PageObjectGenerationContext.parameters` -- the exact same passthrough
    `method_name`/`return_type` already get."""

    def test_orchestrate_page_object_method_passes_parameters_through(self) -> None:
        method_need = PageObjectMethodNeed(
            need=GherkinStepNeed(text="the cart count should display {string}", step_type="Then"),
            method_name="getCartCount",
            parameters=(),  # the call-site's own zero-arity, NOT the step's one capture
        )
        catalog = _catalog()
        matcher = StubSemanticMatcher({method_need.need.text: ()})
        generator = StubPageObjectGenerator(
            {method_need.need.text: "package com.automation.pages;\n"}
        )

        orchestrate_page_object_method(method_need, catalog, matcher, generator)

        assert generator.received_contexts[0].parameters == ()

    def test_defaults_to_none_when_the_need_carries_no_derived_parameters(self) -> None:
        method_need = _method_need()  # parameters defaults to None
        catalog = _catalog()
        matcher = StubSemanticMatcher({method_need.need.text: ()})
        generator = StubPageObjectGenerator(
            {method_need.need.text: "package com.automation.pages;\n"}
        )

        orchestrate_page_object_method(method_need, catalog, matcher, generator)

        assert generator.received_contexts[0].parameters is None

    def test_orchestrate_page_object_class_passes_the_primarys_parameters_through(self) -> None:
        primary = PageObjectMethodNeed(
            need=GherkinStepNeed(text="the cart count should display {string}", step_type="Then"),
            method_name="getCartCount",
            parameters=(),
        )
        sibling = PageObjectMethodNeed(
            need=GherkinStepNeed(text="enter the username {string}", step_type="Given"),
            method_name="enterUsername",
            parameters=(JavaParameter(name="username", java_type="String"),),
        )
        catalog = _catalog()
        matcher = StubSemanticMatcher({primary.need.text: (), sibling.need.text: ()})
        generator = StubPageObjectGenerator({primary.need.text: "package com.automation.pages;\n"})

        orchestrate_page_object_class([primary, sibling], catalog, matcher, generator)

        received = generator.received_contexts[0]
        assert received.parameters == ()
        assert [n.parameters for n in received.additional_method_needs] == [
            (JavaParameter(name="username", java_type="String"),)
        ]


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


class TestPreciseMethodFitUsesCallSiteArityOnTheBindPath:
    """The BIND-side mirror of the captures-arity fix (`TestDerivedParametersReachGeneration`
    above is its GENERATE-side sibling): latent #2 (`docs/architecture/architecture-baseline-v2.md`
    item 36). `verify_specific_method_fit` used to check a TRUSTED_REUSE candidate's
    fit against `need.captures` unconditionally -- the outer step's own capture
    count, which can diverge from what the step-def call site actually passes
    (the SAME live-measured counterexample `PageObjectMethodNeed.parameters`'s own
    docstring records: a captured value routed into `Assertions.assertEquals(...)`
    rather than passed to the page-object call, so the call site takes ZERO
    arguments even though the step's own text captures one). These proofs show
    the bind decision now follows `method_need.parameters` (the call-site arity)
    whenever it is supplied -- the same field the generate path already reads --
    and falls back to `need.captures` exactly as before when it is not."""

    def test_divergence_a_call_site_arity_zero_candidate_binds_despite_one_need_capture(
        self,
    ) -> None:
        """The exact scenario the fifth defect was: the outer step captures
        one value, but the call site the step-def actually uses passes ZERO
        arguments (the captured value went into an assertion instead). A
        zero-arg candidate method is the RIGHT bind for what the call site
        needs -- the OLD `need.captures`-only check would have wrongly
        escalated this (1 required capture vs. a 0-arg method).

        The class also carries a decoy method whose shape fits
        `need.captures` (1 string arg), so the COARSE screen
        (`automation_engineering.reuse.engine.decide_reuse`, untouched by
        this fix and unaware of call-site arity by design -- ADR-0044 D4's
        own "coarse" framing) genuinely returns `TrustedReuse` here, the
        same way ADR-0044 D4's own clarification-note example (a `LoginPage`
        with `open()`, reused for `clickForgotPasswordLink()`) reaches the
        PRECISE check at all -- without it, the coarse screen alone would
        reject this candidate before the precise check the bind-path fix
        touches is ever consulted, and this test would not be exercising
        the fix."""
        asset = _page_object(
            methods=(
                JavaMethod(
                    name="someOtherCoarsePassingMethod",
                    parameters=(JavaParameter(name="value", java_type="String"),),
                    return_type="void",
                ),
                JavaMethod(name="getCartCount", parameters=(), return_type="int"),
            )
        )
        catalog = _catalog(asset)
        method_need = PageObjectMethodNeed(
            need=GherkinStepNeed(
                text="the cart count should display {string}",
                step_type="Then",
                captures=(
                    StepCapture(index=0, style="cucumber_expression", expression_type="string"),
                ),
            ),
            method_name="getCartCount",
            parameters=(),  # the call site's own zero-arity -- diverges from need.captures
        )
        candidate = MatchCandidate(
            asset_id=_LOGIN_ASSET_ID, confidence=0.95, content_hash=_CURRENT_HASH
        )
        matcher = StubSemanticMatcher({method_need.need.text: (candidate,)})
        generator = StubPageObjectGenerator({})

        outcome = orchestrate_page_object_method(method_need, catalog, matcher, generator)

        assert isinstance(outcome, BoundPageObjectMethod)
        assert generator.call_count == 0

    def test_divergence_b_a_candidate_matching_only_the_need_captures_now_escalates(
        self,
    ) -> None:
        """The OTHER direction of the same divergence: a candidate whose
        arity matches `need.captures` (1) but NOT the call site's real
        arity (0) is now correctly REJECTED -- binding it would produce a
        call passing 0 arguments to a 1-parameter method, which does not
        compile. The OLD `need.captures`-only check would have wrongly
        bound this."""
        asset = _page_object(
            methods=(
                JavaMethod(
                    name="getCartCount",
                    parameters=(JavaParameter(name="expected", java_type="String"),),
                    return_type="int",
                ),
            )
        )
        catalog = _catalog(asset)
        method_need = PageObjectMethodNeed(
            need=GherkinStepNeed(
                text="the cart count should display {string}",
                step_type="Then",
                captures=(
                    StepCapture(index=0, style="cucumber_expression", expression_type="string"),
                ),
            ),
            method_name="getCartCount",
            parameters=(),  # the call site's own zero-arity
        )
        candidate = MatchCandidate(
            asset_id=_LOGIN_ASSET_ID, confidence=0.95, content_hash=_CURRENT_HASH
        )
        matcher = StubSemanticMatcher({method_need.need.text: (candidate,)})
        generator = StubPageObjectGenerator({})

        outcome = orchestrate_page_object_method(method_need, catalog, matcher, generator)

        assert isinstance(outcome, EscalatedPageObjectMethodNeed)
        assert outcome.escalation.check == EscalationCheck.METHOD_FIT
        assert "call-site argument" in outcome.escalation.detail
        assert generator.call_count == 0

    def test_verify_specific_method_fit_directly_uses_the_parameters_kwarg_not_captures(
        self,
    ) -> None:
        """Unit-level proof of :func:`verify_specific_method_fit` itself:
        passing `parameters=()` escalates a 1-arg candidate even though
        `need.captures` (2) would, on its own, also mismatch -- and passing
        `parameters` matching the candidate's own arity clears it, showing
        the comparison genuinely switched sources, not merely started
        agreeing with `need.captures` by coincidence."""
        asset = _page_object(
            methods=(
                JavaMethod(
                    name="enterUsername",
                    parameters=(JavaParameter(name="username", java_type="String"),),
                    return_type="void",
                ),
            )
        )
        candidate = MatchCandidate(
            asset_id=_LOGIN_ASSET_ID, confidence=0.95, content_hash=_CURRENT_HASH
        )
        need = GherkinStepNeed(
            text="enter credentials {string} and {string}",
            step_type="Given",
            captures=(
                StepCapture(index=0, style="cucumber_expression", expression_type="string"),
                StepCapture(index=1, style="cucumber_expression", expression_type="string"),
            ),
        )

        escalation_zero_arity = verify_specific_method_fit(
            need, asset, candidate, "enterUsername", parameters=()
        )
        assert escalation_zero_arity is not None
        assert "0 call-site argument(s)" in escalation_zero_arity.detail

        escalation_matching_arity = verify_specific_method_fit(
            need,
            asset,
            candidate,
            "enterUsername",
            parameters=(JavaParameter(name="username", java_type="String"),),
        )
        assert escalation_matching_arity is None

    def test_no_regression_when_call_site_arity_and_need_captures_agree(self) -> None:
        """The ordinary, non-divergent case (the common one in practice) --
        `parameters` supplied and equal in count to `need.captures` -- still
        binds cleanly, exactly as the pre-fix `need.captures`-only check
        already did for this shape."""
        asset = _page_object(
            methods=(
                JavaMethod(
                    name="loginAs",
                    parameters=(
                        JavaParameter(name="username", java_type="String"),
                        JavaParameter(name="password", java_type="String"),
                    ),
                    return_type="void",
                ),
            )
        )
        catalog = _catalog(asset)
        method_need = PageObjectMethodNeed(
            need=GherkinStepNeed(
                text="log in as {string} with password {string}",
                step_type="When",
                captures=(
                    StepCapture(index=0, style="cucumber_expression", expression_type="string"),
                    StepCapture(index=1, style="cucumber_expression", expression_type="string"),
                ),
            ),
            method_name="loginAs",
            parameters=(
                JavaParameter(name="username", java_type="String"),
                JavaParameter(name="password", java_type="String"),
            ),
        )
        candidate = MatchCandidate(
            asset_id=_LOGIN_ASSET_ID, confidence=0.95, content_hash=_CURRENT_HASH
        )
        matcher = StubSemanticMatcher({method_need.need.text: (candidate,)})
        generator = StubPageObjectGenerator({})

        outcome = orchestrate_page_object_method(method_need, catalog, matcher, generator)

        assert isinstance(outcome, BoundPageObjectMethod)

    def test_parity_orchestrate_page_object_class_bind_branch_also_uses_call_site_arity(
        self,
    ) -> None:
        """The SECOND bind call site (`orchestrate_page_object_class`, the
        multi-method-per-class seam) gets the identical fix -- proven
        independently since it is a separate call to
        `verify_specific_method_fit`, not a shared code path with
        `orchestrate_page_object_method`. Carries the same coarse-passing
        decoy method the divergence proofs above need, for the same
        reason."""
        asset = _page_object(
            methods=(
                JavaMethod(
                    name="someOtherCoarsePassingMethod",
                    parameters=(JavaParameter(name="value", java_type="String"),),
                    return_type="void",
                ),
                JavaMethod(name="getCartCount", parameters=(), return_type="int"),
            )
        )
        catalog = _catalog(asset)
        bound_need = PageObjectMethodNeed(
            need=GherkinStepNeed(
                text="the cart count should display {string}",
                step_type="Then",
                captures=(
                    StepCapture(index=0, style="cucumber_expression", expression_type="string"),
                ),
            ),
            method_name="getCartCount",
            parameters=(),
        )
        fresh_need = PageObjectMethodNeed(
            need=GherkinStepNeed(text="open the cart page", step_type="Given"),
            method_name="open",
        )
        candidate = MatchCandidate(
            asset_id=_LOGIN_ASSET_ID, confidence=0.95, content_hash=_CURRENT_HASH
        )
        matcher = StubSemanticMatcher(
            {bound_need.need.text: (candidate,), fresh_need.need.text: ()}
        )
        generator = StubPageObjectGenerator(
            {fresh_need.need.text: "package com.automation.pages;\n"}
        )

        outcomes = orchestrate_page_object_class(
            [bound_need, fresh_need], catalog, matcher, generator
        )

        bound_outcomes = [o for o in outcomes if isinstance(o, BoundPageObjectMethod)]
        assert len(bound_outcomes) == 1
        assert bound_outcomes[0].asset is asset


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


class TestOrchestratePageObjectClass:
    """`orchestrate_page_object_class` -- the multi-method-per-class seam
    extension this build adds. `orchestrate_page_object_method`/
    `generate_page_object_methods` above are untouched by this class'
    existence; these tests prove the NEW function specifically."""

    def test_three_no_match_methods_co_generate_into_one_class(self) -> None:
        catalog = _catalog()  # empty -- all three go NO_MATCH
        needs = (
            _method_need(action_text="enter the username", method_name="enterUsername"),
            _method_need(action_text="enter the password", method_name="enterPassword"),
            _method_need(action_text="click the login button", method_name="clickLogin"),
        )
        matcher = StubSemanticMatcher({n.need.text: () for n in needs})
        canned = (
            "package com.automation.pages;\n\n"
            "public class LoginPage extends BasePage {\n"
            "    public void enterUsername(String username) {}\n"
            "    public void enterPassword(String password) {}\n"
            "    public void clickLogin() {}\n"
            "}\n"
        )
        generator = StubPageObjectGenerator({needs[0].need.text: canned})

        outcomes = orchestrate_page_object_class(needs, catalog, matcher, generator)

        assert generator.call_count == 1
        assert len(outcomes) == 1
        generated = outcomes[0]
        assert isinstance(generated, GeneratedPageObject)
        assert generated.method_need == needs[0]
        assert generated.additional_method_needs == (needs[1], needs[2])
        # Compile-consistency: every requested method is present in the
        # ONE generated class -- none dropped.
        for method_name in ("enterUsername", "enterPassword", "clickLogin"):
            assert method_name in generated.java_source

        received = generator.received_contexts[0]
        assert received.need == needs[0].need
        assert received.additional_method_needs == (needs[1], needs[2])

    def test_mixed_bind_and_generate_within_one_class(self) -> None:
        """One method on the class already exists in the catalog (binds);
        the other two do not (co-generate together) -- the class ends up
        with the bound method plus the freshly generated ones, all three
        references satisfied, only one seam call for the two NO_MATCH
        methods."""
        existing = _page_object(
            methods=(JavaMethod(name="open", parameters=(), return_type="void"),)
        )
        catalog = _catalog(existing)
        bind_need = _method_need(action_text="open the login page", method_name="open")
        generate_need_a = _method_need(
            action_text="enter the username", method_name="enterUsername"
        )
        generate_need_b = _method_need(
            action_text="enter the password", method_name="enterPassword"
        )
        bind_candidate = MatchCandidate(
            asset_id=_LOGIN_ASSET_ID, confidence=0.95, content_hash=_CURRENT_HASH
        )
        matcher = StubSemanticMatcher(
            {
                bind_need.need.text: (bind_candidate,),
                generate_need_a.need.text: (),
                generate_need_b.need.text: (),
            }
        )
        canned = (
            "package com.automation.pages;\n\n"
            "public class LoginPage extends BasePage {\n"
            "    public void enterUsername(String username) {}\n"
            "    public void enterPassword(String password) {}\n"
            "}\n"
        )
        generator = StubPageObjectGenerator({generate_need_a.need.text: canned})

        outcomes = orchestrate_page_object_class(
            (bind_need, generate_need_a, generate_need_b), catalog, matcher, generator
        )

        assert generator.call_count == 1  # ONE call for the two NO_MATCH methods together
        assert len(outcomes) == 2
        assert isinstance(outcomes[0], BoundPageObjectMethod)
        assert outcomes[0].method_need == bind_need
        assert isinstance(outcomes[1], GeneratedPageObject)
        assert outcomes[1].method_need == generate_need_a
        assert outcomes[1].additional_method_needs == (generate_need_b,)
        # Every one of the three original method-needs is satisfied by
        # exactly one outcome, directly or via `additional_method_needs`.
        assert "open" in [m.name for m in existing.methods]
        for method_name in ("enterUsername", "enterPassword"):
            assert method_name in outcomes[1].java_source

    def test_single_method_need_behaves_like_orchestrate_page_object_method(self) -> None:
        catalog = _catalog()
        need = _method_need(action_text="open the checkout page", method_name="open")
        matcher = StubSemanticMatcher({need.need.text: ()})
        canned = "package com.automation.pages;\npublic class CheckoutPage {}\n"

        single = orchestrate_page_object_method(
            need, catalog, matcher, StubPageObjectGenerator({need.need.text: canned})
        )
        batched = orchestrate_page_object_class(
            (need,), catalog, matcher, StubPageObjectGenerator({need.need.text: canned})
        )

        assert len(batched) == 1
        assert batched[0] == single
        assert isinstance(batched[0], GeneratedPageObject)
        assert batched[0].additional_method_needs == ()

    def test_empty_method_needs_returns_empty(self) -> None:
        catalog = _catalog()
        matcher = StubSemanticMatcher({})
        generator = StubPageObjectGenerator({})

        assert orchestrate_page_object_class((), catalog, matcher, generator) == ()
        assert generator.call_count == 0

    def test_determinism(self) -> None:
        catalog = _catalog()
        needs = (
            _method_need(action_text="enter the username", method_name="enterUsername"),
            _method_need(action_text="enter the password", method_name="enterPassword"),
        )
        matcher = StubSemanticMatcher({n.need.text: () for n in needs})
        canned = "package com.automation.pages;\npublic class LoginPage {}\n"

        first = orchestrate_page_object_class(
            needs, catalog, matcher, StubPageObjectGenerator({needs[0].need.text: canned})
        )
        second = orchestrate_page_object_class(
            needs, catalog, matcher, StubPageObjectGenerator({needs[0].need.text: canned})
        )

        assert first == second

    def test_disagreeing_class_name_overrides_raise_rather_than_silently_pick_one(self) -> None:
        catalog = _catalog()
        need_a = PageObjectMethodNeed(
            need=GherkinStepNeed(text="enter the username", step_type="PageAction", captures=()),
            method_name="enterUsername",
            class_name_override="LoginPage",
        )
        need_b = PageObjectMethodNeed(
            need=GherkinStepNeed(text="enter the password", step_type="PageAction", captures=()),
            method_name="enterPassword",
            class_name_override="AccountPage",
        )
        matcher = StubSemanticMatcher({need_a.need.text: (), need_b.need.text: ()})
        generator = StubPageObjectGenerator({})

        with pytest.raises(ValueError, match="disagree on class_name_override"):
            orchestrate_page_object_class((need_a, need_b), catalog, matcher, generator)

        assert generator.call_count == 0


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
