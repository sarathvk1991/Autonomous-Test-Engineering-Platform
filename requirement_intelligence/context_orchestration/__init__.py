"""Engineering Context Orchestration — the canonical orchestration subsystem.

Sits between Consolidation and Analysis:

    list[ConsolidatedArtifact]  ->  Engineering Context Orchestrator  ->  EngineeringContext

Consolidation owns *grouping*: which records share an attribute. This subsystem
owns *orchestration*: which evidence a reasoning session receives, under a
governed :class:`OrchestrationPolicy`. See ADR-0015.

Scope at CAP-076D
-----------------
The subsystem is **live and multi-source**. :class:`EngineeringContextOrchestrator`
is the runtime's single orchestration point: the CLI hands it every consolidation
group, it executes :class:`DefaultOrchestrationPolicy`, and the resulting
``EngineeringContext`` flows to the prompt builder, the analysis service, and
the execution package.

:class:`DefaultOrchestrationPolicy` is the **active** policy. It ranks candidate
groups by rolled-up risk before size, guarantees that every evidence domain the
candidates carry is represented, and bounds each domain so no single verbose
source can crowd out the others — repairing the CAP-074B defect, under which a
reasoner saw one group's evidence and therefore one domain's.

:class:`LegacySelectionPolicy` remains available as the **control arm**: it
reproduces the pre-CAP-076 selection rule exactly, so running both policies over
the same candidates isolates a behaviour change to the policy that caused it.

A note on the word "orchestration"
----------------------------------
ADR-0002, ADR-0003 and ADR-0011 use *orchestration boundary* for components that
sequence collaborators and own **no** policy (``ResponseNormalizer``,
``ResponseValidator``, ``CP1Service``, ``RequirementAnalysisService``).
Engineering Context Orchestration is the opposite: owning policy is its purpose.
Always use the full term (CAP-076A §0.1).
"""

from __future__ import annotations

from requirement_intelligence.context_orchestration.context_exceptions import (
    ContextBudgetExceededError,
    ContextConstructionError,
    ContextOrchestrationError,
    PolicyCompatibilityError,
)
from requirement_intelligence.context_orchestration.engineering_context_builder import (
    SUPPORTED_POLICY_MAJOR,
    EngineeringContextBuilder,
)
from requirement_intelligence.context_orchestration.engineering_context_orchestrator import (
    ContextOrchestrationResult,
    EngineeringContextOrchestrator,
)
from requirement_intelligence.context_orchestration.evidence_budget import (
    allocate_evidence_budget,
)
from requirement_intelligence.context_orchestration.evidence_ordering import order_evidence
from requirement_intelligence.context_orchestration.evidence_selection import GroupContribution
from requirement_intelligence.context_orchestration.models import (
    ENGINEERING_CONTEXT_VERSION,
    EVIDENCE_DOMAINS,
    ContextContribution,
    ContextCorrelation,
    ContextCoverage,
    ContextCoverageDomain,
    ContextDependencies,
    ContextEvidence,
    ContextEvidenceBudgetUsage,
    ContextGrounding,
    ContextMetadata,
    ContextProvenance,
    ContextRanking,
    ContextRankingEntry,
    ContextSubject,
    ContextSubjectBasis,
    DomainBudgetUsage,
    EngineeringContext,
    EngineeringContextId,
    OrchestrationMetadata,
    OrchestrationPolicyId,
    PolicyVersion,
    RankingScoreComponent,
    SourceDistributionEntry,
)
from requirement_intelligence.context_orchestration.policy import (
    CoverageMode,
    CoverageRule,
    DefaultOrchestrationPolicy,
    EvidenceBudget,
    EvidenceOrdering,
    LegacySelectionPolicy,
    OrchestrationPolicy,
    RankingKey,
    RankingRule,
    SelectionStrategy,
    TieBreaker,
)

__all__ = [
    "ENGINEERING_CONTEXT_VERSION",
    "EVIDENCE_DOMAINS",
    "SUPPORTED_POLICY_MAJOR",
    "ContextBudgetExceededError",
    "ContextConstructionError",
    "ContextContribution",
    "ContextCorrelation",
    "ContextCoverage",
    "ContextCoverageDomain",
    "ContextDependencies",
    "ContextEvidence",
    "ContextEvidenceBudgetUsage",
    "ContextGrounding",
    "ContextMetadata",
    "ContextOrchestrationError",
    "ContextOrchestrationResult",
    "ContextProvenance",
    "ContextRanking",
    "ContextRankingEntry",
    "ContextSubject",
    "ContextSubjectBasis",
    "CoverageMode",
    "CoverageRule",
    "DefaultOrchestrationPolicy",
    "DomainBudgetUsage",
    "EngineeringContext",
    "EngineeringContextBuilder",
    "EngineeringContextId",
    "EngineeringContextOrchestrator",
    "EvidenceBudget",
    "EvidenceOrdering",
    "GroupContribution",
    "LegacySelectionPolicy",
    "OrchestrationMetadata",
    "OrchestrationPolicy",
    "OrchestrationPolicyId",
    "PolicyCompatibilityError",
    "PolicyVersion",
    "RankingKey",
    "RankingRule",
    "RankingScoreComponent",
    "SelectionStrategy",
    "SourceDistributionEntry",
    "TieBreaker",
    "allocate_evidence_budget",
    "order_evidence",
]
