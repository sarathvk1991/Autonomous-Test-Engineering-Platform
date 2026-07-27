"""The generation seam: raw scenario content in, everything else platform-owned.

:class:`FeatureContentGenerator` is the one interface the rest of this
package depends on. It has a single responsibility — turn one
:class:`~contracts.testable_requirement.TestableRequirement` into raw Gherkin
scenario content, per the registered ``generate_feature`` prompt's own
contract (``feature_engineering/prompts/versions/generate_feature_v1.1.0.txt``):
no ``Feature:`` line, no ``@REQ-*`` tag anywhere, real ``ac_id`` values
written verbatim, and exactly one ``@SCN-PENDING`` tag per scenario.

Two implementations exist:

* :class:`StubFeatureContentGenerator` — this task's deterministic,
  fixture-driven stand-in. Test/dev scaffolding only.
* The live, ``llm_factory``-backed implementation — **not built here**. That
  is a separate, later task: it renders the prompt template with a real
  ``TestableRequirement``, calls a real provider through ``llm_factory``,
  and returns the response text. This module deliberately imports nothing
  from ``llm_factory`` and makes no network call — the seam exists precisely
  so that task can land without touching anything below it.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol

from contracts.testable_requirement import TestableRequirement


class FeatureContentGenerator(Protocol):
    """Turns one TestableRequirement into raw Gherkin scenario content."""

    def generate(self, requirement: TestableRequirement) -> str:
        """Return raw scenario/background content for ``requirement``.

        No ``Feature:`` line, no ``@REQ-*`` tag; real ``@AC-*`` tag values;
        exactly one ``@SCN-PENDING`` tag per Scenario/Scenario Outline.
        """
        ...


class StubFeatureContentGenerator:
    """Deterministic, fixture-driven stand-in for the live LLM-backed generator.

    **Test/dev scaffolding only — never the production path.** Returns
    fixed, canned content keyed by ``requirement.requirement_id``, authored
    by the caller. Raises if asked to generate for a requirement it has no
    canned answer for: a stub that silently invents content on a cache miss
    is not deterministic, it is a worse-judgment fake LLM.
    """

    def __init__(self, canned_content_by_requirement_id: Mapping[str, str]) -> None:
        self._canned = dict(canned_content_by_requirement_id)

    def generate(self, requirement: TestableRequirement) -> str:
        try:
            return self._canned[requirement.requirement_id]
        except KeyError:
            raise KeyError(
                f"StubFeatureContentGenerator has no canned content for "
                f"requirement_id={requirement.requirement_id!r}. Register it via "
                f"the constructor's canned_content_by_requirement_id mapping."
            ) from None
