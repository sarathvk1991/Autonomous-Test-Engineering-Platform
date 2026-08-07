"""Page-object request derivation (`automation_engineering.generation.
page_object_reference_derivation`) -- proves, deterministically and
without any live call:

* The derivation: parsing a GENERATED step-definition's own Java source
  extracts exactly the page-object class(es)/method(s)/signature(s) its
  body actually calls -- never the reuse engine's `GherkinStepNeed
  .captures`, never a raw-Gherkin-text guess (ADR-0044 D4's own
  clarification note: a specific method call "is not knowable until a
  future generator actually writes that call").
* Signature matching: an identifier argument resolves to the step-def
  method's OWN declared parameter type; a literal resolves by its own
  token shape; an unresolvable expression degrades honestly to `"Object"`,
  never crashes.
* The wiring: `generate_step_definition_with_derived_page_objects`
  sequences the ALREADY-BUILT step-def orchestrator and page-object
  orchestrator, unmodified -- generate the step-def first, derive its own
  page-object references, resolve each (bind/generate/escalate).
* `class_name_override` (the one, additive, backward-compatible field
  this build adds to `PageObjectMethodNeed`) makes a FRESH page object use
  the EXACT class name the step-def's body already references, never
  `derive_page_object_class_name`'s own independent guess.
* Escalation: any derived page-object reference that fails to resolve
  safely diverts the WHOLE step, mirroring `.orchestrator`'s own
  discipline.
* Multiple fresh methods on one class (the gap this derivation build
  originally flagged, closed by this build's multi-method seam
  extension): a step-def calling several methods on one brand-new
  page-object class co-generates ONE class with ALL of them, in ONE seam
  call -- `unverified_method_names` is now always empty.
* Determinism, and no live LLM call anywhere.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from automation_engineering.catalog.models import (
    AssetCatalog,
    JavaMethod,
    JavaParameter,
    PageObjectAsset,
    StepCapture,
)
from automation_engineering.generation.models import (
    BoundPageObjectMethod,
    BoundStepDefinition,
    EscalatedStepNeed,
    GeneratedPageObject,
    GeneratedStepDefinition,
)
from automation_engineering.generation.page_object_generator import StubPageObjectGenerator
from automation_engineering.generation.page_object_orchestrator import (
    DEFAULT_PAGE_OBJECT_TARGET_PACKAGE,
    derive_page_object_class_name,
)
from automation_engineering.generation.page_object_reference_derivation import (
    CoGeneratedStepDefinition,
    DerivedPageObjectMethodCall,
    DerivedPageObjectRequest,
    derive_page_object_requests,
    generate_step_definition_with_derived_page_objects,
)
from automation_engineering.generation.step_definition_generator import (
    StubStepDefinitionGenerator,
)
from automation_engineering.reuse.matcher import StubSemanticMatcher
from automation_engineering.reuse.models import GherkinStepNeed, MatchCandidate

pytestmark = pytest.mark.unit

_LOGIN_STEP_JAVA = """package com.automation.steps;

import io.cucumber.java.en.Given;

public class LoginSteps {
    private LoginPage loginPage;

