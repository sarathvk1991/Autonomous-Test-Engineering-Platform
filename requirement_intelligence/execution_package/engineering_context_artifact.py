"""Engineering context artifact — responsible only for ``engineering_context.json``.

The Engineering Context Orchestrator owns *construction* of an
:class:`EngineeringContext`; this builder owns its *serialisation* into the
execution package, and :class:`~...execution_writer.ExecutionWriter` owns
writing the bytes. No component performs another's job.

Why a projection rather than ``context.model_dump()``
-----------------------------------------------------
The artifact answers an auditor's question — *what evidence did this reasoning
session receive, under which rules, and what did those rules turn away?* — so it
leads with identity, policy, and explanation, and summarises evidence to one line
per artifact. The full source records for the primary group are already persisted
verbatim in ``consolidated_artifact.json``; repeating every record here would
grow the package without saying anything new.

What it must never omit (CAP-076D Stage 6)
------------------------------------------
Every orchestration decision. A context that composed itself from 10 of 23
candidate groups has made 23 decisions, and all 23 are recorded: ``ranking``
carries one entry per candidate with the score it achieved and the reason it was
admitted or excluded; ``coverage`` states per domain whether evidence existed and
whether it was represented; ``evidenceBudget`` states what each domain was
allocated and spent. There is no orchestration decision this file does not name.

Determinism
-----------
Every value is read from the context, which is itself a pure function of the
consolidated artifacts. No timestamps, no uuids, no set iteration: two runs over
the same inputs produce byte-identical output.
"""

from __future__ import annotations

from typing import Any

from requirement_intelligence.context_orchestration.models.engineering_context import (
    ContextRankingEntry,
    EngineeringContext,
)
from requirement_intelligence.models.source_artifact import SourceArtifact

#: JSON contract version of ``engineering_context.json``. Independent of the
#: ``EngineeringContext`` model version: the artifact is a projection, and either
#: can change without the other.
#:
#: 2.0.0 (CAP-076D) added ``ranking``, ``coverage``, ``evidenceBudget`` and
#: ``groundingMetadata``, and reshaped ``provenance.contributions`` around the
#: contributed-versus-carried artifact counts a multi-source, budgeted context
#: requires. Major, not minor: a reader of the 1.0.0 shape would misread a
#: truncated group's ``artifactCount`` as the size of the group.
ENGINEERING_CONTEXT_ARTIFACT_VERSION = "2.0.0"


class EngineeringContextArtifactBuilder:
    """Build the canonical ``engineering_context.json`` dictionary for one run."""

    def build(self, context: EngineeringContext) -> dict[str, Any]:
        """Return the serialisable artifact for *context*."""
        evidence = context.evidence
        return {
            "engineeringContextArtifactVersion": ENGINEERING_CONTEXT_ARTIFACT_VERSION,
            "contextModelVersion": context.orchestration.context_model_version,
            "contextId": str(context.context_id),
            "subject": context.subject.model_dump(mode="json", by_alias=True),
            "orchestration": {
                "policyId": str(context.orchestration.policy_id),
                "policyVersion": str(context.orchestration.policy_version),
                "selectionStrategy": context.coverage.selection_strategy,
                "coverageMode": context.coverage.mode,
            },
            "orchestrationReason": context.orchestration_reason,
            "candidateGroupCount": context.provenance.candidate_group_count,
            "contributingGroupCount": context.provenance.contributing_group_count,
            "contributingConsolidatedIds": list(context.provenance.contributing_consolidated_ids),
            "selectedGroups": [
                _selected_group(entry) for entry in context.ranking.entries if entry.selected
            ],
            "excludedGroups": [
                _excluded_group(entry) for entry in context.ranking.entries if not entry.selected
            ],
            "ranking": {
                "keys": list(context.ranking.keys),
                "tieBreaker": context.ranking.tie_breaker,
                "entries": [
                    entry.model_dump(mode="json", by_alias=True)
                    for entry in context.ranking.entries
                ],
            },
            "coverage": _coverage(context),
            "evidenceBudget": _evidence_budget(context),
            "groundingMetadata": _grounding(context),
            "provenance": {
                "candidateGroupCount": context.provenance.candidate_group_count,
                "contributingGroupCount": context.provenance.contributing_group_count,
                "sourceArtifactCount": context.provenance.source_artifact_count,
                "contributions": [
                    contribution.model_dump(mode="json", by_alias=True)
                    for contribution in context.provenance.contributions
                ],
            },
            "evidenceCounts": {
                "functional": len(evidence.functional_artifacts),
                "security": len(evidence.security_artifacts),
                "quality": len(evidence.quality_artifacts),
                "total": evidence.total_count,
            },
            "evidenceSummary": {
                "functional": [_summarise(a) for a in evidence.functional_artifacts],
                "security": [_summarise(a) for a in evidence.security_artifacts],
                "quality": [_summarise(a) for a in evidence.quality_artifacts],
            },
            "contextMetadata": context.context_metadata.model_dump(mode="json", by_alias=True),
            "dependencies": context.dependencies.model_dump(mode="json", by_alias=True),
        }


