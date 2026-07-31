"""Reuse-first utility orchestration PLUS the precise method-fit discharge
(`automation_engineering.generation.utility_orchestrator`,
`automation_engineering.generation.method_fit`) -- proves, deterministically
and without any live call:

Part 1 (generation, mirrors the page-object/step-def proofs):
* NO_MATCH -> GENERATE: the stub generator IS called, a utility lands in
  `com.automation.utils`, final class / private constructor / static
  methods only, mirroring the real `ConfigReader` shape.
* TRUSTED_REUSE (specific method present) -> BIND, never regenerate: the
  stub generator is proven NOT called via its own spy.
* ESCALATION (reuse engine's own checks) -> neither generated nor bound,
  surfaced for review, untouched.
* customqa:* constraints are actually injected into what the generation seam
  receives -- ONLY `customqa:long-method` (the evidenced one for utilities;
  see `utility_orchestrator`'s own module docstring for why
  `customqa:direct-webdriver-action` is deliberately absent).

Part 2 -- THE METHOD-FIT DISCHARGE FOR UTILITIES (the finding this build's
own pre-flight investigation reached: utilities carry the identical risk
page objects do, sharper if anything, because this platform's own real
utility class, `ConfigReader`, exposes two methods -- `env(String)` and
`data(String)` -- with an IDENTICAL parameter shape a coarse screen cannot
distinguish):
* PRECISE method-fit ESCALATES on the insufficient case: a TRUSTED_REUSE
  `ConfigReader`-shaped utility that has `env` but not the `data` the step
  actually needs.
* PRECISE method-fit PASSES when the reused utility HAS the specific
  method, with a fitting signature.
* CONTRAST proof: the SAME candidate that clears the COARSE screen
  (`decide_reuse` itself returns `TrustedReuse`) still fails the PRECISE
  check.

Builds on the real catalog shapes (`automation_engineering.catalog.models`),
the same discipline `tests/unit/test_automation_engineering_reuse_method_fit.py`
already established for utilities' own coarse screen (`test_utility_method_fit_*`),
so this orchestration is proven against the SAME reuse-decision data the
engine actually produces.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from automation_engineering.catalog.models import (
    AssetCatalog,
    JavaMethod,
    JavaParameter,
    StepCapture,
    UtilityAsset,
)
from automation_engineering.generation.method_fit import verify_specific_method_fit
from automation_engineering.generation.models import (
    BoundUtilityMethod,
    EscalatedUtilityMethodNeed,
    GeneratedUtility,
    UtilityMethodNeed,
)
from automation_engineering.generation.utility_generator import StubUtilityGenerator
from automation_engineering.generation.utility_orchestrator import (
    DEFAULT_CUSTOMQA_UTILITY_CONSTRAINTS,
    DEFAULT_UTILITY_TARGET_PACKAGE,
    derive_utility_class_name,
    generate_utility_methods,
    orchestrate_utility_method,
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

_CONFIG_READER_ASSET_ID = "UTIL-configfixture01"
_CURRENT_HASH = "current-hash-abc123"
_STALE_HASH = "stale-hash-000000"


def _utility(
    asset_id: str = _CONFIG_READER_ASSET_ID,
    class_name: str = "com.automation.utils.ConfigReader",
    methods: tuple[JavaMethod, ...] = (),
    content_hash: str = _CURRENT_HASH,
) -> UtilityAsset:
    return UtilityAsset(
        asset_id=asset_id,
        class_name=class_name,
        fields=(),
        methods=methods,
        source_file="com/automation/utils/ConfigReader.java",
        content_hash=content_hash,
    )


def _catalog(*assets: UtilityAsset) -> AssetCatalog:
    return AssetCatalog(baseline_root="test-suite-baseline", utilities=tuple(assets))


def _method_need(
    action_text: str = "read a test-data value by key",
    method_name: str = "data",
) -> UtilityMethodNeed:
    return UtilityMethodNeed(
        need=GherkinStepNeed(
            text=action_text,
            step_type="UtilityAction",
            captures=(StepCapture(index=0, style="cucumber_expression", expression_type="string"),),
        ),
        method_name=method_name,
    )


def _data_method() -> tuple[JavaMethod, ...]:
    """A `data(String) -> String` method -- the fitting shape `_method_need()`'s
    own one-string-capture requirement needs."""
    return (
        JavaMethod(
            name="data",
            parameters=(JavaParameter(name="key", java_type="String"),),
            return_type="String",
        ),
    )


# ---------------------------------------------------------------------------
# NO_MATCH -> generate
# ---------------------------------------------------------------------------


class TestNoMatchGenerates:
    def test_generates_a_utility_in_com_automation_utils(self) -> None:
        method_need = _method_need()
        catalog = _catalog()  # empty -- nothing to reuse
        matcher = StubSemanticMatcher({method_need.need.text: ()})
        canned_java = (
            "package com.automation.utils;\n\n"
            "public final class TestDataReader {\n\n"
            "    private TestDataReader() {\n"
            "    }\n\n"
            "    public static String data(String key) {\n"
            "        return ConfigReader.data(key);\n"
            "    }\n"
            "}\n"
        )
        generator = StubUtilityGenerator({method_need.need.text: canned_java})

        outcome = orchestrate_utility_method(method_need, catalog, matcher, generator)

        assert isinstance(outcome, GeneratedUtility)
        assert outcome.method_need == method_need
        assert outcome.java_source == canned_java
        assert "final class" in outcome.java_source
        assert "private TestDataReader()" in outcome.java_source
        assert (
            outcome.target_package == DEFAULT_UTILITY_TARGET_PACKAGE == "com.automation.utils"
        )
        assert outcome.class_name  # deterministically derived, non-empty
        assert generator.call_count == 1

    def test_generator_is_called_exactly_once_per_no_match_need(self) -> None:
        method_need = _method_need()
        catalog = _catalog()
        matcher = StubSemanticMatcher({method_need.need.text: ()})
        generator = StubUtilityGenerator({method_need.need.text: "package com.automation.utils;\n"})

        orchestrate_utility_method(method_need, catalog, matcher, generator)

        assert generator.call_count == 1


# ---------------------------------------------------------------------------
# TRUSTED_REUSE (specific method present) -> bind, never regenerate
# ---------------------------------------------------------------------------


class TestTrustedReuseWithSufficientMethodBindsWithoutRegenerating:
    def test_binds_to_the_existing_asset(self) -> None:
        asset = _utility(
            methods=_data_method()
        )
        catalog = _catalog(asset)
        method_need = _method_need()
        candidate = MatchCandidate(
            asset_id=_CONFIG_READER_ASSET_ID, confidence=0.95, content_hash=_CURRENT_HASH
        )
        matcher = StubSemanticMatcher({method_need.need.text: (candidate,)})
        generator = StubUtilityGenerator({})  # must never be called

        outcome = orchestrate_utility_method(method_need, catalog, matcher, generator)

        assert isinstance(outcome, BoundUtilityMethod)
        assert outcome.method_need == method_need
        assert outcome.asset is asset

    def test_generator_is_never_called_for_a_sufficient_trusted_reuse(self) -> None:
        """The spy proof this build's verification section requires: zero
        generation calls when a trusted reuse's specific method is present."""
        asset = _utility(
            methods=_data_method()
        )
        catalog = _catalog(asset)
        method_need = _method_need()
        candidate = MatchCandidate(
            asset_id=_CONFIG_READER_ASSET_ID, confidence=0.95, content_hash=_CURRENT_HASH
        )
        matcher = StubSemanticMatcher({method_need.need.text: (candidate,)})
        generator = StubUtilityGenerator({})

        orchestrate_utility_method(method_need, catalog, matcher, generator)

        assert generator.call_count == 0
        assert generator.received_contexts == ()