    @Given("I log in as {string} with password {string}")
    public void iLogInAsWithPassword(String username, String password) {
        loginPage.enterUsername(username);
        loginPage.enterPassword(password);
        loginPage.clickLogin();
    }
}
"""

_NEED = GherkinStepNeed(text="I log in as {string} with password {string}", step_type="Given")


def _catalog(*assets: PageObjectAsset) -> AssetCatalog:
    return AssetCatalog(baseline_root="test-suite-baseline", page_objects=tuple(assets))


class TestDerivationParsesRealCallSites:
    def test_login_fixture_produces_loginpage_with_its_three_methods(self) -> None:
        requests = derive_page_object_requests(_LOGIN_STEP_JAVA)

        assert requests == (
            DerivedPageObjectRequest(
                class_name="LoginPage",
                method_calls=(
                    DerivedPageObjectMethodCall(
                        method_name="enterUsername",
                        parameters=(JavaParameter(name="arg0", java_type="String"),),
                    ),
                    DerivedPageObjectMethodCall(
                        method_name="enterPassword",
                        parameters=(JavaParameter(name="arg0", java_type="String"),),
                    ),
                    DerivedPageObjectMethodCall(method_name="clickLogin", parameters=()),
                ),
            ),
        )

    def test_a_step_def_calling_no_page_object_field_returns_empty(self) -> None:
        java = (
            "package com.automation.steps;\n\n"
            "import io.cucumber.java.en.Then;\n"
            "import org.junit.jupiter.api.Assertions;\n\n"
            "public class AssertSteps {\n"
            '    @Then("the result is correct")\n'
            "    public void theResultIsCorrect() {\n"
            "        Assertions.assertTrue(true);\n"
            "    }\n"
            "}\n"
        )

        assert derive_page_object_requests(java) == ()

    def test_two_distinct_page_object_fields_produce_two_requests(self) -> None:
        java = (
            "package com.automation.steps;\n\n"
            "import io.cucumber.java.en.Given;\n\n"
            "public class CheckoutSteps {\n"
            "    private CartPage cartPage;\n"
            "    private LoginPage loginPage;\n\n"
            '    @Given("I check out as a logged in user")\n'
            "    public void iCheckOutAsALoggedInUser() {\n"
            "        loginPage.clickLogin();\n"
            "        cartPage.checkout();\n"
            "    }\n"
            "}\n"
        )

        requests = derive_page_object_requests(java)

        assert {r.class_name for r in requests} == {"CartPage", "LoginPage"}

    def test_a_utility_typed_field_is_never_treated_as_a_page_object(self) -> None:
        """Fields whose declared type does NOT end in "Page" (e.g. a
        utility) are deliberately excluded (module docstring) -- utility-
        request derivation is out of this build's own scope."""
        java = (
            "package com.automation.steps;\n\n"
            "import io.cucumber.java.en.Given;\n\n"
            "public class ConfigSteps {\n"
            "    private LoginPage loginPage;\n"
            "    private ConfigReader configReader;\n\n"
            '    @Given("I use the configured username")\n'
            "    public void iUseTheConfiguredUsername() {\n"
            '        loginPage.enterUsername(configReader.data("username"));\n'
            "    }\n"
            "}\n"
        )

        requests = derive_page_object_requests(java)

        assert {r.class_name for r in requests} == {"LoginPage"}


class TestArgumentTypeResolution:
    def test_identifier_argument_resolves_to_the_step_defs_own_parameter_type(self) -> None:
        requests = derive_page_object_requests(_LOGIN_STEP_JAVA)
        enter_username = next(
            c for c in requests[0].method_calls if c.method_name == "enterUsername"
        )

        assert enter_username.parameters == (JavaParameter(name="arg0", java_type="String"),)

    def test_string_int_and_boolean_literals_resolve_by_their_own_token_shape(self) -> None:
        java = (
            "package com.automation.steps;\n\n"
            "import io.cucumber.java.en.Given;\n\n"
            "public class LiteralSteps {\n"
            "    private LoginPage loginPage;\n\n"
            '    @Given("a literal call")\n'
            "    public void aLiteralCall() {\n"
            '        loginPage.doThing("bob", 42, true);\n'
            "    }\n"
            "}\n"
        )

        requests = derive_page_object_requests(java)

        assert requests[0].method_calls[0].parameters == (
            JavaParameter(name="arg0", java_type="String"),
            JavaParameter(name="arg1", java_type="int"),
            JavaParameter(name="arg2", java_type="boolean"),
        )

    def test_an_unresolvable_argument_degrades_honestly_to_object(self) -> None:
        """A call argument that is neither a step-def parameter nor a
        literal (e.g. a field reference, a nested call) resolves to the
        honest, conservative `"Object"` fallback -- never a crash, never a
        silently wrong guess."""
        java = (
            "package com.automation.steps;\n\n"
            "import io.cucumber.java.en.Given;\n\n"
            "public class NestedSteps {\n"
            "    private LoginPage loginPage;\n"
            "    private ConfigReader configReader;\n\n"
            '    @Given("a nested call")\n'
            "    public void aNestedCall() {\n"
            '        loginPage.doThing(configReader.env("USER"));\n'
            "    }\n"
            "}\n"
        )

        requests = derive_page_object_requests(java)

        assert requests[0].method_calls[0].parameters == (
            JavaParameter(name="arg0", java_type="Object"),
        )

    def test_determinism(self) -> None:
        first = derive_page_object_requests(_LOGIN_STEP_JAVA)
        second = derive_page_object_requests(_LOGIN_STEP_JAVA)

        assert first == second


