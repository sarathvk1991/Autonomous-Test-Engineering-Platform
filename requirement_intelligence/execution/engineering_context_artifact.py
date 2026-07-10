"""Engineering context artifact — responsible only for ``engineering_context.json``.

The Engineering Context Orchestrator owns *construction* of an
:class:`EngineeringContext`; this builder owns its *serialisation* into the
execution package, and :class:`~...execution_writer.ExecutionWriter` owns
writing the bytes. No component performs another's job.

Why a projection rather than ``context.model_dump()``
-----------------------------------------------------
The artifact answers an auditor's question — *what evidence did this reasoning
session receive, and under which rules?* — so it leads with identity, policy,
and explanation, and summarises evidence to one line per artifact. The full
source records are already persisted verbatim in ``consolidated_artifact.json``;
repeating them here would double the package size to say nothing new.

Determinism
-----------
Every value is read from the context, which is itself a pure function of the
consolidated artifacts. No timestamps, no uuids, no set iteration: two runs over
the same inputs produce byte-identical output.
"""

from __future__ import annotations

from typing import Any

from requirement_intelligence.context_orchestration.models.engineering_context import (
    EngineeringContext,
)
from requirement_intelligence.models.source_artifact import SourceArtifact

#: JSON contract version of ``engineering_context.json``. Independent of the
#: ``EngineeringContext`` model version: the artifact is a projection, and either
#: can change without the other.
ENGINEERING_CONTEXT_ARTIFACT_VERSION = "1.0.0"


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
            },
            "orchestrationReason": context.orchestration_reason,
            "contributingConsolidatedIds": list(context.provenance.contributing_consolidated_ids),
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
