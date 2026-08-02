"""Candidate-asset identity resolution (ADR-0045 D2(b)).

Proves :func:`resolve_candidate_identity` derives identity via the REAL
catalog scan (:func:`automation_engineering.catalog.scanner.reconcile`) --
not a hand-rolled parse -- for all three catalog asset kinds, and fails
loudly (never silently) on candidate source the catalog scan cannot resolve
to exactly one asset.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from automation_engineering.catalog.models import (
    PageObjectAsset,
    StepDefinitionAsset,
    UtilityAsset,
)
from automation_engineering.catalog.scanner import JAVA_SOURCE_SUBPATH, reconcile
from automation_engineering.promotion.identity import (
    CandidateIdentityError,
    relative_java_path,
    resolve_candidate_identity,
)

pytestmark = pytest.mark.unit

_STEP_DEFINITION_SOURCE = textwrap.dedent(
    """\
    package com.automation.steps;

    import io.cucumber.java.en.When;

    /** Generated step definition -- searches for a product. */
    public class SearchProductSteps {

        @When("I search for a product")
        public void iSearchForAProduct() {
            // generated fixture body
        }
    }
    """
)

_PAGE_OBJECT_SOURCE = textwrap.dedent(
    """\
    package com.automation.pages;

    import com.automation.base.BasePage;
    import org.openqa.selenium.WebDriver;

    /** Generated search page. */
    public class SearchPage extends BasePage {

        public SearchPage(WebDriver driver) {
            super(driver);
        }

        public void enterSearchTerm(String term) {
            // generated fixture body
        }
    }
    """
)

_UTILITY_SOURCE = textwrap.dedent(
    """\
    package com.automation.utils;

    /** Generated config helper. */
    public class SearchConfig {

        public String defaultTerm() {
            return "shoes";
        }
    }
    """
)

_TWO_METHOD_STEP_SOURCE = textwrap.dedent(
    """\
    package com.automation.steps;

    import io.cucumber.java.en.Given;
    import io.cucumber.java.en.When;

    public class TwoStepMethods {

        @Given("I am on the search page")
        public void iAmOnTheSearchPage() {
        }

        @When("I search for a product")
        public void iSearchForAProduct() {
        }
    }
    """
)

_TWO_CLASS_SOURCE = textwrap.dedent(
    """\
    package com.automation.utils;

    public class FirstHelper {
        public void doThing() {
        }
    }

    class SecondHelper {
        public void doOtherThing() {
        }
    }
    """
)


class TestResolvesEachAssetKind:
    def test_step_definition_resolves_to_one_step_definition_asset(self) -> None:
        asset, relative_path = resolve_candidate_identity(_STEP_DEFINITION_SOURCE)

        assert isinstance(asset, StepDefinitionAsset)
        assert asset.class_name == "com.automation.steps.SearchProductSteps"
        assert asset.method_name == "iSearchForAProduct"
        assert asset.pattern == "I search for a product"
        assert relative_path == Path("com/automation/steps/SearchProductSteps.java")

    def test_page_object_resolves_to_one_page_object_asset(self) -> None:
        asset, relative_path = resolve_candidate_identity(_PAGE_OBJECT_SOURCE)

        assert isinstance(asset, PageObjectAsset)
        assert asset.class_name == "com.automation.pages.SearchPage"
        assert asset.extends == "BasePage"
        assert relative_path == Path("com/automation/pages/SearchPage.java")

    def test_utility_resolves_to_one_utility_asset(self) -> None:
        asset, relative_path = resolve_candidate_identity(_UTILITY_SOURCE)

        assert isinstance(asset, UtilityAsset)
        assert asset.class_name == "com.automation.utils.SearchConfig"
        assert relative_path == Path("com/automation/utils/SearchConfig.java")


class TestContentHashMatchesARealReconcile:
    def test_content_hash_equals_a_direct_reconcile_of_the_same_file(self, tmp_path: Path) -> None:
        """The whole point of reusing `reconcile()` (module docstring): identity
        computed here must be byte-identical to identity a real baseline scan
        would compute for the same file, once promoted."""
        asset, relative_path = resolve_candidate_identity(_STEP_DEFINITION_SOURCE)

        baseline_root = tmp_path / "baseline"
        target = baseline_root / JAVA_SOURCE_SUBPATH / relative_path
        target.parent.mkdir(parents=True)
        target.write_text(_STEP_DEFINITION_SOURCE, encoding="utf-8")
        real_catalog = reconcile(baseline_root)

        assert len(real_catalog.step_definitions) == 1
        real_asset = real_catalog.step_definitions[0]
        assert real_asset.content_hash == asset.content_hash
        assert real_asset.asset_id == asset.asset_id


class TestFailsLoudlyOnUnresolvableCandidates:
    def test_two_annotated_methods_raises(self) -> None:
        with pytest.raises(CandidateIdentityError):
            resolve_candidate_identity(_TWO_METHOD_STEP_SOURCE)

    def test_two_top_level_classes_raises(self) -> None:
        with pytest.raises(CandidateIdentityError):
            resolve_candidate_identity(_TWO_CLASS_SOURCE)


def test_relative_java_path_joins_package_segments() -> None:
    assert relative_java_path("com.automation.steps", "FooSteps") == Path(
        "com/automation/steps/FooSteps.java"
    )


def test_relative_java_path_handles_empty_package() -> None:
    assert relative_java_path("", "Foo") == Path("Foo.java")
