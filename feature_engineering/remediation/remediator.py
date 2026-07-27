"""The remediation seam: dirty content + violations in, remediated content
out, everything else platform-owned. Mirrors
:mod:`feature_engineering.generation.content_generator` exactly -- same
shape, same reasoning, same "stub now, live later" split.

:class:`FeatureRemediator` is the one interface the loop (:mod:`.loop`)
depends on. Two implementations exist:

* :class:`StubFeatureRemediator` -- this task's deterministic,
  fixture-driven stand-in. Test/dev scaffolding only.
* The live, ``llm_factory``-backed implementation, loading the already
  -registered ``fix_gherkin_lint`` v1.0.0 prompt
  (``feature_engineering/prompts/versions/fix_gherkin_lint_v1.0.0.txt``,
  already converted and registered in an earlier task) -- **not built
  here**. That is a documented follow-up: it renders the prompt's
  ``feature_content``/``violations`` input contract, calls a real provider
  through ``llm_factory`` (mirroring
  :class:`~feature_engineering.generation.live_content_generator.LiveFeatureContentGenerator`'s
  own pattern exactly -- constructor-injected provider, no `llm_factory`
  import in this module), parses the prompt's own
  ``---FEATURE---``/``---CHANGES---`` output contract, and returns the
  corrected feature text. This module deliberately imports nothing from
  `llm_factory` and makes no network call -- the seam exists precisely so
  that follow-up task can land without touching anything below it.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from feature_engineering.gherkin_lint.models import Violation


class FeatureRemediator(Protocol):
    """Turns one dirty ``.feature`` text plus its lint violations into a
    remediated ``.feature`` text."""

    def remediate(self, content: str, violations: tuple[Violation, ...]) -> str:
        """Return a remediated version of `content` addressing `violations`.

        Per the already-registered ``fix_gherkin_lint`` v1.0.0 prompt's own
        contract: fix only what is reported, preserve every ``@REQ-*``/
        ``@SCN-*``/``@AC-*`` tag verbatim, do not rewrite unrelated
        scenarios. The loop (:mod:`.loop`) re-lints and re-gates whatever
        this returns -- it trusts nothing about the result in advance.
        """
        ...


class StubFeatureRemediator:
    """Deterministic, fixture-driven stand-in for the live LLM-backed remediator.

    **Test/dev scaffolding only -- never the production path.** Returns a
    pre-authored sequence of responses, one per call, in order -- so a test
    can script "attempt 1 still fails, attempt 2 fixes it" or "every
    attempt fails" without any model involved. Raises if called more times
    than responses were provided: a stub that silently invents content past
    its scripted sequence is not deterministic, it is a worse-judgment fake
    LLM (same discipline as
    :class:`~feature_engineering.generation.content_generator.StubFeatureContentGenerator`).
    """

    def __init__(self, responses: Sequence[str]) -> None:
        self._responses = list(responses)
        self._calls = 0

    def remediate(self, content: str, violations: tuple[Violation, ...]) -> str:
        if self._calls >= len(self._responses):
            raise IndexError(
                f"StubFeatureRemediator has no scripted response for call "
                f"#{self._calls + 1}; only {len(self._responses)} were provided. "
                "Register enough responses via the constructor."
            )
        response = self._responses[self._calls]
        self._calls += 1
        return response

    @property
    def call_count(self) -> int:
        return self._calls


__all__ = ["FeatureRemediator", "StubFeatureRemediator"]
