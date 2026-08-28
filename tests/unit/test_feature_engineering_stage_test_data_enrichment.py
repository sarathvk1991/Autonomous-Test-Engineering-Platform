"""#3 Option B -- the post-hoc test-data enrichment stopgap
(`feature_engineering.stage.test_data_enrichment`, ADR-0043 D10).

Seeded from the REAL, currently-tracked 15 SUT requirement statements
(`output/latest/testable_requirement_set.json`, post ADR-0043 D9's own
SUT/framework-SAST split) -- not invented text -- so this suite reports the
derivation's REAL measured coverage on the real corpus, not a synthetic
best case. Also proves the one real bug this build caught by testing
against that real text directly: "invalid" contains "valid" as a bare
substring, which would wrongly imply BOTH polarities without word-boundary
matching.
"""

from __future__ import annotations

import pytest

from contracts.testable_requirement import PolarityHint
from feature_engineering.stage.test_data_enrichment import (
    DerivedDataHints,
    derive_data_hints_from_statement,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Real corpus, real signal -- the 4 of 15 SUT requirements that DO carry
# recoverable data-field signal in their own finalized text.
# ---------------------------------------------------------------------------


class TestRealCorpusPositiveCases:
    def test_login_with_invalid_credentials_derives_username_password_negative(self) -> None:
        """REQ-c64bb0f7, verbatim. The exact regression this build's own
        real-corpus verification caught: a naive substring check on "valid"
        would ALSO match inside "invalid", wrongly adding POSITIVE
        alongside NEGATIVE. Word-boundary matching fixes it -- this test
        pins the fix."""
        statement = (
            "The system shall display an error message when a user attempts to "
            "login with invalid credentials."
        )

        hints = derive_data_hints_from_statement(statement)

        assert set(hints.data_fields) == {"username", "password"}
        assert hints.polarity_hints == (PolarityHint.NEGATIVE,)

    def test_successful_authentication_derives_username_password_positive(self) -> None:
        """REQ-f90f23fa, verbatim -- no literal "login" word, but
        "authentication" satisfies the login-domain pattern's own stem
        match, and "successful" is the polarity cue."""
        statement = (
            "The system shall display the inventory page upon successful user "
            "authentication."
        )

        hints = derive_data_hints_from_statement(statement)

        assert set(hints.data_fields) == {"username", "password"}
        assert hints.polarity_hints == (PolarityHint.POSITIVE,)

    def test_locked_account_login_attempt_derives_username_password_negative(self) -> None:
        """REQ-88607bd5, verbatim -- "deny"/"locked" both cue NEGATIVE,
        deduplicated to one entry."""
        statement = (
            "The system shall deny access to users with locked accounts upon "
            "login attempt."
        )

        hints = derive_data_hints_from_statement(statement)

        assert set(hints.data_fields) == {"username", "password"}
        assert hints.polarity_hints == (PolarityHint.NEGATIVE,)

    def test_postal_code_format_validation_derives_postal_code_positive_and_boundary(
        self,
    ) -> None:
        """REQ-af3142d8, verbatim -- the one literal-noun (not login-domain)
        real hit: "postal code" names the field directly; "valid" and
        "format" both cue, positive and boundary."""
        statement = (
            "The system shall validate that the postal code field in the checkout "
            "form accepts only valid postal code formats."
        )

        hints = derive_data_hints_from_statement(statement)

        assert hints.data_fields == ("postalCode",)
        assert set(hints.polarity_hints) == {PolarityHint.POSITIVE, PolarityHint.BOUNDARY}


# ---------------------------------------------------------------------------
# Real corpus, honest misses -- the 11 of 15 SUT requirements that derive
# NOTHING, correctly, because their own finalized text carries no
# recoverable data signal (behavioral, not data-driven).
# ---------------------------------------------------------------------------


class TestRealCorpusHonestMisses:
    def test_cart_count_increment_derives_nothing(self) -> None:
        """REQ-87f1757e, verbatim -- a UI-interaction requirement with no
        data-field signal at all."""
        statement = (
            "The system shall increment the cart count when a user clicks the "
            "Add To Cart button for an inventory item."
        )

        assert derive_data_hints_from_statement(statement) == DerivedDataHints()

    def test_valid_checkout_information_derives_nothing_the_real_fidelity_gap(self) -> None:
        """REQ-ede9760c, verbatim -- an HONEST LIMIT of the deterministic
        stopgap, shown directly rather than hidden: a human reviewer would
        reasonably infer firstName/lastName/postalCode fields here, but
        this module deliberately recognizes only ONE domain pattern
        (login), not a "checkout information" pattern -- so this real
        requirement, despite genuinely needing checkout data, derives
        NOTHING. This is exactly the class of miss post-hoc text inference
        cannot close and analysis-time elicitation (Option A) could: the
        raw source evidence behind "checkout information" (a form with
        named fields) is available to Layer 1 at analysis time and is
        already gone by the time this module ever sees the finalized text."""
        statement = (
            "The system shall proceed to checkout when valid checkout "
            "information is submitted."
        )

        assert derive_data_hints_from_statement(statement) == DerivedDataHints()

    def test_session_timeout_redirect_to_login_page_is_correctly_excluded(self) -> None:
        """REQ-92502735, verbatim -- the exact false-positive this module's
        own exclusion guard exists for: the statement contains the literal
        word "login" (in "the login page"), which alone would satisfy the
        login-domain trigger, but this requirement is about a SESSION
        TIMEOUT event, never about submitting credentials -- the
        "session"/"timeout" exclusion words correctly suppress the match."""
        statement = (
            "The system shall invalidate the user session and redirect to the "
            "login page upon session timeout."
        )

        assert derive_data_hints_from_statement(statement) == DerivedDataHints()

    def test_logout_session_termination_derives_nothing(self) -> None:
        """REQ-db20c99f, verbatim -- "logout" is a distinct word from
        "login" (no accidental stem overlap), and carries no field/domain
        signal of its own."""
        statement = (
            "The system shall ensure the browser session is fully terminated "
            "upon user logout."
        )

        assert derive_data_hints_from_statement(statement) == DerivedDataHints()

    def test_inventory_sort_order_derives_nothing(self) -> None:
        statement = "The system shall maintain consistent sorting order for inventory items."

        assert derive_data_hints_from_statement(statement) == DerivedDataHints()


# ---------------------------------------------------------------------------
# Word-boundary correctness -- the exact bug class this build's real-corpus
# verification caught, pinned directly against synthetic minimal inputs.
# ---------------------------------------------------------------------------


class TestWordBoundaryCorrectness:
    def test_invalid_never_also_matches_the_valid_cue(self) -> None:
        hints = derive_data_hints_from_statement("Login with an invalid password is rejected.")

        assert hints.polarity_hints == (PolarityHint.NEGATIVE,)
        assert PolarityHint.POSITIVE not in hints.polarity_hints

    def test_valid_alone_matches_positive_only(self) -> None:
        hints = derive_data_hints_from_statement("Login with a valid password succeeds.")

        assert hints.polarity_hints == (PolarityHint.POSITIVE,)

    def test_plural_credentials_still_matches_the_credential_stem(self) -> None:
        hints = derive_data_hints_from_statement("Login fails with bad credentials.")

        assert set(hints.data_fields) == {"username", "password"}

    def test_plural_accounts_still_matches_the_account_stem(self) -> None:
        hints = derive_data_hints_from_statement("Login denies disabled accounts.")

        assert set(hints.data_fields) == {"username", "password"}


# ---------------------------------------------------------------------------
# Default polarity, and determinism
# ---------------------------------------------------------------------------


class TestDefaultPolarityAndDeterminism:
    def test_a_derived_field_with_no_polarity_cue_defaults_to_positive(self) -> None:
        """A documented default, not a claimed inference from the text --
        module docstring."""
        hints = derive_data_hints_from_statement("The username field is displayed on the page.")

        assert hints.data_fields == ("username",)
        assert hints.polarity_hints == (PolarityHint.POSITIVE,)

    def test_no_field_means_no_default_polarity_either(self) -> None:
        """The default only ever applies once a field is genuinely
        derived -- an honest miss stays a fully empty result, never a
        polarity hint with no field to attach to."""
        hints = derive_data_hints_from_statement("The system shall load quickly.")

        assert hints == DerivedDataHints()

    def test_deterministic_across_independent_calls(self) -> None:
        statement = "Login with invalid credentials shows an error."

        assert derive_data_hints_from_statement(statement) == derive_data_hints_from_statement(
            statement
        )
