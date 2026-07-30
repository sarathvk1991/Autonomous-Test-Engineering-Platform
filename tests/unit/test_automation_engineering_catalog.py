"""Layer 3 asset catalog + run-start reconciliation (ADR-0044 D3).

Proves, deterministically and without any LLM call: scanning the real
tracked baseline produces the expected first catalog entries; a fixture
step-definition/page-object's identity (content-hash, signature) is
extracted accurately; reconciliation reflects current code (a content
change is picked up, a no-op rescan is byte-identical); content-hash is
stable across repeated scans and sensitive to real changes; an
asset-free baseline reconciles to an empty catalog, not an error; and a
file javalang's grammar cannot parse is skipped, recorded, and never
crashes the rest of the scan.

Builds ONLY the catalog and its reconciliation (ADR-0044 D3) -- no
semantic matching, no reuse-safety checks (ADR-0044 D4), no generators, no
CP3/CP4, no promotion (ADR-0045). Those are later work; this module's
:func:`reconcile`/:class:`AssetCatalog` are the interface they will call.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from automation_engineering.catalog import (
    AssetCatalog,
    AssetKind,
    reconcile,
)
from automation_engineering.catalog.scanner import JAVA_SOURCE_SUBPATH

pytestmark = pytest.mark.unit

_REAL_BASELINE_ROOT = Path("test-suite-baseline")


def _write_java(root: Path, relative_path: str, content: str) -> Path:
    java_root = root / JAVA_SOURCE_SUBPATH
    file_path = java_root / relative_path
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(textwrap.dedent(content), encoding="utf-8")
    return file_path


_FIXTURE_STEP_CLASS = """\
    package com.automation.steps;

    import io.cucumber.java.en.Given;
    import io.cucumber.java.en.When;

    /** Fixture login step definitions. */
    public class LoginSteps {

        @Given("I am on the login page")
        public void iAmOnTheLoginPage() {
            // no-op fixture body
        }

        @When("I log in as {string} with password {string}")
        public void iLogInAsWithPassword(String username, String password) {
            // no-op fixture body
        }
    }
"""

_FIXTURE_PAGE_OBJECT = """\
    package com.automation.pages;

    import com.automation.base.BasePage;
    import org.openqa.selenium.By;
    import org.openqa.selenium.WebDriver;

    /** Fixture login page -- proves locator field extraction. */
    public class LoginPage extends BasePage {

        private final By usernameField = By.id("user-name");
        private final By loginButton = By.id("login-button");

        public LoginPage(WebDriver driver) {
            super(driver);
        }

        public void login(String username, String password) {
            open("/login");
        }
    }
