"""Test-data generation from Layer 2's own specification (ADR-0044 D7) --
the fourth Layer 3 generator, and the one that BREAKS the pattern the other
three (step definitions, page objects, utilities) share.

THE INPUT-SHAPE BREAK
----------------------
The other three generators consume a
:class:`~automation_engineering.reuse.models.GherkinStepNeed` -- semantic
action text matched against a reuse catalog. This generator consumes a
:class:`~contracts.test_data_specification.TestDataSpecification`: "which
fields are needed, and for each, whether positive/negative/boundary
variants are required" (ADR-0043 D7's own words). There is no Gherkin
action text here at all -- a test-data specification names FIELDS, not an
ACTION, so there is nothing for a semantic matcher to compare against.

**Layer 2 now implements emission of this specification.** A prior build
found no `TestDataSpec`/`test_data_spec`-shaped code anywhere in
`feature_engineering/` and defined this shape unilaterally, on the
consuming side, to build and prove this generator against ADR-0043 D7's
own prose contract without a real emission to consume. THIS build
implements that emission
(:mod:`feature_engineering.stage.test_data_spec`) and reconciles the two
sides: `TestDataSpecification`/`TestDataFieldSpec` now live in
`contracts.test_data_specification` -- the SAME shared home
:class:`~contracts.testable_requirement.TestableRequirement` itself uses
for its own Layer 1 -> Layer 2 boundary -- with no Java-shape fields at
all (`target_class_name`/`target_package` moved OUT of the shared contract
and into this module's own :func:`derive_test_data_class_name`, since
Layer 2 has no business deciding Java naming). The real end-to-end path
(Layer 2 emits a real specification -> Layer 3 generates a real class) is
now genuinely exercisable -- proven directly against the saucedemo corpus
(see the accompanying report for what that corpus's own real
`polarity_hints`/`data_fields` actually contain, honestly, not padded).

THE REUSE QUESTION -- resolved, not assumed: test-data is SPEC-DRIVEN
------------------------------------------------------------------------
The other three generators are reuse-first (ADR-0044 D3): NO_MATCH
generates, TRUSTED_REUSE binds, ESCALATION surfaces. This module never
calls :func:`automation_engineering.reuse.engine.decide_reuse` at all --
every specification is generated, every time. Two independent lines of
evidence support this, not assumption by analogy to the triad:

1. **Structural.** `automation_engineering.catalog.models.AssetKind` names
   exactly three reusable-asset kinds -- `STEP_DEFINITION`, `PAGE_OBJECT`,
   `UTILITY` -- its own docstring: "The three reusable-asset kinds ADR-0044
   D1 names as Layer 3 output." There is no fourth, `TEST_DATA` kind. The
   reuse catalog (D3) was never built to track this asset kind at all.
2. **ADR-0044 D1's own listing.** The Validated Automation Package is
   named as "step definitions, page objects, utility classes, Java
   test-data classes (D7, below)" -- test-data classes are named SEPARATELY
   from the reuse-tracked trio, with their own, distinct decision (D7)
   governing them, never folded into D3's reuse-first discipline.
3. **Practical.** A test-data class's own field set is intrinsically
   specific to the ONE requirement/AC that seeded it (D7's own "seeded by
   `AcceptanceCriterion.polarity_hints[]`") -- unlike a step-definition's
   action, a page-object's UI capability, or a utility's stateless helper
   (a config accessor, a date formatter), none of which are tied to any
   one requirement. A GENUINELY generic, reusable data ACCESSOR (the
   platform's own real example, `ConfigReader`) is already a UTILITY,
   already reuse-tracked by the prior build -- it is not what D7's own
   "test-data class" names. The two concepts do not overlap; requirement-
   specific field bundling is precisely what reuse-matching has nothing to
   offer.

THE ENV/DATA BOUNDARY -- enforced, not merely requested
------------------------------------------------------------
ADR-0037 D3 locks the SUT-binding boundary: no test-data class may itself
resolve an environment URL or credential (`ConfigReader.env()`'s job,
never a generated test-data class's). ADR-0044 D7 restates it: "the
generated `DataProvider` output is `data()`-shaped content, not
`env()`-shaped." The registered prompt's own CONSTRAINTS section asks for
this (born compliant, ADR-0044 D5's discipline) -- but this module does
NOT stop at asking. :func:`_check_no_env_binding` is a deterministic,
orchestration-level guard that scans whatever the seam returns (stub OR
live) for a `ConfigReader.env(...)` call or an `env.`-prefixed config-key
literal, and RAISES rather than silently returning a boundary-violating
class -- the same "never a silent fallback" discipline ADR-0044 D4's own
reuse-safety model uses, applied here to the SUT-binding boundary instead.
This is a real, cheap, always-on check this generator can honestly provide
alongside the prompt's own constraint; it is not a substitute for CP3's
Sonar scan (a later, out-of-scope task) -- it catches exactly one
structural pattern, not general code quality.
"""

from __future__ import annotations

import re
from collections.abc import Sequence

from automation_engineering.generation.models import GeneratedTestDataClass
from automation_engineering.generation.test_data_generator import (
    TestDataGenerationContext,
    TestDataGenerator,
)
from contracts.test_data_specification import TestDataSpecification

_WORD_RE = re.compile(r"[A-Za-z0-9]+")

#: ADR-0044 D7's own package lock -- the SAME package generic utilities
#: target (`automation_engineering.generation.utility_orchestrator.
#: DEFAULT_UTILITY_TARGET_PACKAGE`), not a package this build invents.
DEFAULT_TEST_DATA_TARGET_PACKAGE = "com.automation.utils"