# ---------------------------------------------------------------------------
# ESCALATION (reuse engine's own checks) -> neither generated nor bound
# ---------------------------------------------------------------------------


class TestReuseEngineEscalationSurfacesForReview:
    def test_low_confidence_escalates_without_generating_or_binding(self) -> None:
        asset = _utility(
            methods=_data_method()
        )
        catalog = _catalog(asset)
        method_need = _method_need()
        candidate = MatchCandidate(
            asset_id=_CONFIG_READER_ASSET_ID, confidence=0.10, content_hash=_CURRENT_HASH
        )
        matcher = StubSemanticMatcher({method_need.need.text: (candidate,)})
        generator = StubUtilityGenerator({})

        outcome = orchestrate_utility_method(method_need, catalog, matcher, generator)

        assert isinstance(outcome, EscalatedUtilityMethodNeed)
        assert outcome.method_need == method_need
        assert outcome.escalation.check == EscalationCheck.CONFIDENCE
        assert outcome.escalation.candidate == candidate
        assert generator.call_count == 0

    def test_stale_content_hash_escalates_without_generating_or_binding(self) -> None:
        asset = _utility(
            methods=(
                JavaMethod(
                    name="data",
                    parameters=(JavaParameter(name="key", java_type="String"),),
                    return_type="String",
                ),
            ),
            content_hash=_CURRENT_HASH,
        )
        catalog = _catalog(asset)
        method_need = _method_need()
        candidate = MatchCandidate(
            asset_id=_CONFIG_READER_ASSET_ID, confidence=0.95, content_hash=_STALE_HASH
        )
        matcher = StubSemanticMatcher({method_need.need.text: (candidate,)})
        generator = StubUtilityGenerator({})

        outcome = orchestrate_utility_method(method_need, catalog, matcher, generator)

        assert isinstance(outcome, EscalatedUtilityMethodNeed)
        assert outcome.escalation.check == EscalationCheck.CONTENT_HASH
        assert generator.call_count == 0

    def test_gross_coarse_incompatibility_escalates_without_generating_or_binding(self) -> None:
        """The COARSE screen's own job: a candidate whose class has NO
        method at all with a compatible shape escalates at decision time,
        before this build's own precise check is ever reached -- mirrors
        `test_utility_method_fit_escalates_when_no_compatible_method_exists`
        in `test_automation_engineering_reuse_method_fit.py`."""
        asset = _utility(methods=(JavaMethod(name="reload", parameters=(), return_type="void"),))
        catalog = _catalog(asset)
        method_need = _method_need()  # requires one string capture; reload takes none
        candidate = MatchCandidate(
            asset_id=_CONFIG_READER_ASSET_ID, confidence=0.95, content_hash=_CURRENT_HASH
        )
        matcher = StubSemanticMatcher({method_need.need.text: (candidate,)})
        generator = StubUtilityGenerator({})

        outcome = orchestrate_utility_method(method_need, catalog, matcher, generator)

        assert isinstance(outcome, EscalatedUtilityMethodNeed)
        assert outcome.escalation.check == EscalationCheck.METHOD_FIT
        assert generator.call_count == 0


