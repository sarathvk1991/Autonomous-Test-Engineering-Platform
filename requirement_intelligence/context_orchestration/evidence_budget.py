"""Deterministic allocation of an :class:`EvidenceBudget` across evidence domains.

A budget states two bounds — per domain, and in total. Turning those bounds into
*one number per domain* is the allocation, and it is a decision: it fixes how
many functional, security and quality artifacts a reasoning session may receive.

Why allocation cannot be "cap each domain and hope"
---------------------------------------------------
``DefaultOrchestrationPolicy`` permits 25 artifacts per domain and 60 in total.
Three full domains want 75. Something must give, and *which* domain gives is the
question this module answers deterministically. The naive answer — walk the
domains in order and let each take its cap until the total runs out — lets the
first domain in the list starve the last, which is the CAP-074B defect wearing a
different hat (CAP-076A risk R8).

The rule
--------
1. A domain can never be allocated more than it can actually spend, so its
   ceiling is ``min(maxArtifactsPerDomain, available)``.
2. If those ceilings already fit inside ``maxArtifactsTotal``, every domain gets
   its ceiling. Nothing is contested, so nothing needs deciding.
3. Otherwise the total is **water-filled**: shared equally among the domains
   still competing, with any domain whose ceiling sits below the equal share
   settled at its ceiling and its surplus returned to the pool. Repeat until no
   domain settles, then split what remains equally.

Water-filling is the standard max-min fair allocation: it maximises the smallest
allocation, so a verbose domain can never crowd out a sparse one. A domain that
wants less than its fair share takes only what it wants, and the difference goes
to the domains that can use it.

Determinism (CAP-076A Invariant 7)
----------------------------------
Every step is integer arithmetic over :data:`EVIDENCE_DOMAINS`, whose order is
fixed. The one place a remainder must be broken — an indivisible unit left after
an equal split — is granted in that same canonical order. There is no
randomness, no floating point, and no dependence on dict or set iteration.
"""

from __future__ import annotations

from collections.abc import Mapping

from requirement_intelligence.context_orchestration.context_exceptions import (
    ContextOrchestrationError,
)
from requirement_intelligence.context_orchestration.models.engineering_context import (
    EVIDENCE_DOMAINS,
)
from requirement_intelligence.context_orchestration.policy.orchestration_policy import (
    EvidenceBudget,
)
from requirement_intelligence.models.enums import SourceCategory


def allocate_evidence_budget(
    budget: EvidenceBudget, available: Mapping[SourceCategory, int]
) -> dict[SourceCategory, int]:
    """Allocate *budget* across the evidence domains, given what each can supply.

    Args:
        budget: The policy's declared per-domain and total bounds.
        available: Artifacts each domain could contribute, summed across every
            candidate group. Domains absent from the mapping supply nothing.

    Returns:
        dict[SourceCategory, int]: The artifacts each domain may contribute, keyed
        by every member of :data:`EVIDENCE_DOMAINS` — a domain that can supply
        nothing is allocated zero rather than omitted, so callers never guess.

    Raises:
        ContextOrchestrationError: If any availability is negative.
    """
    ceilings = _ceilings(budget, available)

    if sum(ceilings.values()) <= budget.max_artifacts_total:
        return ceilings

    return _water_fill(ceilings, budget.max_artifacts_total)


def _ceilings(
    budget: EvidenceBudget, available: Mapping[SourceCategory, int]
) -> dict[SourceCategory, int]:
    """The most each domain could ever be allocated: its cap, bounded by its supply."""
    ceilings: dict[SourceCategory, int] = {}
    for domain in EVIDENCE_DOMAINS:
        supply = available.get(domain, 0)
        if supply < 0:
            raise ContextOrchestrationError(
                f"Domain '{domain}' reports {supply} available artifact(s); "
                f"availability cannot be negative."
            )
        ceilings[domain] = min(budget.max_artifacts_per_domain, supply)
    return ceilings


def _water_fill(ceilings: Mapping[SourceCategory, int], total: int) -> dict[SourceCategory, int]:
    """Distribute *total* across the contesting domains, max-min fairly.

    Only domains with a non-zero ceiling contest: allocating to a domain that has
    no evidence would strand budget that another domain could spend.
    """
    allocation: dict[SourceCategory, int] = dict.fromkeys(EVIDENCE_DOMAINS, 0)
    contesting = [domain for domain in EVIDENCE_DOMAINS if ceilings[domain] > 0]
    remaining = total

    while contesting and remaining > 0:
        share = remaining // len(contesting)
        if share == 0:
            break

        settled = [domain for domain in contesting if ceilings[domain] <= share]
        if not settled:
            # No domain is satisfied by an equal share, so every contender takes one.
            for domain in contesting:
                allocation[domain] = share
                remaining -= share
            break

        for domain in settled:
            allocation[domain] = ceilings[domain]
            remaining -= ceilings[domain]
        contesting = [domain for domain in contesting if domain not in settled]

    # Whatever an equal split could not divide is now smaller than the number of
    # domains still wanting evidence, so it is granted one unit at a time in
    # canonical order. Handing the whole remainder to the first domain would be
    # equally deterministic and needlessly unfair — it would let domain order
    # decide what an equal split had just refused to.
    for domain in EVIDENCE_DOMAINS:
        if remaining <= 0:
            break
        if allocation[domain] < ceilings[domain]:
            allocation[domain] += 1
            remaining -= 1

    return allocation
