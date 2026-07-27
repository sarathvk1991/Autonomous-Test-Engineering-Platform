"""Structured output contract for the Gherkin linter (ADR-0043 D3).

This is the shape two future consumers will read, per ADR-0043 D5 — neither
is built here:

* CP2's deterministic gate reads a :class:`LintResult` to decide pass/fail
  on the lint criterion (ADR-0040 Decision 2).
* The bounded remediation loop reads the same :class:`LintResult` to know
  which violations to hand to the LLM for a fix-and-relint attempt.

A human-readable rendering (e.g. grouped by file, or a stylish console
report) can be derived from this shape; it is not the primary form.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Violation:
    """One rule violation at one line in one file."""

    rule: str
    file: str
    line: int
    message: str


@dataclass(frozen=True, slots=True)
class LintResult:
    """The outcome of linting one file or a workspace-scoped corpus."""

    violations: tuple[Violation, ...] = ()

    @property
    def is_clean(self) -> bool:
        return not self.violations

    def for_file(self, file: str) -> tuple[Violation, ...]:
        return tuple(v for v in self.violations if v.file == file)

    def for_rule(self, rule: str) -> tuple[Violation, ...]:
        return tuple(v for v in self.violations if v.rule == rule)