# ---------------------------------------------------------------------------
# customqa:* constraint injection -- ONLY long-method is evidenced
# ---------------------------------------------------------------------------


class TestCustomqaConstraintsAreInjectedIntoGeneration:
    def test_default_constraints_reach_the_generation_seam(self) -> None:
        method_need = _method_need()
        catalog = _catalog()
        matcher = StubSemanticMatcher({method_need.need.text: ()})
        generator = StubUtilityGenerator({method_need.need.text: "package com.automation.utils;\n"})

        orchestrate_utility_method(method_need, catalog, matcher, generator)

        assert generator.call_count == 1
        received = generator.received_contexts[0]
        assert received.customqa_constraints == DEFAULT_CUSTOMQA_UTILITY_CONSTRAINTS
        assert any("customqa:long-method" in c for c in received.customqa_constraints)
        # The honest negative: direct-webdriver-action is NOT fabricated here.
        assert not any(
            "customqa:direct-webdriver-action" in c for c in received.customqa_constraints
        )

    def test_caller_supplied_constraints_reach_the_generation_seam(self) -> None:
        method_need = _method_need()
        catalog = _catalog()
        matcher = StubSemanticMatcher({method_need.need.text: ()})
        generator = StubUtilityGenerator({method_need.need.text: "package com.automation.utils;\n"})
        custom_constraints = ("custom-rule-one", "custom-rule-two")

        orchestrate_utility_method(
            method_need, catalog, matcher, generator, customqa_constraints=custom_constraints
        )

        received = generator.received_contexts[0]
        assert received.customqa_constraints == custom_constraints

    def test_target_package_reaches_the_generation_seam(self) -> None:
        method_need = _method_need()
        catalog = _catalog()
        matcher = StubSemanticMatcher({method_need.need.text: ()})
        generator = StubUtilityGenerator({method_need.need.text: "package com.automation.utils;\n"})

        orchestrate_utility_method(
            method_need, catalog, matcher, generator, target_package="com.custom.utils"
        )

        received = generator.received_contexts[0]
        assert received.target_package == "com.custom.utils"


