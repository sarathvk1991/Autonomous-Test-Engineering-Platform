"""Java source extraction primitives, backing the asset catalog (ADR-0044 D3).

Structure (class/method/annotation/parameter/field) is extracted via
``javalang`` -- a real Java parser, not a regex scrape -- because the
catalog's identity data (content-hash, signature/parameter shape) feeds
ADR-0044 D4's reuse-safety checks directly, and an inaccurate scrape there
would corrupt a safety-critical mechanism. ``javalang`` does not preserve
comments in its token stream (verified directly against this parser: a
tokenize pass over a javadoc-commented fixture emits no comment tokens at
all), so Javadoc text -- used only for the catalog's optional, non-identity
``semantic_tags`` -- is pulled separately via a small, targeted line scan
immediately above a declaration. That split is deliberate: the identity-
critical half uses the real parser; the non-critical, parser-unsupported
half uses a narrow, well-tested text scan, not a second parsing mechanism
for the same data the AST already gives accurately.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import javalang
from javalang.tokenizer import JavaToken

#: Cucumber-java step annotations (io.cucumber.java.en / io.cucumber.java8-style).
CUCUMBER_STEP_ANNOTATIONS = frozenset({"Given", "When", "Then", "And", "But"})

#: A field/annotation signal for a Selenium locator, distinct from an
#: ordinary field, for the page-object schema's ``locators`` subset.
_LOCATOR_TYPE_NAMES = frozenset({"By"})
_LOCATOR_ANNOTATIONS = frozenset({"FindBy", "FindBys", "FindAll"})

_CAMEL_SPLIT_RE = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")
_CUCUMBER_PLACEHOLDER_RE = re.compile(r"\{[^}]*\}")
_REGEX_GROUP_RE = re.compile(r"[()^$\\]")
_WORD_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9]*")

#: Minimum length for a derived semantic-tag token; shorter tokens (articles,
#: prepositions rendered as bare letters) add noise, not signal.
_MIN_TAG_LENGTH = 2


@dataclass(frozen=True, slots=True)
class ParsedFile:
    """One parsed ``.java`` file: its AST, raw source, and the data needed to
    map an AST node's position back to an exact source substring."""

    path: str
    package: str
    source: str
    tree: javalang.tree.CompilationUnit
    tokens: tuple[JavaToken, ...]
    line_offsets: tuple[int, ...]


def parse_java_file(path: str, source: str) -> ParsedFile:
    tree = javalang.parse.parse(source)
    tokens = tuple(javalang.tokenizer.tokenize(source))
    return ParsedFile(
        path=path,
        package=tree.package.name if tree.package else "",
        source=source,
        tree=tree,
        tokens=tokens,
        line_offsets=_line_offsets(source),
    )


def _line_offsets(source: str) -> tuple[int, ...]:
    offsets = [0]
    for line in source.splitlines(keepends=True):
        offsets.append(offsets[-1] + len(line))
    return tuple(offsets)


def _char_offset(line_offsets: tuple[int, ...], position: javalang.tokenizer.Position) -> int:
    line: int = position.line
    column: int = position.column
    return line_offsets[line - 1] + (column - 1)


def _token_index_at(tokens: tuple[JavaToken, ...], position: javalang.tokenizer.Position) -> int:
    for index, token in enumerate(tokens):
        if (token.position.line, token.position.column) == (position.line, position.column):
            return index
    raise ValueError(f"no token found at {position!r}")


def _backward_modifier_start(
    tokens: tuple[JavaToken, ...], from_index: int
) -> javalang.tokenizer.Position:
    """Walk backward over contiguous ``Modifier`` tokens (``public``,
    ``static``, ...) immediately preceding ``from_index``, so an extracted
    span includes access/modifier keywords the AST node's own position
    (typically the return-type or ``class`` keyword) does not cover."""
    start = tokens[from_index].position
    j = from_index - 1
    while j >= 0 and type(tokens[j]).__name__ == "Modifier":
        start = tokens[j].position
        j -= 1
    return start


