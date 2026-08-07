"""The step-definition and page-object orchestrations' own output shapes.

Mirrors :mod:`automation_engineering.reuse.models`'s own discipline exactly:
closed unions, one variant per reuse-engine decision each orchestration
(:mod:`.orchestrator`, :mod:`.page_object_orchestrator`) acts on -- exhaustive,
so a caller (or ``mypy``, via structural matching) cannot silently drop a
case.

Step-definition outcomes: :class:`GeneratedStepDefinition` for NO_MATCH,
:class:`BoundStepDefinition` for TRUSTED_REUSE, :class:`EscalatedStepNeed`
for ESCALATION.

Page-object outcomes (the page-object build's own addition -- the page-object
generator plus the precise method-fit discharge, ADR-0044 D4's clarification
note): :class:`GeneratedPageObject` for NO_MATCH, :class:`BoundPageObjectMethod`
for a TRUSTED_REUSE whose specific method PASSES the precise check,
:class:`EscalatedPageObjectMethodNeed` for either a reuse-engine escalation
OR a TRUSTED_REUSE whose specific method FAILS the precise check.

Utility outcomes (this build's own addition -- utilities get the IDENTICAL
precise method-fit discharge page objects did; see
:mod:`automation_engineering.generation.utility_orchestrator`'s own module
docstring for the usage-pattern investigation that resolved utilities need
it too, not merely "the same treatment by analogy"): :class:`GeneratedUtility`
for NO_MATCH, :class:`BoundUtilityMethod` for a TRUSTED_REUSE whose specific
method PASSES the precise check, :class:`EscalatedUtilityMethodNeed` for
either a reuse-engine escalation OR a TRUSTED_REUSE whose specific method
FAILS the precise check.

Test-data outcomes (BREAKS the pattern above, deliberately):
:class:`GeneratedTestDataClass` is the ONLY outcome -- there is no
:class:`~automation_engineering.reuse.models.TrustedReuse` bind and no
reuse-engine `Escalation` variant here, because test-data is SPEC-DRIVEN,
not reuse-first (see :mod:`.test_data_orchestrator`'s own module docstring
for the investigation that resolved this): a test-data class's own field
set is intrinsically specific to the one requirement/AC that seeded it,
unlike a step-definition/page-object/utility's GENERIC, requirement-
independent capability. ``GeneratedTestDataClass.specification`` is
:class:`~contracts.test_data_specification.TestDataSpecification` -- the
REAL Layer 2 -> Layer 3 boundary contract (`contracts/`, this platform's
existing shared home for exactly this kind of cross-layer shape, the SAME
one :class:`~contracts.testable_requirement.TestableRequirement` uses),
not a Layer-3-only shape defined here: this module originally defined that
shape unilaterally (Layer 2 emitted nothing to consume at the time); it now
lives in `contracts.test_data_specification`, the single definition both
layers reference, since Layer 2's own emission
(:mod:`feature_engineering.stage.test_data_spec`) now exists.
"""

from __future__ import annotations

from dataclasses import dataclass

from automation_engineering.catalog.models import CatalogAsset
from automation_engineering.reuse.models import Escalation, GherkinStepNeed
from contracts.test_data_specification import TestDataSpecification

