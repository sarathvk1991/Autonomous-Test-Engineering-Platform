"""Deterministic, text-level merge for two independently generated Java
classes that collide on the same class name.

**The gap this closes.** Two Gherkin step needs generated independently
(:mod:`.orchestrator`, one LLM call per NO_MATCH need, ADR-0044 D3) have no
visibility into each other's own class-name choice -- the generator derives
a class name from "the step's own subject" (`generate_step_definitions`
prompt's OUTPUT CONTRACT), a many-to-one function: two different steps whose
subjects both center on the same noun (e.g. "the user attempts to login...",
"the system displays an error message [after a failed login]...") can both
be named ``LoginSteps``. A live regeneration run hit exactly this
(``[[cap-compile-gap-closed]]``) -- the assembly write step
(:func:`automation_engineering.stage.runner._write_generated_java`) wrote
the second class over the first with no detection at all, caught only by
luck (a catalog count mismatch, 34 vs. expected 35), then fixed by hand with
a deterministic text-level merge: both needs' methods folded into one class.
This module is that fix, generalized and unit-tested, so the next
collision is DETECTED and MERGED automatically rather than silently
overwritten.

**Merge, not escalate, is the default resolution** -- per the same
reasoning the run's own manual fix already proved out: two step-defs
converging on one class name usually means they genuinely belong in that
one class (the same discipline
:func:`automation_engineering.generation.page_object_orchestrator.orchestrate_page_object_class`
already applies to page-object methods destined for the same class, just
one step later -- AFTER independent generation rather than batched before
it, since step-defs are generated one need at a time with no shared
visibility to batch ahead of time). Escalation
(:class:`UnsafeClassMergeError`) is the fallback for a collision that is NOT
safe to merge automatically: a different package, a different superclass,
or a same-named member (field or method) whose two declarations disagree --
merging THOSE silently would be exactly the kind of one-silently-wins
defect this module exists to prevent, just moved one level down (which
member's body wins). The one invariant that must never fail either way:
nothing is silently dropped.
"""

from __future__ import annotations

import re

import javalang

from automation_engineering.catalog.java_source import extract_declaration_span, parse_java_file

_IMPORT_LINE_RE = re.compile(r"^import\s+[\w.]+\s*;\s*$")


class UnsafeClassMergeError(ValueError):
    """Two same-named generated classes cannot be merged deterministically.

    Raised instead of guessing which side should win -- the caller must
    escalate the collision (surface it for review), never pick a winner and
    silently drop the other side's content.
    """


def _single_class(
    source: str, label: str
) -> tuple[javalang.tree.ClassDeclaration, str]:
    """The one top-level class declaration in ``source`` plus its package,
    or :class:`UnsafeClassMergeError` if ``source`` is not shaped that way
    (the generation seam's own output contract: one class per candidate)."""
    parsed = parse_java_file(f"{label}.java", source)
    classes = [node for _, node in parsed.tree.filter(javalang.tree.ClassDeclaration)]
    if len(classes) != 1:
        raise UnsafeClassMergeError(
            f"{label}: expected exactly one top-level class declaration, found {len(classes)}"
        )
    return classes[0], parsed.package


def _field_identity(field: javalang.tree.FieldDeclaration) -> tuple[str, ...]:
    return tuple(sorted(declarator.name for declarator in field.declarators))


def _member_spans(
    source: str, label: str
) -> tuple[javalang.tree.ClassDeclaration, dict[str, str], dict[tuple[str, ...], str]]:
    parsed = parse_java_file(f"{label}.java", source)
    classes = [node for _, node in parsed.tree.filter(javalang.tree.ClassDeclaration)]
    class_node = classes[0]
    methods = {
        method.name: extract_declaration_span(parsed, method) for method in class_node.methods
    }
    fields = {
        _field_identity(field): extract_declaration_span(parsed, field)
        for field in class_node.fields
    }
    return class_node, methods, fields


