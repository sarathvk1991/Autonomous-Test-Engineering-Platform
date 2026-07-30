"""The page-object/utility realization of ADR-0044 D4(c) -- METHOD-FIT
(`automation_engineering.reuse.engine._check_method_fit`).

**What this proves, and deliberately does NOT claim to prove.** Method-fit
is a COARSE, decision-time CLASS-COMPATIBILITY SCREEN: it escalates only
when the candidate class has NO method at all whose parameter shape
(arity + per-position type) is compatible with the step-need's own
required captures. This file proves exactly that -- GROSS incompatibility
escalates, coarse compatibility passes -- and does NOT assert escalation
for "the class has some shape-compatible method but not the SPECIFIC one
the binding needs," because the engine cannot detect that case at
decision time (the engine has no method-name/intent-level information to
compare against; only a future generator, which knows which method it is
about to call, can catch that). That precise case is instead proven as a
CONTRACT: a `TrustedReuse` for a page-object/utility asset exposes the
full method inventory (`asset.methods`), which is what the generator needs
to perform the check this file's coarse tests do not.
"""

from __future__ import annotations

import pytest

from automation_engineering.catalog.models import (
    AssetCatalog,
    JavaField,
    JavaMethod,
    JavaParameter,
    PageObjectAsset,
    StepCapture,
    UtilityAsset,
)
from automation_engineering.reuse.engine import decide_reuse
from automation_engineering.reuse.matcher import StubSemanticMatcher
from automation_engineering.reuse.models import (
    Escalation,
    EscalationCheck,
    GherkinStepNeed,
    MatchCandidate,
    TrustedReuse,
)

pytestmark = pytest.mark.unit

_LOGIN_PAGE_ASSET_ID = "PAGE-loginfixture01"
_CURRENT_HASH = "page-current-hash-abc123"


def _two_string_captures() -> tuple[StepCapture, ...]:
    return (
        StepCapture(index=0, style="cucumber_expression", expression_type="string"),
        StepCapture(index=1, style="cucumber_expression", expression_type="string"),
    )


def _login_page(
    methods: tuple[JavaMethod, ...], content_hash: str = _CURRENT_HASH
) -> PageObjectAsset:
    return PageObjectAsset(
        asset_id=_LOGIN_PAGE_ASSET_ID,
        class_name="com.automation.pages.LoginPage",
        extends="BasePage",
        fields=(JavaField(name="usernameField", java_type="By", is_locator=True),),
        locators=(JavaField(name="usernameField", java_type="By", is_locator=True),),
        methods=methods,
        source_file="com/automation/pages/LoginPage.java",
        content_hash=content_hash,
    )


def _catalog_with_page(page: PageObjectAsset) -> AssetCatalog:
    return AssetCatalog(baseline_root="test-suite-baseline", page_objects=(page,))


def _catalog_with_utility(utility: UtilityAsset) -> AssetCatalog:
    return AssetCatalog(baseline_root="test-suite-baseline", utilities=(utility,))


def _login_need() -> GherkinStepNeed:
    return GherkinStepNeed(
        text='I log in as "alice" with password "secret"',
        step_type="When",
        captures=_two_string_captures(),
    )


# ---------------------------------------------------------------------------
# Coarse ESCALATION: gross class-level incompatibility
# ---------------------------------------------------------------------------


def test_method_fit_escalates_when_class_has_no_compatible_method_at_all() -> None:
    """GROSS incompatibility: the step needs 2 `{string}` captures; the
    matched page object's only methods are zero-arg -- no method on the
    class could possibly accept this call. ESCALATE(method_fit), despite
    high confidence and a current content-hash -- proving (c) still fires
    even when (a) and (b) would pass, for page objects at the coarse
    level, exactly as it already does for step definitions."""
    page = _login_page(methods=(JavaMethod(name="open", parameters=(), return_type="void"),))
    catalog = _catalog_with_page(page)
    need = _login_need()
    candidate = MatchCandidate(
        asset_id=_LOGIN_PAGE_ASSET_ID, confidence=0.95, content_hash=_CURRENT_HASH
    )
    matcher = StubSemanticMatcher({need.text: (candidate,)})

    decision = decide_reuse(need, catalog, matcher)

    assert isinstance(decision, Escalation)
    assert decision.check is EscalationCheck.METHOD_FIT
    assert "provides no method" in decision.detail
    assert "2 required capture(s)" in decision.detail