# ---------------------------------------------------------------------------
# PART 2 -- THE METHOD-FIT DISCHARGE FOR UTILITIES
# ---------------------------------------------------------------------------


class TestPreciseMethodFitEscalatesTheInsufficientCase:
    """The finding this build's own pre-flight investigation reached: a
    `ConfigReader`-shaped utility whose `env(String)` and `data(String)`
    accessors share an IDENTICAL parameter shape -- the coarse screen
    cannot tell them apart at all. Reused for a step needing
    `data("username")`, where the catalogued class only has `env`."""

    def test_reuse_engine_itself_returns_trusted_reuse_not_an_escalation(self) -> None:
        """First, prove the COARSE screen genuinely passes -- this is not a
        contrived case the engine would have caught anyway."""
        asset = _utility(
            methods=(
                JavaMethod(
                    name="env",
                    parameters=(JavaParameter(name="key", java_type="String"),),
                    return_type="String",
                ),
            )
        )
        catalog = _catalog(asset)
        method_need = _method_need()  # needs "data" -- absent
        candidate = MatchCandidate(
            asset_id=_CONFIG_READER_ASSET_ID, confidence=0.95, content_hash=_CURRENT_HASH
        )
        matcher = StubSemanticMatcher({method_need.need.text: (candidate,)})

        decision = decide_reuse(method_need.need, catalog, matcher)

        assert isinstance(decision, TrustedReuse)
        assert decision.asset is asset

    def test_orchestration_escalates_despite_the_coarse_pass(self) -> None:
        """Then prove the FULL orchestration -- coarse pass included --
        still escalates, because the PRECISE check catches what the coarse
        one could not (identically shaped `env`/`data`). THIS is the
        obligation this build discharged for utilities."""
        asset = _utility(
            methods=(
                JavaMethod(
                    name="env",
                    parameters=(JavaParameter(name="key", java_type="String"),),
                    return_type="String",
                ),
            )
        )
        catalog = _catalog(asset)
        method_need = _method_need()
        candidate = MatchCandidate(
            asset_id=_CONFIG_READER_ASSET_ID, confidence=0.95, content_hash=_CURRENT_HASH
        )
        matcher = StubSemanticMatcher({method_need.need.text: (candidate,)})
        generator = StubUtilityGenerator({})  # must never be called

        outcome = orchestrate_utility_method(method_need, catalog, matcher, generator)

        assert isinstance(outcome, EscalatedUtilityMethodNeed)
        assert outcome.escalation.check == EscalationCheck.METHOD_FIT
        assert "data" in outcome.escalation.detail
        assert "env" in outcome.escalation.detail  # names what IS available
        assert generator.call_count == 0

    def test_method_fit_verify_function_directly_escalates_on_absent_method(self) -> None:
        """Unit-level proof of :func:`verify_specific_method_fit` itself --
        the SAME function the page-object build wrote, reused unchanged."""
        asset = _utility(
            methods=(
                JavaMethod(
                    name="env",
                    parameters=(JavaParameter(name="key", java_type="String"),),
                    return_type="String",
                ),
            )
        )
        candidate = MatchCandidate(
            asset_id=_CONFIG_READER_ASSET_ID, confidence=0.95, content_hash=_CURRENT_HASH
        )

        escalation = verify_specific_method_fit(_method_need().need, asset, candidate, "data")

        assert escalation is not None
        assert escalation.check == EscalationCheck.METHOD_FIT


