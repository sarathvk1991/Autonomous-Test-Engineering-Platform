"""ADR-0051 D5's second-generator eval set: `LiveFeatureContentGenerator`.

Same discipline as `step_definition_eval_set.py`, applied to a different
artifact -- seeded from real generation contexts, not invented, versioned
independently of `GenerationIdentity`/the prompt.

Each case's `requirement` is a real `TestableRequirement` from the
currently-tracked `output/latest/testable_requirement_set.json` corpus --
the SAME 20-requirement corpus the real, live-regen `.feature` files under
`output/executions/run-20260812T064317663150Z-a20b0cc2/.../features/` were
generated from ([[cap-real-completeness-measured]], [[cap-stage14-live-cli-wiring]]:
that live E2E run scored 15/15 features clean, 0 escalations -- unlike
step-def's 76%-defective `gemini-2.5-flash` regression, there is no known
historical feature-content defect on record to seed a negative case from).
This module curates the INPUT contexts only; it carries no canned generator
output (ADR-0051 D2's own "rejected as the primary mechanism" finding for
expected-output matching) -- a caller pairs each case with whatever a real or
stub generator actually produces for it.
"""

from __future__ import annotations

from dataclasses import dataclass

from contracts.testable_requirement import (
    AcceptanceCriterion,
    Category,
    TestableRequirement,
)

#: Independent from `GenerationIdentity`/the prompt version (ADR-0051 D2) --
#: this is the CURATED SET's own version, advanced when cases are added,
#: removed, or re-labeled, never when the generator or prompt changes.
FEATURE_CONTENT_EVAL_SET_VERSION = "1.0.0"

_COMPONENT = "Automation-POC:src/test/java/com/automation/pages/badexamples/BadLoginPage.java"
_FUNCTIONAL_TAG = "@automationpocsrctestjavacomautomationpagesbadexamplesbadloginpagejava"


@dataclass(frozen=True, slots=True)
class EvalCase:
    """One curated eval case: an id (for diagnosis) plus the real
    `TestableRequirement` a `FeatureContentGenerator` would be called with."""

    case_id: str
    requirement: TestableRequirement


#: Seeded directly from three real, currently-tracked requirements in
#: `output/latest/testable_requirement_set.json` -- the exact corpus whose
#: real, live-regenerated `.feature` files this eval set's own property-check
#: fixtures (`tests/unit/test_eval_harness_feature_content_properties.py`)
#: reconstruct the raw (pre-assembly) generator output from. Every real
#: requirement in this corpus carries exactly one acceptance criterion (a
#: real, honest fact about this corpus, not a simplification made here) and
#: no Background-common steps -- so no real case in this set exercises the
#: NOT_APPLICABLE path for `check_no_tags_on_background`; that check's own
#: unit tests (not this curated set) prove it fires correctly against a
#: synthetic Background: violation, mirroring exactly how
#: `STEP_DEFINITION_EVAL_SET`'s third case, not a synthetic unit fixture, was
#: the vehicle step-def used for its own NOT_APPLICABLE proof -- the two sets
#: differ here because feature-content's real corpus has no case that
#: naturally exercises it, and inventing one would violate this module's own
#: "seeded from real generation contexts, not invented" discipline.
FEATURE_CONTENT_EVAL_SET: tuple[EvalCase, ...] = (
    EvalCase(
        case_id="login_invalid_credentials_error",
        requirement=TestableRequirement(
            requirement_id="REQ-c64bb0f7",
            content_hash="da1d2b238166302c1535b7dbac647e86e91810ddea2cf6d927ca0eedf48d6cda",
            title=(
                "The system shall display an error message when a user attempts to "
                "login with invalid credentials."
            ),
            component=_COMPONENT,
            functional_tag=_FUNCTIONAL_TAG,
            narrative=None,
            priority=None,
            acceptance_criteria=(
                AcceptanceCriterion(
                    criterion_id="AC-c64bb0f7-01",
                    category=Category.FUNCTIONAL,
                    statement=(
                        "The system shall display an error message when a user attempts "
                        "to login with invalid credentials."
                    ),
                    polarity_hints=(),
                    data_fields=(),
                    traces_to=(),
                ),
            ),
            risks=(),
            traces_to=(),
        ),
    ),
    EvalCase(
        case_id="inventory_display_after_authentication",
        requirement=TestableRequirement(
            requirement_id="REQ-f90f23fa",
            content_hash="181d1c6d011ab39566449e5f4f8f164c668fe155b5d4191ee23480013f1136bf",
            title=(
                "The system shall display the inventory page upon successful user "
                "authentication."
            ),
            component=_COMPONENT,
            functional_tag=_FUNCTIONAL_TAG,
            narrative=None,
            priority=None,
            acceptance_criteria=(
                AcceptanceCriterion(
                    criterion_id="AC-f90f23fa-01",
                    category=Category.FUNCTIONAL,
                    statement=(
                        "The system shall display the inventory page upon successful "
                        "user authentication."
                    ),
                    polarity_hints=(),
                    data_fields=(),
                    traces_to=(),
                ),
            ),
            risks=(),
            traces_to=(),
        ),
    ),
    EvalCase(
        case_id="session_timeout_invalidation",
        requirement=TestableRequirement(
            requirement_id="REQ-92502735",
            content_hash="2440eed8fd3619e9bd20af4f6ac6bd94c68cd55c8853f2d63c95dab048cedf28",
            title=(
                "The system shall invalidate the user session and redirect to the "
                "login page upon session timeout."
            ),
            component=_COMPONENT,
            functional_tag=_FUNCTIONAL_TAG,
            narrative=None,
            priority=None,
            acceptance_criteria=(
                AcceptanceCriterion(
                    criterion_id="AC-92502735-01",
                    category=Category.FUNCTIONAL,
                    statement=(
                        "The system shall invalidate the user session and redirect to "
                        "the login page upon session timeout."
                    ),
                    polarity_hints=(),
                    data_fields=(),
                    traces_to=(),
                ),
            ),
            risks=(),
            traces_to=(),
        ),
    ),
)


__all__ = ["FEATURE_CONTENT_EVAL_SET", "FEATURE_CONTENT_EVAL_SET_VERSION", "EvalCase"]
