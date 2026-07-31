"""Reuse-first step-definition orchestration (`automation_engineering.
generation.orchestrator`) -- proves, deterministically and without any live
call:

* NO_MATCH -> GENERATE: the stub generator IS called, a step def lands in
  `com.automation.steps`, matching conventions.
* TRUSTED_REUSE -> BIND, never regenerate: the stub generator is proven NOT
  called via its own spy (`call_count == 0`).
* ESCALATION -> neither generated nor bound, surfaced for review.
* customqa:* constraints are actually injected into what the generation seam
  receives (so a live call would be constrained).
* The precise method-fit obligation (ADR-0044 D4's clarification note),
  NOW DISCHARGED: when a `page_object_request` is supplied, a step whose
  required page-object call resolves to a TRUSTED_REUSE with the SPECIFIC
  method present binds and generates against it; one whose specific method
  is ABSENT escalates the whole step, never silently generating against an
  unverified call. Omitted, behavior is unchanged: `page_object_interface`
  stays `None`. See `test_automation_engineering_generation_page_object_orchestrator.py`
  for the method-fit discharge's own dedicated proofs (insufficient
  escalates, sufficient passes, the coarse/precise contrast).
* Determinism, and no live LLM call anywhere in the orchestration path.

Builds on the real catalog shapes (`automation_engineering.catalog.models`)
and the real capture/correlation machinery
(`automation_engineering.catalog.alignment.correlate`), the same discipline
`tests/unit/test_automation_engineering_reuse_engine.py` already established,
so this orchestration is proven against the SAME reuse-decision data the
engine actually produces, not a hand-rolled stand-in.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from automation_engineering.catalog.alignment import correlate
from automation_engineering.catalog.models import AssetCatalog, JavaParameter, StepDefinitionAsset
from automation_engineering.generation.models import (
    BoundStepDefinition,
    EscalatedStepNeed,
    GeneratedStepDefinition,
)
from automation_engineering.generation.orchestrator import (
    DEFAULT_CUSTOMQA_STEP_DEFINITION_CONSTRAINTS,
    DEFAULT_TARGET_PACKAGE,
    generate_step_definitions,
    orchestrate_step_definition,
)
from automation_engineering.generation.step_definition_generator import (
    StubStepDefinitionGenerator,
)
from automation_engineering.reuse.matcher import StubSemanticMatcher
from automation_engineering.reuse.models import EscalationCheck, GherkinStepNeed, MatchCandidate

pytestmark = pytest.mark.unit

_LOGIN_PATTERN = "I log in as {string} with password {string}"
_LOGIN_ASSET_ID = "STEP-loginasfixture01"
_CURRENT_HASH = "current-hash-abc123"
_STALE_HASH = "stale-hash-000000"


def _login_step_definition(content_hash: str = _CURRENT_HASH) -> StepDefinitionAsset:
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


def _need(text: str = 'I log in as "alice" with password "secret"') -> GherkinStepNeed:
    return GherkinStepNeed(text=text, step_type="When", captures=())


# ---------------------------------------------------------------------------
# NO_MATCH -> generate
# ---------------------------------------------------------------------------


class TestNoMatchGenerates:
    def test_generates_a_step_definition_in_com_automation_steps(self) -> None:
        need = _need("I log out")
        catalog = _catalog()  # empty -- nothing to reuse
        matcher = StubSemanticMatcher({need.text: ()})
        canned_java = (
            "package com.automation.steps;\n\n"
            "import io.cucumber.java.en.When;\n\n"
            "public class LogoutSteps {\n"
            "    @When(\"I log out\")\n"
            "    public void iLogOut() {}\n"
            "}\n"
        )
        generator = StubStepDefinitionGenerator({need.text: canned_java})

        outcome = orchestrate_step_definition(need, catalog, matcher, generator)

        assert isinstance(outcome, GeneratedStepDefinition)
        assert outcome.need == need
        assert outcome.java_source == canned_java
        assert outcome.target_package == DEFAULT_TARGET_PACKAGE == "com.automation.steps"
        assert generator.call_count == 1

    def test_generator_is_called_exactly_once_per_no_match_need(self) -> None:
        need = _need("I log out")
        catalog = _catalog()
        matcher = StubSemanticMatcher({need.text: ()})
        generator = StubStepDefinitionGenerator({need.text: "package com.automation.steps;\n"})

        orchestrate_step_definition(need, catalog, matcher, generator)

        assert generator.call_count == 1


# ---------------------------------------------------------------------------
# TRUSTED_REUSE -> bind, never regenerate
# ---------------------------------------------------------------------------


class TestTrustedReuseBindsWithoutRegenerating:
    def test_binds_to_the_existing_asset(self) -> None:
        asset = _login_step_definition()
        catalog = _catalog(asset)
        need = GherkinStepNeed(
            text='I log in as "alice" with password "secret"',
            step_type="When",
            captures=(),
        )
        # Reuse the asset's OWN recorded captures as the need's required
        # shape, mirroring test_automation_engineering_reuse_engine.py's own
        # `_fitting_need` construction -- a need whose captures fit the
        # candidate's own signature alignment.
        need = GherkinStepNeed(
            text=need.text,
            step_type=need.step_type,
            captures=asset.signature_alignment.captures,
        )
        candidate = MatchCandidate(
            asset_id=_LOGIN_ASSET_ID, confidence=0.95, content_hash=_CURRENT_HASH
        )
        matcher = StubSemanticMatcher({need.text: (candidate,)})
        generator = StubStepDefinitionGenerator({})  # no canned answers -- must never be called

        outcome = orchestrate_step_definition(need, catalog, matcher, generator)

        assert isinstance(outcome, BoundStepDefinition)
        assert outcome.need == need
        assert outcome.asset is asset

    def test_generator_is_never_called_for_a_trusted_reuse(self) -> None:
        """The spy proof this build's verification section requires: zero
        generation calls when reuse is trusted -- not merely that the
        outcome is a bind, but that the seam was never touched at all."""
        asset = _login_step_definition()
        catalog = _catalog(asset)
        need = GherkinStepNeed(
            text='I log in as "alice" with password "secret"',
            step_type="When",
            captures=asset.signature_alignment.captures,
        )
        candidate = MatchCandidate(
            asset_id=_LOGIN_ASSET_ID, confidence=0.95, content_hash=_CURRENT_HASH
        )
        matcher = StubSemanticMatcher({need.text: (candidate,)})
        generator = StubStepDefinitionGenerator({})

        orchestrate_step_definition(need, catalog, matcher, generator)

        assert generator.call_count == 0
        assert generator.received_contexts == ()


# ---------------------------------------------------------------------------
# ESCALATION -> neither generated nor bound
# ---------------------------------------------------------------------------


class TestEscalationSurfacesForReview:
    def test_low_confidence_escalates_without_generating_or_binding(self) -> None:
        asset = _login_step_definition()
        catalog = _catalog(asset)
        need = GherkinStepNeed(
            text='I log in as "alice" with password "secret"',
            step_type="When",
            captures=asset.signature_alignment.captures,
        )
        candidate = MatchCandidate(
            asset_id=_LOGIN_ASSET_ID, confidence=0.10, content_hash=_CURRENT_HASH
        )
        matcher = StubSemanticMatcher({need.text: (candidate,)})
        generator = StubStepDefinitionGenerator({})

        outcome = orchestrate_step_definition(need, catalog, matcher, generator)

        assert isinstance(outcome, EscalatedStepNeed)
        assert outcome.need == need
        assert outcome.escalation.check == EscalationCheck.CONFIDENCE
        assert outcome.escalation.candidate == candidate
        assert generator.call_count == 0

    def test_stale_content_hash_escalates_without_generating_or_binding(self) -> None:
        asset = _login_step_definition(content_hash=_CURRENT_HASH)
        catalog = _catalog(asset)
        need = GherkinStepNeed(
            text='I log in as "alice" with password "secret"',
            step_type="When",
            captures=asset.signature_alignment.captures,
        )
        # Candidate was computed against a hash the catalog no longer carries.
        candidate = MatchCandidate(
            asset_id=_LOGIN_ASSET_ID, confidence=0.95, content_hash=_STALE_HASH
        )
        matcher = StubSemanticMatcher({need.text: (candidate,)})
        generator = StubStepDefinitionGenerator({})

        outcome = orchestrate_step_definition(need, catalog, matcher, generator)

        assert isinstance(outcome, EscalatedStepNeed)
        assert outcome.escalation.check == EscalationCheck.CONTENT_HASH
        assert generator.call_count == 0

    def test_signature_mismatch_escalates_without_generating_or_binding(self) -> None:
        asset = _login_step_definition()
        catalog = _catalog(asset)
        need = GherkinStepNeed(
            text='I log in as "alice" with password "secret"',
            step_type="When",
            captures=(),  # wrong arity -- asset needs 2 captures, need declares 0
        )
        candidate = MatchCandidate(
            asset_id=_LOGIN_ASSET_ID, confidence=0.95, content_hash=_CURRENT_HASH
        )
        matcher = StubSemanticMatcher({need.text: (candidate,)})
        generator = StubStepDefinitionGenerator({})

        outcome = orchestrate_step_definition(need, catalog, matcher, generator)

        assert isinstance(outcome, EscalatedStepNeed)
        assert outcome.escalation.check == EscalationCheck.SIGNATURE_FIT
        assert generator.call_count == 0


# ---------------------------------------------------------------------------
# customqa:* constraint injection
# ---------------------------------------------------------------------------


class TestCustomqaConstraintsAreInjectedIntoGeneration:
    def test_default_constraints_reach_the_generation_seam(self) -> None:
        need = _need("I log out")
        catalog = _catalog()
        matcher = StubSemanticMatcher({need.text: ()})
        generator = StubStepDefinitionGenerator({need.text: "package com.automation.steps;\n"})

        orchestrate_step_definition(need, catalog, matcher, generator)

        assert generator.call_count == 1
        received = generator.received_contexts[0]
        assert received.customqa_constraints == DEFAULT_CUSTOMQA_STEP_DEFINITION_CONSTRAINTS
        assert any("customqa:direct-webdriver-action" in c for c in received.customqa_constraints)
        assert any("customqa:long-method" in c for c in received.customqa_constraints)

    def test_caller_supplied_constraints_reach_the_generation_seam(self) -> None:
        need = _need("I log out")
        catalog = _catalog()
        matcher = StubSemanticMatcher({need.text: ()})
        generator = StubStepDefinitionGenerator({need.text: "package com.automation.steps;\n"})
        custom_constraints = ("custom-rule-one", "custom-rule-two")

        orchestrate_step_definition(
            need, catalog, matcher, generator, customqa_constraints=custom_constraints
        )

        received = generator.received_contexts[0]
        assert received.customqa_constraints == custom_constraints

    def test_target_package_reaches_the_generation_seam(self) -> None:
        need = _need("I log out")
        catalog = _catalog()
        matcher = StubSemanticMatcher({need.text: ()})
        generator = StubStepDefinitionGenerator({need.text: "package com.automation.steps;\n"})

        orchestrate_step_definition(
            need, catalog, matcher, generator, target_package="com.custom.steps"
        )

        received = generator.received_contexts[0]
        assert received.target_package == "com.custom.steps"


# ---------------------------------------------------------------------------
# THE PRECISE METHOD-FIT OBLIGATION -- now DISCHARGED (ADR-0044 D4's
# clarification note). The dedicated insufficient/sufficient/contrast
# proofs live in
# `tests/unit/test_automation_engineering_generation_page_object_orchestrator.py`;
# this class proves the WIRING at the step-def orchestrator's own binding
# point, plus the AST guard's own deliberate, documented update: page
# objects are now legitimately handled here; utilities are still not.
# ---------------------------------------------------------------------------


class TestPageObjectAndUtilityMethodFitBothDischarged:
    def test_generation_context_defaults_to_no_hints(self) -> None:
        """Unchanged default: when neither `page_object_request` nor
        `utility_request` is supplied, behavior is identical to before any
        of this -- both interface fields stay `None`."""
        need = _need("I log out")
        catalog = _catalog()
        matcher = StubSemanticMatcher({need.text: ()})
        generator = StubStepDefinitionGenerator({need.text: "package com.automation.steps;\n"})

        orchestrate_step_definition(need, catalog, matcher, generator)

        received = generator.received_contexts[0]
        assert received.page_object_interface is None
        assert received.utility_interface is None

    def test_generation_context_carries_the_verified_class_name_when_request_supplied(
        self,
    ) -> None:
        """THE discharge, proven at the ACTUAL binding point: a
        `page_object_request` whose page-object need resolves to a
        TRUSTED_REUSE with the specific method PRESENT populates
        `page_object_interface` with the reused class's own verified
        `class_name` -- never a name this orchestrator merely hopes is
        right."""
        from automation_engineering.catalog.models import JavaMethod, PageObjectAsset
        from automation_engineering.generation.models import PageObjectMethodNeed
        from automation_engineering.generation.page_object_generator import (
            StubPageObjectGenerator,
        )
        from automation_engineering.generation.page_object_orchestrator import (
            PageObjectBindingRequest,
        )

        login_page = PageObjectAsset(
            asset_id="PAGE-login01",
            class_name="com.automation.pages.LoginPage",
            extends="BasePage",
            fields=(),
            locators=(),
            methods=(
                JavaMethod(name="clickForgotPasswordLink", parameters=(), return_type="void"),
            ),
            source_file="com/automation/pages/LoginPage.java",
            content_hash="hash1",
        )
        catalog = AssetCatalog(baseline_root="test-suite-baseline", page_objects=(login_page,))
        step_need = _need("I click forgot password")
        step_matcher = StubSemanticMatcher({step_need.text: ()})
        step_generator = StubStepDefinitionGenerator(
            {step_need.text: "package com.automation.steps;\n"}
        )
        po_need_text = "click the forgot password link"
        po_candidate = MatchCandidate(
            asset_id="PAGE-login01", confidence=0.9, content_hash="hash1"
        )
        po_matcher = StubSemanticMatcher({po_need_text: (po_candidate,)})
        method_need = PageObjectMethodNeed(
            need=GherkinStepNeed(text=po_need_text, step_type="PageAction", captures=()),
            method_name="clickForgotPasswordLink",
        )
        page_object_request = PageObjectBindingRequest(
            method_need=method_need, matcher=po_matcher, generator=StubPageObjectGenerator({})
        )

        outcome = orchestrate_step_definition(
            step_need,
            catalog,
            step_matcher,
            step_generator,
            page_object_request=page_object_request,
        )

        assert isinstance(outcome, GeneratedStepDefinition)
        assert (
            step_generator.received_contexts[0].page_object_interface
            == "com.automation.pages.LoginPage"
        )

    def test_whole_step_escalates_when_the_specific_page_object_method_is_absent(self) -> None:
        """The precise check catches what the coarse screen could not: a
        TRUSTED_REUSE page object (coarse compatibility passed -- it has
        SOME zero-arg method) that lacks the SPECIFIC method the step is
        about to call. The step is NOT generated against an unverified
        call -- it escalates, and the step-def seam is never touched."""
        from automation_engineering.catalog.models import JavaMethod, PageObjectAsset
        from automation_engineering.generation.models import PageObjectMethodNeed
        from automation_engineering.generation.page_object_generator import (
            StubPageObjectGenerator,
        )
        from automation_engineering.generation.page_object_orchestrator import (
            PageObjectBindingRequest,
        )

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
        catalog = AssetCatalog(baseline_root="test-suite-baseline", page_objects=(login_page,))
        step_need = _need("I click forgot password")
        step_matcher = StubSemanticMatcher({step_need.text: ()})
        step_generator = StubStepDefinitionGenerator({})  # must never be called
        po_need_text = "click the forgot password link"
        po_candidate = MatchCandidate(
            asset_id="PAGE-login01", confidence=0.9, content_hash="hash1"
        )
        po_matcher = StubSemanticMatcher({po_need_text: (po_candidate,)})
        method_need = PageObjectMethodNeed(
            need=GherkinStepNeed(text=po_need_text, step_type="PageAction", captures=()),
            method_name="clickForgotPasswordLink",
        )
        page_object_request = PageObjectBindingRequest(
            method_need=method_need, matcher=po_matcher, generator=StubPageObjectGenerator({})
        )

        outcome = orchestrate_step_definition(
            step_need,
            catalog,
            step_matcher,
            step_generator,
            page_object_request=page_object_request,
        )

        assert isinstance(outcome, EscalatedStepNeed)
        assert outcome.escalation.check == EscalationCheck.METHOD_FIT
        assert step_generator.call_count == 0

    def test_generation_context_carries_the_verified_utility_class_name_when_request_supplied(
        self,
    ) -> None:
        """The SAME discharge, mirrored for utilities: a `utility_request`
        whose utility need resolves to a TRUSTED_REUSE with the specific
        method PRESENT populates `utility_interface` with the reused
        class's own verified `class_name`."""
        from automation_engineering.catalog.models import JavaMethod, UtilityAsset
        from automation_engineering.generation.models import UtilityMethodNeed
        from automation_engineering.generation.utility_generator import StubUtilityGenerator
        from automation_engineering.generation.utility_orchestrator import (
            UtilityBindingRequest,
        )

        config_reader = UtilityAsset(
            asset_id="UTIL-config01",
            class_name="com.automation.utils.ConfigReader",
            fields=(),
            methods=(JavaMethod(name="data", parameters=(), return_type="String"),),
            source_file="com/automation/utils/ConfigReader.java",
            content_hash="hash1",
        )
        catalog = AssetCatalog(baseline_root="test-suite-baseline", utilities=(config_reader,))
        step_need = _need("I read the stored username")
        step_matcher = StubSemanticMatcher({step_need.text: ()})
        step_generator = StubStepDefinitionGenerator(
            {step_need.text: "package com.automation.steps;\n"}
        )
        util_need_text = "read a test-data value"
        util_candidate = MatchCandidate(
            asset_id="UTIL-config01", confidence=0.9, content_hash="hash1"
        )
        util_matcher = StubSemanticMatcher({util_need_text: (util_candidate,)})
        method_need = UtilityMethodNeed(
            need=GherkinStepNeed(text=util_need_text, step_type="UtilityAction", captures=()),
            method_name="data",
        )
        utility_request = UtilityBindingRequest(
            method_need=method_need, matcher=util_matcher, generator=StubUtilityGenerator({})
        )

        outcome = orchestrate_step_definition(
            step_need,
            catalog,
            step_matcher,
            step_generator,
            utility_request=utility_request,
        )

        assert isinstance(outcome, GeneratedStepDefinition)
        assert (
            step_generator.received_contexts[0].utility_interface
            == "com.automation.utils.ConfigReader"
        )

    def test_whole_step_escalates_when_the_specific_utility_method_is_absent(self) -> None:
        """The precise check catches what the coarse screen could not, for
        utilities too: a TRUSTED_REUSE `ConfigReader`-shaped utility (coarse
        compatibility passed) that lacks the SPECIFIC method the step is
        about to call escalates the WHOLE step; the step-def seam is never
        touched."""
        from automation_engineering.catalog.models import JavaMethod, UtilityAsset
        from automation_engineering.generation.models import UtilityMethodNeed
        from automation_engineering.generation.utility_generator import StubUtilityGenerator
        from automation_engineering.generation.utility_orchestrator import (
            UtilityBindingRequest,
        )

        config_reader = UtilityAsset(
            asset_id="UTIL-config01",
            class_name="com.automation.utils.ConfigReader",
            fields=(),
            methods=(JavaMethod(name="env", parameters=(), return_type="String"),),
            source_file="com/automation/utils/ConfigReader.java",
            content_hash="hash1",
        )
        catalog = AssetCatalog(baseline_root="test-suite-baseline", utilities=(config_reader,))
        step_need = _need("I read the stored username")
        step_matcher = StubSemanticMatcher({step_need.text: ()})
        step_generator = StubStepDefinitionGenerator({})  # must never be called
        util_need_text = "read a test-data value"
        util_candidate = MatchCandidate(
            asset_id="UTIL-config01", confidence=0.9, content_hash="hash1"
        )
        util_matcher = StubSemanticMatcher({util_need_text: (util_candidate,)})
        method_need = UtilityMethodNeed(
            need=GherkinStepNeed(text=util_need_text, step_type="UtilityAction", captures=()),
            method_name="data",  # absent -- only "env" exists, same shape
        )
        utility_request = UtilityBindingRequest(
            method_need=method_need, matcher=util_matcher, generator=StubUtilityGenerator({})
        )

        outcome = orchestrate_step_definition(
            step_need,
            catalog,
            step_matcher,
            step_generator,
            utility_request=utility_request,
        )

        assert isinstance(outcome, EscalatedStepNeed)
        assert outcome.escalation.check == EscalationCheck.METHOD_FIT
        assert step_generator.call_count == 0

    def test_orchestrator_now_imports_both_page_object_and_utility_orchestrators(
        self,
    ) -> None:
        """A structural guard, updated deliberately a second time -- not
        deleted, not broken accidentally. All three catalog asset kinds
        (step definitions, page objects, utilities) are now legitimately
        handled somewhere in this generation package: the step-def
        orchestrator's own source imports BOTH `page_object_orchestrator`
        AND `utility_orchestrator`. There is no fourth, still-deferred
        asset kind for a "never reaches for X" guard to protect -- this
        test is a positive completeness check, not a restriction."""
        orchestrator_source = Path("automation_engineering/generation/orchestrator.py").read_text(
            encoding="utf-8"
        )
        assert "page_object_orchestrator" in orchestrator_source
        assert "utility_orchestrator" in orchestrator_source

    def test_module_docstring_records_the_discharge_explicitly(self) -> None:
        import automation_engineering.generation.orchestrator as orchestrator_module

        doc = (orchestrator_module.__doc__ or "").lower()
        assert "discharged" in doc
        assert "inherited" in doc
        assert "utilit" in doc  # matches "utility"/"utilities"
        assert "no fourth" in doc or "no still-deferred" in doc