"""


class TestRealTrackedBaseline:
    """Scans the ACTUAL walking-skeleton tracked baseline -- the real first
    catalog entries (no fixtures)."""

    def test_smoke_steps_are_catalogued(self) -> None:
        catalog = reconcile(_REAL_BASELINE_ROOT)

        assert len(catalog.step_definitions) == 2
        by_method = {s.method_name: s for s in catalog.step_definitions}
        given = by_method["iOpenTheApplicationUnderTest"]
        assert given.class_name == "com.automation.steps.SmokeSteps"
        assert given.step_type == "Given"
        assert given.pattern == "I open the application under test"
        assert given.parameters == ()
        assert given.return_type == "void"
        assert given.kind is AssetKind.STEP_DEFINITION

        then = by_method["thePageTitleIsNotEmpty"]
        assert then.step_type == "Then"
        assert then.pattern == "the page title is not empty"

    def test_smoke_page_is_catalogued_as_page_object(self) -> None:
        catalog = reconcile(_REAL_BASELINE_ROOT)

        assert len(catalog.page_objects) == 1
        smoke_page = catalog.page_objects[0]
        assert smoke_page.class_name == "com.automation.pages.SmokePage"
        assert smoke_page.extends == "BasePage"
        assert smoke_page.kind is AssetKind.PAGE_OBJECT
        method_names = {m.name for m in smoke_page.methods}
        assert method_names == {"openApplicationUnderTest"}

    def test_framework_and_runner_packages_are_excluded(self) -> None:
        catalog = reconcile(_REAL_BASELINE_ROOT)

        all_classes = {a.class_name for a in catalog.all_assets()}
        assert "com.automation.base.BasePage" not in all_classes
        assert "com.automation.base.ConfigReader" not in all_classes
        assert "com.automation.base.DriverFactory" not in all_classes
        assert "com.automation.base.Hooks" not in all_classes
        assert "com.automation.runners.RunCucumberTest" not in all_classes
        assert catalog.utilities == ()

    def test_driver_factory_switch_expression_never_reaches_the_parser(self) -> None:
        """DriverFactory.java uses a Java 14+ switch expression javalang's
        grammar cannot parse -- confirmed directly. It must never surface as
        an ``unparsed_files`` entry, because the path-based package filter
        excludes `com.automation.base` before any parse is attempted."""
        catalog = reconcile(_REAL_BASELINE_ROOT)

        assert catalog.unparsed_files == ()

    def test_content_hash_and_asset_id_are_present_and_distinct_concepts(self) -> None:
        catalog = reconcile(_REAL_BASELINE_ROOT)

        for asset in catalog.all_assets():
            assert len(asset.content_hash) == 64  # full sha256 hex digest
            assert asset.asset_id.startswith(("STEP-", "PAGE-", "UTIL-"))


class TestFixtureIdentityExtraction:
    """A fixture Java step-definition class / page object -> the catalog
    records its identity (content-hash, signature, Gherkin binding)
    accurately -- proven against source we wrote ourselves, so the expected
    values are known exactly."""

    def test_step_definition_pattern_and_parameters_extracted_accurately(
        self, tmp_path: Path
    ) -> None:
        _write_java(tmp_path, "com/automation/steps/LoginSteps.java", _FIXTURE_STEP_CLASS)

        catalog = reconcile(tmp_path)

        assert len(catalog.step_definitions) == 2
        by_method = {s.method_name: s for s in catalog.step_definitions}

        given = by_method["iAmOnTheLoginPage"]
        assert given.pattern == "I am on the login page"
        assert given.parameters == ()
        assert given.class_name == "com.automation.steps.LoginSteps"

        when = by_method["iLogInAsWithPassword"]
        assert when.pattern == "I log in as {string} with password {string}"
        assert [p.java_type for p in when.parameters] == ["String", "String"]
        assert [p.name for p in when.parameters] == ["username", "password"]
        assert when.step_type == "When"

    def test_step_definition_semantic_tags_derived_from_pattern(self) -> None:
        catalog_dir_assets = reconcile(_REAL_BASELINE_ROOT).step_definitions
        given = next(
            s for s in catalog_dir_assets if s.method_name == "iOpenTheApplicationUnderTest"
        )
        # Derived purely from the Cucumber pattern text -- no authored metadata.
        assert set(given.semantic_tags) >= {"open", "application", "under", "test"}

    def test_content_hash_matches_the_exact_extracted_source(self, tmp_path: Path) -> None:
        _write_java(tmp_path, "com/automation/steps/LoginSteps.java", _FIXTURE_STEP_CLASS)
        catalog = reconcile(tmp_path)

        given = next(s for s in catalog.step_definitions if s.method_name == "iAmOnTheLoginPage")
        # Recompute the hash independently over the known fixture text and
        # confirm it matches -- proves the extracted span is exactly the
        # annotation-through-closing-brace region, nothing more or less.
        import hashlib

        expected_span = (
            '@Given("I am on the login page")\n'
            "    public void iAmOnTheLoginPage() {\n"
            "        // no-op fixture body\n"
            "    }"
        )
        assert hashlib.sha256(expected_span.encode("utf-8")).hexdigest() == given.content_hash

    def test_page_object_locator_fields_are_extracted(self, tmp_path: Path) -> None:
        _write_java(tmp_path, "com/automation/pages/LoginPage.java", _FIXTURE_PAGE_OBJECT)

        catalog = reconcile(tmp_path)

        assert len(catalog.page_objects) == 1
        login_page = catalog.page_objects[0]
        assert login_page.extends == "BasePage"
        assert {f.name for f in login_page.locators} == {"usernameField", "loginButton"}
        assert all(f.java_type == "By" for f in login_page.locators)
        assert {m.name for m in login_page.methods} == {"login"}

    def test_page_object_javadoc_contributes_semantic_tags(self, tmp_path: Path) -> None:
        _write_java(tmp_path, "com/automation/pages/LoginPage.java", _FIXTURE_PAGE_OBJECT)
        catalog = reconcile(tmp_path)

        login_page = catalog.page_objects[0]
        assert "fixture" in login_page.semantic_tags
        assert "login" in login_page.semantic_tags


class TestAssetIdentityStability:
    """``asset_id`` (stable identity) vs. ``content_hash`` (content
    fingerprint) -- ADR-0044 D4(b)'s staleness check needs both distinct."""

    def test_asset_id_is_stable_across_content_edits(self, tmp_path: Path) -> None:
        _write_java(tmp_path, "com/automation/steps/LoginSteps.java", _FIXTURE_STEP_CLASS)
        before = reconcile(tmp_path)
        before_asset = next(
            s for s in before.step_definitions if s.method_name == "iAmOnTheLoginPage"
        )

        edited = _FIXTURE_STEP_CLASS.replace("// no-op fixture body", "// EDITED fixture body")
        _write_java(tmp_path, "com/automation/steps/LoginSteps.java", edited)
        after = reconcile(tmp_path)
        after_asset = next(
            s for s in after.step_definitions if s.method_name == "iAmOnTheLoginPage"
        )

        assert before_asset.asset_id == after_asset.asset_id
        assert before_asset.content_hash != after_asset.content_hash

    def test_content_hash_is_stable_across_repeated_scans_of_unchanged_code(
        self, tmp_path: Path
    ) -> None:
        _write_java(tmp_path, "com/automation/steps/LoginSteps.java", _FIXTURE_STEP_CLASS)

        first = reconcile(tmp_path)
        second = reconcile(tmp_path)

        assert first == second
        first_hashes = {s.method_name: s.content_hash for s in first.step_definitions}
        second_hashes = {s.method_name: s.content_hash for s in second.step_definitions}
        assert first_hashes == second_hashes

    def test_content_hash_is_sensitive_to_a_real_change(self, tmp_path: Path) -> None:
        _write_java(tmp_path, "com/automation/steps/LoginSteps.java", _FIXTURE_STEP_CLASS)
        before = reconcile(tmp_path)

        changed_pattern = _FIXTURE_STEP_CLASS.replace(
            "I am on the login page", "I am on the sign-in page"
        )
        _write_java(tmp_path, "com/automation/steps/LoginSteps.java", changed_pattern)
        after = reconcile(tmp_path)

        before_asset = next(
            s for s in before.step_definitions if s.method_name == "iAmOnTheLoginPage"
        )
        after_asset = next(
            s for s in after.step_definitions if s.method_name == "iAmOnTheLoginPage"
        )
        assert before_asset.content_hash != after_asset.content_hash
        assert after_asset.pattern == "I am on the sign-in page"


