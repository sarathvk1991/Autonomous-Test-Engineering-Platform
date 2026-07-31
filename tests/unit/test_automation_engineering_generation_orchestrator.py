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
* The inherited, NOT-discharged precise method-fit obligation on reused page
  objects: `page_object_interface` is never populated by this orchestration.
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
# THE INHERITED PRECISE METHOD-FIT OBLIGATION -- carried forward, not
# discharged here (ADR-0044 D4's clarification note).
# ---------------------------------------------------------------------------


class TestInheritedPageObjectMethodFitObligationIsCarriedForwardNotDischarged:
    def test_generation_context_never_carries_a_page_object_hint(self) -> None:
        """This orchestration never performs a page-object catalog lookup --
        page-object reuse/generation is the next task. Every context this
        module constructs carries `page_object_interface=None`."""
        need = _need("I log out")
        catalog = _catalog()
        matcher = StubSemanticMatcher({need.text: ()})
        generator = StubStepDefinitionGenerator({need.text: "package com.automation.steps;\n"})

        orchestrate_step_definition(need, catalog, matcher, generator)

        assert generator.received_contexts[0].page_object_interface is None

    def test_orchestrator_module_never_looks_up_page_objects_or_utilities(self) -> None:
        """A structural guard, not just a behavioral one: the orchestrator's
        own source never references `catalog.page_objects` or
        `catalog.utilities` at all -- the obligation is carried forward by
        never reaching for that data, not by reaching for it and discarding
        the result."""
        source = Path("automation_engineering/generation/orchestrator.py").read_text(
            encoding="utf-8"
        )
        tree = ast.parse(source)
        attribute_names = {
            node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)
        }
        assert "page_objects" not in attribute_names
        assert "utilities" not in attribute_names

    def test_module_docstring_records_the_deferral_explicitly(self) -> None:
        import automation_engineering.generation.orchestrator as orchestrator_module

        doc = (orchestrator_module.__doc__ or "").lower()
        assert "inherited" in doc
        assert "does not discharge" in doc or "not discharge" in doc
        assert "next task" in doc or "page-object generator" in doc


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
