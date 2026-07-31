"""CP4 -- static locator health (ADR-0044 D6). Four criteria, all pure
functions of extracted locator data (:mod:`.extraction`); this module never
imports a browser/WebDriver library, never opens a network socket, never
reads an environment variable naming a SUT. If a check here ever needed a
running page to answer ("does this locator match a real element"), it
would have moved Layer 5's job into Layer 3 -- D6's own boundary,
structural here: nothing in this module accepts a driver, a URL, or a SUT
connection as an input, so there is no seam through which a live call
could even be threaded in by a future edit without changing this module's
own function signatures first.

Four named criteria, matching D6's own four verbatim:

* ``locator_uniqueness`` -- INTRA-class: no two DIFFERENT fields on the
  SAME page object share an identical (strategy, value) locator. A single
  field referenced from multiple methods is not a violation (there is only
  ONE field declaration to begin with) -- this criterion fires only on
  TWO OR MORE distinct field *declarations* colliding, the actual bug this
  check exists to catch (a copy-paste error naming two "different"
  elements that are actually the same selector, or worse, the wrong
  selector copied onto a second field).
* ``duplicate_locators`` -- CROSS-class, over every page object in one CP4
  run (mirroring :func:`automation_engineering.cp3.coverage._find_duplicate_patterns`'s
  own cross-asset, not per-artifact, scope): the identical (strategy,
  value) locator declared on TWO OR MORE DIFFERENT classes. A collision
  already reported by ``locator_uniqueness`` (same class) is excluded here
  -- each fact is reported by exactly one criterion, never both, so a
  test can prove they fail independently (this task's own requirement).
* ``dynamic_xpath`` -- fragile locators: absolute XPath, indexed/
  positional XPath predicates, and auto-generated-id-shaped values
  (regardless of strategy -- an unstable framework-generated id is
  fragile whether it is selected via ``By.id`` or embedded in an XPath
  ``@id`` predicate). See :data:`_ABSOLUTE_XPATH_RE`/:data:`_INDEXED_XPATH_RE`/
  :func:`_looks_auto_generated` for the exact, defined anti-pattern set.
* ``well_formedness`` -- syntactic validity: non-empty, balanced
  brackets/parens/quotes. This is a STRUCTURAL check, not a full XPath/CSS
  grammar validator (which would require a new parser dependency, out of
  scope) -- it catches truncated/malformed strings (a real, observed LLM
  failure mode: an unclosed bracket or quote), not every way a selector
  could fail to compile.
"""

from __future__ import annotations

import re
from collections import defaultdict

from automation_engineering.cp4.extraction import Cp4Locator, extract_locators
from automation_engineering.cp4.models import (
    CRITERION_DUPLICATE_LOCATORS,
    CRITERION_DYNAMIC_XPATH,
    CRITERION_LOCATOR_UNIQUENESS,
    CRITERION_WELL_FORMEDNESS,
    Cp4CriterionResult,
    Cp4PageObjectInput,
    Cp4Result,
)
from shared.enums.base import ValidationVerdict

#: A single leading `/` not followed by a second `/` -- an absolute path
#: from the document root, tied to the DOM's exact structural depth.
_ABSOLUTE_XPATH_RE = re.compile(r"^/[^/]")
#: A bracketed integer index (`[3]`) or the `position()`/`last()`
#: functions -- positional predicates that break when sibling order or
#: count changes, the literal "dynamic" fragility D6's own name describes.
_INDEXED_XPATH_RE = re.compile(r"\[\s*\d+\s*\]|position\s*\(\s*\)|last\s*\(\s*\)")
#: Four or more consecutive digits, OR a UUID-shaped token -- a heuristic
#: for a framework/auto-generated identifier, not a perfect classifier
#: (documented as a heuristic, not overclaimed as exhaustive).
_LONG_DIGIT_RUN_RE = re.compile(r"\d{4,}")
_UUID_RE = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)


def _looks_auto_generated(value: str) -> bool:
    return bool(_LONG_DIGIT_RUN_RE.search(value) or _UUID_RE.search(value))


def _locator_label(locator: Cp4Locator) -> str:
    return f"{locator.class_name}.{locator.field_name} ({locator.strategy}={locator.value!r})"


def _evaluate_uniqueness(
    locators_by_class: dict[str, tuple[Cp4Locator, ...]],
) -> Cp4CriterionResult:
    messages: list[str] = []
    for class_name, locators in locators_by_class.items():
        by_key: dict[tuple[str, str], list[Cp4Locator]] = defaultdict(list)
        for locator in locators:
            by_key[(locator.strategy, locator.value)].append(locator)
        for (strategy, value), group in sorted(by_key.items()):
            if len(group) > 1:
                fields = ", ".join(sorted(loc.field_name for loc in group))
                messages.append(
                    f"{class_name}: fields [{fields}] share the identical locator "
                    f"{strategy}={value!r}"
                )
    verdict = ValidationVerdict.FAIL if messages else ValidationVerdict.PASS
    return Cp4CriterionResult(
        criterion=CRITERION_LOCATOR_UNIQUENESS, verdict=verdict, messages=tuple(messages)
    )


