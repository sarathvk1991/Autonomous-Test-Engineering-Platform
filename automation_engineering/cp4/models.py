"""CP4's structured result contract (ADR-0044 D6, ADR-0040 Decision 1/2).

D6 names CP4's own criteria, verbatim: "locator uniqueness, duplicate-
locator detection, dynamic-XPath anti-pattern thresholds, and well-
formedness" -- ALL computed statically from generated page-object SOURCE
alone. D6 is explicit that CP4 has **no live-infrastructure dependency at
all** ("Layer 3 has no running-browser or SUT dependency at all, unlike
CP3 ... which does depend on live infrastructure") -- unlike CP3
(:mod:`automation_engineering.cp3`), CP4 has no adapter seam, no Protocol,
no stub/live split, because there is nothing live to stand in for. Every
criterion here is a pure function of source text.

There is no reuse-percentage analogue for CP4 (unlike CP3's
``Cp3ReuseReport``) -- D6 names no reuse concept for locator health; CP4 is
pure locator health, four gating criteria, nothing reported alongside them
that CONTRIBUTES to ``overall_verdict``.

Mirrors :mod:`automation_engineering.cp3.models`/:mod:`feature_engineering.
cp2.models` deliberately -- same ``<Prefix>CriterionResult``/``<Prefix>Result``
shape, same ``.criterion(name)`` lookup, same ``overall_verdict`` derived
from ``criteria`` alone.

**``Cp4GroundingReport`` (ADR-0044 D10, additive, finding #4) -- REPORT-ONLY,
structurally separate from the four D6 criteria above.** The four criteria
are exhaustively STRUCTURAL (uniqueness, duplication, fragility,
well-formedness) and cannot detect a locator that is well-formed, unique,
and non-fragile yet references NOTHING real on the target SUT (the
fabricated ``//div[@class='method-line-count']`` that passed every D6
criterion cleanly is the finding's own confirmed example). ``Cp4Result.
grounding`` classifies every extracted locator against the same static,
target-keyed ``LOCATOR_CATALOG`` (:mod:`automation_engineering.catalog.
locator_catalog`) finding #1 already uses at generation time -- but it
carries no ``overall_verdict``/``passed`` field anywhere, mirroring
:class:`suite_quality_governance.cp7.models.Cp7WholeSuiteQualityReport`'s
own "no verdict concept for a component that structurally never gates"
shape: nothing in :mod:`.gate` reads ``grounding`` when computing
``overall_verdict``/``passed``, which remain exactly the four-criteria
computation D6 already locked, unchanged by this addition.
"""

from __future__ import annotations

from dataclasses import dataclass

from shared.enums.base import ValidationVerdict

#: D6's own four static criteria, verbatim.
CRITERION_LOCATOR_UNIQUENESS = "locator_uniqueness"
CRITERION_DUPLICATE_LOCATORS = "duplicate_locators"
CRITERION_DYNAMIC_XPATH = "dynamic_xpath"
CRITERION_WELL_FORMEDNESS = "well_formedness"

CP4_CRITERIA: tuple[str, ...] = (
    CRITERION_LOCATOR_UNIQUENESS,
    CRITERION_DUPLICATE_LOCATORS,
    CRITERION_DYNAMIC_XPATH,
    CRITERION_WELL_FORMEDNESS,
)


@dataclass(frozen=True, slots=True)
class Cp4CriterionResult:
    """One CP4 gate criterion's own deterministic verdict -- see
    :class:`automation_engineering.cp3.models.Cp3CriterionResult`, the same
    shape. ``messages`` is empty on a clean ``PASS``, one entry per
    distinct problem on a ``FAIL``.
    """

    criterion: str
    verdict: ValidationVerdict
    messages: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Cp4PageObjectInput:
    """One page object's own real Java source, already scoped by the
    caller as a page object -- CP4 never re-derives "is this a page
    object" classification itself (that is the catalog's own job,
    :mod:`automation_engineering.catalog`); it only gates locator health
    on the source it is handed, mirroring
    :class:`automation_engineering.cp3.models.Cp3FeatureInput`'s own
    "verify what generation already decided" discipline.
    """

    class_name: str
    java_source: str