def merge_java_classes(existing_source: str, incoming_source: str) -> str:
    """Merge ``incoming_source``'s own fields/methods into
    ``existing_source``'s class body, deterministically, when both declare
    the SAME class name.

    Safe (mergeable) iff: both sources parse to exactly one top-level class
    sharing the same name, package, and superclass, AND no member (field or
    method) present in both declares a DIFFERENT body under the same
    identity (same field-declarator name(s), same method name) -- an
    identical member on both sides is treated as already merged, not a
    conflict. Any other member is unioned in, appended before the class's
    own closing brace; new imports ``incoming_source`` carries that
    ``existing_source`` lacks are unioned into the import block.

    Raises :class:`UnsafeClassMergeError` or if the collision is not safe to
    resolve this way -- the caller must escalate instead of calling this
    function's result.
    """
    existing_class, existing_package = _single_class(existing_source, "existing")
    incoming_class, incoming_package = _single_class(incoming_source, "incoming")

    if existing_class.name != incoming_class.name:
        raise UnsafeClassMergeError(
            f"class-name mismatch: {existing_class.name!r} vs {incoming_class.name!r} "
            "-- not a same-name collision, refusing to merge"
        )
    class_name = existing_class.name

    if existing_package != incoming_package:
        raise UnsafeClassMergeError(
            f"{class_name}: package mismatch ({existing_package!r} vs "
            f"{incoming_package!r}) -- refusing to merge"
        )

    existing_extends = existing_class.extends.name if existing_class.extends else None
    incoming_extends = incoming_class.extends.name if incoming_class.extends else None
    if existing_extends != incoming_extends:
        raise UnsafeClassMergeError(
            f"{class_name}: superclass mismatch ({existing_extends!r} vs "
            f"{incoming_extends!r}) -- refusing to merge"
        )

    _, existing_methods, existing_fields = _member_spans(existing_source, "existing")
    _, incoming_methods, incoming_fields = _member_spans(incoming_source, "incoming")

    new_spans: list[str] = []

    for identity, span in incoming_fields.items():
        prior = existing_fields.get(identity)
        if prior is None:
            new_spans.append(span)
        elif prior.strip() != span.strip():
            raise UnsafeClassMergeError(
                f"{class_name}: field {list(identity)!r} is declared differently in both "
                "colliding classes -- refusing to silently pick a winner"
            )

    for name, span in incoming_methods.items():
        prior = existing_methods.get(name)
        if prior is None:
            new_spans.append(span)
        elif prior.strip() != span.strip():
            raise UnsafeClassMergeError(
                f"{class_name}: method {name!r} is defined differently in both "
                "colliding classes -- refusing to silently pick a winner"
            )

    if not new_spans:
        return existing_source

    merged = _insert_before_final_brace(existing_source, new_spans)
    merged = _merge_import_block(merged, incoming_source)

    try:
        parse_java_file(f"{class_name}.java", merged)
    except (javalang.parser.JavaSyntaxError, javalang.tokenizer.LexerError) as exc:
        raise UnsafeClassMergeError(
            f"{class_name}: merged source failed to re-parse -- refusing to write a broken merge"
        ) from exc

    return merged


def _insert_before_final_brace(source: str, spans: list[str]) -> str:
    stripped = source.rstrip()
    if not stripped.endswith("}"):
        raise UnsafeClassMergeError("existing class source does not end with a closing brace")
    head = stripped[:-1].rstrip("\n")
    addition = "\n\n" + "\n\n".join(span.strip() for span in spans)
    return f"{head}{addition}\n}}\n"


def _merge_import_block(source: str, incoming_source: str) -> str:
    existing_imports = {
        line.strip() for line in source.splitlines() if _IMPORT_LINE_RE.match(line.strip())
    }
    missing = [
        line.strip()
        for line in incoming_source.splitlines()
        if _IMPORT_LINE_RE.match(line.strip()) and line.strip() not in existing_imports
    ]
    if not missing:
        return source

    lines = source.splitlines()
    insert_at = 0
    for index, line in enumerate(lines):
        if _IMPORT_LINE_RE.match(line.strip()):
            insert_at = index + 1
    if insert_at == 0:
        for index, line in enumerate(lines):
            if line.strip().startswith("package "):
                insert_at = index + 1
                break
    new_lines = lines[:insert_at] + missing + lines[insert_at:]
    return "\n".join(new_lines) + ("\n" if source.endswith("\n") else "")


__all__ = ["UnsafeClassMergeError", "merge_java_classes"]
