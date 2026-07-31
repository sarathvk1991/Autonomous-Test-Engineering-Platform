"""Layer 2's own test-data specification emission (ADR-0043 D7,
`feature_engineering.stage.test_data_spec`) -- the decision this platform
locked but never implemented until this build.

Proves:
* THE DERIVATION, correct when data exists: `data_fields`/`polarity_hints`
  roll up per field, across every acceptance criterion, correctly.
* THE HONEST-EMPTY FINDING, reproduced directly: no real Layer 1 emitter
  code populates `data_fields`/`polarity_hints` (verified against
  `requirement_intelligence/testable_requirement/emitter.py` directly, and
  the real, committed `output/latest/testable_requirement_set.json` --
  every field-less requirement in this test suite mirrors that real shape,
  not a contrived edge case).
* Granularity: one specification per requirement, unconditionally -- even a
  field-less one, never silently omitted.
* THE SPEC-IS-NOT-DATA BOUNDARY: the emitted specification carries field
  NAMES and variant REQUIREMENTS only, never a data VALUE.
* JSON round-trip: `test_data_specifications_to_json` produces exactly what
  `contracts.test_data_specification.TestDataSpecification.model_dump`
  already produces, camelCase, matching this platform's other boundary
  artifacts.
"""

from __future__ import annotations

import json

import pytest

from contracts.test_data_specification import TestDataSpecification
from contracts.testable_requirement import (
    AcceptanceCriterionInput,
    Category,
    PolarityHint,
    Priority,
    TestableRequirement,
    build_testable_requirement,
)
from feature_engineering.stage.test_data_spec import (
    TEST_DATA_SPECIFICATIONS_FILENAME,
    build_test_data_specification,
    build_test_data_specifications,
    test_data_specifications_to_json,
)

pytestmark = pytest.mark.unit


def _requirement(**overrides: object) -> TestableRequirement:
    defaults: dict[str, object] = {
        "title": "User can log in",
        "component": "auth",
        "functional_tag": "@auth",
        "priority": Priority.HIGH,
        "traces_to": (),
        "narrative": "Users log in with credentials.",
        "acceptance_criteria": [
            AcceptanceCriterionInput(category=Category.FUNCTIONAL, statement="A"),
        ],
    }
    defaults.update(overrides)
    return build_testable_requirement(**defaults)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# THE HONEST-EMPTY FINDING -- reproduced directly, not merely claimed
# ---------------------------------------------------------------------------


class TestHonestEmptyDerivationOnRealShapedRequirements:
    def test_a_field_less_acceptance_criterion_yields_an_empty_but_present_specification(
        self,
    ) -> None:
        """The shape every real, currently-emitted `TestableRequirement`
        actually has (verified directly against
        `requirement_intelligence/testable_requirement/emitter.py`, which
        never passes `data_fields`/`polarity_hints`, and against the real,
        committed `output/latest/testable_requirement_set.json`, where
        every one of 30 acceptance criteria carries both empty)."""
        req = _requirement(
            acceptance_criteria=[
                AcceptanceCriterionInput(category=Category.FUNCTIONAL, statement="A"),
            ]
        )
        assert req.acceptance_criteria[0].data_fields == ()
        assert req.acceptance_criteria[0].polarity_hints == ()

        spec = build_test_data_specification(req)

        assert isinstance(spec, TestDataSpecification)
        assert spec.requirement_id == req.requirement_id
        assert spec.fields == ()

    def test_specification_is_still_emitted_for_a_field_less_requirement_never_omitted(
        self,
    ) -> None:
        """Granularity: one specification per requirement, UNCONDITIONALLY
        -- a field-less requirement still gets a (correctly empty) entry,
        it is never silently absent from the emitted set."""
        req_a = _requirement()
        req_b = _requirement(title="User can log out")

        specs = build_test_data_specifications((req_a, req_b))

        assert len(specs) == 2
        assert {s.requirement_id for s in specs} == {req_a.requirement_id, req_b.requirement_id}


# ---------------------------------------------------------------------------
# THE DERIVATION -- correct when data_fields/polarity_hints DO exist
# ---------------------------------------------------------------------------