def _selected_group(entry: ContextRankingEntry) -> dict[str, Any]:
    """One admitted group: what it was ranked, what it gave, and why it was taken."""
    return {
        "consolidatedId": entry.consolidated_id,
        "rank": entry.rank,
        "riskLevel": str(entry.risk_level),
        "candidateArtifactCount": entry.candidate_artifact_count,
        "contributedArtifactCount": entry.contributed_artifact_count,
        "truncated": entry.contributed_artifact_count < entry.candidate_artifact_count,
        "inclusionReason": entry.decision_reason,
    }


def _excluded_group(entry: ContextRankingEntry) -> dict[str, Any]:
    """One turned-away group. Recorded so the ranking cannot hide behind its result."""
    return {
        "consolidatedId": entry.consolidated_id,
        "rank": entry.rank,
        "riskLevel": str(entry.risk_level),
        "candidateArtifactCount": entry.candidate_artifact_count,
        "exclusionReason": entry.decision_reason,
    }


def _coverage(context: EngineeringContext) -> dict[str, Any]:
    """The coverage outcome, per domain, with both satisfaction facts kept apart."""
    coverage = context.coverage
    return {
        "mode": coverage.mode,
        "selectionStrategy": coverage.selection_strategy,
        "ruleSatisfied": coverage.rule_satisfied,
        "allPresentCategoriesRepresented": coverage.all_present_categories_represented,
        "presentCategories": [str(c) for c in coverage.present_categories],
        "representedCategories": [str(c) for c in coverage.represented_categories],
        "domains": [domain.model_dump(mode="json", by_alias=True) for domain in coverage.domains],
    }


def _evidence_budget(context: EngineeringContext) -> dict[str, Any]:
    """The budget's allocation and spend. Derived properties are rendered explicitly."""
    budget = context.evidence_budget
    return {
        "maxArtifactsPerDomain": budget.max_artifacts_per_domain,
        "maxArtifactsTotal": budget.max_artifacts_total,
        "totalAvailable": budget.total_available,
        "totalAllocated": budget.total_allocated,
        "totalUsed": budget.total_used,
        "truncated": budget.truncated,
        "domains": [
            {
                "category": str(domain.category),
                "available": domain.available,
                "allocated": domain.allocated,
                "used": domain.used,
                "truncated": domain.truncated,
            }
            for domain in budget.domains
        ],
    }


def _grounding(context: EngineeringContext) -> dict[str, Any]:
    """What the reasoning session stands on.

    Composes the context's own :class:`ContextGrounding` measurement with the two
    facts an auditor always asks next — was coverage achieved, and did the budget
    bind. Those live in ``coverage`` and ``evidenceBudget``; this block references
    them rather than the model duplicating them.
    """
    grounding = context.grounding
    return {
        "evidenceDomains": [str(domain) for domain in grounding.evidence_domains],
        "evidenceCounts": {
            "functional": grounding.functional_count,
            "security": grounding.security_count,
            "quality": grounding.quality_count,
            "total": grounding.total_count,
        },
        "sourceDistribution": [
            {
                "sourceSystem": str(entry.source_system),
                "artifactCount": entry.artifact_count,
            }
            for entry in grounding.source_distribution
        ],
        "coverageAchieved": context.coverage.all_present_categories_represented,
        "evidenceBudgetUsage": {
            "totalAllocated": context.evidence_budget.total_allocated,
            "totalUsed": context.evidence_budget.total_used,
            "truncated": context.evidence_budget.truncated,
        },
    }


def _summarise(artifact: SourceArtifact) -> dict[str, Any]:
    """Summarise one evidence artifact to the fields that identify and rank it.

    ``(sourceSystem, sourceRecordId)`` is the artifact's traceable identity back
    to its origin system; ``artifactId`` is deliberately omitted because all three
    mappers mint it from ``uuid4`` and it would make this artifact non-reproducible.
    """
    return {
        "sourceSystem": str(artifact.source_system),
        "sourceRecordId": artifact.source_record_id,
        "sourceCategory": str(artifact.source_category),
        "sourceType": str(artifact.source_type),
        "title": artifact.title,
        "severity": artifact.severity,
        "priority": artifact.priority,
        "status": artifact.status,
        "component": artifact.component,
    }