# ---------------------------------------------------------------------------
# Page-object need
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PageObjectMethodNeed:
    """The page-object action a step definition is ABOUT to call, expressed
    the same way a step's own capture-shape is
    (:class:`~automation_engineering.reuse.models.GherkinStepNeed` --
    ``need.text`` is the semantic-match input, ``need.captures`` is the
    required parameter shape) PLUS ``method_name``: the exact method name
    the generated/bound step-def call site will use.

    ``method_name`` is always CALLER-supplied, never derived from
    ``need.text`` by this platform -- deriving a specific method name from
    natural-language text is exactly the judgement ADR-0044 D4's own
    clarification note says "is not knowable until a future generator
    actually writes that call" (:mod:`.page_object_orchestrator`'s own
    module docstring quotes the note in full). This shape is the input a
    caller who already knows which method a step will invoke supplies to
    get that choice VERIFIED against a reused page object's real inventory,
    the same way :class:`GherkinStepNeed.captures` is a caller-supplied,
    already-derived shape the reuse engine consumes without re-deriving it.

    ``class_name_override`` is a SECOND, optional, additive piece of
    caller-supplied knowledge (default ``None`` -- every pre-existing call
    site's behavior is unchanged): when the caller already knows which
    class this need's own generated code will reference -- because it
    parsed that class name out of an ALREADY-GENERATED step-definition's
    own field declaration, :mod:`.page_object_reference_derivation`'s own
    job -- a fresh page object generated for this need must use THAT exact
    name, never :func:`~.page_object_orchestrator.derive_page_object_class_name`'s
    own independent guess from ``need.text``, which has no way to know what
    a step-def already wrote and could easily disagree with it (a compile-
    breaking class-name mismatch, the same class of defect ``method_name``
    already exists to prevent for method names specifically). ``None``
    (omitted) preserves the prior, sole behavior: the class name is derived
    from ``need.text`` exactly as it always was.
    """

    need: GherkinStepNeed
    method_name: str
    class_name_override: str | None = None


@dataclass(frozen=True, slots=True)
class UtilityMethodNeed:
    """The utility action a step definition is ABOUT to call -- the exact
    same shape as :class:`PageObjectMethodNeed`, for the exact same reason
    (``method_name`` is always CALLER-supplied, never derived from
    ``need.text``; see that class's own docstring). Kept as its own,
    separate type rather than a shared generic -- mirroring this package's
    own established convention of parallel, asset-specific types
    (:class:`GeneratedStepDefinition`/:class:`GeneratedPageObject` are two
    types, not one generic ``GeneratedAsset``) -- so each asset kind's own
    vocabulary stays self-explanatory at the call site.
    """

    need: GherkinStepNeed
    method_name: str


# ---------------------------------------------------------------------------
# Step-definition outcomes
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class GeneratedStepDefinition:
    """ADR-0044 D3's reuse-or-generate boundary's "generate" side, realized:
    one Gherkin step the reuse engine found NO_MATCH for, satisfied by a
    freshly generated Java step-definition (:mod:`.step_definition_generator`'s
    own seam, never regeneration of an existing asset).

    ``page_object_outcome``/``utility_outcome`` are ``None`` unless the
    caller supplied a ``page_object_request``/``utility_request`` to the
    step-def orchestrator (:mod:`.orchestrator`) -- when supplied, each is
    always its own GENERATE/BIND outcome, never its own ESCALATE outcome: a
    page-object-side OR utility-side escalation diverts the WHOLE step to
    :class:`EscalatedStepNeed` instead of reaching this outcome at all (see
    :mod:`.orchestrator`'s own module docstring).
    """

    need: GherkinStepNeed
    java_source: str
    target_package: str
    page_object_outcome: GeneratedPageObject | BoundPageObjectMethod | None = None
    utility_outcome: GeneratedUtility | BoundUtilityMethod | None = None


@dataclass(frozen=True, slots=True)
class BoundStepDefinition:
    """A Gherkin step whose reuse binding was trusted (ADR-0044 D4) --
    bound to an existing catalog asset, never regenerated. ``asset`` is the
    same :class:`~automation_engineering.reuse.models.TrustedReuse.asset`
    the reuse engine resolved -- always a
    :class:`~automation_engineering.catalog.models.StepDefinitionAsset` in
    this task's own orchestration, since the matcher this task wires in
    (:class:`~automation_engineering.reuse.matcher.SemanticMatcher`) only
    ever matches a step-need against catalogued step definitions (see
    :mod:`automation_engineering.reuse.live_matcher`'s own docstring: "Only
    step definitions are matched").
    """

    need: GherkinStepNeed
    asset: CatalogAsset