class TestPreciseMethodFitPassesTheSufficientCase:
    def test_method_present_with_fitting_signature_verifies_clean(self) -> None:
        asset = _utility(
            methods=(
                JavaMethod(
                    name="data",
                    parameters=(JavaParameter(name="key", java_type="String"),),
                    return_type="String",
                ),
            )
        )
        candidate = MatchCandidate(
            asset_id=_CONFIG_READER_ASSET_ID, confidence=0.95, content_hash=_CURRENT_HASH
        )

        escalation = verify_specific_method_fit(_method_need().need, asset, candidate, "data")

        assert escalation is None

    def test_orchestration_binds_when_the_specific_method_is_present(self) -> None:
        asset = _utility(
            methods=(
                JavaMethod(
                    name="data",
                    parameters=(JavaParameter(name="key", java_type="String"),),
                    return_type="String",
                ),
            )
        )
        catalog = _catalog(asset)
        method_need = _method_need()
        candidate = MatchCandidate(
            asset_id=_CONFIG_READER_ASSET_ID, confidence=0.95, content_hash=_CURRENT_HASH
        )
        matcher = StubSemanticMatcher({method_need.need.text: (candidate,)})
        generator = StubUtilityGenerator({})

        outcome = orchestrate_utility_method(method_need, catalog, matcher, generator)

        assert isinstance(outcome, BoundUtilityMethod)
        assert generator.call_count == 0


class TestCoarseAndPreciseCatchDifferentThings:
    """The contrast proof this build's verification section names
    explicitly: the SAME candidate that clears the coarse screen still
    fails the precise one."""

    def test_same_candidate_clears_coarse_but_fails_precise(self) -> None:
        asset = _utility(
            methods=(
                JavaMethod(
                    name="env",
                    parameters=(JavaParameter(name="key", java_type="String"),),
                    return_type="String",
                ),
            )
        )
        catalog = _catalog(asset)
        method_need = _method_need()
        candidate = MatchCandidate(
            asset_id=_CONFIG_READER_ASSET_ID, confidence=0.95, content_hash=_CURRENT_HASH
        )
        matcher = StubSemanticMatcher({method_need.need.text: (candidate,)})

        # COARSE (the reuse engine's own decision): passes -- env's shape
        # (String -> String) coarsely fits the need's one-string-capture shape.
        coarse_decision = decide_reuse(method_need.need, catalog, matcher)
        assert isinstance(coarse_decision, TrustedReuse)
        assert isinstance(coarse_decision.asset, UtilityAsset)

        # PRECISE (this build's discharge): fails -- "data" isn't "env",
        # even though the two share an identical parameter shape.
        precise_escalation = verify_specific_method_fit(
            method_need.need,
            coarse_decision.asset,
            coarse_decision.candidate,
            "data",
        )
        assert precise_escalation is not None
        assert precise_escalation.check == EscalationCheck.METHOD_FIT

    def test_a_different_need_naming_an_existing_method_passes_both(self) -> None:
        """Contrast the other direction: the SAME class, a need that asks
        for the method it ACTUALLY has, passes both halves."""
        asset = _utility(
            methods=(
                JavaMethod(
                    name="env",
                    parameters=(JavaParameter(name="key", java_type="String"),),
                    return_type="String",
                ),
            )
        )
        catalog = _catalog(asset)
        method_need = _method_need(action_text="read an environment value", method_name="env")
        candidate = MatchCandidate(
            asset_id=_CONFIG_READER_ASSET_ID, confidence=0.95, content_hash=_CURRENT_HASH
        )
        matcher = StubSemanticMatcher({method_need.need.text: (candidate,)})
        generator = StubUtilityGenerator({})

        outcome = orchestrate_utility_method(method_need, catalog, matcher, generator)

        assert isinstance(outcome, BoundUtilityMethod)


