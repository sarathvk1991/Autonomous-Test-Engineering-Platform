"""CP4's own referential-grounding tally (ADR-0044 D10, finding #4) --
REPORT-ONLY, structurally separate from the four D6 gating criteria
(`test_automation_engineering_cp4_gate.py` proves those independently).

Proves, against the real, live `LOCATOR_CATALOG` (saucedemo) finding #1
already ships: a real catalog locator is tallied `grounded`; the exact
historical defect (`username` vs. the real `user-name`) is tallied
`hallucination`; the honest placeholder is tallied `placeholder`, never
punished as a hallucination; a hallucination NEVER changes
`overall_verdict`/`passed` (the report-only structural proof); and an
uncatalogued/empty catalog reports `NOT_APPLICABLE` (`applicable=False`),
never a fabricated verdict.
"""

from __future__ import annotations

import socket

import pytest

from automation_engineering.catalog.locator_catalog import LOCATOR_CATALOG
from automation_engineering.cp4.gate import evaluate_cp4
from automation_engineering.cp4.models import (
    GROUNDING_STATUS_GROUNDED,
    GROUNDING_STATUS_HALLUCINATION,
    GROUNDING_STATUS_PLACEHOLDER,
    Cp4PageObjectInput,
)
from shared.enums.base import ValidationVerdict

pytestmark = pytest.mark.unit

_SAUCEDEMO_CATALOG = LOCATOR_CATALOG["saucedemo"]

#: The real, catalog-exact locator (`user-name`) -- clean by every one of
#: CP4's four D6 structural criteria AND referentially grounded.
_GROUNDED_LOGIN_PAGE = """
package com.automation.pages;

import org.openqa.selenium.By;

public class LoginPage {
    private final By usernameField = By.id("user-name");
    private final By passwordField = By.id("password");
}
"""

#: The exact historical defect (`[[cap-page-object-defect1-method-name-
#: fix]]`): `By.id("username")` -- well-formed, unique, non-fragile, so it
#: PASSES all four D6 criteria, yet the real saucedemo field is `user-name`,
#: never `username`. This is finding #4's own confirmed example of what
#: the four structural criteria alone cannot see.
_HALLUCINATED_LOGIN_PAGE = """
package com.automation.pages;

import org.openqa.selenium.By;

public class LoginPage {
    private final By usernameField = By.id("username");
}
"""

#: The investigation's own fabricated example -- well-formed, unique,
#: non-dynamic-XPath (relative, no index/position, no auto-generated-id
#: shape) -- passes CP4's four structural criteria cleanly, yet references
#: nothing the real catalog knows about.
_FABRICATED_METHOD_LINE_COUNT_PAGE = """
package com.automation.pages;

import org.openqa.selenium.By;

public class CodebasePage {
    private final By methodLineCount = By.xpath("//div[@class='method-line-count']");
}
"""

#: The honest-placeholder output the platform's own generation prompt
#: emits on a genuine catalog miss (ADR-0044 D9) -- the CORRECT output,
#: never a defect.
_PLACEHOLDER_PAGE = """
package com.automation.pages;

import org.openqa.selenium.By;

public class DashboardPage {
    private final By logoutButton = By.cssSelector("TODO-locator-not-in-catalog");
}
"""


def _page(class_name: str, source: str) -> Cp4PageObjectInput:
    return Cp4PageObjectInput(class_name=class_name, java_source=source)


def test_a_real_catalog_locator_is_tallied_grounded() -> None:
    result = evaluate_cp4(
        (_page("com.automation.pages.LoginPage", _GROUNDED_LOGIN_PAGE),),
        locator_catalog=_SAUCEDEMO_CATALOG,
    )

    assert result.grounding.applicable is True
    assert len(result.grounding.grounded) == 2
    assert result.grounding.placeholders == ()
    assert result.grounding.hallucinations == ()
    assert {f.value for f in result.grounding.grounded} == {"user-name", "password"}
    assert all(f.status == GROUNDING_STATUS_GROUNDED for f in result.grounding.grounded)


def test_the_historical_defect_username_vs_user_name_is_tallied_hallucination() -> None:
    """The exact regression finding #1 fixed at generation time -- proven
    here at the CP4-detection layer: `username` is well-formed and unique
    (all four D6 criteria PASS), but the real field is `user-name`, so the
    grounding tally must flag it, distinctly from a structural failure."""
    result = evaluate_cp4(
        (_page("com.automation.pages.LoginPage", _HALLUCINATED_LOGIN_PAGE),),
        locator_catalog=_SAUCEDEMO_CATALOG,
    )

    assert result.overall_verdict == ValidationVerdict.PASS  # four D6 criteria see nothing wrong
    assert len(result.grounding.hallucinations) == 1
    hallucination = result.grounding.hallucinations[0]
    assert hallucination.value == "username"
    assert hallucination.status == GROUNDING_STATUS_HALLUCINATION
    assert result.grounding.grounded == ()
    assert result.grounding.placeholders == ()


def test_the_fabricated_investigation_example_passes_cp4_but_is_tallied_hallucination() -> None:
    """The exact case that motivated finding #4: `//div[@class='method-
    line-count']` is relative (not absolute), has no indexed/positional
    predicate, and is not auto-generated-id-shaped -- so it PASSES CP4's
    four D6 structural criteria cleanly, yet references nothing the real
    catalog knows about."""
    result = evaluate_cp4(
        (_page("com.automation.pages.CodebasePage", _FABRICATED_METHOD_LINE_COUNT_PAGE),),
        locator_catalog=_SAUCEDEMO_CATALOG,
    )

    for criterion in result.criteria:
        assert criterion.verdict == ValidationVerdict.PASS
    assert result.overall_verdict == ValidationVerdict.PASS
    assert result.passed is True

    assert len(result.grounding.hallucinations) == 1
    assert result.grounding.hallucinations[0].value == "//div[@class='method-line-count']"


