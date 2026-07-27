"""Orchestrates the 17 ported gherkin-lint rules over one file or a corpus.

``lint_file`` is the single-file entry point. ``lint_corpus`` /
``lint_workspace`` are the workspace-scoped entry points ``no-dupe-feature-names``
requires (ADR-0043 D3: cross-file by definition) and that ``no-dupe-scenario-names``
runs correctly under too (its committed ``in-feature`` config resets per file
regardless of call shape). Both return the same :class:`~.models.LintResult`
shape (see that module for the CP2 / remediation consumers it is designed for).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .config import enabled_rules
from .models import LintResult, Violation
from .rules import CORPUS_RULES, PER_FILE_RULES
from .source import SourceFile, read_source


def _lint_sources(corpus: list[SourceFile], config: dict[str, Any]) -> LintResult:
    rules = enabled_rules(config)
    violations: list[Violation] = []

    for source in corpus:
        if source.parse_error:
            violations.append(
                Violation(rule="parse-error", file=source.path, line=1, message=source.parse_error)
            )
            continue
        for name, option in rules.items():
            per_file_rule = PER_FILE_RULES.get(name)
            if per_file_rule is None:
                continue
            for line, message in per_file_rule(source, option):
                violations.append(
                    Violation(rule=name, file=source.path, line=line, message=message)
                )

    parseable = [s for s in corpus if not s.parse_error]
    for name, option in rules.items():
        corpus_rule = CORPUS_RULES.get(name)
        if corpus_rule is None:
            continue
        for file, line, message in corpus_rule(parseable, option):
            violations.append(Violation(rule=name, file=file, line=line, message=message))

    ordered = sorted(violations, key=lambda v: (v.file, v.line, v.rule))
    return LintResult(violations=tuple(ordered))


def lint_file(path: str | Path, config: dict[str, Any]) -> LintResult:
    """Lint exactly one file.

    Corpus-scoped rules still run correctly against a single-file corpus:
    ``no-dupe-feature-names`` cannot find a duplicate in one file, and
    ``no-dupe-scenario-names`` under the committed ``in-feature`` config is
    scoped to one file by definition — so this is a first-class entry point,
    not a degraded one.
    """
    return _lint_sources([read_source(path)], config)


def lint_corpus(paths: list[str | Path], config: dict[str, Any]) -> LintResult:
    """Lint an explicit set of files as one workspace-scoped corpus."""
    return _lint_sources([read_source(p) for p in paths], config)


def lint_workspace(directory: str | Path, config: dict[str, Any]) -> LintResult:
    """Lint every ``.feature`` file under ``directory`` as one corpus."""
    paths = sorted(Path(directory).rglob("*.feature"))
    return _lint_sources([read_source(p) for p in paths], config)
