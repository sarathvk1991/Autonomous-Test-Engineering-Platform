"""Token-consumption-by-call-type instrumentation.

Nitin's re-run/token-cost clarification (2026-08-12, `docs/architecture/
mentor-feedback-scoping.md`) names token-consumption instrumentation "by
stage and run" as his own highest-priority, cheapest concrete ask --
"Critically," in his own words -- the observability step that shows where
optimization (caching, delta-scoped regeneration, model choice) would pay
off most, before any of those heavier mechanisms are built.

This module is that instrumentation, and nothing more: it aggregates token
usage :class:`~requirement_intelligence.llm.llm_models.LLMUsage` already
captured on every :class:`~requirement_intelligence.llm.llm_models.LLMResponse`
(``GeminiProvider._extract_usage`` has captured it since before this module
existed -- capture was never the gap; every caller simply discarded it after
reading ``generated_text``). Purely additive: nothing here changes what any
call site generates, gates, caches, retries, or skips. A caller that never
constructs a :class:`TokenUsageTracker` sees no behavior change at all.
"""

from __future__ import annotations

from requirement_intelligence.llm.llm_models import LLMUsage
from shared.contracts.base import Schema


class TokenUsageTotals(Schema):
    """Aggregated token counts for one call type, or a run's grand total.

    ``unmeasured_call_count`` counts calls whose provider returned no usage
    metadata at all (:class:`LLMUsage` is itself a best-effort, may-be-``None``
    contract -- see ``GeminiProvider._extract_usage``'s own docstring) --
    tracked so a run with unmeasured calls is visibly incomplete rather than
    silently under-counted as zero-cost.

    ``cache_hit_count`` counts calls the artifact-generation cache satisfied
    without an LLM call at all (ADR-0050 D3's "Gap 2" -- a cache hit is
    *zero-cost-verified*, a fundamentally different fact than "unmeasured": an
    unmeasured call still cost real, unknown tokens; a cache hit provably cost
    none. Recording a hit as ``unmeasured_call_count`` would make the very
    saving this bucket exists to show look like a measurement gap instead --
    the opposite of the intended signal. A hit therefore never increments
    ``call_count`` either: it is not an LLM call this run made.
    """

    call_count: int = 0
    unmeasured_call_count: int = 0
    cache_hit_count: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    def plus(self, other: TokenUsageTotals) -> TokenUsageTotals:
        """Return the element-wise sum of ``self`` and ``other``.

        Named ``plus``, not ``__add__``, deliberately: a frozen
        :class:`~shared.contracts.base.Schema` already defines ``__eq__``
        or via pydantic's own dunder set, and this keeps the accumulation
        operation unambiguous and explicit at call sites.
        """
        return TokenUsageTotals(
            call_count=self.call_count + other.call_count,
            unmeasured_call_count=self.unmeasured_call_count + other.unmeasured_call_count,
            cache_hit_count=self.cache_hit_count + other.cache_hit_count,
            prompt_tokens=self.prompt_tokens + other.prompt_tokens,
            completion_tokens=self.completion_tokens + other.completion_tokens,
            total_tokens=self.total_tokens + other.total_tokens,
        )


class TokenUsageTracker:
    """Accumulates :class:`LLMUsage` per named call type across one run.

    Deterministic and side-effect-free beyond its own internal state --
    :meth:`record`/:meth:`record_cache_hit` are the only mutators, neither
    ever raises, and neither performs I/O. Constructed once per run by
    whichever entry point (the CLI's ``handle_analyze``, or a test) wants a
    token-by-stage breakdown, then passed as an optional collaborator to the
    generator/service classes that make LLM calls; a collaborator never
    given a tracker behaves exactly as it did before this module existed.
    """

    def __init__(self) -> None:
        self._totals_by_call_type: dict[str, TokenUsageTotals] = {}

    def record(self, call_type: str, usage: LLMUsage | None) -> None:
        """Attribute one completed call's usage to ``call_type``.

        ``usage=None`` (the provider's own best-effort-may-be-absent
        contract) still counts the call -- as unmeasured, never silently
        dropped or estimated as zero-cost.
        """
        current = self._totals_by_call_type.get(call_type, TokenUsageTotals())
        if usage is None:
            increment = TokenUsageTotals(call_count=1, unmeasured_call_count=1)
        else:
            increment = TokenUsageTotals(
                call_count=1,
                prompt_tokens=usage.prompt_tokens or 0,
                completion_tokens=usage.completion_tokens or 0,
                total_tokens=usage.total_tokens or 0,
            )
        self._totals_by_call_type[call_type] = current.plus(increment)

    def record_cache_hit(self, call_type: str) -> None:
        """Attribute one artifact-generation-cache hit to ``call_type``
        (ADR-0050 D3's "Gap 2") -- the LLM call this hit skipped cost zero
        new tokens, verified, not merely unmeasured. Does not increment
        ``call_count``: a cache hit is not an LLM call this run made.
        """
        current = self._totals_by_call_type.get(call_type, TokenUsageTotals())
        increment = TokenUsageTotals(cache_hit_count=1)
        self._totals_by_call_type[call_type] = current.plus(increment)

    def by_call_type(self) -> dict[str, TokenUsageTotals]:
        """Per-call-type totals, insertion-ordered (first-recorded first)."""
        return dict(self._totals_by_call_type)

    def grand_total(self) -> TokenUsageTotals:
        """The run's own totals across every call type recorded so far."""
        total = TokenUsageTotals()
        for totals in self._totals_by_call_type.values():
            total = total.plus(totals)
        return total

    def distribution(self) -> dict[str, float]:
        """Each call type's percentage share of the run's ``total_tokens``.

        ``0.0`` for every call type when the grand total is ``0`` (never
        divides by zero). Percentages are rounded to one decimal place; do
        not assume they sum to exactly ``100.0`` because of rounding.
        """
        grand = self.grand_total()
        if grand.total_tokens == 0:
            return {call_type: 0.0 for call_type in self._totals_by_call_type}
        return {
            call_type: round(totals.total_tokens / grand.total_tokens * 100.0, 1)
            for call_type, totals in self._totals_by_call_type.items()
        }

    def as_dict(self) -> dict[str, object]:
        """A full, JSON-serializable snapshot answering "where did the
        tokens go" for one run: per-call-type totals, the grand total, and
        the distribution."""
        return {
            "by_call_type": {
                call_type: totals.model_dump()
                for call_type, totals in self._totals_by_call_type.items()
            },
            "grand_total": self.grand_total().model_dump(),
            "distribution_pct": self.distribution(),
        }


__all__ = ["TokenUsageTotals", "TokenUsageTracker"]
