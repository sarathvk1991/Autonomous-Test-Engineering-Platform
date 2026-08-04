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

    ``content`` carries the fully-assembled, already-tagged (but lint-dirty)
    ``.feature`` text -- populated only alongside ``lint_result`` (a lint
    failure has real assembled text to show; a pre-assembly tag-contract
    violation does not). This is what ADR-0043 D5's bounded remediation
    loop needs to operate on -- Tier 1's deterministic formatter and Tier
    2's LLM remediation both require the actual dirty text, which this
    exception previously discarded. Additive: existing callers that only
    read ``lint_result`` are unaffected.
    """

    def __init__(
        self,
        message: str,
        *,
        lint_result: LintResult | None = None,
        content: str | None = None,
    ) -> None:
        super().__init__(message)
        self.lint_result = lint_result
        self.content = content


class TransportFailureError(Exception):
    """Raised when a `FeatureContentGenerator`/`FeatureRemediator` call fails
    for a reason unrelated to the content it returned -- a provider
    exception, a quota/rate-limit rejection, a timeout, or a malformed/empty
    response at the LLM boundary itself, before there is any generated text
    to validate at all.

    Distinct from `FeatureGenerationError` on purpose: that exception means
    the generator/remediator DID return content, and the content failed
    validation. This one means no usable content was returned, for a reason
    that has nothing to do with what any content would have said. Both are
    per-requirement recoverable -- neither is stage-fatal -- but
    `feature_engineering.stage.runner` escalates them under different
    reasons, so a human reviewing an escalated requirement knows whether to
    look at the generated content (a content failure) or at provider/network
    conditions (a transport failure).

    This is the seam's own transport-failure contract, not one
    implementation's private type: a concrete live implementation's own
    exception (e.g. `LiveGenerationError`, `LiveRemediationError`) subclasses
    this rather than replacing it, so callers outside this package's live
    modules can catch transport failures without importing a specific
    provider-backed implementation.
    """

