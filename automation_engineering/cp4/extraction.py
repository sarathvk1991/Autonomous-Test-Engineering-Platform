"""Locator extraction from page-object Java source (ADR-0044 D6).

The catalog (:mod:`automation_engineering.catalog`) already detects WHICH
fields are locators (`JavaField.is_locator`, `is_locator_field` in
:mod:`automation_engineering.catalog.java_source`) but never records the
locator's own STRATEGY (id/xpath/css/...) or VALUE (the selector string) --
it only needs to know a field IS a locator for its own identity/reuse
purposes, never what the locator actually selects. CP4 needs exactly that
value, so this module extracts it directly, reusing the catalog's own
`javalang`-based parsing primitives (`parse_java_file`, `type_name`) rather
than inventing a second parsing mechanism.

Two source shapes are extracted, both real conventions this platform's own
generation prompt (`generate_page_objects_v1.0.0.txt`) and catalog already
anticipate:

* ``private final By fieldName = By.id("value");`` (or ``.xpath``/
  ``.cssSelector``/``.name``/``.className``/``.linkText``/
  ``.partialLinkText``/``.tagName``) -- the ACTUAL convention the governed
  page-object generation prompt instructs: "one or more `private final By`
  locator fields declared with By.id/By.cssSelector/By.xpath." This is
  what every generated page object in this platform actually contains.
* ``@FindBy(id = "value")`` / ``@FindBy(xpath = "value")`` / ...
  (PageFactory-style, on a `WebElement` field) -- not the platform's own
  generation convention, but a shape the catalog's own
  `_LOCATOR_ANNOTATIONS` (`FindBy`/`FindBys`/`FindAll`) already
  anticipates; supported here for the same reason, so a hand-written or
  future page object using it is not silently skipped.

``cssSelector`` (the `By` method name) and ``css`` (the `@FindBy` element
name) are normalized to the SAME canonical strategy string, ``"css"`` --
otherwise the identical selector written the two different ways would
never be recognized as the same locator by the uniqueness/duplicate
criteria (:mod:`.gate`).
"""

from __future__ import annotations

from dataclasses import dataclass

import javalang

from automation_engineering.catalog.java_source import parse_java_file
from automation_engineering.cp4.models import Cp4PageObjectInput

#: `By.<method>(...)` method names this platform's own generation prompt
#: and Selenium's `By` class both use, normalized to a canonical strategy.
_BY_METHOD_STRATEGY: dict[str, str] = {
    "id": "id",
    "xpath": "xpath",
    "cssSelector": "css",
    "name": "name",
    "className": "className",
    "linkText": "linkText",
    "partialLinkText": "partialLinkText",
    "tagName": "tagName",
}

#: `@FindBy(<element> = "...")` element names, normalized the same way.
_FINDBY_ELEMENT_STRATEGY: dict[str, str] = {
    "id": "id",
    "xpath": "xpath",
    "css": "css",
    "name": "name",
    "className": "className",
    "linkText": "linkText",
    "partialLinkText": "partialLinkText",
    "tagName": "tagName",
}


@dataclass(frozen=True, slots=True)
class Cp4Locator:
    """One extracted locator: which field declared it, on which page
    object, under which normalized strategy, with which raw (unquoted)
    selector value."""

    class_name: str
    field_name: str
    strategy: str
    value: str


def _unquote(literal_value: str) -> str:
    if len(literal_value) >= 2 and literal_value[0] == literal_value[-1] and literal_value[0] in {
        '"',
        "'",
    }:
        return literal_value[1:-1]
    return literal_value


def _from_by_initializer(
    class_name: str, field_name: str, initializer: javalang.tree.MethodInvocation
) -> Cp4Locator | None:
    if getattr(initializer, "qualifier", None) != "By":
        return None
    strategy = _BY_METHOD_STRATEGY.get(initializer.member)
    if strategy is None or len(initializer.arguments) != 1:
        return None
    argument = initializer.arguments[0]
    if not isinstance(argument, javalang.tree.Literal) or not isinstance(argument.value, str):
        return None
    return Cp4Locator(
        class_name=class_name,
        field_name=field_name,
        strategy=strategy,
        value=_unquote(argument.value),
    )


def _from_findby_annotation(
    class_name: str, field_name: str, annotation: javalang.tree.Annotation
) -> Cp4Locator | None:
    if annotation.name != "FindBy":
        return None
    pairs = annotation.element
    if not isinstance(pairs, list):
        return None
    for pair in pairs:
        strategy = _FINDBY_ELEMENT_STRATEGY.get(pair.name)
        value = pair.value
        if strategy is None or not isinstance(value, javalang.tree.Literal):
            continue
        if not isinstance(value.value, str):
            continue
        return Cp4Locator(
            class_name=class_name,
            field_name=field_name,
            strategy=strategy,
            value=_unquote(value.value),
        )
    return None


def extract_locators(page_object: Cp4PageObjectInput) -> tuple[Cp4Locator, ...]:
    """Every locator field declared on `page_object`'s first class
    declaration -- both the `By`-field and `@FindBy`-annotation styles
    (module docstring). A field matching neither shape (an ordinary field,
    or a `By`/`WebElement` field this module's own extraction cannot
    confidently parse) is silently skipped, never guessed at -- the same
    "extract only what is unambiguous" discipline
    :func:`automation_engineering.catalog.java_source.annotation_string_value`
    already uses.
    """
    parsed = parse_java_file(page_object.class_name, page_object.java_source)
    locators: list[Cp4Locator] = []
    for _, node in parsed.tree.filter(javalang.tree.ClassDeclaration):
        for field_decl in node.fields:
            for declarator in field_decl.declarators:
                if isinstance(declarator.initializer, javalang.tree.MethodInvocation):
                    locator = _from_by_initializer(
                        page_object.class_name, declarator.name, declarator.initializer
                    )
                    if locator is not None:
                        locators.append(locator)
                        continue
                for annotation in field_decl.annotations:
                    locator = _from_findby_annotation(
                        page_object.class_name, declarator.name, annotation
                    )
                    if locator is not None:
                        locators.append(locator)
                        break
        break  # ADR-0044 D3: one page object per file/class, the catalog's own convention.
    return tuple(locators)


__all__ = ["Cp4Locator", "extract_locators"]
