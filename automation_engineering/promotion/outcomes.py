"""Glue: map generation's own outcome unions
(:mod:`automation_engineering.generation.models`) onto this package's gate
inputs (:mod:`.gate`) -- promotion never re-judges reuse itself, it only
routes each outcome to the ONE decision that outcome kind already implies:

* ``Generated*`` (``NoMatch`` at generation time) -- the ONLY outcome kind
  with new content to promote. Resolved to a
  :class:`~automation_engineering.promotion.models.PromotionCandidate` via
  :mod:`.identity`, then gated (:func:`~automation_engineering.promotion.
  gate.evaluate_promotion`).
* ``Bound*`` (``TrustedReuse`` at generation time) -- nothing new was
  generated; the asset it bound to already exists in the tracked baseline
  (that is WHY the bind was trusted). Nothing to promote, no decision to
  make -- ``None``.
* ``Escalated*`` (``Escalation`` at generation time, either the reuse
  engine's own or the precise method-fit discharge's) -- carried through
  unedited (:func:`~automation_engineering.promotion.gate.
  evaluate_escalated_promotion`), joining the one shared review queue (D3).
"""

from __future__ import annotations

from automation_engineering.catalog.models import AssetCatalog
from automation_engineering.generation.models import (
    BoundPageObjectMethod,
    BoundStepDefinition,
    BoundUtilityMethod,
    EscalatedPageObjectMethodNeed,
    EscalatedStepNeed,
    EscalatedUtilityMethodNeed,
    GeneratedPageObject,
    GeneratedStepDefinition,
    GeneratedUtility,
    PageObjectMethodOutcome,
    StepDefinitionOutcome,
    UtilityMethodOutcome,
)
from automation_engineering.promotion.gate import evaluate_escalated_promotion, evaluate_promotion
from automation_engineering.promotion.identity import resolve_candidate_identity
from automation_engineering.promotion.models import (
    AssetGateOutcomes,
    PromotionCandidate,
    PromotionDecision,
)

#: The three "new content" generation outcomes -- the only ones with a
#: `java_source` to promote.
GeneratedOutcome = GeneratedStepDefinition | GeneratedPageObject | GeneratedUtility

#: The three "already in the baseline" generation outcomes -- never a
#: promotion candidate (see module docstring).
BoundOutcome = BoundStepDefinition | BoundPageObjectMethod | BoundUtilityMethod

#: The three "reuse engine could not trust this" generation outcomes -- each
#: carries an unedited `Escalation` (ADR-0044 D4).
EscalatedOutcome = EscalatedStepNeed | EscalatedPageObjectMethodNeed | EscalatedUtilityMethodNeed


def build_candidate(java_source: str) -> PromotionCandidate:
    """Resolve one generated asset's own identity (:mod:`.identity`) into a
    :class:`~automation_engineering.promotion.models.PromotionCandidate`."""
    asset, relative_path = resolve_candidate_identity(java_source)
    return PromotionCandidate(java_source=java_source, asset=asset, relative_path=relative_path)


def promote_outcome(
    outcome: StepDefinitionOutcome | PageObjectMethodOutcome | UtilityMethodOutcome,
    gates: AssetGateOutcomes | None,
    baseline_catalog: AssetCatalog,
) -> PromotionDecision | None:
    """Dispatch one generation outcome to its own promotion decision --
    ``None`` for a ``Bound*`` outcome (module docstring: nothing to promote).

    ``gates`` is required (and used) only for a ``Generated*`` outcome;
    raises :class:`ValueError` if omitted for one, since D2(a) cannot be
    evaluated without it.
    """
    if isinstance(
        outcome,
        (EscalatedStepNeed, EscalatedPageObjectMethodNeed, EscalatedUtilityMethodNeed),
    ):
        return evaluate_escalated_promotion(outcome.escalation)

    if isinstance(outcome, (BoundStepDefinition, BoundPageObjectMethod, BoundUtilityMethod)):
        return None

    if gates is None:
        raise ValueError(
            "gates is required to evaluate promotion for a Generated* outcome "
            f"({type(outcome).__name__})"
        )
    candidate = build_candidate(outcome.java_source)
    return evaluate_promotion(candidate, gates, baseline_catalog)


__all__ = [
    "BoundOutcome",
    "EscalatedOutcome",
    "GeneratedOutcome",
    "build_candidate",
    "promote_outcome",
]
