"""DOM-grounding for page-object locator generation (ADR-0044 additive
note) -- a static, TARGET-keyed catalog of REAL, verified Selenium
selectors, fed into ``generate_page_objects`` as additional grounding
input, exactly the way ``customqa_constraints`` already is
(:mod:`.page_object_orchestrator`'s own precedent).

**The finding this closes.** The quality investigation confirmed the
page-object generation prompt receives ONLY a natural-language
``action_text`` per method, with zero DOM/HTML/element-map input -- the
model invents a plausible-looking ``By.id``/``By.cssSelector``/``By.xpath``
value from that text alone. Measured hallucinations against the real,
live saucedemo.com DOM: ``By.id("username")`` (real: ``user-name``),
``By.id("error-message")`` (real: ``[data-test='error']``),
``By.id("cart-count")`` (real: ``.shopping_cart_badge``).

**Where the real values come from.** Vendored, by hand, from the sibling
``Automation POC Project/`` repository's own hand-authored, real page
objects (``LoginPage``/``InventoryPage``/``CartPage``/``CheckoutPage``/
``CheckoutOverviewPage``) -- curated STATIC data, never a live scrape
(ADR-0044 D6 forbids Layer 3 any running-browser/SUT dependency at all;
a live fetch of saucedemo.com at generation time would violate that
Decision directly). This is Source B from the finding's own surfacing:
a curated catalog derived from Source A's real content, not Source A
itself (which lives outside this repository and is never read at
generation time).

**Coverage is real but partial, and that is recorded, not hidden.** The
sibling repo itself has no locator for "remove item from cart",
"cancel checkout", or "logout" -- ``DashboardPage`` is explicitly a
stub there. An uncatalogued element is a genuine catalog miss, handled
by :data:`LOCATOR_PLACEHOLDER_ENTRY` (the honest-placeholder policy,
never a guessed selector) -- never silently backfilled with an invented
value here.

**Multi-SUT structure, saucedemo populated.** :data:`LOCATOR_CATALOG` is
keyed by TARGET (a normalized hostname label, e.g. ``"saucedemo"``), not
hardcoded to one SUT -- ``saucedemo`` is the only entry today because it
is this platform's only real target, but the structure accommodates a
second target's own catalog without any code change, only a new entry.
An uncatalogued target (no entry in :data:`LOCATOR_CATALOG`) resolves to
an empty catalog -- generation for that SUT falls back entirely to
honest placeholders, exactly the same posture as an uncatalogued element
within a known target.

**Freeze-clean (ADR-0044).** This module is Layer 3-internal static
reference data, structurally identical to ``customqa_constraints``
(:data:`~.page_object_orchestrator.DEFAULT_CUSTOMQA_PAGE_OBJECT_CONSTRAINTS`)
and ``.gherkin-lintrc`` -- it is never part of the Layer 2 -> Layer 3
handoff ADR-0044 D1 locks, and it never touches a live SUT/browser, so
D6's "no running-browser or SUT dependency at all" is honored, not
redesigned. No ADR-0044 Decision (D1-D8) is redesigned by this module.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

#: Mirrors `feature_engineering.stage.workspace.DEFAULT_BASELINE_ROOT`'s own
#: value -- NOT imported from there (Layer 3 does not import Layer 2's own
#: internal modules, ADR-0044 D1's boundary), a duplicated literal of the
#: same well-known, ADR-0037-fixed tracked-baseline path every layer already
#: treats as a shared constant.
DEFAULT_BASELINE_ROOT = Path("test-suite-baseline")

_CONFIG_RELATIVE_PATH = Path("src/test/resources/config.properties")

#: The `.properties` key ADR-0037 D3 locks for the SUT's own base URL --
#: `env.base.url`, `env.`-namespaced (environment binding, never test data).
_BASE_URL_KEY = "env.base.url"

#: The Selenium `By.*` static-factory strategy names this catalog (and the
#: governed prompt) ever names -- the same vocabulary
#: `generate_page_objects` has always used.
LOCATOR_STRATEGIES: tuple[str, ...] = ("id", "cssSelector", "xpath", "className", "name")


@dataclass(frozen=True, slots=True)
class LocatorCatalogEntry:
    """One REAL, verified selector for one named element on one target SUT.

    ``element`` is a plain-English description (matched by the model's own
    semantic judgement against a method's ``action_text``, mirroring
    ADR-0044 D3's own "semantic, not exact-string" matching philosophy) --
    never a machine key the model would have to guess correctly. ``strategy``
    is one of :data:`LOCATOR_STRATEGIES`; ``value`` is the exact selector
    string to use VERBATIM.
    """

    element: str
    strategy: str
    value: str


#: The honest-placeholder policy (the decision: NEVER a guessed selector on
#: a catalog miss). `strategy="cssSelector"` keeps the emitted Java
#: compileable (a real `By.cssSelector(...)` call); `value` is deliberately
#: not a plausible-looking real selector -- its own text names exactly what
#: it is, so a reviewer (or a property check, `eval_harness.
#: page_object_properties.check_locator_grounding`) can never mistake it for
#: a verified value.
LOCATOR_PLACEHOLDER_STRATEGY = "cssSelector"
LOCATOR_PLACEHOLDER_VALUE = "TODO-locator-not-in-catalog"

#: Vendored from the sibling `Automation POC Project/` repository's own
#: real, hand-authored page objects (`src/test/java/com/automation/pages/
#: {Login,Inventory,Cart,Checkout,CheckoutOverview}Page.java`) -- checked
#: directly, not from memory, during the finding's own surfacing. Covers
#: login, inventory browse/sort, cart, and checkout -- the SUT surface the
#: platform's own real, live 15 kept (post-#2-filter) SUT requirements
#: actually need. Does NOT cover remove-from-cart, cancel-checkout, or
#: logout -- the sibling repo has no locator for these either
#: (`CartPage` has no remove button; `DashboardPage` is an explicit stub) --
#: a genuine, recorded gap, not an oversight; those elements are honest
#: catalog misses today.
LOCATOR_CATALOG: Mapping[str, tuple[LocatorCatalogEntry, ...]] = {
    "saucedemo": (
        LocatorCatalogEntry("username input field on the login page", "id", "user-name"),
        LocatorCatalogEntry("password input field on the login page", "id", "password"),
        LocatorCatalogEntry("login submit button on the login page", "id", "login-button"),
        LocatorCatalogEntry(
            "login or checkout form error message banner", "cssSelector", "[data-test='error']"
        ),
        LocatorCatalogEntry("login page heading/logo", "cssSelector", ".login_logo"),
        LocatorCatalogEntry(
            "inventory product list container", "cssSelector", ".inventory_list"
        ),
        LocatorCatalogEntry(
            "inventory sort-order dropdown",
            "cssSelector",
            "[data-test='product-sort-container']",
        ),
        LocatorCatalogEntry(
            "inventory item name text (also used for a cart item's own product "
            "name)",
            "cssSelector",
            ".inventory_item_name",
        ),
        LocatorCatalogEntry("inventory item price text", "cssSelector", ".inventory_item_price"),
        LocatorCatalogEntry(
            "page title heading (shared markup across every saucedemo page)",
            "cssSelector",
            "span.title",
        ),
        LocatorCatalogEntry(
            "shopping cart icon/link in the page header",
            "cssSelector",
            "[data-test='shopping-cart-link']",
        ),
        LocatorCatalogEntry(
            "shopping cart item-count badge", "cssSelector", ".shopping_cart_badge"
        ),
        LocatorCatalogEntry("cart page's individual cart item row", "cssSelector", ".cart_item"),
        LocatorCatalogEntry(
            "checkout button on the cart page", "cssSelector", "[data-test='checkout']"
        ),
        LocatorCatalogEntry(
            "first name field on the checkout information page", "id", "first-name"
        ),
        LocatorCatalogEntry(
            "last name field on the checkout information page", "id", "last-name"
        ),
        LocatorCatalogEntry(
            "postal or zip code field on the checkout information page", "id", "postal-code"
        ),
        LocatorCatalogEntry(
            "continue button on the checkout information page",
            "cssSelector",
            "[data-test='continue']",
        ),
        LocatorCatalogEntry(
            "order total label on the checkout overview page",
            "cssSelector",
            ".summary_total_label",
        ),
        LocatorCatalogEntry(
            "finish button on the checkout overview page", "cssSelector", "[data-test='finish']"
        ),
        LocatorCatalogEntry(
            "order confirmation success header", "cssSelector", ".complete-header"
        ),
    ),
}


def read_base_url(baseline_root: Path = DEFAULT_BASELINE_ROOT) -> str | None:
    """The tracked baseline's own `env.base.url` (ADR-0037 D3) -- the SAME
    static, checked-in `config.properties` every run's workspace already
    materializes unchanged (ADR-0037 Path A). Read here, not by any live
    request: this is a static-file read, never a network call (ADR-0044
    D6). Returns `None` (never raises) when the file, or the key, is
    missing -- an honest "no SUT identity known," handled the same as any
    other catalog miss."""
    config_path = baseline_root / _CONFIG_RELATIVE_PATH
    if not config_path.exists():
        return None
    for line in config_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        if key.strip() == _BASE_URL_KEY:
            resolved = value.strip()
            return resolved or None
    return None


def resolve_target_from_base_url(base_url: str) -> str | None:
    """Normalizes a base URL to a catalog TARGET key: the hostname's first
    label, lowercased, `www.` stripped -- `"https://www.saucedemo.com"` ->
    `"saucedemo"`. Returns `None` for a URL with no parseable hostname."""
    hostname = urlparse(base_url).hostname
    if not hostname:
        return None
    hostname = hostname.lower()
    if hostname.startswith("www."):
        hostname = hostname[len("www.") :]
    label = hostname.split(".")[0]
    return label or None


def resolve_locator_catalog(
    baseline_root: Path = DEFAULT_BASELINE_ROOT,
) -> tuple[LocatorCatalogEntry, ...]:
    """The active target's own catalog, resolved end-to-end from the tracked
    baseline's `env.base.url` -- `()` (never a raised exception) whenever
    the base URL is unreadable, unparseable, or names a target with no
    curated catalog: an uncatalogued SUT falls back entirely to honest
    placeholders, the same as an uncatalogued element within a known
    target."""
    base_url = read_base_url(baseline_root)
    if base_url is None:
        return ()
    target = resolve_target_from_base_url(base_url)
    if target is None:
        return ()
    return LOCATOR_CATALOG.get(target, ())


__all__ = [
    "DEFAULT_BASELINE_ROOT",
    "LOCATOR_CATALOG",
    "LOCATOR_PLACEHOLDER_STRATEGY",
    "LOCATOR_PLACEHOLDER_VALUE",
    "LOCATOR_STRATEGIES",
    "LocatorCatalogEntry",
    "read_base_url",
    "resolve_locator_catalog",
    "resolve_target_from_base_url",
]
