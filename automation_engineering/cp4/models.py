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
pure locator health, four gating criteria, nothing reported alongside them.

Mirrors :mod:`automation_engineering.cp3.models`/:mod:`feature_engineering.
cp2.models` deliberately -- same ``<Prefix>CriterionResult``/``<Prefix>Result``
shape, same ``.criterion(name)`` lookup, same ``overall_verdict`` derived
from ``criteria`` alone.
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


@dataclass(frozen=True, slots=True)
class Cp4Result:
    """The single output of one CP4 evaluation
    (:func:`automation_engineering.cp4.gate.evaluate_cp4`).
    ``overall_verdict`` is ``PASS`` iff every one of the four named
    criteria is ``PASS``.
    """

    overall_verdict: ValidationVerdict
    criteria: tuple[Cp4CriterionResult, ...]

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
    "Cp4CriterionResult",
    "Cp4PageObjectInput",
    "Cp4Result",
]