@dataclass(frozen=True, slots=True)
class EscalatedStepNeed:
    """A Gherkin step whose reuse candidate failed one of ADR-0044 D4's three
    checks -- neither generated nor bound, surfaced for human review via the
    same plain-record discipline every other layer's escalation already uses
    (:mod:`automation_engineering.reuse.engine`'s own module docstring:
    "no new queue, no new mechanism, built here"). ``escalation`` is either
    the reuse engine's own :class:`~automation_engineering.reuse.models.Escalation`
    record, unedited, OR the precise method-fit discharge's own
    :class:`~automation_engineering.reuse.models.Escalation` (this build's
    addition, :mod:`automation_engineering.generation.method_fit`) when a
    step's own reuse was fine but its required PAGE-OBJECT call was not --
    this variant only re-homes whichever it is under this orchestration's
    own result vocabulary, it does not re-decide anything.
    """

    need: GherkinStepNeed
    escalation: Escalation


#: ADR-0044 D3's reuse-or-generate-or-escalate vocabulary, realized for the
#: step-definition generator specifically. A caller handles all three; there
#: is no fourth case.
StepDefinitionOutcome = GeneratedStepDefinition | BoundStepDefinition | EscalatedStepNeed


# ---------------------------------------------------------------------------
# Page-object outcomes (this build)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class GeneratedPageObject:
    """ADR-0044 D3's reuse-or-generate boundary's "generate" side, for page
    objects: no catalogued page object even coarsely matched the need, so a
    brand-new page object is generated (:mod:`.page_object_generator`'s own
    seam). ``class_name`` is the deterministically derived name
    (:func:`~.page_object_orchestrator.derive_page_object_class_name`) the
    generation context instructed the seam to use -- informational, not
    re-parsed out of ``java_source`` after the fact, the same trust level
    the step-definition generator already places in its own naming
    convention without parsing generated code back.
    """

    method_need: PageObjectMethodNeed
    java_source: str
    target_package: str
    class_name: str


@dataclass(frozen=True, slots=True)
class BoundPageObjectMethod:
    """A page-object need whose reuse binding was trusted by ALL of ADR-0044
    D4(a)/(b)/(c) -- (c) now fully realized for page objects: the COARSE
    class-compatibility screen at decision time
    (`automation_engineering.reuse.engine._check_method_fit`) AND the
    PRECISE, specific-method check at generation time
    (:mod:`automation_engineering.generation.method_fit`, this build). Never
    regenerated. ``asset`` is the same
    :class:`~automation_engineering.reuse.models.TrustedReuse.asset` the
    reuse engine resolved -- a
    :class:`~automation_engineering.catalog.models.PageObjectAsset` in
    practice, since this orchestration's own matcher only ever matches a
    page-object need against ``catalog.page_objects``.
    """

    method_need: PageObjectMethodNeed
    asset: CatalogAsset


@dataclass(frozen=True, slots=True)
class EscalatedPageObjectMethodNeed:
    """A page-object need that was neither generated nor bound -- either the
    reuse engine's own three checks (a)/(b)/(c)-coarse failed (``escalation``
    is the reuse engine's own, unedited :class:`~automation_engineering.reuse.models.Escalation`),
    OR the coarse screen passed but the PRECISE method-fit discharge
    (:mod:`automation_engineering.generation.method_fit`) found the reused
    class lacks the SPECIFIC method this need requires -- the exact gap
    ADR-0044 D4's clarification note recorded as this build's own obligation
    to close. Both routes produce the identical
    :class:`~automation_engineering.reuse.models.Escalation` shape, carried
    through unedited to the same human-in-the-loop surface every other
    escalation in this platform already uses.
    """

    method_need: PageObjectMethodNeed
    escalation: Escalation


#: ADR-0044 D3's reuse-or-generate-or-escalate vocabulary, realized for the
#: page-object generator, WITH check (c) now fully realized (coarse +
#: precise) rather than coarse-only. A caller handles all three; there is no
#: fourth case.
PageObjectMethodOutcome = (
    GeneratedPageObject | BoundPageObjectMethod | EscalatedPageObjectMethodNeed
)


# ---------------------------------------------------------------------------
# Utility outcomes (this build)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class GeneratedUtility:
    """ADR-0044 D3's reuse-or-generate boundary's "generate" side, for
    utilities: no catalogued utility even coarsely matched the need, so a
    brand-new utility class is generated (:mod:`.utility_generator`'s own
    seam). ``class_name`` is the deterministically derived name
    (:func:`~.utility_orchestrator.derive_utility_class_name`) the
    generation context instructed the seam to use -- informational, the
    same trust level :class:`GeneratedPageObject.class_name` already uses.
    """

    method_need: UtilityMethodNeed
    java_source: str
    target_package: str
    class_name: str