# ---------------------------------------------------------------------------
# Batch orchestration, determinism, and no live LLM call anywhere here
# ---------------------------------------------------------------------------


class TestBatchOrchestration:
    def test_generate_step_definitions_processes_each_need_independently_in_order(self) -> None:
        asset = _login_step_definition()
        bind_need = GherkinStepNeed(
            text='I log in as "alice" with password "secret"',
            step_type="When",
            captures=asset.signature_alignment.captures,
        )
        generate_need = _need("I log out")
        escalate_need = GherkinStepNeed(
            text="I do something ambiguous", step_type="When", captures=()
        )
        catalog = _catalog(asset)
        bind_candidate = MatchCandidate(
            asset_id=_LOGIN_ASSET_ID, confidence=0.95, content_hash=_CURRENT_HASH
        )
        escalate_candidate = MatchCandidate(
            asset_id=_LOGIN_ASSET_ID, confidence=0.10, content_hash=_CURRENT_HASH
        )
        matcher = StubSemanticMatcher(
            {
                bind_need.text: (bind_candidate,),
                generate_need.text: (),
                escalate_need.text: (escalate_candidate,),
            }
        )
        generator = StubStepDefinitionGenerator(
            {generate_need.text: "package com.automation.steps;\n"}
        )

        outcomes = generate_step_definitions(
            [bind_need, generate_need, escalate_need], catalog, matcher, generator
        )

        assert len(outcomes) == 3
        assert isinstance(outcomes[0], BoundStepDefinition)
        assert isinstance(outcomes[1], GeneratedStepDefinition)
        assert isinstance(outcomes[2], EscalatedStepNeed)
        assert generator.call_count == 1  # only the NO_MATCH need generated


class TestDeterminism:
    def test_same_inputs_yield_the_same_outcome(self) -> None:
        need = _need("I log out")
        catalog = _catalog()
        matcher = StubSemanticMatcher({need.text: ()})
        canned = "package com.automation.steps;\n"

        first = orchestrate_step_definition(
            need, catalog, matcher, StubStepDefinitionGenerator({need.text: canned})
        )
        second = orchestrate_step_definition(
            need, catalog, matcher, StubStepDefinitionGenerator({need.text: canned})
        )

        assert first == second


class TestNoLiveLlmInvolvementInOrchestration:
    def test_orchestrator_module_never_imports_llm_factory_or_an_embedding_provider(
        self,
    ) -> None:
        source = Path("automation_engineering/generation/orchestrator.py").read_text(
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
