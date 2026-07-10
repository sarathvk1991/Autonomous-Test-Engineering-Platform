"""EngineeringContextBuilder — constructs an immutable EngineeringContext.

The builder owns **construction only**. Given a subject, the already-selected,
already-ordered, already-budgeted evidence, the per-group contributions that
produced it, the decisions the orchestrator recorded, and the policy those
decisions were made under, it validates the inputs and assembles one
:class:`EngineeringContext`.

What the builder does *not* do
-----------------------------
It does not orchestrate, rank, apply coverage, apply a budget, or execute a
policy. Those are the Engineering Context Orchestrator's responsibilities. The
builder *reads* the policy in exactly three ways, none of which is a decision:

1. **Compatibility check** — refuses a policy whose major version it was not
   built against.
2. **Budget enforcement as an input contract** — raises when the caller hands it
   more evidence than the policy permits. Enforcing a bound is not applying one:
   the builder never truncates, it rejects.
3. **Reason rendering** — substitutes provenance facts into the policy's own
   explainability template.

It is handed the evidence pre-assembled rather than handed the groups to flatten
(CAP-076D). A domain's evidence is ordered *across* the contributing groups, so
no group owns a contiguous slice of it; a builder that concatenated per-group
lists would silently undo the policy's ordering rule. Giving it nothing to
reorder is how "the builder never reorders" stays true structurally.

The one thing it derives
------------------------
:class:`ContextGrounding` — a pure measurement of the evidence it was handed. It
is not a decision: no ordering, selection or bound depends on it, and computing
it anywhere else would mean re-walking the same artifacts to reach the same
answer.

Reproducibility (CAP-076A Invariant 7)
--------------------------------------
The builder is a pure function of its inputs. The context identity is a SHA-256
of the subject and the contributing group ids — never ``uuid4``, never a clock,
never ``hash()``. This matters concretely: all three mappers mint
``artifact_id=str(uuid4())``, so any identity derived from an artifact id would
differ on every run. Derived collections (``components``, ``endpoints``,
``source_distribution``) are sorted, never taken from set-iteration order.
"""

from __future__ import annotations