class TestReconciliationIsFresh:
    """ADR-0044 D3: the catalog is rebuilt from a fresh scan every time --
    it is never a stale index of what the code used to be."""

    def test_unchanged_source_reconciles_identically(self, tmp_path: Path) -> None:
        _write_java(tmp_path, "com/automation/pages/LoginPage.java", _FIXTURE_PAGE_OBJECT)

        first = reconcile(tmp_path)
        second = reconcile(tmp_path)

        assert first == second

    def test_changed_source_reconciles_to_a_different_catalog(self, tmp_path: Path) -> None:
        _write_java(tmp_path, "com/automation/pages/LoginPage.java", _FIXTURE_PAGE_OBJECT)
        before = reconcile(tmp_path)

        added_field = _FIXTURE_PAGE_OBJECT.replace(
            'private final By loginButton = By.id("login-button");',
            'private final By loginButton = By.id("login-button");\n'
            '    private final By errorBanner = By.id("error-banner");',
        )
        _write_java(tmp_path, "com/automation/pages/LoginPage.java", added_field)
        after = reconcile(tmp_path)

        assert before != after
        before_page = before.page_objects[0]
        after_page = after.page_objects[0]
        assert before_page.content_hash != after_page.content_hash
        # Identity (asset_id, keyed on class name only) is unaffected by a
        # field addition -- the same class is still the same catalog entry.
        assert before_page.asset_id == after_page.asset_id
        assert {f.name for f in after_page.locators} == {
            "usernameField",
            "loginButton",
            "errorBanner",
        }


