"""The semantic-matching seam: a Gherkin step-need plus the catalog in,
candidate matches (with confidence) out -- everything else (the
reuse-safety trust decision, ADR-0044 D4) is platform-owned, built in
:mod:`.engine`, never here.

This is the ONLY nondeterministic part of the reuse engine (ADR-0044 D3's
own "semantic matching mechanism" TBD, resolved toward embeddings --
:mod:`.live_matcher`). :class:`SemanticMatcher` is the one interface the
engine depends on. Two implementations exist:

* :class:`StubSemanticMatcher` -- this task's deterministic, fixture-driven
  stand-in. Test/dev scaffolding only -- the same pattern as
  :class:`~feature_engineering.remediation.remediator.StubFeatureRemediator`/
  :class:`~feature_engineering.generation.content_generator.StubFeatureContentGenerator`.
* :class:`~automation_engineering.reuse.live_matcher.LiveSemanticMatcher` --
  the live, embeddings-backed implementation (a peer behind this same seam,
  built in :mod:`.live_matcher`, not this module).

The engine (:mod:`.engine`) never imports an embedding provider or any live
infrastructure -- it depends only on this Protocol, so its decision logic is
provably deterministic regardless of which implementation is wired in.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol

from automation_engineering.catalog.models import AssetCatalog
from automation_engineering.reuse.models import GherkinStepNeed, MatchCandidate


class SemanticMatcher(Protocol):
    """Matches one :class:`GherkinStepNeed` against a catalog's own recorded
    intent, returning candidates ordered best-first (highest confidence
    first). An empty tuple means "nothing even remotely similar" -- the
    engine's own NO_MATCH/generate boundary (ADR-0044 D3), never an error
    and never itself an escalation."""

    def match(self, need: GherkinStepNeed, catalog: AssetCatalog) -> tuple[MatchCandidate, ...]:
        """Return candidates for `need` against `catalog`, best-first.

        Implementations decide their own confidence scale (``[0.0, 1.0]``,
        by convention) and their own notion of "nothing found" (returning
        ``()``). The engine (:mod:`.engine`) trusts nothing about ordering
        or scale beyond "higher confidence sorts first" and "confidence is
        comparable against its own configured threshold."
        """
        ...


class StubSemanticMatcher:
    """Deterministic, fixture-driven stand-in for the live embeddings-backed
    matcher.

    **Test/dev scaffolding only -- never the production path.** Returns a
    pre-authored candidate tuple keyed by :attr:`GherkinStepNeed.text`, so a
    test can script exactly which candidates (and confidences) a given step
    need resolves to, with no model or embedding call involved. Raises if
    asked to match a step text it has no canned answer for: a stub that
    silently invents a match (or silently returns "no match") for an
    unscripted input is not deterministic, it is a worse-judgment fake
    matcher -- the same discipline
    :class:`~feature_engineering.remediation.remediator.StubFeatureRemediator`
    already established.
    """

    def __init__(
        self,
        candidates_by_step_text: Mapping[str, tuple[MatchCandidate, ...]],
    ) -> None:
        self._canned = dict(candidates_by_step_text)
        self._calls = 0

    def match(self, need: GherkinStepNeed, catalog: AssetCatalog) -> tuple[MatchCandidate, ...]:
        self._calls += 1
        try:
            return self._canned[need.text]
        except KeyError:
            raise KeyError(
                f"StubSemanticMatcher has no canned candidates for "
                f"need.text={need.text!r}. Register it via the constructor's "
                "candidates_by_step_text mapping."
            ) from None

    @property
    def call_count(self) -> int:
        return self._calls


__all__ = ["SemanticMatcher", "StubSemanticMatcher"]
