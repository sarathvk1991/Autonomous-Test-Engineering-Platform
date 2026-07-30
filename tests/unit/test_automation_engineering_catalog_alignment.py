"""Capture-to-parameter correlation for step definitions (ADR-0044 D4(c)).

The read-only inspection that preceded this module confirmed the catalog's
javalang-based parameter extraction is sound (count, order, and Java type
-- including boxed-vs-primitive -- all extract correctly). What it found
missing is exactly what this module adds: the catalog recorded a step
definition's Gherkin pattern and its Java parameters INDEPENDENTLY, with no
data about whether they actually align. This proves that gap is closed --
additively, on top of the sound extraction, not a rework of it.

Proves every case the hardening task named, deterministically, with no LLM
call: 0/0, one capture, ordered multi-capture, a typed ``{int}`` capture,
the D4-CRITICAL case (a real, plausible-but-wrong 1-capture-to-2-parameter
method -- exactly the "wrong arity" mis-binding ADR-0044 D4(c) exists to
catch), an explicit type mismatch, the DataTable non-capture case (proving
no false-positive on a legitimate trailing parameter), and both supported
annotation styles (Cucumber Expressions -- the style the real tracked
baseline's own imports use -- and regex, handled defensively since the
codebase could use either).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from automation_engineering.catalog import AssetCatalog, reconcile
from automation_engineering.catalog.alignment import correlate
from automation_engineering.catalog.models import JavaParameter

pytestmark = pytest.mark.unit

_REAL_BASELINE_ROOT = Path("test-suite-baseline")


class TestRealBaselineAlignment:
    """The real tracked baseline's own step definitions -- both have zero
    captures and zero parameters, so both must be aligned."""

    def test_smoke_steps_are_aligned(self) -> None:
        catalog = reconcile(_REAL_BASELINE_ROOT)

        assert len(catalog.step_definitions) == 2
        for step in catalog.step_definitions:
            alignment = step.signature_alignment
            assert alignment.captures == ()
            assert alignment.correlations == ()
            assert alignment.non_capture_parameters == ()
            assert alignment.is_aligned is True
            assert alignment.mismatch_reason is None

    def test_baseline_uses_cucumber_expression_style_annotations(self) -> None:
        """`SmokeSteps.java` imports `io.cucumber.java.en.Given`/`Then` --
        the Cucumber Expression package, confirmed directly against the
        file -- not the base `io.cucumber.java.*` regex-style package.
        Both real step patterns are plain phrases with no placeholders, so
        this is the only fact directly provable from the real baseline
        today; the regex path is exercised via fixtures below."""
        steps_file = _REAL_BASELINE_ROOT / "src/test/java/com/automation/steps/SmokeSteps.java"
        source = steps_file.read_text()
        assert "io.cucumber.java.en.Given" in source
        assert "io.cucumber.java.en.Then" in source


class TestCorrelateRequiredCases:
    """Every case named in the hardening task, proven directly against
    :func:`correlate` -- pattern + already-extracted parameters in,
    alignment data out."""

    def test_zero_capture_zero_param_is_aligned(self) -> None:
        alignment = correlate("user logs in", ())

        assert alignment.captures == ()
        assert alignment.non_capture_parameters == ()
        assert alignment.is_aligned is True
        assert alignment.mismatch_reason is None

    def test_one_string_capture_one_string_param_is_aligned(self) -> None:
        params = (JavaParameter("username", "String"),)
        alignment = correlate("user enters {string} in the username field", params)

        assert [c.expression_type for c in alignment.captures] == ["string"]
        assert len(alignment.correlations) == 1
        assert alignment.correlations[0].type_compatible is True
        assert alignment.is_aligned is True

    def test_two_string_captures_align_in_order(self) -> None:
        params = (JavaParameter("u", "String"), JavaParameter("p", "String"))
        alignment = correlate("user enters {string} and {string}", params)

        assert len(alignment.correlations) == 2
        # Positional: correlation[i] pairs capture[i] with parameter[i].
        assert alignment.correlations[0].parameter.name == "u"
        assert alignment.correlations[1].parameter.name == "p"
        assert all(c.type_compatible for c in alignment.correlations)
        assert alignment.is_aligned is True

    def test_int_capture_aligns_to_int_param_not_string(self) -> None:
        params = (JavaParameter("count", "int"),)
        alignment = correlate("the cart shows {int} items", params)

        assert alignment.captures[0].expression_type == "int"
        assert alignment.correlations[0].parameter.java_type == "int"
        assert alignment.correlations[0].type_compatible is True
        assert alignment.is_aligned is True

    def test_boxed_integer_also_type_compatible_with_int_capture(self) -> None:
        params = (JavaParameter("count", "Integer"),)
        alignment = correlate("the cart shows {int} items", params)

        assert alignment.correlations[0].type_compatible is True
        assert alignment.is_aligned is True

    def test_d4_critical_one_capture_two_params_is_misaligned(self) -> None:
        """The exact plausible-but-wrong mis-binding shape ADR-0044 D4(c)
        exists to catch: a method whose parameter COUNT does not match its
        own annotation's capture count. Recorded as an arity mismatch, not
        silently treated as an extra trailing parameter -- this method has
        no legitimate reason to have 2 params for 1 capture."""
        params = (JavaParameter("u", "String"), JavaParameter("p", "String"))
        alignment = correlate("user enters {string}", params)

        assert len(alignment.captures) == 1
        assert alignment.correlations == ()
        assert alignment.non_capture_parameters == ()
        assert alignment.is_aligned is False
        assert alignment.mismatch_reason == "arity"

    def test_string_capture_to_int_param_is_type_misaligned(self) -> None:
        params = (JavaParameter("username", "int"),)
        alignment = correlate("user enters {string} as username", params)

        assert alignment.correlations[0].type_compatible is False
        assert alignment.is_aligned is False
        assert alignment.mismatch_reason == "type"

    def test_int_capture_to_string_param_is_type_misaligned(self) -> None:
        params = (JavaParameter("count", "String"),)
        alignment = correlate("the cart shows {int} items", params)

        assert alignment.correlations[0].type_compatible is False
        assert alignment.is_aligned is False
        assert alignment.mismatch_reason == "type"

    def test_datatable_trailing_param_is_non_capture_and_aligned(self) -> None:
        """The subtle case: 0 captures, 1 param, but the param is a
        DataTable -- a legitimate Cucumber-JVM trailing parameter that
        does NOT correspond to any step-text capture. Must be ALIGNED,
        not a false-positive arity mismatch."""
        params = (JavaParameter("data", "DataTable"),)
        alignment = correlate("user submits the form", params)

        assert alignment.captures == ()
        assert alignment.non_capture_parameters == params
        assert alignment.correlations == ()
        assert alignment.is_aligned is True
        assert alignment.mismatch_reason is None

    def test_datatable_trailing_param_after_real_captures_is_aligned(self) -> None:
        """A DataTable can legitimately trail AFTER genuine captures too --
        the non-capture recognition must apply on top of, not instead of,
        normal correlation."""
        params = (JavaParameter("username", "String"), JavaParameter("data", "DataTable"))
        alignment = correlate("user enters {string} with the following data:", params)

        assert len(alignment.captures) == 1
        assert len(alignment.correlations) == 1
        assert alignment.correlations[0].parameter.name == "username"
        assert alignment.non_capture_parameters == (params[1],)
        assert alignment.is_aligned is True

    def test_extra_plain_string_param_is_not_assumed_to_be_a_docstring(self) -> None:
        """A trailing plain String beyond the capture count is NOT given a
        free pass merely because Cucumber's docstring convention also uses
        String -- a step-definition-only scan cannot distinguish "this is
        the docstring" from "this is a genuine miscount" (that depends on
        the invoking Gherkin step, which this catalog never sees). The
        conservative, D4-safe default is to flag it, not silently assume
        the benign explanation."""
        params = (JavaParameter("note", "String"),)
        alignment = correlate("user submits the form", params)

        assert alignment.captures == ()
        assert alignment.non_capture_parameters == ()
        assert alignment.is_aligned is False
        assert alignment.mismatch_reason == "arity"

    def test_regex_style_non_capturing_group_is_excluded(self) -> None:
        alignment = correlate("^user (?:logs|signs) in$", ())

        assert alignment.captures == ()
        assert alignment.is_aligned is True

    def test_regex_style_capture_group_is_counted_and_type_agnostic(self) -> None:
        params = (JavaParameter("username", "String"),)
        alignment = correlate("^user enters (.*) as username$", params)

        assert len(alignment.captures) == 1
        assert alignment.captures[0].style == "regex"
        assert alignment.captures[0].expression_type is None
        # A regex capture has no independently declared type to disagree
        # with -- always type-compatible, whatever the param's Java type.
        assert alignment.correlations[0].type_compatible is True
        assert alignment.is_aligned is True

    def test_regex_style_arity_mismatch_is_still_caught(self) -> None:
        params = (JavaParameter("a", "String"), JavaParameter("b", "String"))
        alignment = correlate("^user enters (.*)$", params)

        assert len(alignment.captures) == 1
        assert alignment.is_aligned is False
        assert alignment.mismatch_reason == "arity"


class TestDeterminism:
    def test_same_input_yields_identical_alignment(self) -> None:
        params = (JavaParameter("username", "String"), JavaParameter("password", "String"))
        first = correlate("user enters {string} and {string}", params)
        second = correlate("user enters {string} and {string}", params)

        assert first == second


class TestJsonRoundTrip:
    def test_signature_alignment_round_trips_through_json(self) -> None:
        catalog = reconcile(_REAL_BASELINE_ROOT)

        restored = AssetCatalog.from_json(catalog.to_json())

        assert restored == catalog
        for step in restored.step_definitions:
            assert step.signature_alignment.is_aligned is True