# ---------------------------------------------------------------------------
# Deterministic class-name derivation
# ---------------------------------------------------------------------------


class TestDeriveUtilityClassName:
    def test_strips_a_leading_verb_and_stopwords(self) -> None:
        assert derive_utility_class_name("read a test-data value by key") == "TestDataValueKey"

    def test_no_fixed_suffix_is_fabricated(self) -> None:
        """Unlike page objects (`derive_page_object_class_name`'s own
        evidenced "Page" suffix), no "Util"/"Utils" suffix is appended --
        `ConfigReader`, the one real utility class this platform has ever
        committed, carries no such suffix."""
        name = derive_utility_class_name("format a date")
        assert not name.endswith("Util")
        assert not name.endswith("Utils")

    def test_deterministic_across_calls(self) -> None:
        first = derive_utility_class_name("read a test-data value by key")
        second = derive_utility_class_name("read a test-data value by key")
        assert first == second


# ---------------------------------------------------------------------------
# Batch orchestration, determinism, and no live LLM call anywhere here
# ---------------------------------------------------------------------------


class TestBatchOrchestration:
    def test_generate_utility_methods_processes_each_need_independently_in_order(self) -> None:
        asset = _utility(
            methods=(
                JavaMethod(
                    name="data",
                    parameters=(JavaParameter(name="key", java_type="String"),),
                    return_type="String",
                ),
            )
        )
        bind_need = _method_need()
        generate_need = _method_need(action_text="format a date", method_name="formatDate")
        escalate_need = _method_need(
            action_text="an ambiguous utility action", method_name="doSomethingAmbiguous"
        )
        catalog = _catalog(asset)
        bind_candidate = MatchCandidate(
            asset_id=_CONFIG_READER_ASSET_ID, confidence=0.95, content_hash=_CURRENT_HASH
        )
        escalate_candidate = MatchCandidate(
            asset_id=_CONFIG_READER_ASSET_ID, confidence=0.10, content_hash=_CURRENT_HASH
        )
        matcher = StubSemanticMatcher(
            {
                bind_need.need.text: (bind_candidate,),
                generate_need.need.text: (),
                escalate_need.need.text: (escalate_candidate,),
            }
        )
        generator = StubUtilityGenerator(
            {generate_need.need.text: "package com.automation.utils;\n"}
        )

        outcomes = generate_utility_methods(
            [bind_need, generate_need, escalate_need], catalog, matcher, generator
        )

        assert len(outcomes) == 3
        assert isinstance(outcomes[0], BoundUtilityMethod)
        assert isinstance(outcomes[1], GeneratedUtility)
        assert isinstance(outcomes[2], EscalatedUtilityMethodNeed)
        assert generator.call_count == 1  # only the NO_MATCH need generated


class TestDeterminism:
    def test_same_inputs_yield_the_same_outcome(self) -> None:
        method_need = _method_need()
        catalog = _catalog()
        matcher = StubSemanticMatcher({method_need.need.text: ()})
        canned = "package com.automation.utils;\n"

        first = orchestrate_utility_method(
            method_need, catalog, matcher, StubUtilityGenerator({method_need.need.text: canned})
        )
        second = orchestrate_utility_method(
            method_need, catalog, matcher, StubUtilityGenerator({method_need.need.text: canned})
        )

        assert first == second


class TestNoLiveLlmInvolvementInOrchestration:
    def test_orchestrator_module_never_imports_llm_factory_or_an_embedding_provider(
        self,
    ) -> None:
        for module_name in ("utility_orchestrator.py", "method_fit.py"):
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