#: ADR-0044 D5's "constrain at generation" -- ONLY `customqa:long-method` is
#: evidenced as applicable (`requirement_intelligence/input/sonar/
#: sonar-issues.json`, the same fixture every Layer 3 constraint set cites).
#: `customqa:direct-webdriver-action` is not injected: test-data classes
#: never touch WebDriver, the identical reasoning
#: `utility_orchestrator.DEFAULT_CUSTOMQA_UTILITY_CONSTRAINTS` already
#: established for generic utilities.
DEFAULT_CUSTOMQA_TEST_DATA_CONSTRAINTS: tuple[str, ...] = (
    "customqa:long-method -- keep every generated method under 40 lines; "
    "split a multi-field class into focused, single-concern accessors.",
)

_ENV_BINDING_PATTERN = re.compile(r"ConfigReader\s*\.\s*env\s*\(|[\"']env\.[A-Za-z0-9_.]*[\"']")


class TestDataBoundaryError(Exception):
    """Raised when generated test-data source crosses ADR-0037 D3's
    SUT-binding boundary -- a `ConfigReader.env(...)` call, or a literal
    `env.`-prefixed config-key reference, found in output that must be
    DATA-side only. Never silently dropped or corrected; the caller sees
    exactly what violated the boundary and where."""

    #: Not a test class -- silences pytest's default `Test*` collection
    #: heuristic for a production exception that happens to share ADR-0043
    #: D7's own "test-data" naming.
    __test__ = False


def derive_test_data_class_name(requirement_id: str) -> str:
    """Deterministic UpperCamelCase + ``TestData`` derivation from a
    specification's own ``requirement_id`` -- Layer 3's OWN naming
    decision, mirroring
    :func:`~.page_object_orchestrator.derive_page_object_class_name`/
    :func:`~.utility_orchestrator.derive_utility_class_name` exactly, and
    for the same reason those exist: `contracts.test_data_specification`
    carries no Java-shape fields at all (ADR-0043 D7's own "not a dataset
    and not Java"), so naming the generated class is entirely this
    orchestrator's own job, never something Layer 2's specification
    supplies.

    Unlike the action-text-derived names the other two `derive_*`
    functions produce, a `requirement_id` is a platform-minted,
    content-addressed identifier (ADR-0042 Decision 2 -- short, hash-based,
    not human-readable prose), so the derived name is correspondingly
    plain (e.g. ``"REQ-8604e1d3"`` -> ``"Req8604e1d3TestData"``) --
    deterministic and always available, not a fabricated business name the
    specification's own data does not support.
    """
    words = _WORD_RE.findall(requirement_id)
    return "".join(word.capitalize() for word in words) + "TestData"


def _check_no_env_binding(java_source: str) -> None:
    match = _ENV_BINDING_PATTERN.search(java_source)
    if match is not None:
        raise TestDataBoundaryError(
            f"generated test-data source references environment/SUT-binding "
            f"({match.group()!r}) -- test-data classes are the DATA side of "
            "ADR-0037 D3's SUT-binding boundary; ConfigReader.env(...) and env.* "
            "config keys stay ConfigReader.env()'s job, never a generated "
            "test-data class's."
        )


def generate_test_data_class(
    specification: TestDataSpecification,
    generator: TestDataGenerator,
    *,
    target_package: str = DEFAULT_TEST_DATA_TARGET_PACKAGE,
    customqa_constraints: tuple[str, ...] = DEFAULT_CUSTOMQA_TEST_DATA_CONSTRAINTS,
) -> GeneratedTestDataClass:
    """Generate ONE Java test-data class from ``specification``.

    Always generates -- there is no reuse decision, no bind, no escalate
    (see module docstring, "THE REUSE QUESTION"). The env/data boundary is
    enforced deterministically (:func:`_check_no_env_binding`) on whatever
    the seam returns before this function ever returns a result, so a
    caller never receives a boundary-violating class, from a stub or a
    live generator alike.

    Raises
    ------
    TestDataBoundaryError
        If the generated source crosses the SUT-binding boundary.
    """
    class_name = derive_test_data_class_name(specification.requirement_id)
    context = TestDataGenerationContext(
        specification=specification,
        class_name=class_name,
        target_package=target_package,
        customqa_constraints=customqa_constraints,
    )
    java_source = generator.generate(context)
    _check_no_env_binding(java_source)
    return GeneratedTestDataClass(
        specification=specification,
        java_source=java_source,
        target_package=target_package,
        class_name=class_name,
        generation_identity=getattr(generator, "last_identity", None),
    )


def generate_test_data_classes(
    specifications: Sequence[TestDataSpecification],
    generator: TestDataGenerator,
    *,
    target_package: str = DEFAULT_TEST_DATA_TARGET_PACKAGE,
    customqa_constraints: tuple[str, ...] = DEFAULT_CUSTOMQA_TEST_DATA_CONSTRAINTS,
) -> tuple[GeneratedTestDataClass, ...]:
    """Generate one Java test-data class per specification, in order."""
    return tuple(
        generate_test_data_class(
            specification,
            generator,
            target_package=target_package,
            customqa_constraints=customqa_constraints,
        )
        for specification in specifications
    )


__all__ = [
    "DEFAULT_CUSTOMQA_TEST_DATA_CONSTRAINTS",
    "DEFAULT_TEST_DATA_TARGET_PACKAGE",
    "TestDataBoundaryError",
    "derive_test_data_class_name",
    "generate_test_data_class",
    "generate_test_data_classes",
]