class TestWiringPassesThroughBoundAndEscalatedUnchanged:
    def test_a_trusted_reuse_step_definition_is_returned_unchanged(self) -> None:
        from automation_engineering.catalog.alignment import correlate
        from automation_engineering.catalog.models import StepDefinitionAsset

        need = GherkinStepNeed(text="I log out", step_type="Given")
        asset = StepDefinitionAsset(
            asset_id="STEP-1",
            class_name="com.automation.steps.LoginSteps",
            method_name="iLogOut",
            step_type="Given",
            pattern=need.text,
            parameters=(),
            return_type="void",
            source_file="com/automation/steps/LoginSteps.java",
            content_hash="hash-1",
            signature_alignment=correlate(need.text, ()),
        )
        catalog = AssetCatalog(baseline_root="test-suite-baseline", step_definitions=(asset,))
        candidate = MatchCandidate(asset_id="STEP-1", confidence=0.95, content_hash="hash-1")
        step_matcher = StubSemanticMatcher({need.text: (candidate,)})
        step_generator = StubStepDefinitionGenerator({})  # never called -- would raise if it were

        outcome = generate_step_definition_with_derived_page_objects(
            need,
            catalog,
            step_matcher,
            step_generator,
            page_object_matcher=StubSemanticMatcher({}),
            page_object_generator=StubPageObjectGenerator({}),
        )

        assert isinstance(outcome, BoundStepDefinition)


class TestWiringNoPageObjectReferenceIsReturnedUnchanged:
    def test_a_step_def_calling_no_page_object_returns_the_plain_outcome(self) -> None:
        need = GherkinStepNeed(text="the result is correct", step_type="Then")
        catalog = _catalog()
        step_matcher = StubSemanticMatcher({need.text: ()})
        java = (
            "package com.automation.steps;\n\n"
            "import io.cucumber.java.en.Then;\n"
            "import org.junit.jupiter.api.Assertions;\n\n"
            "public class AssertSteps {\n"
            '    @Then("the result is correct")\n'
            "    public void theResultIsCorrect() {\n"
            "        Assertions.assertTrue(true);\n"
            "    }\n"
            "}\n"
        )
        step_generator = StubStepDefinitionGenerator({need.text: java})

        outcome = generate_step_definition_with_derived_page_objects(
            need,
            catalog,
            step_matcher,
            step_generator,
            page_object_matcher=StubSemanticMatcher({}),
            page_object_generator=StubPageObjectGenerator({}),
        )

        assert isinstance(outcome, GeneratedStepDefinition)
        assert outcome.java_source == java


class TestWiringBindsAnExistingPageObject:
    """A SINGLE-page-object-call fixture, deliberately -- `need.captures`
    is shared, unchanged, across every derived method-need this wiring
    resolves (module docstring), so it correctly represents ONE reused
    method's own required arity only when the step's body calls exactly
    one page-object method consuming every one of its own captures --
    the SAME shape every pre-existing `PageObjectMethodNeed` fixture in
    this codebase already uses (`test_automation_engineering_generation_
    orchestrator.py`'s own `captures=()` zero-arg example). A step body
    that calls MULTIPLE page-object methods, each consuming a SUBSET of
    the step's own captures, is a genuine, unresolved limitation this
    derivation inherits from `PageObjectMethodNeed`'s existing, unmodified
    precise-fit machinery (`verify_specific_method_fit` compares a reused
    method's own arity against the WHOLE step's aggregate `need.captures`,
    not a per-call subset) -- flagged as a finding, not fixed here (out of
    this build's own scope: derivation + wiring, never the precise-fit
    check's own semantics).
    """

    def test_a_single_derived_call_binds_against_a_real_catalogued_page_object(self) -> None:
        need = GherkinStepNeed(
            text="I enter the username {string}",
            step_type="Given",
            captures=(StepCapture(index=0, style="cucumber_expression", expression_type="string"),),
        )
        java = (
            "package com.automation.steps;\n\n"
            "import io.cucumber.java.en.Given;\n\n"
            "public class LoginSteps {\n"
            "    private LoginPage loginPage;\n\n"
            '    @Given("I enter the username {string}")\n'
            "    public void iEnterTheUsername(String username) {\n"
            "        loginPage.enterUsername(username);\n"
            "    }\n"
            "}\n"
        )
        login_page = PageObjectAsset(
            asset_id="PAGE-login01",
            class_name="com.automation.pages.LoginPage",
            extends="BasePage",
            fields=(),
            locators=(),
            methods=(
                JavaMethod(
                    name="enterUsername",
                    parameters=(JavaParameter(name="username", java_type="String"),),
                    return_type="void",
                ),
            ),
            source_file="com/automation/pages/LoginPage.java",
            content_hash="hash1",
        )
        catalog = _catalog(login_page)
        step_matcher = StubSemanticMatcher({need.text: ()})
        step_generator = StubStepDefinitionGenerator({need.text: java})
        po_candidate = MatchCandidate(asset_id="PAGE-login01", confidence=0.9, content_hash="hash1")
        page_object_matcher = StubSemanticMatcher({need.text: (po_candidate,)})
        page_object_generator = StubPageObjectGenerator(
            {}
        )  # never called -- would raise if it were

        outcome = generate_step_definition_with_derived_page_objects(
            need,
            catalog,
            step_matcher,
            step_generator,
            page_object_matcher=page_object_matcher,
            page_object_generator=page_object_generator,
        )

        assert isinstance(outcome, CoGeneratedStepDefinition)
        assert len(outcome.page_object_outcomes) == 1
        assert isinstance(outcome.page_object_outcomes[0], BoundPageObjectMethod)
        assert outcome.unverified_method_names == ()
        assert page_object_generator.call_count == 0