def _evaluate_duplicates(all_locators: tuple[Cp4Locator, ...]) -> Cp4CriterionResult:
    by_key: dict[tuple[str, str], list[Cp4Locator]] = defaultdict(list)
    for locator in all_locators:
        by_key[(locator.strategy, locator.value)].append(locator)
    messages: list[str] = []
    for (strategy, value), group in sorted(by_key.items()):
        classes = {loc.class_name for loc in group}
        if len(classes) > 1:
            labels = ", ".join(_locator_label(loc) for loc in group)
            messages.append(
                f"locator {strategy}={value!r} declared on {len(classes)} different "
                f"page objects: {labels}"
            )
    verdict = ValidationVerdict.FAIL if messages else ValidationVerdict.PASS
    return Cp4CriterionResult(
        criterion=CRITERION_DUPLICATE_LOCATORS, verdict=verdict, messages=tuple(messages)
    )


def _evaluate_dynamic_xpath(all_locators: tuple[Cp4Locator, ...]) -> Cp4CriterionResult:
    messages: list[str] = []
    for locator in all_locators:
        if locator.strategy == "xpath":
            if _ABSOLUTE_XPATH_RE.match(locator.value):
                messages.append(
                    f"{_locator_label(locator)}: absolute XPath (tied to document root)"
                )
            if _INDEXED_XPATH_RE.search(locator.value):
                messages.append(
                    f"{_locator_label(locator)}: positional/indexed XPath predicate "
                    "(breaks when sibling order or count changes)"
                )
        if _looks_auto_generated(locator.value):
            messages.append(
                f"{_locator_label(locator)}: value looks auto-generated "
                "(numeric/UUID pattern suggests a framework-generated, unstable id)"
            )
    verdict = ValidationVerdict.FAIL if messages else ValidationVerdict.PASS
    return Cp4CriterionResult(
        criterion=CRITERION_DYNAMIC_XPATH, verdict=verdict, messages=tuple(messages)
    )


def _balanced(value: str, open_char: str, close_char: str) -> bool:
    return value.count(open_char) == value.count(close_char)


def _is_well_formed(locator: Cp4Locator) -> str | None:
    """Returns a failure reason, or ``None`` if `locator` is well-formed."""
    if not locator.value.strip():
        return "empty locator value"
    if "\n" in locator.value or "\t" in locator.value:
        return "locator value contains a raw newline/tab (likely a truncated string)"
    if not _balanced(locator.value, "[", "]"):
        return "unbalanced [ ] brackets"
    if not _balanced(locator.value, "(", ")"):
        return "unbalanced ( ) parentheses"
    if locator.value.count('"') % 2 != 0:
        return "unbalanced double quotes"
    if locator.value.count("'") % 2 != 0:
        return "unbalanced single quotes"
    return None


def _evaluate_well_formedness(all_locators: tuple[Cp4Locator, ...]) -> Cp4CriterionResult:
    messages: list[str] = []
    for locator in all_locators:
        reason = _is_well_formed(locator)
        if reason is not None:
            messages.append(f"{_locator_label(locator)}: {reason}")
    verdict = ValidationVerdict.FAIL if messages else ValidationVerdict.PASS
    return Cp4CriterionResult(
        criterion=CRITERION_WELL_FORMEDNESS, verdict=verdict, messages=tuple(messages)
    )


def evaluate_cp4(page_objects: tuple[Cp4PageObjectInput, ...]) -> Cp4Result:
    """Evaluate CP4's four static locator-health criteria over every page
    object in `page_objects`.

    Pure and deterministic: no network call, no subprocess, no file I/O
    beyond reading the already-in-memory `java_source` strings this
    function is handed. The same input always yields the same result.
    """
    locators_by_class: dict[str, tuple[Cp4Locator, ...]] = {
        page_object.class_name: extract_locators(page_object) for page_object in page_objects
    }
    all_locators = tuple(loc for locators in locators_by_class.values() for loc in locators)

    criteria = (
        _evaluate_uniqueness(locators_by_class),
        _evaluate_duplicates(all_locators),
        _evaluate_dynamic_xpath(all_locators),
        _evaluate_well_formedness(all_locators),
    )
    overall = (
        ValidationVerdict.PASS
        if all(c.verdict == ValidationVerdict.PASS for c in criteria)
        else ValidationVerdict.FAIL
    )
    return Cp4Result(overall_verdict=overall, criteria=criteria)


__all__ = ["evaluate_cp4"]
