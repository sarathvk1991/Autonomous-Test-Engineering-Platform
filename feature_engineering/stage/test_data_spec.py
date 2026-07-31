"""``test_data_specifications.json`` -- Layer 2's own emission of ADR-0043
D7's test-data specification (`contracts.test_data_specification.
TestDataSpecification`), the decision this platform locked but never
implemented until this build.

Derivation, honestly, from what Layer 1 actually emits today
------------------------------------------------------------------
D7's own prose contract: "which fields are needed, and for each, whether
positive/negative/boundary variants are required, seeded by
``AcceptanceCriterion.polarity_hints[]``." Both halves of that derivation
are already real, committed fields on `AcceptanceCriterion`
(`contracts/testable_requirement.py`, ADR-0042): ``data_fields[]`` ("Seeds
`Examples:` tables and Layer 3's test-data spec" -- ADR-0042's own field
table, verbatim) names WHICH fields; ``polarity_hints[]`` names WHICH
variants. This module reads both, unchanged, and rolls them up per
requirement: for every acceptance criterion, for every field its own
``data_fields`` names, that field's required variants are the UNION of
that criterion's own ``polarity_hints`` (a field named by more than one
criterion accumulates every criterion's hints).

**Neither field is populated by any real Layer 1 output today -- verified
directly, not assumed.** `requirement_intelligence/testable_requirement/
emitter.py` constructs every `AcceptanceCriterionInput` as
``AcceptanceCriterionInput(category=category, statement=statement)`` --
`polarity_hints` and `data_fields` are never passed, so both default to
`()` on every real, emitted `TestableRequirement`. Confirmed empirically
against `output/latest/testable_requirement_set.json` (a real, live
end-to-end analysis run against the saucedemo corpus): 30 requirements, 30
acceptance criteria, EVERY ONE with `polarityHints: []` and
`dataFields: []`. The specification this module honestly derives from any
real requirement today is therefore EMPTY (zero fields) -- not padded, not
fabricated, correctly reflecting that Layer 1 does not yet emit the
signal D7's own specification depends on. This is a recorded finding
(architecture-baseline-v2.md), not a defect in this module: the derivation
logic itself is exercised and correct (proven directly against
hand-constructed, schema-compliant `AcceptanceCriterion`s carrying real
`data_fields`/`polarity_hints`, in this module's own test suite), it
simply has nothing to derive from yet on the live corpus.

Granularity and placement
------------------------------
One `TestDataSpecification` per `TestableRequirement`, UNCONDITIONALLY --
even a requirement whose criteria carry no `data_fields` still gets an
(honestly empty) specification, the same "always one record per
requirement" discipline `FeatureRecord` (`.models`) already establishes;
a requirement is never silently absent from the file, only its own
`fields` tuple may be empty. Written into the run directory alongside
`feature_engineering_package.json`/`traceability.json`
(`.runner.run_feature_engineering_stage`, ADR-0043 D8's own artifact-path
discipline), never into the untracked workspace -- this is a run-scoped
derived index, the same category as `traceability.json`, not a workspace
source file.
"""

from __future__ import annotations

from typing import Any

from contracts.test_data_specification import TestDataFieldSpec, TestDataSpecification
from contracts.testable_requirement import PolarityHint, TestableRequirement

TEST_DATA_SPECIFICATIONS_FILENAME = "test_data_specifications.json"


def build_test_data_specification(requirement: TestableRequirement) -> TestDataSpecification:
    """Derive one requirement's own test-data specification from its
    acceptance criteria's own ``data_fields``/``polarity_hints`` -- see
    module docstring for the exact derivation rule and the honest-empty
    finding on real Layer 1 output.
    """
    variants_by_field: dict[str, set[PolarityHint]] = {}
    for criterion in requirement.acceptance_criteria:
        for field_name in criterion.data_fields:
            variants_by_field.setdefault(field_name, set()).update(criterion.polarity_hints)

    fields = tuple(
        TestDataFieldSpec(
            field_name=field_name,
            required_variants=tuple(sorted(variants_by_field[field_name])),
        )
        for field_name in sorted(variants_by_field)
    )
    return TestDataSpecification(requirement_id=requirement.requirement_id, fields=fields)


def build_test_data_specifications(
    requirements: tuple[TestableRequirement, ...],
) -> tuple[TestDataSpecification, ...]:
    """One specification per requirement, in the SAME order as
    ``requirements`` -- unconditionally, never omitting a requirement whose
    own derivation happens to be empty."""
    return tuple(build_test_data_specification(requirement) for requirement in requirements)


def test_data_specifications_to_json(
    specifications: tuple[TestDataSpecification, ...],
) -> dict[str, Any]:
    """Canonical JSON envelope -- mirrors `traceability.json`'s own
    ``{"entries": [...]}`` shape (`.traceability.build_traceability_index`),
    here ``{"specifications": [...]}``, each entry the specification's own
    ``model_dump(mode="json", by_alias=True)`` (camelCase, matching every
    other boundary-contract artifact this platform already writes -- e.g.
    `output/latest/testable_requirement_set.json`)."""
    return {
        "specifications": [
            specification.model_dump(mode="json", by_alias=True) for specification in specifications
        ]
    }


#: Not a test function -- silences pytest's default `test_*` collection
#: heuristic once this function is imported by name into an actual test
#: module (its own name coincidentally matches that pattern; it takes a
#: required positional argument pytest would otherwise try to resolve as a
#: fixture).
test_data_specifications_to_json.__test__ = False  # type: ignore[attr-defined]


__all__ = [
    "TEST_DATA_SPECIFICATIONS_FILENAME",
    "build_test_data_specification",
    "build_test_data_specifications",
    "test_data_specifications_to_json",
]
