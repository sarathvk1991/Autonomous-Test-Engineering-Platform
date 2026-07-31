"""Layer 3's CP4 -- static locator health (ADR-0044 D6, ADR-0040 Decision
1/2).

Four criteria, all pure functions of generated page-object SOURCE text
alone -- ``locator_uniqueness``, ``duplicate_locators``, ``dynamic_xpath``,
``well_formedness`` (D6's own four, verbatim). **No running browser, no
SUT, no infrastructure of any kind** -- unlike CP3 (:mod:`automation_engineering.
cp3`), which hard-requires a live SonarQube server, CP4 has no adapter seam
at all, because there is nothing live to stand in for.

"Does this locator actually match a real element on a running page" is
explicitly **not** CP4's job (D6) -- that is Layer 5's runtime concern,
exercised against a real SUT once the suite executes. CP4 must not acquire
a browser/SUT dependency; nothing in this package accepts a driver, a URL,
or a SUT connection as an input.

This module builds ONLY CP4. It does not build promotion (workspace ->
tracked baseline, ADR-0045) -- out of scope here.
"""

from __future__ import annotations

from automation_engineering.cp4.extraction import Cp4Locator, extract_locators
from automation_engineering.cp4.gate import evaluate_cp4
from automation_engineering.cp4.models import (
    CP4_CRITERIA,
    CRITERION_DUPLICATE_LOCATORS,
    CRITERION_DYNAMIC_XPATH,
    CRITERION_LOCATOR_UNIQUENESS,
    CRITERION_WELL_FORMEDNESS,
    Cp4CriterionResult,
    Cp4PageObjectInput,
    Cp4Result,
)

__all__ = [
    "CP4_CRITERIA",
    "CRITERION_DUPLICATE_LOCATORS",
    "CRITERION_DYNAMIC_XPATH",
    "CRITERION_LOCATOR_UNIQUENESS",
    "CRITERION_WELL_FORMEDNESS",
    "Cp4CriterionResult",
    "Cp4Locator",
    "Cp4PageObjectInput",
    "Cp4Result",
    "evaluate_cp4",
    "extract_locators",
]
