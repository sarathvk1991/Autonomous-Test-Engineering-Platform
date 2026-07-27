"""Errors the Layer 2 generation core raises.

A generated feature that fails structural validation (unparseable, lint-dirty,
or violates the registered prompt's own tag contract) is a generation
failure at this stage — surfaced by raising, never silently emitted as if it
had succeeded (ADR-0043 D5's own framing for the two non-remediable rules,
applied here to every validation this core performs).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from feature_engineering.gherkin_lint.models import LintResult


class FeatureGenerationError(Exception):
    """Raised when assembled feature content fails validation.

    Carries the diagnostic that explains the failure: ``lint_result`` when
    the assembled file parsed but failed the 17-rule gate, or ``None`` when
    the content generator's own raw output violated its tag contract before
    lint ever ran (e.g. a missing ``@SCN-PENDING`` tag, or a stray
    ``@REQ-*`` tag the contract forbids).
    """

    def __init__(self, message: str, *, lint_result: LintResult | None = None) -> None:
        super().__init__(message)
        self.lint_result = lint_result