import hashlib
import re
from collections import Counter
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
from requirement_intelligence.context_orchestration.evidence_selection import GroupContribution
from requirement_intelligence.context_orchestration.models.context_identity import (
    EngineeringContextId,
    PolicyVersion,
)
from requirement_intelligence.context_orchestration.models.engineering_context import (
    ENGINEERING_CONTEXT_VERSION,
    EVIDENCE_DOMAINS,
    ContextContribution,
    ContextCoverage,
    ContextEvidence,
    ContextEvidenceBudgetUsage,
    ContextGrounding,
    ContextMetadata,
    ContextProvenance,
    ContextRanking,
    ContextSubject,
    EngineeringContext,
    OrchestrationMetadata,
    SourceDistributionEntry,
)
from requirement_intelligence.context_orchestration.policy.orchestration_policy import (
    OrchestrationPolicy,
)
from requirement_intelligence.models.enums import SourceCategory
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
        evidence: ContextEvidence,
        contributions: Sequence[GroupContribution],
        policy: OrchestrationPolicy,
        ranking: ContextRanking,
        coverage: ContextCoverage,
        evidence_budget: ContextEvidenceBudgetUsage,
        candidate_group_count: int | None = None,
    ) -> EngineeringContext:
        """Assemble one ``EngineeringContext`` from an orchestrator's decisions.

        Args:
            subject: What the context is about. Chosen by the orchestrator.
            evidence: The selected, ordered, budgeted evidence. Recorded verbatim;
                the builder never reorders or drops an artifact.
            contributions: One record per contributing group, in rank order,
                stating how many artifacts it supplied to each domain and why it
                was admitted.
            policy: The policy under which the decisions were made. Recorded in
                the context and used to render the Orchestration Reason.
            ranking: Every candidate group's rank, score, and fate.
            coverage: Whether each evidence domain was represented, and why.
            evidence_budget: How the policy's budget was allocated and spent.
            candidate_group_count: How many groups the orchestrator ranked before
                selecting. Defaults to the number of contributing groups, which
                is the truth when no group was discarded.

        Returns:
            EngineeringContext: The immutable, fully populated context.

        Raises:
            ContextConstructionError: If any input is missing, wrongly typed, or
                if the contributions do not account for the evidence supplied.
            PolicyCompatibilityError: If *policy* has an incompatible major version.
            ContextBudgetExceededError: If the evidence exceeds *policy*'s budget.
        """
        self._validate_inputs(subject, evidence, contributions, policy)
        self._validate_policy_compatibility(policy)
        self._validate_contributions_account_for_evidence(contributions, evidence)
        self._enforce_budget(evidence, policy)

        candidates = self._resolve_candidate_count(contributions, candidate_group_count)
        members = self._all_artifacts(evidence)
        provenance = self._build_provenance(contributions, candidates, len(members))
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
            ranking=ranking,
            coverage=coverage,
            evidence_budget=evidence_budget,
            grounding=self._build_grounding(evidence, members),
            orchestration_reason=self._render_reason(
                subject, contributions, evidence, policy, candidates
            ),
        )

    # ------------------------------------------------------------------
    # Input validation (never a policy decision)
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_inputs(
        subject: ContextSubject,
        evidence: ContextEvidence,
        contributions: Sequence[GroupContribution],
        policy: OrchestrationPolicy,
    ) -> None:
        """Reject missing or wrongly-typed builder inputs."""
        if not isinstance(subject, ContextSubject):
            raise ContextConstructionError(
                f"Expected a ContextSubject, got: {type(subject).__name__}"
            )
        if not isinstance(evidence, ContextEvidence):
            raise ContextConstructionError(
                f"Expected a ContextEvidence, got: {type(evidence).__name__}"
            )
        if not isinstance(policy, OrchestrationPolicy):
            raise ContextConstructionError(
                f"Expected an OrchestrationPolicy, got: {type(policy).__name__}"
            )
        if not contributions:
            raise ContextConstructionError(
                "At least one ConsolidatedArtifact must contribute to a context."
            )
        for contribution in contributions:
            if not isinstance(contribution, GroupContribution):
                raise ContextConstructionError(
                    f"Expected GroupContribution, got: {type(contribution).__name__}"
                )
            if not contribution.inclusion_reason.strip():
                raise ContextConstructionError(
                    f"Group '{contribution.consolidated_id}' was admitted without a reason; "
                    f"an unexplained group is not permitted."
                )

    @staticmethod
    def _validate_contributions_account_for_evidence(
        contributions: Sequence[GroupContribution], evidence: ContextEvidence
    ) -> None:
        """Every evidence artifact must be claimed by exactly one contributing group.

        This is the seam where a selection bug would otherwise pass silently: the
        orchestrator counts what each group supplied, and assembles the evidence
        separately. If the two disagree, one of them is wrong.
        """
        declared = {
            SourceCategory.FUNCTIONAL: sum(c.functional_count for c in contributions),
            SourceCategory.SECURITY: sum(c.security_count for c in contributions),
            SourceCategory.QUALITY: sum(c.quality_count for c in contributions),
        }
        supplied = {
            SourceCategory.FUNCTIONAL: len(evidence.functional_artifacts),
            SourceCategory.SECURITY: len(evidence.security_artifacts),
            SourceCategory.QUALITY: len(evidence.quality_artifacts),
        }
        for domain in EVIDENCE_DOMAINS:
            if declared[domain] != supplied[domain]:
                raise ContextConstructionError(
                    f"Contributing groups declare {declared[domain]} {domain} artifact(s) "
                    f"but {supplied[domain]} were supplied as evidence."
                )
        for contribution in contributions:
            if contribution.contributed_count == 0:
                raise ContextConstructionError(
                    f"Group '{contribution.consolidated_id}' contributed no evidence; "
                    f"a group that supplies nothing is not a contributor."
                )

    @staticmethod
    def _resolve_candidate_count(
        contributions: Sequence[GroupContribution], supplied: int | None
    ) -> int:
        """Return the number of groups the orchestrator ranked."""
        if supplied is None:
            return len(contributions)
        if supplied < len(contributions):
            raise ContextConstructionError(
                f"candidate_group_count ({supplied}) is below the {len(contributions)} "
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
    def _build_grounding(
        evidence: ContextEvidence, members: Sequence[SourceArtifact]
    ) -> ContextGrounding:
        """Measure what the assembled evidence is grounded in.

        ``source_distribution`` is what turns "the reasoner saw 54 artifacts" into
        "the reasoner saw 4 from JIRA, 25 from OWASP ZAP and 25 from SonarQube" —
        the single number that would have exposed the CAP-074B defect on sight.
        Sorted by source system so two runs serialise identically.
        """
        counts = Counter(str(artifact.source_system) for artifact in members)
        return ContextGrounding(
            evidence_domains=tuple(sorted(evidence.categories_present, key=_domain_position)),
            functional_count=len(evidence.functional_artifacts),
            security_count=len(evidence.security_artifacts),
            quality_count=len(evidence.quality_artifacts),
            total_count=evidence.total_count,
            source_distribution=tuple(
                SourceDistributionEntry(source_system=system, artifact_count=count)
                for system, count in sorted(counts.items())
            ),
        )

    @staticmethod
    def _build_provenance(
        contributions: Sequence[GroupContribution],
        candidate_group_count: int,
        artifact_count: int,
    ) -> ContextProvenance:
        """Record which groups contributed, in the order they were selected."""
        records = tuple(
            ContextContribution(
                consolidated_id=contribution.consolidated_id,
                module=contribution.group.module,
                business_area=contribution.group.business_area,
                consolidation_reason=contribution.group.consolidation_reason,
                rank=contribution.rank,
                artifact_count=contribution.contributed_count,
                candidate_artifact_count=contribution.candidate_count,
                functional_count=contribution.functional_count,
                security_count=contribution.security_count,
                quality_count=contribution.quality_count,
                inclusion_reason=contribution.inclusion_reason,
            )
            for contribution in contributions
        )
        return ContextProvenance(
            contributions=records,
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
        contributions: Sequence[GroupContribution],
        evidence: ContextEvidence,
        policy: OrchestrationPolicy,
        candidate_group_count: int,
    ) -> str:
        """Render the Orchestration Reason from the policy's own template."""
        categories = ", ".join(sorted(str(c) for c in evidence.categories_present))
        return policy.render_reason(
            subject=subject.label,
            strategy=str(policy.selection_strategy),
            groups=len(contributions),
            candidates=candidate_group_count,
            categories=categories or "no evidence",
        )


def _domain_position(category: SourceCategory) -> int:
    """Sort key placing evidence domains in the canonical order."""
    return EVIDENCE_DOMAINS.index(SourceCategory(category))