class TestWiringGeneratesAFreshPageObjectWithTheDerivedClassName:
    def test_class_name_override_wins_over_the_independently_derived_guess(self) -> None:
        catalog = _catalog()  # empty -- nothing to reuse
        step_matcher = StubSemanticMatcher({_NEED.text: ()})
        # Only the FIRST method (`enterUsername`) is exercised here -- a
        # single-page-object-field, single-method fixture, so the "known
        # gap" (multiple fresh methods on one class) is proven separately.
        single_method_java = (
            "package com.automation.steps;\n\n"
            "import io.cucumber.java.en.Given;\n\n"
            "public class LoginSteps {\n"
            "    private LoginPage loginPage;\n\n"
            '    @Given("I log in as {string} with password {string}")\n'
            "    public void iLogInAsWithPassword(String username, String password) {\n"
            "        loginPage.enterUsername(username);\n"
            "    }\n"
            "}\n"
        )
        step_generator = StubStepDefinitionGenerator({_NEED.text: single_method_java})
        page_object_matcher = StubSemanticMatcher({_NEED.text: ()})
        canned_page_object = "package com.automation.pages;\npublic class LoginPage {}\n"
        page_object_generator = StubPageObjectGenerator({_NEED.text: canned_page_object})

        # The independently-derived guess (from the step's own text alone)
        # would NOT be "LoginPage" -- proving the override, not a
        # coincidence, is what makes this pass.
        assert derive_page_object_class_name(_NEED.text) != "LoginPage"

        outcome = generate_step_definition_with_derived_page_objects(
            _NEED,
            catalog,
            step_matcher,
            step_generator,
            page_object_matcher=page_object_matcher,
            page_object_generator=page_object_generator,
        )

        assert isinstance(outcome, CoGeneratedStepDefinition)
        assert len(outcome.page_object_outcomes) == 1
        generated = outcome.page_object_outcomes[0]
        assert isinstance(generated, GeneratedPageObject)
        assert generated.class_name == "LoginPage"
        received = page_object_generator.received_contexts[0]
        assert received.class_name == "LoginPage"
        assert received.target_package == DEFAULT_PAGE_OBJECT_TARGET_PACKAGE


