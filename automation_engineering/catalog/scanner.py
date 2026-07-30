"""Run-start reconciliation: scan the tracked baseline's committed Java and
produce the current asset catalog (ADR-0044 D3).

**Storage-location decision, resolved here.** ADR-0044 D3 left the catalog's
persistent storage location TBD, framed as Model B, "a persistent store."
This module resolves it: the catalog is a **derived index, fully rebuilt
by scanning the tracked baseline every time**, not a separately persisted
store with its own drift risk. Two things make this sufficient rather than
a compromise:

1. Every field the catalog needs is deterministically re-derivable from the
   tracked baseline's own committed Java: identity (content-hash, computed
   over the exact extracted source span), signature/parameter shape (from
   the AST), and Gherkin bindings (the Cucumber annotation's own string
   argument -- required source content on every step definition already,
   not optional metadata). Semantic-intent metadata (the LLD §7
   ``supportedActions`` analogue) is likewise derivable -- from the step
   pattern text itself for step definitions, and from Javadoc plus
   camelCase-split identifiers for page objects/utilities. Nothing the
   catalog needs requires authored metadata a scan cannot reconstruct, so
   a persisted authoritative store is not required to avoid data loss.
2. Model B's actual requirement is that reuse survive *across runs* -- and
   it does, because the thing that persists across runs is the tracked
   baseline itself (already git-tracked, durable independent of any run).
   A promoted asset (ADR-0045) becomes part of that committed Java; the
   next run's reconciliation scans the (now-updated) baseline and finds it,
   with no separate catalog store needing to "remember" anything between
   runs. Reconciliation is exactly reproducing this: build fresh from
   current source, every time, so the code is always what the catalog
   describes (D3's "code remains the effective source of truth"), never a
   stale index of what the code used to be.

A JSON snapshot may still be written to disk (``AssetCatalog.to_json``) for
inspection or as a performance cache -- but reconciliation never reads such
a snapshot back as authoritative, and deleting it changes nothing about
what the next reconciliation produces.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from pathlib import Path

import javalang

from automation_engineering.catalog.java_source import (
    CUCUMBER_STEP_ANNOTATIONS,
    ParsedFile,
    annotation_string_value,
    dedupe_tags,
    extract_declaration_span,
    extract_preceding_javadoc,
    is_locator_field,
    parse_java_file,
    semantic_tags_from_identifier,
    semantic_tags_from_pattern,
    semantic_tags_from_text,
    type_name,
)
from automation_engineering.catalog.models import (
    AssetCatalog,
    JavaField,
    JavaMethod,
    JavaParameter,
    PageObjectAsset,
    StepDefinitionAsset,
    UtilityAsset,
)

#: Relative to a baseline root (tracked ``test-suite-baseline/`` or an
#: untracked per-run workspace copy of it, ADR-0037 Path A) -- where
#: generated/hand-written Java lives.
JAVA_SOURCE_SUBPATH = Path("src/test/java")

#: Packages holding day-one tracked FRAMEWORK code (ADR-0037's "framework
#: code (drivers, base classes, utilities)... base page objects" bucket)
#: and the prohibited-from-regeneration runner class (ADR-0044 D2). Neither
#: is a reusable-asset candidate in the sense Layer 3's reuse-first
#: discipline (ADR-0044 D3) means: nothing Layer 3 ever generates a
#: competing copy of. Excluded from the catalog entirely, not merely
#: unclassified.
EXCLUDED_PACKAGES = frozenset({"com.automation.base", "com.automation.runners"})

#: The tracked baseline's own base page-object class (ADR-0037's
#: resolution note; ADR-0041 D5) -- a class extending this by name is
#: classified as a page object. Matched by simple name, not a resolved
#: fully-qualified type, since cross-file type resolution is out of this
#: task's scope (Consequences, below).
PAGE_OBJECT_BASE_CLASS = "BasePage"


def _content_hash(source_span: str) -> str:
    return hashlib.sha256(source_span.encode("utf-8")).hexdigest()


def _identity_hash(*parts: str) -> str:
    return hashlib.sha256("\x00".join(parts).encode("utf-8")).hexdigest()


def _iter_java_files(java_root: Path) -> Iterable[Path]:
    if not java_root.is_dir():
        return
    yield from sorted(java_root.rglob("*.java"))


def _extract_fields(
    parsed: ParsedFile, node: javalang.tree.ClassDeclaration
) -> tuple[JavaField, ...]:
    fields: list[JavaField] = []
    for field_decl in node.fields:
        field_type = type_name(field_decl.type)
        annotation_names = tuple(a.name for a in field_decl.annotations)
        locator = is_locator_field(field_type, annotation_names)
        for declarator in field_decl.declarators:
            fields.append(
                JavaField(name=declarator.name, java_type=field_type, is_locator=locator)
            )
    return tuple(fields)


def _extract_methods(node: javalang.tree.ClassDeclaration) -> tuple[JavaMethod, ...]:
    methods: list[JavaMethod] = []
    for method in node.methods:
        params = tuple(
            JavaParameter(name=p.name, java_type=type_name(p.type)) for p in method.parameters
        )
        methods.append(
            JavaMethod(
                name=method.name,
                parameters=params,
                return_type=type_name(method.return_type),
            )
        )
    return tuple(methods)


def _extract_step_definitions(
    parsed: ParsedFile, node: javalang.tree.ClassDeclaration, qualified_class_name: str
) -> list[StepDefinitionAsset]:
    assets: list[StepDefinitionAsset] = []
    for method in node.methods:
        for annotation in method.annotations:
            if annotation.name not in CUCUMBER_STEP_ANNOTATIONS:
                continue
            pattern = annotation_string_value(annotation)
            if pattern is None:
                continue
            params = tuple(
                JavaParameter(name=p.name, java_type=type_name(p.type)) for p in method.parameters
            )
            span = extract_declaration_span(parsed, method)
            content_hash = _content_hash(span)
            asset_id = "STEP-" + _identity_hash(qualified_class_name, method.name, annotation.name)[
                :8
            ]
            tags = dedupe_tags(
                semantic_tags_from_pattern(pattern),
                semantic_tags_from_identifier(method.name),
            )
            assets.append(
                StepDefinitionAsset(
                    asset_id=asset_id,
                    class_name=qualified_class_name,
                    method_name=method.name,
                    step_type=annotation.name,
                    pattern=pattern,
                    parameters=params,
                    return_type=type_name(method.return_type),
                    source_file=parsed.path,
                    content_hash=content_hash,
                    semantic_tags=tags,
                )
            )
    return assets


def _extract_page_object(
    parsed: ParsedFile, node: javalang.tree.ClassDeclaration, qualified_class_name: str
) -> PageObjectAsset:
    span = extract_declaration_span(parsed, node)
    fields = _extract_fields(parsed, node)
    locators = tuple(f for f in fields if f.is_locator)
    methods = _extract_methods(node)
    javadoc = extract_preceding_javadoc(parsed, node)
    tags = dedupe_tags(
        semantic_tags_from_text(javadoc) if javadoc else (),
        semantic_tags_from_identifier(node.name),
        *(semantic_tags_from_identifier(m.name) for m in methods),
    )
    return PageObjectAsset(
        asset_id="PAGE-" + _identity_hash(qualified_class_name)[:8],
        class_name=qualified_class_name,
        extends=node.extends.name if node.extends else None,
        fields=fields,
        locators=locators,
        methods=methods,
        source_file=parsed.path,
        content_hash=_content_hash(span),
        semantic_tags=tags,
    )


def _extract_utility(
    parsed: ParsedFile, node: javalang.tree.ClassDeclaration, qualified_class_name: str
) -> UtilityAsset:
    span = extract_declaration_span(parsed, node)
    fields = _extract_fields(parsed, node)
    methods = _extract_methods(node)
    javadoc = extract_preceding_javadoc(parsed, node)
    tags = dedupe_tags(
        semantic_tags_from_text(javadoc) if javadoc else (),
        semantic_tags_from_identifier(node.name),
        *(semantic_tags_from_identifier(m.name) for m in methods),
    )
    return UtilityAsset(
        asset_id="UTIL-" + _identity_hash(qualified_class_name)[:8],
        class_name=qualified_class_name,
        fields=fields,
        methods=methods,
        source_file=parsed.path,
        content_hash=_content_hash(span),
        semantic_tags=tags,
    )


def _package_from_relative_path(relative_path: str) -> str:
    """The Java package implied by a file's directory position under the
    java source root -- standard one-package-per-directory Java convention.
    Computed from the path alone, with no parse required, specifically so
    an excluded-package file (framework code, ADR-0037's tracked-baseline
    bucket; the runner class ADR-0044 D2 forbids regenerating) can be
    skipped *before* attempting a parse. This matters in practice, not only
    for efficiency: `DriverFactory.java` (`com.automation.base`, excluded)
    uses a Java 14+ switch expression javalang's grammar cannot parse at
    all -- confirmed directly, not assumed -- and this framework class was
    never a catalog candidate regardless of whether it happens to parse."""
    directory = str(Path(relative_path).parent)
    if directory in {"", "."}:
        return ""
    return directory.replace("/", ".").replace("\\", ".")


def _scan_file(
    file_path: Path,
    java_root: Path,
    step_definitions: list[StepDefinitionAsset],
    page_objects: list[PageObjectAsset],
    utilities: list[UtilityAsset],
    unparsed_files: list[str],
) -> None:
    relative_path = file_path.relative_to(java_root).as_posix()
    if _package_from_relative_path(relative_path) in EXCLUDED_PACKAGES:
        return
    source = file_path.read_text(encoding="utf-8")
    try:
        parsed = parse_java_file(relative_path, source)
    except (javalang.parser.JavaSyntaxError, javalang.tokenizer.LexerError):
        unparsed_files.append(relative_path)
        return
    if parsed.package in EXCLUDED_PACKAGES:
        return
    for _, node in parsed.tree.filter(javalang.tree.ClassDeclaration):
        qualified_class_name = f"{parsed.package}.{node.name}" if parsed.package else node.name
        step_assets = _extract_step_definitions(parsed, node, qualified_class_name)
        if step_assets:
            step_definitions.extend(step_assets)
            continue
        if node.extends is not None and node.extends.name == PAGE_OBJECT_BASE_CLASS:
            page_objects.append(_extract_page_object(parsed, node, qualified_class_name))
            continue
        utilities.append(_extract_utility(parsed, node, qualified_class_name))


def reconcile(baseline_root: Path) -> AssetCatalog:
    """Scan ``baseline_root`` (the tracked ``test-suite-baseline/``, or an
    untracked per-run workspace copy of it, ADR-0037 Path A) and return the
    current asset catalog.

    Deterministic and side-effect-free: the same source tree always
    produces byte-identical catalog content (ADR-0044 D3's "code remains
    the effective source of truth"); an empty or asset-free baseline
    produces an empty catalog, not an error -- the correct bootstrap case
    ADR-0044 D5 already establishes for 0% reuse. A file that fails to
    parse is skipped and recorded on ``AssetCatalog.unparsed_files``, never
    silently dropped and never a fatal error for the rest of the scan.
    """
    java_root = baseline_root / JAVA_SOURCE_SUBPATH
    step_definitions: list[StepDefinitionAsset] = []
    page_objects: list[PageObjectAsset] = []
    utilities: list[UtilityAsset] = []
    unparsed_files: list[str] = []
    for file_path in _iter_java_files(java_root):
        _scan_file(file_path, java_root, step_definitions, page_objects, utilities, unparsed_files)
    return AssetCatalog(
        baseline_root=str(baseline_root),
        step_definitions=tuple(step_definitions),
        page_objects=tuple(page_objects),
        utilities=tuple(utilities),
        unparsed_files=tuple(unparsed_files),
    )


__all__ = ["EXCLUDED_PACKAGES", "JAVA_SOURCE_SUBPATH", "PAGE_OBJECT_BASE_CLASS", "reconcile"]
