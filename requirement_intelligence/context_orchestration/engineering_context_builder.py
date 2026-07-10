"""EngineeringContextBuilder — constructs an immutable EngineeringContext.

The builder owns **construction only**. Given a subject, an already-selected,
already-ordered, already-budgeted sequence of ``ConsolidatedArtifact``s, and the
policy under which they were chosen, it validates the inputs and assembles one
:class:`EngineeringContext`.

What the builder does *not* do
-----------------------------
It does not orchestrate, rank, apply coverage, apply a budget, or execute a
policy. Those are the Engineering Context Orchestrator's responsibilities
(CAP-076C). The builder *reads* the policy in exactly three ways, none of which
is a decision:

1. **Compatibility check** — refuses a policy whose major version it was not
   built against.
2. **Budget enforcement as an input contract** — raises when the caller hands it
   more evidence than the policy permits. Enforcing a bound is not applying one:
   the builder never truncates, it rejects.
3. **Reason rendering** — substitutes provenance facts into the policy's own
   explainability template.

Reproducibility (CAP-076A Invariant 7)
--------------------------------------
The builder is a pure function of its inputs. The context identity is a SHA-256
of the subject and the contributing group ids — never ``uuid4``, never a clock,
never ``hash()``. This matters concretely: all three mappers mint
``artifact_id=str(uuid4())``, so any identity derived from an artifact id would
differ on every run. Derived collections (``components``, ``endpoints``) are
sorted, never taken from set-iteration order.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Sequence

from requirement_intelligence.consolidation.consolidation_rules import (
    extract_endpoint,
    rollup_risk,
)
from requirement_intelligence.context_orchestration.context_exceptions import (
    ContextBudgetExceededError,
    ContextConstructionError,
    PolicyCompatibilityError,
)
from requirement_intelligence.context_orchestration.models.context_identity import (
    EngineeringContextId,
    PolicyVersion,
)
from requirement_intelligence.context_orchestration.models.engineering_context import (
    ENGINEERING_CONTEXT_VERSION,
    ContextContribution,
    ContextEvidence,
    ContextMetadata,
    ContextProvenance,
    ContextSubject,
    EngineeringContext,
    OrchestrationMetadata,
)
from requirement_intelligence.context_orchestration.policy.orchestration_policy import (
    OrchestrationPolicy,
)
from requirement_intelligence.models.consolidated_artifact import ConsolidatedArtifact
from requirement_intelligence.models.source_artifact import SourceArtifact

#: The ``OrchestrationPolicy`` major version this builder understands.
SUPPORTED_POLICY_MAJOR = 1

#: Length of the identity digest appended to a context id. Twelve hex characters
#: is ~48 bits — ample for the tens of groups a single run produces, and short
#: enough to stay readable in a manifest.
_DIGEST_LENGTH = 12

_SLUG_RE = re.compile(r"[^a-z0-9]+")


class EngineeringContextBuilder:
    """Validates inputs and constructs one immutable :class:`EngineeringContext`.

    Stateless and deterministic; a single instance is safe to reuse.
    """

    def __init__(self, context_model_version: str = ENGINEERING_CONTEXT_VERSION) -> None:
        """Bind the builder to the context model shape it constructs."""
        self._context_model_version = context_model_version

    def build(
        self,
        *,
        subject: ContextSubject,
        contributing_groups: Sequence[ConsolidatedArtifact],
        policy: OrchestrationPolicy,
        inclusion_reasons: Sequence[str] | None = None,
        candidate_group_count: int | None = None,
    ) -> EngineeringContext:
        """Assemble one ``EngineeringContext`` from already-selected groups.

        Args:
            subject: What the context is about. Chosen by the orchestrator.
            contributing_groups: The consolidated artifacts to draw evidence
                from, in the order the orchestrator selected them. Evidence
                order is preserved exactly; the builder never reorders.
            policy: The policy under which the groups were selected. Recorded in
                the context and used to render the Orchestration Reason.
            inclusion_reasons: One reason per contributing group, explaining why
                the policy admitted it. Supplied by the orchestrator, which is
                the only component that knows the ranking each group survived.
                When omitted, a reason naming the policy is recorded — never an
                empty one, because an unexplained group is not permitted.
            candidate_group_count: How many groups the orchestrator ranked before
                selecting. Defaults to the number of contributing groups, which
                is the truth when no group was discarded.

        Returns:
            EngineeringContext: The immutable, fully populated context.

        Raises:
            ContextConstructionError: If any input is missing, wrongly typed, or
                if the supplied reasons or candidate count do not match the groups.
            PolicyCompatibilityError: If *policy* has an incompatible major version.
            ContextBudgetExceededError: If the evidence exceeds *policy*'s budget.
        """
        self._validate_inputs(subject, contributing_groups, policy)
        self._validate_policy_compatibility(policy)

        reasons = self._resolve_inclusion_reasons(contributing_groups, policy, inclusion_reasons)
        candidates = self._resolve_candidate_count(contributing_groups, candidate_group_count)

        evidence = self._collect_evidence(contributing_groups)
        self._enforce_budget(evidence, policy)

        members = self._all_artifacts(evidence)
        provenance = self._build_provenance(contributing_groups, reasons, candidates, len(members))
        context_id = self._build_context_id(subject, provenance.contributing_consolidated_ids)

        return EngineeringContext(
            context_id=context_id,
            subject=subject,
            evidence=evidence,
            context_metadata=self._build_metadata(members),
            provenance=provenance,
            orchestration=OrchestrationMetadata(
                policy_id=policy.policy_id,
                policy_version=policy.policy_version,
                context_model_version=self._context_model_version,
            ),
            orchestration_reason=self._render_reason(
                subject, contributing_groups, evidence, policy, candidates
            ),
        )

    # ------------------------------------------------------------------
    # Input validation (never a policy decision)
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_inputs(
        subject: ContextSubject,
        contributing_groups: Sequence[ConsolidatedArtifact],
        policy: OrchestrationPolicy,
    ) -> None:
        """Reject missing or wrongly-typed builder inputs."""
        if not isinstance(subject, ContextSubject):
            raise ContextConstructionError(
                f"Expected a ContextSubject, got: {type(subject).__name__}"
            )
        if not isinstance(policy, OrchestrationPolicy):
            raise ContextConstructionError(
                f"Expected an OrchestrationPolicy, got: {type(policy).__name__}"
            )
        if not contributing_groups:
            raise ContextConstructionError(
                "At least one ConsolidatedArtifact must contribute to a context."
            )
        for group in contributing_groups:
            if not isinstance(group, ConsolidatedArtifact):
                raise ContextConstructionError(
                    f"Expected ConsolidatedArtifact, got: {type(group).__name__}"
                )

    @staticmethod
    def _resolve_inclusion_reasons(
        groups: Sequence[ConsolidatedArtifact],
        policy: OrchestrationPolicy,
        supplied: Sequence[str] | None,
    ) -> tuple[str, ...]:
        """Return one non-empty inclusion reason per contributing group."""
        if supplied is None:
            return tuple(f"Included by policy '{policy.policy_id}'." for _ in groups)
        if len(supplied) != len(groups):
            raise ContextConstructionError(
                f"Expected one inclusion reason per contributing group: "
                f"{len(groups)} group(s), {len(supplied)} reason(s)."
            )
        for reason in supplied:
            if not isinstance(reason, str) or not reason.strip():
                raise ContextConstructionError("An inclusion reason must be a non-empty string.")
        return tuple(supplied)

    @staticmethod
    def _resolve_candidate_count(
        groups: Sequence[ConsolidatedArtifact], supplied: int | None
    ) -> int:
        """Return the number of groups the orchestrator ranked."""
        if supplied is None:
            return len(groups)
        if supplied < len(groups):
            raise ContextConstructionError(
                f"candidate_group_count ({supplied}) is below the {len(groups)} "
                f"group(s) supplied as contributing."
            )
        return supplied

    @staticmethod
    def _validate_policy_compatibility(policy: OrchestrationPolicy) -> None:
        """Refuse a policy whose major version this builder was not built against."""
        supported = PolicyVersion(SUPPORTED_POLICY_MAJOR, 0, 0)
        if not policy.policy_version.is_compatible_with(supported):
            raise PolicyCompatibilityError(
                f"Policy '{policy.policy_id}' version {policy.policy_version} is not "
                f"compatible with EngineeringContextBuilder, which supports major "
                f"version {SUPPORTED_POLICY_MAJOR}."
            )

    @staticmethod
    def _enforce_budget(evidence: ContextEvidence, policy: OrchestrationPolicy) -> None:
        """Reject evidence exceeding the policy budget. Never truncates.

        Truncating would be *applying* the budget, which is orchestration. The
        builder only enforces the contract the orchestrator was obliged to meet.
        """
        budget = policy.evidence_budget
        domains = (
            ("functional", len(evidence.functional_artifacts)),
            ("security", len(evidence.security_artifacts)),
            ("quality", len(evidence.quality_artifacts)),
        )
        for domain, count in domains:
            if count > budget.max_artifacts_per_domain:
                raise ContextBudgetExceededError(
                    f"Policy '{policy.policy_id}' permits {budget.max_artifacts_per_domain} "
                    f"{domain} artifacts; {count} were supplied. The orchestrator must "
                    f"apply the budget before calling the builder."
                )
        if evidence.total_count > budget.max_artifacts_total:
            raise ContextBudgetExceededError(
                f"Policy '{policy.policy_id}' permits {budget.max_artifacts_total} artifacts "
                f"in total; {evidence.total_count} were supplied."
            )

    # ------------------------------------------------------------------
    # Construction helpers (pure, deterministic)
    # ------------------------------------------------------------------

    @staticmethod
    def _collect_evidence(groups: Sequence[ConsolidatedArtifact]) -> ContextEvidence:
        """Flatten the groups' three domain lists, preserving the supplied order."""
        functional: list[SourceArtifact] = []
        security: list[SourceArtifact] = []
        quality: list[SourceArtifact] = []
        for group in groups:
            functional.extend(group.functional_artifacts)
            security.extend(group.security_artifacts)
            quality.extend(group.quality_artifacts)
        return ContextEvidence(
            functional_artifacts=tuple(functional),
            security_artifacts=tuple(security),
            quality_artifacts=tuple(quality),
        )

    @staticmethod
    def _all_artifacts(evidence: ContextEvidence) -> tuple[SourceArtifact, ...]:
        """Every evidence artifact, in domain order."""
        return (
            *evidence.functional_artifacts,
            *evidence.security_artifacts,
            *evidence.quality_artifacts,
        )

    @staticmethod
    def _build_metadata(members: Sequence[SourceArtifact]) -> ContextMetadata:
        """Derive the engineering surface from the evidence.

        Risk rollup is delegated to ``consolidation_rules.rollup_risk`` — the
        platform's single owner of severity normalisation. Duplicating that
        ladder here would be the exact duplication CAP-076A §7 promised to avoid.
        Components and endpoints are ``sorted`` so ordering never depends on set
        iteration (Invariant 7).
        """
        components = sorted(
            {a.component.strip() for a in members if a.component and a.component.strip()}
        )
        endpoints = sorted({e for e in (extract_endpoint(a) for a in members) if e})
        return ContextMetadata(
            risk_level=rollup_risk(list(members)),
            components=tuple(components),
            endpoints=tuple(endpoints),
        )

    @staticmethod
    def _build_provenance(
        groups: Sequence[ConsolidatedArtifact],
        inclusion_reasons: Sequence[str],
        candidate_group_count: int,
        artifact_count: int,
    ) -> ContextProvenance:
        """Record which groups contributed, in the order they were selected."""
        contributions = tuple(
            ContextContribution(
                consolidated_id=group.consolidated_id,
                module=group.module,
                business_area=group.business_area,
                consolidation_reason=group.consolidation_reason,
                artifact_count=(
                    len(group.functional_artifacts)
                    + len(group.security_artifacts)
                    + len(group.quality_artifacts)
                ),
                inclusion_reason=reason,
            )
            for group, reason in zip(groups, inclusion_reasons, strict=True)
        )
        return ContextProvenance(
            contributions=contributions,
            candidate_group_count=candidate_group_count,
            source_artifact_count=artifact_count,
        )

    @staticmethod
    def _build_context_id(
        subject: ContextSubject, contributing_ids: Sequence[str]
    ) -> EngineeringContextId:
        """Mint a deterministic context id from the subject and contributing groups.

        Reproducible across processes and machines: SHA-256 over a canonical,
        order-sensitive joining of the inputs. Order is significant because two
        contexts drawing the same groups in a different evidence order are
        different contexts.
        """
        slug = _SLUG_RE.sub("-", subject.label.lower()).strip("-") or "context"
        payload = "\n".join([subject.label, *contributing_ids]).encode("utf-8")
        digest = hashlib.sha256(payload).hexdigest()[:_DIGEST_LENGTH]
        return EngineeringContextId(f"ctx-{slug}-{digest}")

    @staticmethod
    def _render_reason(
        subject: ContextSubject,
        groups: Sequence[ConsolidatedArtifact],
        evidence: ContextEvidence,
        policy: OrchestrationPolicy,
        candidate_group_count: int,
    ) -> str:
        """Render the Orchestration Reason from the policy's own template."""
        categories = ", ".join(sorted(str(c) for c in evidence.categories_present))
        return policy.render_reason(
            subject=subject.label,
            strategy=str(policy.selection_strategy),
            groups=len(groups),
            candidates=candidate_group_count,
            categories=categories or "no evidence",
        )