class TestCatalogLocationDecision:
    """Proves the storage-location resolution: the catalog is a derived
    index, not a separately persisted authoritative store. A JSON snapshot
    may exist for inspection, but reconciliation never reads it back, and
    deleting it changes nothing about the next reconciliation's output."""

    def test_snapshot_round_trips_byte_for_byte(self, tmp_path: Path) -> None:
        _write_java(tmp_path, "com/automation/pages/LoginPage.java", _FIXTURE_PAGE_OBJECT)
        catalog = reconcile(tmp_path)

        snapshot_path = tmp_path / "asset_catalog.json"
        snapshot_path.write_text(catalog.to_json(), encoding="utf-8")
        restored = AssetCatalog.from_json(snapshot_path.read_text(encoding="utf-8"))

        assert restored == catalog

    def test_deleting_the_snapshot_never_affects_the_next_reconciliation(
        self, tmp_path: Path
    ) -> None:
        _write_java(tmp_path, "com/automation/pages/LoginPage.java", _FIXTURE_PAGE_OBJECT)
        catalog = reconcile(tmp_path)

        snapshot_path = tmp_path / "asset_catalog.json"
        snapshot_path.write_text(catalog.to_json(), encoding="utf-8")
        snapshot_path.unlink()

        rescanned = reconcile(tmp_path)
        assert rescanned == catalog

    def test_promotion_can_reuse_the_same_content_hash_identity_lookup(
        self, tmp_path: Path
    ) -> None:
        """ADR-0045 D2(b) reuses this exact lookup as its promotion-time
        anti-duplicate check -- proven here at the catalog level, not
        re-implemented."""
        _write_java(tmp_path, "com/automation/pages/LoginPage.java", _FIXTURE_PAGE_OBJECT)
        catalog = reconcile(tmp_path)
        login_page = catalog.page_objects[0]

        found = catalog.by_content_hash(login_page.content_hash)
        assert found == (login_page,)
        assert catalog.by_content_hash("0" * 64) == ()


class TestEmptyBaseline:
    """ADR-0044 D5: an empty/asset-free baseline is the correct bootstrap
    case -- 0% reuse because there is nothing yet to reuse, not an error."""

    def test_baseline_with_no_java_source_reconciles_to_an_empty_catalog(
        self, tmp_path: Path
    ) -> None:
        catalog = reconcile(tmp_path)

        assert catalog.step_definitions == ()
        assert catalog.page_objects == ()
        assert catalog.utilities == ()
        assert catalog.unparsed_files == ()
        assert catalog.all_assets() == ()

    def test_baseline_with_only_excluded_packages_reconciles_to_an_empty_catalog(
        self, tmp_path: Path
    ) -> None:
        _write_java(
            tmp_path,
            "com/automation/base/BasePage.java",
            """\
            package com.automation.base;

            public abstract class BasePage {
                protected BasePage() {
                }
            }
            """,
        )

        catalog = reconcile(tmp_path)

        assert catalog.all_assets() == ()


class TestUnparsableFileIsSkippedNotFatal:
    """A file javalang's grammar cannot parse is skipped and recorded, and
    never crashes the rest of the scan -- the same real limitation observed
    against `DriverFactory.java`, reproduced here in a package that IS in
    scope, so it must surface on ``unparsed_files`` rather than being
    silently excluded."""

    _SWITCH_EXPRESSION_UTILITY = """\
        package com.automation.utils;

        public final class BrowserPicker {
            public static String pick(String name) {
                return switch (name) {
                    case "chrome" -> "chrome-driver";
                    default -> "unknown";
                };
            }
        }
    """

    def test_unparsable_file_is_recorded_and_skipped(self, tmp_path: Path) -> None:
        _write_java(
            tmp_path, "com/automation/utils/BrowserPicker.java", self._SWITCH_EXPRESSION_UTILITY
        )
        _write_java(tmp_path, "com/automation/pages/LoginPage.java", _FIXTURE_PAGE_OBJECT)

        catalog = reconcile(tmp_path)

        assert catalog.unparsed_files == ("com/automation/utils/BrowserPicker.java",)
        # The unparsable file never prevents the rest of the scan from
        # completing -- the valid fixture page object is still catalogued.
        assert len(catalog.page_objects) == 1