def test_method_fit_escalates_on_arity_mismatch_specifically() -> None:
    """A method exists, but its arity doesn't fit (1 param vs. 2 needed
    captures) -- still a gross, class-level incompatibility (no method of
    ANY arity here would accept a 2-argument call), not the finer
    specific-method case this coarse check cannot see."""
    page = _login_page(
        methods=(
            JavaMethod(
                name="enterUsername",
                parameters=(JavaParameter(name="username", java_type="String"),),
                return_type="void",
            ),
        )
    )
    catalog = _catalog_with_page(page)
    need = _login_need()
    candidate = MatchCandidate(
        asset_id=_LOGIN_PAGE_ASSET_ID, confidence=0.95, content_hash=_CURRENT_HASH
    )
    matcher = StubSemanticMatcher({need.text: (candidate,)})

    decision = decide_reuse(need, catalog, matcher)

    assert isinstance(decision, Escalation)
    assert decision.check is EscalationCheck.METHOD_FIT


def test_method_fit_escalates_on_type_mismatch_with_matching_arity() -> None:
    """Arity matches (2 params) but types don't (int, int vs. string,
    string needed) -- still gross class-level incompatibility."""
    page = _login_page(
        methods=(
            JavaMethod(
                name="selectQuantities",
                parameters=(
                    JavaParameter(name="a", java_type="int"),
                    JavaParameter(name="b", java_type="int"),
                ),
                return_type="void",
            ),
        )
    )
    catalog = _catalog_with_page(page)
    need = _login_need()
    candidate = MatchCandidate(
        asset_id=_LOGIN_PAGE_ASSET_ID, confidence=0.95, content_hash=_CURRENT_HASH
    )
    matcher = StubSemanticMatcher({need.text: (candidate,)})

    decision = decide_reuse(need, catalog, matcher)

    assert isinstance(decision, Escalation)
    assert decision.check is EscalationCheck.METHOD_FIT


# ---------------------------------------------------------------------------
# Coarse PASS: some shape-compatible method exists -> TRUSTED_REUSE
# ---------------------------------------------------------------------------


def test_method_fit_passes_when_a_shape_compatible_method_exists() -> None:
    """The page object has a method whose shape (2 String params) fits the
    step's 2 string captures -> the coarse screen passes, and (with
    confidence and hash also passing) the binding is trusted."""
    login_method = JavaMethod(
        name="loginAs",
        parameters=(
            JavaParameter(name="username", java_type="String"),
            JavaParameter(name="password", java_type="String"),
        ),
        return_type="void",
    )
    page = _login_page(methods=(login_method,))
    catalog = _catalog_with_page(page)
    need = _login_need()
    candidate = MatchCandidate(
        asset_id=_LOGIN_PAGE_ASSET_ID, confidence=0.95, content_hash=_CURRENT_HASH
    )
    matcher = StubSemanticMatcher({need.text: (candidate,)})

    decision = decide_reuse(need, catalog, matcher)

    assert isinstance(decision, TrustedReuse)
    assert decision.asset is page


