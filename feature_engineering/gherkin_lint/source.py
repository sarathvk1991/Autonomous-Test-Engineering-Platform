"""Raw source lines plus parsed AST for one ``.feature`` file.

ADR-0043 D3: several ported rules need the raw source text, not just the
parsed AST, because the AST does not preserve every byte of the file. This
module reads a file exactly once and keeps both representations side by
side so no rule needs to re-read the file, and so a rule that turns out not
to need the raw lines simply doesn't reference them.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from gherkin.errors import CompositeParserException
from gherkin.parser import Parser

_LINE_SPLIT = re.compile(r"\r\n|\r|\n")


@dataclass(frozen=True, slots=True)
class SourceFile:
    """One ``.feature`` file: its path, raw lines, and parsed ``feature`` AST node.

    ``feature`` is ``None`` for a file with no ``Feature:`` line at all —
    the condition ``no-empty-file`` checks. ``parse_error`` is set only when
    the Gherkin parser rejects the file outright (malformed syntax); this is
    distinct from all 17 lint rules, none of which fire for a file that
    failed to parse.
    """

    path: str
    lines: tuple[str, ...]
    feature: dict[str, Any] | None
    language: str
    parse_error: str | None = None


def parse_source_text(text: str, *, path: str = "<memory>") -> SourceFile:
    """Parse already-in-memory ``.feature`` text into a :class:`SourceFile`.

    No disk I/O — for callers (e.g. the Layer 2 generation core) that
    assemble or validate feature content before it is ever written to a
    file. ``path`` is a display label only; it is never read from.
    """
    lines = tuple(_LINE_SPLIT.split(text))

    try:
        document = Parser().parse(text)
    except CompositeParserException as exc:
        return SourceFile(path=path, lines=lines, feature=None, language="en", parse_error=str(exc))

    feature = document.get("feature")
    language = feature["language"] if feature else "en"
    return SourceFile(path=path, lines=lines, feature=feature, language=language)


def read_source(path: str | Path) -> SourceFile:
    """Read and parse one ``.feature`` file into a :class:`SourceFile`."""
    with open(path, encoding="utf-8", newline="") as handle:
        text = handle.read()
    return parse_source_text(text, path=str(path))
