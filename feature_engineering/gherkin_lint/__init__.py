"""Gherkin linter — the Python port of the 17-rule ``gherkin-lint`` set (ADR-0043 D3).

Platform component, not part of the generated Maven test suite: it reads
``.feature`` files and emits a structured :class:`~.models.LintResult` for
the platform to consume (future CP2 gate and remediation loop, ADR-0043 D5).
"""

from __future__ import annotations

from .config import KNOWN_RULES, GherkinLintConfigError, load_config
from .linter import lint_corpus, lint_file, lint_in_memory_corpus, lint_source, lint_workspace
from .models import LintResult, Violation
from .source import SourceFile, parse_source_text, read_source

__all__ = [
    "KNOWN_RULES",
    "GherkinLintConfigError",
    "LintResult",
    "SourceFile",
    "Violation",
    "lint_corpus",
    "lint_file",
    "lint_in_memory_corpus",
    "lint_source",
    "lint_workspace",
    "load_config",
    "parse_source_text",
    "read_source",
]
