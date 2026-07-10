"""Deterministic ordering of evidence within one domain section.

The policy's :class:`EvidenceOrdering` decides two things at once, and it is
worth being explicit that they are the same decision:

* **Which artifacts survive the budget.** When a domain may contribute 25 of the
  71 artifacts a group carries, the ordering decides which 25. Under
  ``risk_then_record_id`` the 25 most severe survive; under ``group_order`` the
  first 25 the source system happened to emit survive.
* **How the surviving artifacts read.** The order of the lines the reasoner sees
  inside each of the prompt's three domain sections.

Determinism (CAP-076A Invariant 7)
----------------------------------
``risk_then_record_id`` sorts on ``(-risk, source_record_id)``. Both components
are values the artifact already carries, and ``source_record_id`` is a required,
non-empty string, so the comparison always terminates. ``artifact_id`` is never
used: all three mappers mint it from ``uuid4``, and an ordering keyed on it would
differ on every run. Neither is ``created_at``: it is optional, and timestamp
ordering is forbidden.

Python's sort is stable, so artifacts that compare equal retain the order the
orchestrator supplied them in — itself a deterministic, rank-ordered sequence.
"""

from __future__ import annotations

from collections.abc import Sequence

from requirement_intelligence.consolidation.consolidation_rules import artifact_risk
from requirement_intelligence.context_orchestration.context_exceptions import (
    ContextOrchestrationError,
)
from requirement_intelligence.context_orchestration.policy.orchestration_policy import (
    EvidenceOrdering,
)
from requirement_intelligence.models.enums import RiskLevel
from requirement_intelligence.models.source_artifact import SourceArtifact

#: Severity ladder for ordering. A local constant rather than an import of
#: ``consolidation_rules._RISK_ORDER``: orchestration must not reach into
#: Consolidation's private module (ADR-0015 §D3). ``artifact_risk`` — which *is*
#: public, and is the platform's single owner of severity normalisation — is
#: reused rather than reimplemented.
_RISK_RANK: dict[RiskLevel, int] = {
    RiskLevel.LOW: 0,
    RiskLevel.MEDIUM: 1,
    RiskLevel.HIGH: 2,
    RiskLevel.CRITICAL: 3,
}


def order_evidence(
    ordering: EvidenceOrdering, artifacts: Sequence[SourceArtifact]
) -> tuple[SourceArtifact, ...]:
    """Order *artifacts* within one domain, per the policy's ordering rule.

    Args:
        ordering: The rule the governed policy declared.
        artifacts: One domain's artifacts, in the order the orchestrator
            assembled them (contributing groups in rank order).

    Returns:
        tuple[SourceArtifact, ...]: The ordered evidence.

    Raises:
        ContextOrchestrationError: If *ordering* names a rule this module does
            not implement. Silently falling back to the supplied order would make
            a governed policy advisory.
    """
    if ordering == EvidenceOrdering.GROUP_ORDER:
        return tuple(artifacts)
    if ordering == EvidenceOrdering.RISK_THEN_RECORD_ID:
        return tuple(sorted(artifacts, key=_risk_then_record_id))
    raise ContextOrchestrationError(
        f"Evidence ordering '{ordering}' is not implemented by this orchestrator."
    )


def _risk_then_record_id(artifact: SourceArtifact) -> tuple[int, str]:
    """Sort key placing the most severe artifact first, ties broken by record id."""
    return (-_RISK_RANK[artifact_risk(artifact)], artifact.source_record_id)
