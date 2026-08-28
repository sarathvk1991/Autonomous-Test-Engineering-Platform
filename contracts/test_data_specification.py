"""TestDataSpecification — the Layer 2 -> Layer 3 boundary contract
(ADR-0043 D7 / ADR-0044 D7).

ADR-0043 D7 locks this specification's own prose contract, verbatim: "which
fields are needed, and for each, whether positive/negative/boundary
variants are required, seeded by ``AcceptanceCriterion.polarity_hints[]``."
It is "a handoff contract, not a dataset and not Java" — this module
therefore carries no Java-shape concerns (a target class name, a target
Java package) at all; those are Layer 3's own derivation
(``automation_engineering.generation.test_data_orchestrator.derive_test_data_class_name``),
computed FROM ``requirement_id`` at generation time, never carried on this
contract. This mirrors ``TestableRequirement`` itself (this module's own
sibling boundary contract, Layer 1 -> Layer 2): the contract that crosses a
layer boundary carries only what the UPSTREAM layer can honestly derive,
never a downstream layer's own shape decisions.

History, recorded because it explains this module's placement
------------------------------------------------------------------
This shape was FIRST defined, unilaterally, on the Layer 3 (consuming) side
(`automation_engineering/generation/models.py`, the test-data generator
build) because Layer 2 emitted nothing to consume at the time — and it
carried `target_class_name`/`target_package` fields that shape did not
actually need Layer 2 to supply. This build is where Layer 2's own emission
was implemented; reconciling the two sides moved this shape here, to
`contracts/` (the SAME shared home `TestableRequirement` itself already
uses for exactly this kind of cross-layer boundary), stripped of the two
Layer-3-only fields, so there is exactly ONE definition both layers
reference — never two drifting copies.

Derivation (Layer 2's own job, not this module's)
-----------------------------------------------------
This module carries the SHAPE only. The DERIVATION — reading
``AcceptanceCriterion.data_fields``/``.polarity_hints`` off a real
``TestableRequirement`` and rolling them up into one specification per
requirement — lives in ``feature_engineering.stage.test_data_spec``, the
Layer 2 stage 14 code that actually produces instances of this shape.
"""

from __future__ import annotations

from pydantic import ConfigDict, Field
from pydantic.alias_generators import to_camel

from contracts.testable_requirement import PolarityHint
from shared.contracts.base import Schema

#: This contract's own version — bumped on a shape change, independent of
#: `contracts.testable_requirement.CONTRACT_VERSION` (a different boundary
#: contract) and `feature_engineering.stage.models.CONTRACT_VERSION` (the
#: Validated Feature Package's own, separate contract).
CONTRACT_VERSION = "1.0.0"


class TestDataFieldSpec(Schema):
    """One field ADR-0043 D7's own prose contract names: "which fields are
    needed, and for each, whether positive/negative/boundary variants are
    required." ``required_variants`` reuses
    :class:`~contracts.testable_requirement.PolarityHint` UNCHANGED
    (ADR-0042) — D7's own text names it explicitly ("seeded by
    ``AcceptanceCriterion.polarity_hints[]``").

    Nothing beyond "field name + which variants" is modeled here — D7's own
    prose contract says no more than that, and adding a Java-type or
    literal-vs-config-driven dimension would be inventing specification
    surface ADR-0043 never locked, not implementing what it did.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    #: Not a test class -- silences pytest's default `Test*` collection
    #: heuristic for a production model that happens to share ADR-0043 D7's
    #: own "test-data" naming.
    __test__ = False

    field_name: str
    required_variants: tuple[PolarityHint, ...] = Field(default_factory=tuple)


class TestDataSpecification(Schema):
    """One requirement's own test-data specification — ADR-0043 D7's
    "handoff contract, not a dataset and not Java," emitted by Layer 2
    (:mod:`feature_engineering.stage.test_data_spec`) and consumed by Layer
    3 (:mod:`automation_engineering.generation.test_data_orchestrator`).

    ``requirement_id`` is carried through for traceability only — this
    shape performs no lookup against it. ``fields`` may be EMPTY: a
    requirement whose real Layer 1 ``data_fields`` is empty AND whose
    statement text carries no #3 Option B enrichment signal either (see
    :mod:`feature_engineering.stage.test_data_spec`'s own module docstring
    for the direct evidence and the enrichment fallback's own account)
    yields an honestly empty specification, never a padded one. As of
    ADR-0043 D10 (additive, 2026-08-28), ``fields`` is no longer
    unconditionally empty on real corpus output — several real requirements
    now derive real fields via that same stopgap enrichment.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    #: Not a test class -- see `TestDataFieldSpec`'s own note above.
    __test__ = False

    requirement_id: str
    fields: tuple[TestDataFieldSpec, ...] = Field(default_factory=tuple)


__all__ = ["CONTRACT_VERSION", "TestDataFieldSpec", "TestDataSpecification"]