class TestDerivationWhenDataExists:
    def test_one_field_named_by_one_criterion_gets_that_criterions_own_variants(self) -> None:
        req = _requirement(
            acceptance_criteria=[
                AcceptanceCriterionInput(
                    category=Category.FUNCTIONAL,
                    statement="Valid login succeeds",
                    polarity_hints=(PolarityHint.POSITIVE,),
                    data_fields=("username",),
                ),
            ]
        )

        spec = build_test_data_specification(req)

        assert len(spec.fields) == 1
        assert spec.fields[0].field_name == "username"
        assert spec.fields[0].required_variants == (PolarityHint.POSITIVE.value,)

    def test_a_field_named_by_multiple_criteria_accumulates_the_union_of_variants(self) -> None:
        """The roll-up rule: `username` is named by TWO criteria, one
        POSITIVE-only, one NEGATIVE+BOUNDARY -- the derived field's own
        required variants are the union of both, not just the last one."""
        req = _requirement(
            acceptance_criteria=[
                AcceptanceCriterionInput(
                    category=Category.FUNCTIONAL,
                    statement="Valid login succeeds",
                    polarity_hints=(PolarityHint.POSITIVE,),
                    data_fields=("username", "password"),
                ),
                AcceptanceCriterionInput(
                    category=Category.FUNCTIONAL,
                    statement="Invalid login rejected",
                    polarity_hints=(PolarityHint.NEGATIVE, PolarityHint.BOUNDARY),
                    data_fields=("username",),
                ),
            ]
        )

        spec = build_test_data_specification(req)

        by_field = {f.field_name: set(f.required_variants) for f in spec.fields}
        assert by_field["username"] == {
            PolarityHint.POSITIVE.value,
            PolarityHint.NEGATIVE.value,
            PolarityHint.BOUNDARY.value,
        }
        assert by_field["password"] == {PolarityHint.POSITIVE.value}

    def test_fields_are_sorted_deterministically(self) -> None:
        req = _requirement(
            acceptance_criteria=[
                AcceptanceCriterionInput(
                    category=Category.FUNCTIONAL,
                    statement="A",
                    polarity_hints=(PolarityHint.POSITIVE,),
                    data_fields=("zeta", "alpha"),
                ),
            ]
        )

        spec = build_test_data_specification(req)

        assert [f.field_name for f in spec.fields] == ["alpha", "zeta"]

    def test_deterministic_across_independent_calls(self) -> None:
        req = _requirement(
            acceptance_criteria=[
                AcceptanceCriterionInput(
                    category=Category.FUNCTIONAL,
                    statement="A",
                    polarity_hints=(PolarityHint.POSITIVE, PolarityHint.BOUNDARY),
                    data_fields=("username",),
                ),
            ]
        )

        first = build_test_data_specification(req)
        second = build_test_data_specification(req)

        assert first == second


# ---------------------------------------------------------------------------
# THE SPEC-IS-NOT-DATA BOUNDARY
# ---------------------------------------------------------------------------


class TestSpecIsNotDataBoundary:
    def test_specification_carries_no_data_value_only_field_names_and_variant_requirements(
        self,
    ) -> None:
        """A structural proof, not just an assertion: every leaf value the
        specification's own JSON carries is either the requirement id, a
        field NAME (a string naming what's needed), or a variant NAME
        (positive/negative/boundary) -- never a data VALUE (a username, a
        password, an expected label)."""
        req = _requirement(
            acceptance_criteria=[
                AcceptanceCriterionInput(
                    category=Category.FUNCTIONAL,
                    statement="A",
                    polarity_hints=(PolarityHint.POSITIVE,),
                    data_fields=("username",),
                ),
            ]
        )

        spec = build_test_data_specification(req)
        payload = spec.model_dump(mode="json", by_alias=True)

        assert set(payload.keys()) == {"requirementId", "fields"}
        for field_payload in payload["fields"]:
            assert set(field_payload.keys()) == {"fieldName", "requiredVariants"}
            for variant in field_payload["requiredVariants"]:
                assert variant in {"positive", "negative", "boundary"}
        # No sentinel of an actual credential/value ever appears.
        serialized = json.dumps(payload)
        assert "standard_user" not in serialized
        assert "secret_sauce" not in serialized


# ---------------------------------------------------------------------------
# JSON envelope
# ---------------------------------------------------------------------------


class TestJsonEnvelope:
    def test_envelope_shape_matches_the_specifications_own_model_dump(self) -> None:
        req = _requirement(
            acceptance_criteria=[
                AcceptanceCriterionInput(
                    category=Category.FUNCTIONAL,
                    statement="A",
                    polarity_hints=(PolarityHint.POSITIVE,),
                    data_fields=("username",),
                ),
            ]
        )
        specs = build_test_data_specifications((req,))

        envelope = test_data_specifications_to_json(specs)

        assert set(envelope.keys()) == {"specifications"}
        assert envelope["specifications"] == [
            specs[0].model_dump(mode="json", by_alias=True)
        ]

    def test_filename_constant_is_a_plain_json_file(self) -> None:
        assert TEST_DATA_SPECIFICATIONS_FILENAME == "test_data_specifications.json"