@dataclass(frozen=True, slots=True)
class BoundUtilityMethod:
    """A utility need whose reuse binding was trusted by ALL of ADR-0044
    D4(a)/(b)/(c) -- (c) fully realized for utilities exactly as it is for
    page objects: the COARSE class-compatibility screen at decision time
    (`automation_engineering.reuse.engine._check_method_fit`) AND the
    PRECISE, specific-method check at generation time
    (:mod:`automation_engineering.generation.method_fit`, reused unchanged
    -- it was already written generically over ``PageObjectAsset |
    UtilityAsset``). Never regenerated. ``asset`` is the same
    :class:`~automation_engineering.reuse.models.TrustedReuse.asset` the
    reuse engine resolved -- a
    :class:`~automation_engineering.catalog.models.UtilityAsset` in
    practice, since this orchestration's own matcher only ever matches a
    utility need against ``catalog.utilities``.
    """

    method_need: UtilityMethodNeed
    asset: CatalogAsset


@dataclass(frozen=True, slots=True)
class EscalatedUtilityMethodNeed:
    """A utility need that was neither generated nor bound -- either the
    reuse engine's own three checks (a)/(b)/(c)-coarse failed, OR the coarse
    screen passed but the PRECISE method-fit discharge
    (:mod:`automation_engineering.generation.method_fit`) found the reused
    class lacks the SPECIFIC method this need requires -- this build's own
    resolution of the obligation the page-object build's clarification note
    left open for utilities ("that remains the next task's own obligation
    to discharge"). Both routes produce the identical
    :class:`~automation_engineering.reuse.models.Escalation` shape.
    """

    method_need: UtilityMethodNeed
    escalation: Escalation


#: ADR-0044 D3's reuse-or-generate-or-escalate vocabulary, realized for the
#: utility generator, WITH check (c) fully realized (coarse + precise) --
#: the same completeness page objects already have. A caller handles all
#: three; there is no fourth case.
UtilityMethodOutcome = GeneratedUtility | BoundUtilityMethod | EscalatedUtilityMethodNeed


# ---------------------------------------------------------------------------
# Test-data outcome (this build -- breaks the pattern above)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class GeneratedTestDataClass:
    """The ONLY test-data outcome -- see module docstring for why there is
    no bind/escalate variant here (test-data is SPEC-DRIVEN, not
    reuse-first; ADR-0044 D3's reuse-first discipline does not apply to
    this asset kind). ``specification`` is the REAL
    :class:`~contracts.test_data_specification.TestDataSpecification` Layer
    2 emitted (:mod:`feature_engineering.stage.test_data_spec`) -- not a
    Layer-3-only shape. ``class_name``/``target_package`` are Layer 3's OWN
    derivation (:func:`~.test_data_orchestrator.derive_test_data_class_name`),
    computed from ``specification.requirement_id`` at generation time, never
    carried on the specification itself -- Layer 2's own contract stays
    Java-shape-free, per ADR-0043 D7's own "not a dataset and not Java."
    """

    #: Not a test class -- silences pytest's default `Test*` collection
    #: heuristic for a production dataclass that happens to share ADR-0043
    #: D7's own "test-data" naming.
    __test__ = False

    specification: TestDataSpecification
    java_source: str
    target_package: str
    class_name: str


__all__ = [
    "BoundPageObjectMethod",
    "BoundStepDefinition",
    "BoundUtilityMethod",
    "EscalatedPageObjectMethodNeed",
    "EscalatedStepNeed",
    "EscalatedUtilityMethodNeed",
    "GeneratedPageObject",
    "GeneratedStepDefinition",
    "GeneratedTestDataClass",
    "GeneratedUtility",
    "PageObjectMethodNeed",
    "PageObjectMethodOutcome",
    "StepDefinitionOutcome",
    "UtilityMethodNeed",
    "UtilityMethodOutcome",
]