def test_hallucination_is_reported_but_never_gates_report_only_structural_proof() -> None:
    """The load-bearing structural proof (mirrors CP7's own report/gate
    separation): a page object whose ONLY locator is a hallucination still
    passes CP4 overall, because `overall_verdict`/`passed` are computed
    from the four D6 criteria alone -- `grounding` never participates."""
    result = evaluate_cp4(
        (_page("com.automation.pages.LoginPage", _HALLUCINATED_LOGIN_PAGE),),
        locator_catalog=_SAUCEDEMO_CATALOG,
    )

    assert len(result.grounding.hallucinations) == 1  # flagged
    assert result.overall_verdict == ValidationVerdict.PASS  # never gated
    assert result.passed is True  # never blocks promotion (no PromotionBlockReason)


def test_honest_placeholder_is_tallied_placeholder_never_hallucination() -> None:
    """The placeholder tension the investigation surfaced: an honest
    catalog-miss placeholder is the CORRECT output, not a defect -- it must
    never be counted alongside a genuine hallucination."""
    result = evaluate_cp4(
        (_page("com.automation.pages.DashboardPage", _PLACEHOLDER_PAGE),),
        locator_catalog=_SAUCEDEMO_CATALOG,
    )

    assert len(result.grounding.placeholders) == 1
    assert result.grounding.placeholders[0].status == GROUNDING_STATUS_PLACEHOLDER
    assert result.grounding.hallucinations == ()
    assert result.overall_verdict == ValidationVerdict.PASS


def test_mixed_page_object_tallies_all_three_buckets_separately() -> None:
    source = """
    package com.automation.pages;
    import org.openqa.selenium.By;
    public class CheckoutPage {
        private final By firstName = By.id("first-name");
        private final By legacyField = By.id("username");
        private final By logoutButton = By.cssSelector("TODO-locator-not-in-catalog");
    }
    """
    result = evaluate_cp4(
        (_page("com.automation.pages.CheckoutPage", source),), locator_catalog=_SAUCEDEMO_CATALOG
    )

    assert len(result.grounding.grounded) == 1
    assert len(result.grounding.hallucinations) == 1
    assert len(result.grounding.placeholders) == 1
    statuses = {f.value: f.status for f in result.grounding.findings}
    assert statuses["first-name"] == GROUNDING_STATUS_GROUNDED
    assert statuses["username"] == GROUNDING_STATUS_HALLUCINATION
    assert statuses["TODO-locator-not-in-catalog"] == GROUNDING_STATUS_PLACEHOLDER


def test_no_catalog_supplied_reports_not_applicable_never_a_false_verdict() -> None:
    """The default -- no `locator_catalog` argument at all -- must never
    fabricate a grounded/hallucination verdict; mirrors `check_locator_
    grounding`'s own `NOT_APPLICABLE` posture for an empty catalog."""
    result = evaluate_cp4((_page("com.automation.pages.LoginPage", _HALLUCINATED_LOGIN_PAGE),))

    assert result.grounding.applicable is False
    assert result.grounding.findings == ()
    assert result.grounding.grounded == ()
    assert result.grounding.placeholders == ()
    assert result.grounding.hallucinations == ()
    # The four D6 criteria are computed exactly as before this parameter existed.
    assert result.overall_verdict == ValidationVerdict.PASS


def test_empty_catalog_tuple_explicitly_also_reports_not_applicable() -> None:
    result = evaluate_cp4(
        (_page("com.automation.pages.LoginPage", _HALLUCINATED_LOGIN_PAGE),), locator_catalog=()
    )

    assert result.grounding.applicable is False
    assert result.grounding.findings == ()


def test_empty_page_object_set_with_a_real_catalog_is_applicable_but_empty() -> None:
    result = evaluate_cp4((), locator_catalog=_SAUCEDEMO_CATALOG)

    assert result.grounding.applicable is True
    assert result.grounding.findings == ()


def test_grounding_never_adds_a_criterion_to_cp4_criteria() -> None:
    """The four D6-named criteria (`gate.py`'s own `CP4_CRITERIA`) are the
    ONLY entries in `result.criteria` -- grounding lives exclusively on the
    separate `result.grounding` field, never folded into this tuple."""
    result = evaluate_cp4(
        (_page("com.automation.pages.LoginPage", _HALLUCINATED_LOGIN_PAGE),),
        locator_catalog=_SAUCEDEMO_CATALOG,
    )

    assert len(result.criteria) == 4
    assert {c.criterion for c in result.criteria} == {
        "locator_uniqueness",
        "duplicate_locators",
        "dynamic_xpath",
        "well_formedness",
    }


def test_evaluate_cp4_grounding_is_deterministic() -> None:
    page_objects = (_page("com.automation.pages.LoginPage", _HALLUCINATED_LOGIN_PAGE),)
    assert evaluate_cp4(page_objects, locator_catalog=_SAUCEDEMO_CATALOG) == evaluate_cp4(
        page_objects, locator_catalog=_SAUCEDEMO_CATALOG
    )


def test_grounding_makes_no_network_call(monkeypatch: pytest.MonkeyPatch) -> None:
    """Static-catalog only (ADR-0044 D6/D9): patch `socket.socket` to raise
    if grounding classification ever tries to open one."""

    def _forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("CP4 grounding attempted to open a network socket")

    monkeypatch.setattr(socket, "socket", _forbidden)
    result = evaluate_cp4(
        (_page("com.automation.pages.LoginPage", _GROUNDED_LOGIN_PAGE),),
        locator_catalog=_SAUCEDEMO_CATALOG,
    )

    assert result.grounding.applicable is True