def test_method_fit_does_not_require_the_matching_method_to_be_the_only_one() -> None:
    """A class with several methods, only one of which fits -> still
    passes (this screen only needs SOME method to fit, not ALL to fit)."""
    page = _login_page(
        methods=(
            JavaMethod(name="open", parameters=(), return_type="void"),
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
    catalog = _catalog_with_page(page)
    need = _login_need()
    candidate = MatchCandidate(
        asset_id=_LOGIN_PAGE_ASSET_ID, confidence=0.95, content_hash=_CURRENT_HASH
    )
    matcher = StubSemanticMatcher({need.text: (candidate,)})

    decision = decide_reuse(need, catalog, matcher)

    assert isinstance(decision, TrustedReuse)


# ---------------------------------------------------------------------------
# No-single-check-bypass, at the coarse level, for page objects
# ---------------------------------------------------------------------------


def test_page_object_method_fit_escalation_is_not_bypassed_by_good_confidence_and_hash() -> None:
    """Confidence high, content-hash current, method-fit alone fails ->
    still escalates. The page-object analogue of the step-definition
    no-bypass proof: no combination of the other two passing checks
    compensates for a class that structurally cannot satisfy the call."""
    page = _login_page(methods=(JavaMethod(name="open", parameters=(), return_type="void"),))
    catalog = _catalog_with_page(page)
    need = _login_need()
    candidate = MatchCandidate(
        asset_id=_LOGIN_PAGE_ASSET_ID, confidence=0.99, content_hash=_CURRENT_HASH
    )
    matcher = StubSemanticMatcher({need.text: (candidate,)})

    decision = decide_reuse(need, catalog, matcher)

    assert isinstance(decision, Escalation)
    assert decision.check is EscalationCheck.METHOD_FIT
    assert not isinstance(decision, TrustedReuse)


# ---------------------------------------------------------------------------
# Utilities: same coarse treatment
# ---------------------------------------------------------------------------


def test_utility_method_fit_escalates_when_no_compatible_method_exists() -> None:
    """A utility class gets the identical coarse screen a page object
    does: no zero-arg method on this config-reader-shaped utility, but the
    need has zero captures -> no method fits -> escalate. Proves utilities
    are not silently exempted from method-fit."""
    utility = UtilityAsset(
        asset_id="UTIL-configfixture01",
        class_name="com.automation.utils.ConfigReader",
        fields=(),
        methods=(
            JavaMethod(
                name="env",
                parameters=(JavaParameter(name="key", java_type="String"),),
                return_type="String",
            ),
        ),
        source_file="com/automation/utils/ConfigReader.java",
        content_hash=_CURRENT_HASH,
    )
    catalog = _catalog_with_utility(utility)
    need = GherkinStepNeed(text="I read the test data", step_type="Given", captures=())
    candidate = MatchCandidate(
        asset_id="UTIL-configfixture01", confidence=0.9, content_hash=_CURRENT_HASH
    )
    matcher = StubSemanticMatcher({need.text: (candidate,)})

    decision = decide_reuse(need, catalog, matcher)

    assert isinstance(decision, Escalation)
    assert decision.check is EscalationCheck.METHOD_FIT


def test_utility_method_fit_passes_when_a_zero_arg_method_exists() -> None:
    """The same utility, matched against a need with zero captures, but
    this time the class DOES provide a genuine zero-arg method -> passes."""
    utility = UtilityAsset(
        asset_id="UTIL-configfixture01",
        class_name="com.automation.utils.ConfigReader",
        fields=(),
        methods=(JavaMethod(name="reload", parameters=(), return_type="void"),),
        source_file="com/automation/utils/ConfigReader.java",
        content_hash=_CURRENT_HASH,
    )
    catalog = _catalog_with_utility(utility)
    need = GherkinStepNeed(text="I reload the configuration", step_type="Given", captures=())
    candidate = MatchCandidate(
        asset_id="UTIL-configfixture01", confidence=0.9, content_hash=_CURRENT_HASH
    )
    matcher = StubSemanticMatcher({need.text: (candidate,)})

    decision = decide_reuse(need, catalog, matcher)

    assert isinstance(decision, TrustedReuse)


# ---------------------------------------------------------------------------
# The generation-time CONTRACT: TrustedReuse carries the full method
# inventory, so the generator (not this engine) can perform the precise,
# specific-method check the coarse screen above cannot.
# ---------------------------------------------------------------------------


def test_trusted_reuse_for_a_page_object_carries_its_full_method_inventory() -> None:
    """The contract this coarse check depends on: a future generator,
    before actually calling a reused page object's method, must verify the
    SPECIFIC method it needs exists. It can only do that if `TrustedReuse`
    hands over the full method list -- proven here directly, by asset
    kind, independent of which method happened to satisfy the coarse
    screen above."""
    open_method = JavaMethod(name="open", parameters=(), return_type="void")
    login_method = JavaMethod(
        name="loginAs",
        parameters=(
            JavaParameter(name="username", java_type="String"),
            JavaParameter(name="password", java_type="String"),
        ),
        return_type="void",
    )
    page = _login_page(methods=(open_method, login_method))
    catalog = _catalog_with_page(page)
    need = _login_need()
    candidate = MatchCandidate(
        asset_id=_LOGIN_PAGE_ASSET_ID, confidence=0.95, content_hash=_CURRENT_HASH
    )
    matcher = StubSemanticMatcher({need.text: (candidate,)})

    decision = decide_reuse(need, catalog, matcher)

    assert isinstance(decision, TrustedReuse)
    # The generator's own obligation (models.TrustedReuse docstring): check
    # a SPECIFIC method name is present before calling it. This is what
    # makes that check possible -- the full inventory, names included.
    method_names = {m.name for m in decision.asset.methods}  # type: ignore[union-attr]
    assert method_names == {"open", "loginAs"}
    assert "clickForgotPasswordLink" not in method_names  # the method NOT present,
    # to make concrete what the generator's own presence-check would catch
    # that this coarse decision-time screen already passed regardless.


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


def test_method_fit_decision_is_deterministic() -> None:
    login_method = JavaMethod(
        name="loginAs",
        parameters=(
            JavaParameter(name="username", java_type="String"),
            JavaParameter(name="password", java_type="String"),
        ),
        return_type="void",
    )
    page = _login_page(methods=(login_method,))
    catalog = _catalog_with_page(page)
    need = _login_need()
    candidate = MatchCandidate(
        asset_id=_LOGIN_PAGE_ASSET_ID, confidence=0.95, content_hash=_CURRENT_HASH
    )
    matcher = StubSemanticMatcher({need.text: (candidate,)})

    decisions = [decide_reuse(need, catalog, matcher) for _ in range(5)]

    assert all(d == decisions[0] for d in decisions)
    assert isinstance(decisions[0], TrustedReuse)