#: Referential-grounding classification (ADR-0044 D10, finding #4) --
#: REPORT-ONLY (module docstring above): never one of the four D6
#: structural criteria in `CP4_CRITERIA`, and never folds into
#: `Cp4Result.overall_verdict`/`.passed`.
GROUNDING_STATUS_GROUNDED = "grounded"
GROUNDING_STATUS_PLACEHOLDER = "placeholder"
GROUNDING_STATUS_HALLUCINATION = "hallucination"


@dataclass(frozen=True, slots=True)
class Cp4GroundingFinding:
    """One locator's own referential-grounding classification.

    ``status`` is one of :data:`GROUNDING_STATUS_GROUNDED` (a verbatim
    ``LOCATOR_CATALOG`` value -- real), :data:`GROUNDING_STATUS_PLACEHOLDER`
    (the honest ``LOCATOR_PLACEHOLDER_VALUE`` -- the CORRECT output for an
    uncatalogued element, never a defect), or
    :data:`GROUNDING_STATUS_HALLUCINATION` (neither -- a guessed selector
    matching nothing real, the actual defect the four D6 structural
    criteria cannot see).
    """

    class_name: str
    field_name: str
    strategy: str
    value: str
    status: str


@dataclass(frozen=True, slots=True)
class Cp4GroundingReport:
    """CP4's own referential-grounding tally (ADR-0044 D10) -- REPORT-ONLY,
    structurally separate from the four D6 gating criteria (module
    docstring): deliberately no ``overall_verdict``/``passed`` field
    anywhere. A hallucination found here is tallied, never gated.

    ``applicable=False`` (an honest, empty report, never a fabricated
    verdict) whenever no locator catalog was available to classify
    against -- an uncatalogued target, or a run this catalog was never
    wired for -- the identical ``NOT_APPLICABLE`` posture
    :func:`eval_harness.page_object_properties.check_locator_grounding`
    already takes for the same condition.
    """

    applicable: bool
    findings: tuple[Cp4GroundingFinding, ...] = ()

    @property
    def grounded(self) -> tuple[Cp4GroundingFinding, ...]:
        return tuple(f for f in self.findings if f.status == GROUNDING_STATUS_GROUNDED)

    @property
    def placeholders(self) -> tuple[Cp4GroundingFinding, ...]:
        return tuple(f for f in self.findings if f.status == GROUNDING_STATUS_PLACEHOLDER)

    @property
    def hallucinations(self) -> tuple[Cp4GroundingFinding, ...]:
        return tuple(f for f in self.findings if f.status == GROUNDING_STATUS_HALLUCINATION)


@dataclass(frozen=True, slots=True)
class Cp4Result:
    """The single output of one CP4 evaluation
    (:func:`automation_engineering.cp4.gate.evaluate_cp4`).
    ``overall_verdict`` is ``PASS`` iff every one of the four named
    criteria is ``PASS`` -- ``grounding`` (ADR-0044 D10) is a structurally
    separate, report-only field that never contributes to this
    computation, mirroring :class:`suite_quality_governance.cp7.models.
    Cp7WholeSuiteQualityReport`'s own report/gate separation.
    """

    overall_verdict: ValidationVerdict
    criteria: tuple[Cp4CriterionResult, ...]
    grounding: Cp4GroundingReport

    def criterion(self, name: str) -> Cp4CriterionResult:
        """Return the named criterion's result.

        Raises
        ------
        KeyError
            If no criterion with this name was evaluated.
        """
        for c in self.criteria:
            if c.criterion == name:
                return c
        raise KeyError(f"No CP4 criterion named {name!r} in this result.")

    @property
    def passed(self) -> bool:
        return self.overall_verdict == ValidationVerdict.PASS


__all__ = [
    "CP4_CRITERIA",
    "CRITERION_DUPLICATE_LOCATORS",
    "CRITERION_DYNAMIC_XPATH",
    "CRITERION_LOCATOR_UNIQUENESS",
    "CRITERION_WELL_FORMEDNESS",
    "GROUNDING_STATUS_GROUNDED",
    "GROUNDING_STATUS_HALLUCINATION",
    "GROUNDING_STATUS_PLACEHOLDER",
    "Cp4CriterionResult",
    "Cp4GroundingFinding",
    "Cp4GroundingReport",
    "Cp4PageObjectInput",
    "Cp4Result",
]
