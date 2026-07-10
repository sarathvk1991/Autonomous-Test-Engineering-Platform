"""EngineeringContextOrchestrator — the runtime's single orchestration point.

Sits between Consolidation and Analysis and answers the one question no other
component may answer: *which evidence does this reasoning session receive?*

    list[ConsolidatedArtifact]  ->  EngineeringContextOrchestrator  ->  EngineeringContext

Responsibilities
----------------
* Consume the ``ConsolidatedArtifact``s Consolidation produced.
* Execute the governed :class:`OrchestrationPolicy` — rank, select, order.
* Derive the :class:`ContextSubject` the context is about.
* Invoke :class:`EngineeringContextBuilder` to construct the context.
* Record why each group was included (the Orchestration Reason and the
  per-group inclusion reasons).

It does **not** own grouping (Consolidation), connectors, prompt rendering,
analysis, validation, or execution writing. It reads consolidated artifacts and
returns a context; it never mutates either.

Policy support at CAP-076C
--------------------------
Only :class:`~...policy.default_policy.LegacySelectionPolicy`'s rules are
executable today: the ``single_largest`` strategy and ``group_order`` evidence
ordering, which together reproduce the pre-CAP-076 runtime selection exactly.
``coverage_guaranteed`` selection and ``risk_then_record_id`` ordering — the
rules ``DefaultOrchestrationPolicy`` declares — raise rather than silently
degrade. Activating them is CAP-076D. An orchestrator that quietly did
something *close to* what a policy asked for would defeat the purpose of having
a governed policy at all.

Determinism (CAP-076A Invariant 7)
----------------------------------
Every ranking key is a total order over data the groups already carry, and the
policy's tie-breaker terminates every comparison. Two runs over the same
consolidated artifacts select the same groups in the same order.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from requirement_intelligence.context_orchestration.context_exceptions import (
    ContextOrchestrationError,
)
from requirement_intelligence.context_orchestration.engineering_context_builder import (
    EngineeringContextBuilder,
)
from requirement_intelligence.context_orchestration.models.engineering_context import (
    ContextSubject,
    ContextSubjectBasis,
    EngineeringContext,
)
from requirement_intelligence.context_orchestration.policy.orchestration_policy import (
    EvidenceOrdering,
    OrchestrationPolicy,
    RankingKey,
    SelectionStrategy,
    TieBreaker,
)
from requirement_intelligence.models.consolidated_artifact import ConsolidatedArtifact
from requirement_intelligence.models.enums import RiskLevel

#: Severity ladder used by ``RISK_LEVEL_DESC``. Deliberately a local constant
#: rather than an import of ``consolidation_rules._RISK_ORDER``: orchestration
#: must not reach into Consolidation's private module, and ranking severity is
#: an orchestration concern (ADR-0015 §D3).
_RISK_RANK: dict[RiskLevel, int] = {
    RiskLevel.LOW: 0,
    RiskLevel.MEDIUM: 1,
    RiskLevel.HIGH: 2,
    RiskLevel.CRITICAL: 3,
}

#: Maps the grouping dimension encoded in a ``consolidated_id`` onto the subject
#: basis. ``build_consolidated_id`` mints ``cons-<dimension>-<slug>``; a group
#: does not otherwise retain the dimension it was formed on.
_BASIS_BY_DIMENSION: dict[str, ContextSubjectBasis] = {
    "component": ContextSubjectBasis.COMPONENT,
    "tag": ContextSubjectBasis.TAG,
    "endpoint": ContextSubjectBasis.ENDPOINT,
    "risk": ContextSubjectBasis.RISK,
}

_CONSOLIDATED_ID_PREFIX = "cons-"


@dataclass(frozen=True)
class ContextOrchestrationResult:
    """The orchestrator's output: the context, and the groups that composed it.

    ``context`` is the product. ``selected_groups`` is returned alongside it
    because the execution package still persists the selected
    ``ConsolidatedArtifact`` verbatim (``consolidated_artifact.json``), and a
    context — which flattens evidence across its groups — cannot reconstitute
    one. Callers read the groups; they never re-select.
    """

    context: EngineeringContext
    selected_groups: tuple[ConsolidatedArtifact, ...]


def _total_artifacts(group: ConsolidatedArtifact) -> int:
    """Total source artifacts a group carries across all three domains."""
    return (
        len(group.functional_artifacts)
        + len(group.security_artifacts)
        + len(group.quality_artifacts)
    )


#: One sort-key function per ranking key. Each returns a value whose natural
#: ascending order is the key's declared order, so a tuple of them sorts
#: correctly under a single ``sorted(..., key=...)`` with no ``reverse``.
_RANKING_KEY_FUNCTIONS = {
    RankingKey.RISK_LEVEL_DESC: lambda g: -_RISK_RANK[g.risk_level],
    RankingKey.ARTIFACT_COUNT_DESC: lambda g: -_total_artifacts(g),
    RankingKey.CONSOLIDATED_ID_ASC: lambda g: g.consolidated_id,
}

_TIE_BREAKER_FUNCTIONS = {
    TieBreaker.CONSOLIDATED_ID_ASC: lambda g: g.consolidated_id,
}


class EngineeringContextOrchestrator:
    """Applies one governed :class:`OrchestrationPolicy` to produce one context.

    Stateless and deterministic; a single instance is safe to reuse across runs.
    """

    def __init__(
        self,
        policy: OrchestrationPolicy,
        builder: EngineeringContextBuilder,
    ) -> None:
        """Bind the orchestrator to the policy it executes and the builder it calls."""
        if not isinstance(policy, OrchestrationPolicy):
            raise ContextOrchestrationError(
                f"Expected an OrchestrationPolicy, got: {type(policy).__name__}"
            )
        if not isinstance(builder, EngineeringContextBuilder):
            raise ContextOrchestrationError(
                f"Expected an EngineeringContextBuilder, got: {type(builder).__name__}"
            )
        self._policy = policy
        self._builder = builder

    @property
    def policy(self) -> OrchestrationPolicy:
        """The governed policy this orchestrator executes."""
        return self._policy

    def orchestrate(self, candidates: Sequence[ConsolidatedArtifact]) -> ContextOrchestrationResult:
        """Rank *candidates*, select under the policy, and build the context.

        Args:
            candidates: Every consolidation group eligible for this run, in the
                order Consolidation produced them.

        Returns:
            ContextOrchestrationResult: The composed context and the groups that
            composed it, in selection order.

        Raises:
            ContextOrchestrationError: If *candidates* is empty or wrongly typed,
                or if the policy declares a rule this orchestrator cannot execute.
            ContextConstructionError: Propagated from the builder.
            ContextBudgetExceededError: If the selected evidence exceeds the
                policy's budget. The orchestrator does not truncate: dropping
                evidence a reasoner would otherwise have seen is a decision, and
                it belongs to the coverage strategy that lands in CAP-076D.
        """
        self._validate_candidates(candidates)

        ranked = self._rank(candidates)
        selected = self._select(ranked)
        selected = self._apply_evidence_ordering(selected)

        subject = self._derive_subject(selected)
        inclusion_reasons = self._explain_inclusions(selected, ranked)

        context = self._builder.build(
            subject=subject,
            contributing_groups=selected,
            policy=self._policy,
            inclusion_reasons=inclusion_reasons,
            candidate_group_count=len(candidates),
        )
        return ContextOrchestrationResult(context=context, selected_groups=selected)

    # ------------------------------------------------------------------
    # Policy execution
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_candidates(candidates: Sequence[ConsolidatedArtifact]) -> None:
        """Reject an empty or wrongly-typed candidate set."""
        if not candidates:
            raise ContextOrchestrationError(
                "At least one ConsolidatedArtifact is required to orchestrate a context."
            )
        for candidate in candidates:
            if not isinstance(candidate, ConsolidatedArtifact):
                raise ContextOrchestrationError(
                    f"Expected ConsolidatedArtifact, got: {type(candidate).__name__}"
                )

    def _rank(self, candidates: Sequence[ConsolidatedArtifact]) -> tuple[ConsolidatedArtifact, ...]:
        """Sort candidates by the policy's ranking keys, then its tie-breaker."""
        ranking = self._policy.ranking
        key_functions = [_RANKING_KEY_FUNCTIONS[key] for key in ranking.keys]
        key_functions.append(_TIE_BREAKER_FUNCTIONS[ranking.tie_breaker])

        def sort_key(group: ConsolidatedArtifact) -> tuple[object, ...]:
            return tuple(function(group) for function in key_functions)

        return tuple(sorted(candidates, key=sort_key))

    def _select(self, ranked: Sequence[ConsolidatedArtifact]) -> tuple[ConsolidatedArtifact, ...]:
        """Draw the contributing groups from the ranking, per the policy's strategy."""
        strategy = self._policy.selection_strategy
        if strategy == SelectionStrategy.SINGLE_LARGEST:
            return (ranked[0],)
        raise ContextOrchestrationError(
            f"Policy '{self._policy.policy_id}' declares selection strategy "
            f"'{strategy}', which this orchestrator does not execute. Only "
            f"'{SelectionStrategy.SINGLE_LARGEST}' is active; multi-source "
            f"activation is CAP-076D."
        )

    def _apply_evidence_ordering(
        self, selected: tuple[ConsolidatedArtifact, ...]
    ) -> tuple[ConsolidatedArtifact, ...]:
        """Order evidence within the selection, per the policy's ordering rule."""
        ordering = self._policy.evidence_ordering
        if ordering == EvidenceOrdering.GROUP_ORDER:
            return selected
        raise ContextOrchestrationError(
            f"Policy '{self._policy.policy_id}' declares evidence ordering "
            f"'{ordering}', which this orchestrator does not execute. Only "
            f"'{EvidenceOrdering.GROUP_ORDER}' is active; reordering evidence "
            f"across sources is CAP-076D."
        )

    # ------------------------------------------------------------------
    # Subject derivation and explainability
    # ------------------------------------------------------------------

    @staticmethod
    def _derive_subject(selected: Sequence[ConsolidatedArtifact]) -> ContextSubject:
        """Derive what the context is about from the groups that compose it."""
        if len(selected) == 1:
            group = selected[0]
            return ContextSubject(
                label=group.module,
                business_area=group.business_area,
                basis=_basis_of(group),
            )
        modules = sorted({group.module for group in selected})
        business_areas = [g.business_area for g in selected if g.business_area]
        return ContextSubject(
            label=" + ".join(modules),
            business_area=business_areas[0] if len(set(business_areas)) == 1 else None,
            basis=ContextSubjectBasis.MULTI,
        )

    def _explain_inclusions(
        self,
        selected: Sequence[ConsolidatedArtifact],
        ranked: Sequence[ConsolidatedArtifact],
    ) -> tuple[str, ...]:
        """Explain, per group, the rank it achieved and the rule that admitted it.

        The context's ``orchestration_reason`` renders the policy's own template
        and speaks about the context as a whole. These reasons are the per-group
        counterpart: they name the position each group held in the ranking and
        the total it was ranked against, so no group's presence is unexplained
        (CAP-076C Stage 9).
        """
        keys = ", ".join(str(key) for key in self._policy.ranking.keys)
        positions = {group.consolidated_id: index for index, group in enumerate(ranked, start=1)}
        return tuple(
            f"Ranked {positions[group.consolidated_id]} of {len(ranked)} candidate group(s) "
            f"by [{keys}], tie-broken by {self._policy.ranking.tie_breaker}, and admitted "
            f"by the '{self._policy.selection_strategy}' strategy of policy "
            f"'{self._policy.policy_id}' v{self._policy.policy_version}."
            for group in selected
        )


def _basis_of(group: ConsolidatedArtifact) -> ContextSubjectBasis:
    """Recover the grouping dimension a group was formed on, from its id.

    Returns :attr:`ContextSubjectBasis.MULTI` when the id does not carry a
    recognisable dimension — the honest answer for a group whose subject cannot
    be attributed to any single dimension this model knows about.
    """
    identifier = group.consolidated_id.lower()
    if not identifier.startswith(_CONSOLIDATED_ID_PREFIX):
        return ContextSubjectBasis.MULTI
    remainder = identifier[len(_CONSOLIDATED_ID_PREFIX) :]
    dimension = remainder.split("-", 1)[0]
    return _BASIS_BY_DIMENSION.get(dimension, ContextSubjectBasis.MULTI)