def _declared_start(
    parsed: ParsedFile, node: javalang.tree.Declaration
) -> javalang.tokenizer.Position:
    """The true start of a declaration's source span: the earliest of its
    annotations (if any) or its own AST position, then walked back over any
    preceding modifier keywords."""
    annotations = getattr(node, "annotations", None) or []
    if annotations:
        earliest = min(annotations, key=lambda a: (a.position.line, a.position.column))
        anchor = earliest.position
    else:
        anchor = node.position
    index = _token_index_at(parsed.tokens, anchor)
    return _backward_modifier_start(parsed.tokens, index)


def _body_end_position(
    parsed: ParsedFile, search_from: javalang.tokenizer.Position
) -> javalang.tokenizer.Position:
    """The position of the closing brace (or, for a body-less declaration,
    the terminating semicolon) of the declaration whose signature starts at
    ``search_from``.

    Scanning starts from the declaration's own AST position (past any
    annotations) specifically so an annotation's own array-literal braces
    (e.g. ``@SuppressWarnings({"a", "b"})``) are never mistaken for the
    body's opening brace.
    """
    start_index = _token_index_at(parsed.tokens, search_from)
    depth = 0
    opened = False
    for index in range(start_index, len(parsed.tokens)):
        token = parsed.tokens[index]
        if token.value == "{":
            depth += 1
            opened = True
        elif token.value == "}":
            depth -= 1
            if opened and depth == 0:
                return token.position
        elif token.value == ";" and not opened:
            return token.position
    raise ValueError(f"no terminator found for declaration at {search_from!r}")


def _body_end_offset(parsed: ParsedFile, search_from: javalang.tokenizer.Position) -> int:
    """The offset one past :func:`_body_end_position`'s own terminator."""
    return _char_offset(parsed.line_offsets, _body_end_position(parsed, search_from)) + 1


def extract_declaration_span(parsed: ParsedFile, node: javalang.tree.Declaration) -> str:
    """The exact source text of ``node`` -- annotations/modifiers through its
    closing brace (or terminating semicolon) -- used as the catalog's
    content-hash input (ADR-0044 D4(b))."""
    start = _declared_start(parsed, node)
    start_offset = _char_offset(parsed.line_offsets, start)
    end_offset = _body_end_offset(parsed, node.position)
    return parsed.source[start_offset:end_offset]


def declaration_line_span(parsed: ParsedFile, node: javalang.tree.Declaration) -> tuple[int, int]:
    """The 1-indexed ``(start_line, end_line)`` of ``node``'s full
    declaration span -- the same start/end anchors
    :func:`extract_declaration_span` uses (annotations/modifiers through the
    closing brace or terminating semicolon), as line numbers instead of a
    source substring. Used by CP3's ``long-method`` static check (ADR-0044
    D5 revision) to measure a method's physical line count.
    """
    start = _declared_start(parsed, node)
    end = _body_end_position(parsed, node.position)
    return start.line, end.line


def extract_preceding_javadoc(parsed: ParsedFile, node: javalang.tree.Declaration) -> str | None:
    """The Javadoc comment text immediately above ``node``'s declaration, if
    one exists -- used only for the catalog's optional ``semantic_tags``,
    never for identity or content-hash data."""
    start = _declared_start(parsed, node)
    lines = parsed.source.splitlines()
    i = start.line - 2  # convert 1-indexed "line above" to a 0-indexed index
    while i >= 0 and lines[i].strip() == "":
        i -= 1
    if i < 0 or not lines[i].strip().endswith("*/"):
        return None
    end_index = i
    start_index = None
    j = i
    while j >= 0:
        if lines[j].strip().startswith("/**"):
            start_index = j
            break
        j -= 1
    if start_index is None:
        return None
    parts: list[str] = []
    for raw_line in lines[start_index : end_index + 1]:
        stripped = raw_line.strip().removeprefix("/**").removesuffix("*/").strip()
        stripped = stripped.lstrip("*").strip()
        if stripped:
            parts.append(stripped)
    return " ".join(parts) if parts else None


