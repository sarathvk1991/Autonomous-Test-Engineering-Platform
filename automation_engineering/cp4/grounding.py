"""CP4's own report-only referential-grounding tally (ADR-0044 D10 --
finding #4). Detects the defect class the four D6 structural criteria
(:mod:`.gate`) cannot: a locator that is well-formed, unique, and
non-fragile, yet references NOTHING real on the target SUT (the
fabricated ``//div[@class='method-line-count']`` that passed every D6
criterion cleanly is the finding's own confirmed example).

Ports :func:`eval_harness.page_object_properties.check_locator_grounding`'s
own three-way classification -- real (a verbatim ``LOCATOR_CATALOG``
match), honest placeholder (``LOCATOR_PLACEHOLDER_VALUE``, the CORRECT
output for an uncatalogued element, never a defect), or hallucination
(neither) -- into CP4 itself, over the SAME extracted ``(strategy, value)``
locators :mod:`.gate` already computes for the four structural criteria,
rather than only at :mod:`eval_harness`'s own offline-corpus remove.
Matching is VALUE-only, exactly mirroring ``check_locator_grounding``'s own
logic (it never compares strategy) -- a locator's normalized ``strategy``
(:mod:`.extraction`'s own ``cssSelector`` -> ``css`` canonicalization) is
carried on :class:`~automation_engineering.cp4.models.Cp4GroundingFinding`
for display only, never used to decide grounding status.

**REPORT-ONLY, structurally (mirrors `suite_quality_governance.cp7`'s own
`Cp7WholeSuiteQualityReport`).** This module never contributes to
``Cp4Result.overall_verdict``/``.passed`` -- see :mod:`.models`' own
``Cp4GroundingReport`` docstring. Static-catalog only: this module never
imports a browser/WebDriver library, opens a network socket, or reads an
environment variable naming a SUT -- the identical D6 purity :mod:`.gate`'s
own module docstring already establishes, extended to a fifth, additive,
non-gating criterion rather than redesigning the four D6 names.
"""

from __future__ import annotations

from automation_engineering.catalog.locator_catalog import (
    LOCATOR_PLACEHOLDER_VALUE,
    LocatorCatalogEntry,
)
from automation_engineering.cp4.extraction import Cp4Locator
from automation_engineering.cp4.models import (
    GROUNDING_STATUS_GROUNDED,
    GROUNDING_STATUS_HALLUCINATION,
    GROUNDING_STATUS_PLACEHOLDER,
    Cp4GroundingFinding,
    Cp4GroundingReport,
)


def _classify(value: str, catalog_values: frozenset[str]) -> str:
    if value == LOCATOR_PLACEHOLDER_VALUE:
        return GROUNDING_STATUS_PLACEHOLDER
    if value in catalog_values:
        return GROUNDING_STATUS_GROUNDED
    return GROUNDING_STATUS_HALLUCINATION


def evaluate_cp4_grounding(
    all_locators: tuple[Cp4Locator, ...],
    locator_catalog: tuple[LocatorCatalogEntry, ...] = (),
) -> Cp4GroundingReport:
    """Classify every locator in `all_locators` against `locator_catalog`
    -- REPORT-ONLY (module docstring): never raises, never fails, never
    feeds `Cp4Result.overall_verdict`.

    `applicable=False` (an honest, empty `Cp4GroundingReport`, never a
    fabricated verdict) when `locator_catalog` is empty -- an uncatalogued
    target (or a run this catalog was never wired for) offers no grounding
    to check compliance against, the identical `NOT_APPLICABLE` posture
    `eval_harness.page_object_properties.check_locator_grounding` already
    takes for the same condition.
    """
    if not locator_catalog:
        return Cp4GroundingReport(applicable=False, findings=())
    catalog_values = frozenset(entry.value for entry in locator_catalog)
    findings = tuple(
        Cp4GroundingFinding(
            class_name=locator.class_name,
            field_name=locator.field_name,
            strategy=locator.strategy,
            value=locator.value,
            status=_classify(locator.value, catalog_values),
        )
        for locator in all_locators
    )
    return Cp4GroundingReport(applicable=True, findings=findings)


__all__ = ["evaluate_cp4_grounding"]
