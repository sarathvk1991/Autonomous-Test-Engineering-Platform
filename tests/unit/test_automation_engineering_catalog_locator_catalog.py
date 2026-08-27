"""DOM-grounding locator catalog (`automation_engineering.catalog
.locator_catalog`) -- the finding #1 fix: real, verified selectors fed into
`generate_page_objects` as static grounding input, target-keyed (multi-SUT
structure, saucedemo populated today), never a live scrape (ADR-0044 D6).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from automation_engineering.catalog.locator_catalog import (
    DEFAULT_BASELINE_ROOT,
    LOCATOR_CATALOG,
    LOCATOR_PLACEHOLDER_STRATEGY,
    LOCATOR_PLACEHOLDER_VALUE,
    LOCATOR_STRATEGIES,
    LocatorCatalogEntry,
    read_base_url,
    resolve_locator_catalog,
    resolve_target_from_base_url,
)

pytestmark = pytest.mark.unit


class TestCatalogStructure:
    def test_saucedemo_is_one_target_among_a_target_keyed_mapping(self) -> None:
        """Multi-SUT structure (the decision): the catalog is keyed by
        TARGET, not hardcoded to one SUT -- saucedemo is the only populated
        entry today, but the mapping shape accommodates a second target's
        own catalog with no code change."""
        assert isinstance(LOCATOR_CATALOG, dict)
        assert "saucedemo" in LOCATOR_CATALOG
        assert all(isinstance(entries, tuple) for entries in LOCATOR_CATALOG.values())

    def test_every_saucedemo_entry_uses_a_real_strategy(self) -> None:
        for entry in LOCATOR_CATALOG["saucedemo"]:
            assert entry.strategy in LOCATOR_STRATEGIES

    def test_saucedemo_catalog_covers_login_inventory_cart_checkout(self) -> None:
        """Coverage check against the real vendored set -- login, inventory,
        cart, and checkout selectors are all present (the SUT surface the
        real, live 15 kept SUT requirements need)."""
        values = {entry.value for entry in LOCATOR_CATALOG["saucedemo"]}
        assert "user-name" in values  # login
        assert "[data-test='product-sort-container']" in values  # inventory
        assert ".shopping_cart_badge" in values  # cart
        assert "postal-code" in values  # checkout
        assert "[data-test='finish']" in values  # checkout overview

    def test_no_locator_value_is_empty(self) -> None:
        for entries in LOCATOR_CATALOG.values():
            for entry in entries:
                assert entry.value.strip()
                assert entry.element.strip()

    def test_an_uncatalogued_target_is_a_genuine_miss_not_present(self) -> None:
        assert "some-other-sut" not in LOCATOR_CATALOG


class TestPlaceholderPolicy:
    def test_placeholder_is_valid_compileable_java_shape(self) -> None:
        """The honest-placeholder decision: a catalog miss is never a
        guess. `strategy` stays a real `By.*` factory name so the emitted
        field still compiles."""
        assert LOCATOR_PLACEHOLDER_STRATEGY in LOCATOR_STRATEGIES

    def test_placeholder_value_names_itself_honestly(self) -> None:
        assert "TODO" in LOCATOR_PLACEHOLDER_VALUE
        assert "not-in-catalog" in LOCATOR_PLACEHOLDER_VALUE
        # Never collides with a real catalog value.
        for entries in LOCATOR_CATALOG.values():
            assert LOCATOR_PLACEHOLDER_VALUE not in {entry.value for entry in entries}


class TestResolveTargetFromBaseUrl:
    def test_saucedemo_url_resolves_to_saucedemo(self) -> None:
        assert resolve_target_from_base_url("https://www.saucedemo.com") == "saucedemo"

    def test_strips_www_and_scheme_and_path(self) -> None:
        assert resolve_target_from_base_url("http://saucedemo.com/inventory.html") == "saucedemo"

    def test_unparseable_url_returns_none(self) -> None:
        assert resolve_target_from_base_url("not a url") is None

    def test_empty_string_returns_none(self) -> None:
        assert resolve_target_from_base_url("") is None


class TestReadBaseUrl:
    def test_reads_the_real_tracked_baseline_config(self) -> None:
        """Grounded against the real, currently-tracked
        `test-suite-baseline/src/test/resources/config.properties` -- not a
        fixture. Confirms the resolution mechanism actually works against
        this platform's own real artifact."""
        assert read_base_url() == "https://www.saucedemo.com"

    def test_missing_baseline_root_returns_none(self, tmp_path: Path) -> None:
        assert read_base_url(tmp_path / "does-not-exist") is None

    def test_missing_key_returns_none(self, tmp_path: Path) -> None:
        config = tmp_path / "src" / "test" / "resources"
        config.mkdir(parents=True)
        (config / "config.properties").write_text("env.browser=chrome\n", encoding="utf-8")
        assert read_base_url(tmp_path) is None

    def test_ignores_comments_and_blank_lines(self, tmp_path: Path) -> None:
        config = tmp_path / "src" / "test" / "resources"
        config.mkdir(parents=True)
        (config / "config.properties").write_text(
            "# a comment\n\nenv.base.url=https://example.com\n", encoding="utf-8"
        )
        assert read_base_url(tmp_path) == "https://example.com"


class TestResolveLocatorCatalog:
    def test_resolves_the_real_saucedemo_catalog_end_to_end(self) -> None:
        """The real, currently-tracked baseline's own `env.base.url`
        resolves all the way through to the real, populated catalog."""
        catalog = resolve_locator_catalog()
        assert catalog == LOCATOR_CATALOG["saucedemo"]
        assert len(catalog) > 0

    def test_uses_default_baseline_root_by_default(self) -> None:
        assert resolve_locator_catalog() == resolve_locator_catalog(DEFAULT_BASELINE_ROOT)

    def test_an_uncatalogued_target_falls_back_to_an_empty_catalog(self, tmp_path: Path) -> None:
        """Multi-SUT structure's own honest fallback: a real, resolvable
        base URL for a SUT with no curated catalog yields `()`, never an
        error and never someone else's catalog."""
        config = tmp_path / "src" / "test" / "resources"
        config.mkdir(parents=True)
        (config / "config.properties").write_text(
            "env.base.url=https://www.example-shop.com\n", encoding="utf-8"
        )
        assert resolve_locator_catalog(tmp_path) == ()

    def test_a_missing_config_file_falls_back_to_an_empty_catalog(self, tmp_path: Path) -> None:
        assert resolve_locator_catalog(tmp_path / "nonexistent") == ()

    def test_never_raises_on_any_malformed_input(self, tmp_path: Path) -> None:
        config = tmp_path / "src" / "test" / "resources"
        config.mkdir(parents=True)
        (config / "config.properties").write_text("env.base.url=\n", encoding="utf-8")
        assert resolve_locator_catalog(tmp_path) == ()


class TestLocatorCatalogEntry:
    def test_is_frozen_and_hashable(self) -> None:
        entry = LocatorCatalogEntry(element="x", strategy="id", value="y")
        assert hash(entry) is not None
        with pytest.raises(AttributeError):
            entry.value = "z"  # type: ignore[misc]