class TestWiringEscalatesTheWholeStepOnAnUnverifiedBinding:
    def test_a_trusted_reuse_missing_the_specific_method_escalates_the_whole_step(self) -> None:
        login_page = PageObjectAsset(
            asset_id="PAGE-login01",
            class_name="com.automation.pages.LoginPage",
            extends="BasePage",
            fields=(),
            locators=(),
            methods=(JavaMethod(name="open", parameters=(), return_type="void"),),
            source_file="com/automation/pages/LoginPage.java",
            content_hash="hash1",
        )
        catalog = _catalog(login_page)
        step_matcher = StubSemanticMatcher({_NEED.text: ()})
        step_generator = StubStepDefinitionGenerator({_NEED.text: _LOGIN_STEP_JAVA})
        po_candidate = MatchCandidate(asset_id="PAGE-login01", confidence=0.9, content_hash="hash1")
        page_object_matcher = StubSemanticMatcher({_NEED.text: (po_candidate,)})
        page_object_generator = StubPageObjectGenerator(
            {}
        )  # never called -- would raise if it were

        outcome = generate_step_definition_with_derived_page_objects(
            _NEED,
            catalog,
            step_matcher,
            step_generator,
            page_object_matcher=page_object_matcher,
            page_object_generator=page_object_generator,
        )

        assert isinstance(outcome, EscalatedStepNeed)
        assert outcome.need == _NEED
        assert page_object_generator.call_count == 0


class TestMultipleFreshMethodsOnOneClassAreCoGenerated:
    """The gap `TestKnownGapMultipleFreshMethodsOnOneClass` used to record
    (a second-or-later fresh method landing in ``unverified_method_names``,
    never generated) is now closed -- proves the multi-method seam
    extension (`page_object_generator.PageObjectGenerationContext
    .additional_method_needs`, `page_object_orchestrator
    .orchestrate_page_object_class`) end to end through this module's own
    wiring."""

    def test_all_three_methods_co_generate_into_one_class_unverified_empty(self) -> None:
        catalog = _catalog()  # empty -- all three methods go NO_MATCH
        step_matcher = StubSemanticMatcher({_NEED.text: ()})
        step_generator = StubStepDefinitionGenerator({_NEED.text: _LOGIN_STEP_JAVA})
        page_object_matcher = StubSemanticMatcher({_NEED.text: ()})
        # A canned class carrying ALL THREE requested methods -- proves the
        # class the stub returns (and, by construction, whatever a live
        # generator would be asked to return) is expected to satisfy every
        # one of them, not just the first.
        canned_page_object = (
            "package com.automation.pages;\n\n"
            "public class LoginPage extends BasePage {\n"
            "    public void enterUsername(String username) { /* ... */ }\n"
            "    public void enterPassword(String password) { /* ... */ }\n"
            "    public void clickLogin() { /* ... */ }\n"
            "}\n"
        )
        page_object_generator = StubPageObjectGenerator({_NEED.text: canned_page_object})

        outcome = generate_step_definition_with_derived_page_objects(
            _NEED,
            catalog,
            step_matcher,
            step_generator,
            page_object_matcher=page_object_matcher,
            page_object_generator=page_object_generator,
        )

        assert isinstance(outcome, CoGeneratedStepDefinition)
        # THREE derived calls (enterUsername, enterPassword, clickLogin),
        # all on the SAME "LoginPage" -- ONE seam call, ONE outcome, ALL
        # THREE methods carried through -- the gap the derivation build
        # flagged, now closed.
        assert page_object_generator.call_count == 1
        assert len(outcome.page_object_outcomes) == 1
        assert outcome.unverified_method_names == ()

        generated = outcome.page_object_outcomes[0]
        assert isinstance(generated, GeneratedPageObject)
        assert generated.class_name == "LoginPage"
        assert generated.method_need.method_name == "enterUsername"
        assert [n.method_name for n in generated.additional_method_needs] == [
            "enterPassword",
            "clickLogin",
        ]

        # Compile-consistency: every method the step-def's own body calls
        # is actually present in the generated class -- nothing dropped.
        for method_name in ("enterUsername", "enterPassword", "clickLogin"):
            assert method_name in generated.java_source

        received = page_object_generator.received_contexts[0]
        assert received.class_name == "LoginPage"
        assert [n.method_name for n in received.additional_method_needs] == [
            "enterPassword",
            "clickLogin",
        ]


class TestNoLiveLLMCall:
    def test_the_wiring_function_depends_only_on_protocol_seams(self) -> None:
        """Structural proof: this module never imports `llm_factory` or a
        concrete live generator -- the same guard every orchestration
        module in this package already carries."""
        source = Path(
            "automation_engineering/generation/page_object_reference_derivation.py"
        ).read_text(encoding="utf-8")

        assert "llm_factory" not in source
        assert "Live" not in source