def type_name(java_type: javalang.tree.Type | None) -> str:
    """A readable type name for a parameter/field/return type -- ``"void"``
    for a method with no return type (javalang's own representation of
    ``void``), base name plus one ``"[]"`` per array dimension otherwise."""
    if java_type is None:
        return "void"
    name: str = java_type.name
    dimensions = getattr(java_type, "dimensions", None) or []
    return name + "[]" * len(dimensions)


def annotation_string_value(annotation: javalang.tree.Annotation) -> str | None:
    """The single string-literal argument of an annotation like
    ``@Given("...")`` -- Cucumber step annotations always take exactly this
    shape. Returns ``None`` for any other annotation-argument shape (no
    argument, multiple named pairs) rather than guessing."""
    element = annotation.element
    if isinstance(element, javalang.tree.Literal) and isinstance(element.value, str):
        value = element.value
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            return value[1:-1]
        return value
    return None


def is_locator_field(field_type_name: str, field_annotations: tuple[str, ...]) -> bool:
    return field_type_name in _LOCATOR_TYPE_NAMES or bool(
        _LOCATOR_ANNOTATIONS.intersection(field_annotations)
    )


def semantic_tags_from_identifier(identifier: str) -> tuple[str, ...]:
    """CamelCase-split, lowercased tokens from a class/method name -- e.g.
    ``openApplicationUnderTest`` -> ``("open", "application", "under",
    "test")``. Fully derivable from source; no authored metadata needed."""
    words = _CAMEL_SPLIT_RE.split(identifier)
    return tuple(w.lower() for w in words if len(w) >= _MIN_TAG_LENGTH)


def semantic_tags_from_pattern(pattern: str) -> tuple[str, ...]:
    """Lowercased words from a Cucumber step pattern, with expression
    placeholders (``{string}``, ``{int}``) and regex punctuation stripped --
    e.g. ``"I open the application under test"`` -> ``("open",
    "application", "under", "test")``. This is the free-text intent signal
    already required on every step definition by Cucumber itself (LLD §7's
    ``supportedActions`` for a step is, in substance, this text) -- no
    separate authored metadata is needed for step definitions."""
    without_placeholders = _CUCUMBER_PLACEHOLDER_RE.sub(" ", pattern)
    without_regex_punct = _REGEX_GROUP_RE.sub(" ", without_placeholders)
    words = _WORD_RE.findall(without_regex_punct.lower())
    seen: dict[str, None] = {}
    for word in words:
        if len(word) >= _MIN_TAG_LENGTH and word not in seen:
            seen[word] = None
    return tuple(seen.keys())


def semantic_tags_from_text(text: str) -> tuple[str, ...]:
    """Lowercased words from free text (Javadoc) -- used the same way as
    :func:`semantic_tags_from_pattern`, for assets whose intent is not
    itself a Cucumber pattern (page objects, utilities)."""
    words = _WORD_RE.findall(text.lower())
    seen: dict[str, None] = {}
    for word in words:
        if len(word) >= _MIN_TAG_LENGTH and word not in seen:
            seen[word] = None
    return tuple(seen.keys())


def dedupe_tags(*tag_groups: tuple[str, ...]) -> tuple[str, ...]:
    seen: dict[str, None] = {}
    for group in tag_groups:
        for tag in group:
            if tag not in seen:
                seen[tag] = None
    return tuple(seen.keys())


__all__ = [
    "CUCUMBER_STEP_ANNOTATIONS",
    "ParsedFile",
    "annotation_string_value",
    "declaration_line_span",
    "dedupe_tags",
    "extract_declaration_span",
    "extract_preceding_javadoc",
    "is_locator_field",
    "parse_java_file",
    "semantic_tags_from_identifier",
    "semantic_tags_from_pattern",
    "semantic_tags_from_text",
    "type_name",
]
