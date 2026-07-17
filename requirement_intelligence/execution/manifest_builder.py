"""Manifest builder — responsible only for ``manifest.json`` content."""

from __future__ import annotations

from typing import Any

from requirement_intelligence.execution.execution_data import ExecutionData
from requirement_intelligence.execution.execution_metrics import sha256_text
from requirement_intelligence.platform import platform_metadata as meta


class ManifestBuilder:
    """Build the canonical manifest dictionary for an execution package."""

    def build(
        self,
        data: ExecutionData,
        *,
        started_timestamp: str,
        completed_timestamp: str,
        generated_artifacts: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Return the manifest dict for *data* and the written artifacts."""
        result = data.result
        full_prompt = data.full_prompt
        generated_text = data.generated_text
        context = data.engineering_context

        manifest: dict[str, Any] = {
            "manifestSchemaVersion": meta.MANIFEST_SCHEMA_VERSION,
            "platformVersion": meta.PLATFORM_VERSION,
            "baselineVersion": meta.BASELINE_VERSION,
            "executionPackageVersion": meta.EXECUTION_PACKAGE_VERSION,
            "connectorRegistryVersion": meta.CONNECTOR_REGISTRY_VERSION,
            "mapperVersion": meta.MAPPER_VERSION,
            "consolidationEngineVersion": meta.CONSOLIDATION_ENGINE_VERSION,
            "contextOrchestrationVersion": meta.CONTEXT_ORCHESTRATION_VERSION,
            "promptFrameworkVersion": meta.PROMPT_FRAMEWORK_VERSION,
            "llmFrameworkVersion": meta.LLM_FRAMEWORK_VERSION,
            "analysisServiceVersion": meta.ANALYSIS_SERVICE_VERSION,
            "executionWriterVersion": meta.EXECUTION_WRITER_VERSION,
            "platformCapabilitiesVersion": meta.PLATFORM_CAPABILITIES_VERSION,
            "subcommand": data.subcommand,
            "executionMode": "dry-run" if data.dry_run else "live",
            "dryRun": bool(data.dry_run),
            "executionName": data.execution_name,
            "executionTimestamp": started_timestamp,
            "executionCompletedTimestamp": completed_timestamp,
            "analysisId": result.analysis_id if result else None,
            "executionId": result.execution_id if result else None,
            "provider": data.provider_name,
            "model": (result.model if result else data.requested_model),
            "promptVersion": data.prompt_request.prompt_version,
            "reasoningContractVersion": data.reasoning_contract_version,
            # The primary (highest-ranked) contributing group, persisted verbatim as
            # ``consolidated_artifact.json``. Under a multi-source policy it is one
            # of several contributors, which ``contributingConsolidatedIds`` names.
            "selectedArtifactId": data.selected.consolidated_id,
            # Engineering Context references (CAP-076C, extended CAP-076D). The
            # manifest names the artifact, the governed rules that produced it, and
            # the shape of the orchestration it performed, so a package can be
            # attributed to its policy and its coverage read without opening another
            # file. SHA-256 and byte count are recorded in ``generatedArtifacts``
            # alongside every other artifact — one mechanism, no special case.
            "engineeringContextArtifact": "engineering_context.json",
            "engineeringContextId": str(context.context_id),
            "orchestrationPolicyId": str(context.orchestration.policy_id),
            "orchestrationPolicyVersion": str(context.orchestration.policy_version),
            "selectionStrategy": context.coverage.selection_strategy,
            "candidateGroupCount": context.provenance.candidate_group_count,
            "contributingGroupCount": context.provenance.contributing_group_count,
            "contributingConsolidatedIds": list(context.provenance.contributing_consolidated_ids),
            "evidenceDomainsRepresented": [
                str(category) for category in context.coverage.represented_categories
            ],
            "coverageComplete": context.coverage.all_present_categories_represented,
            "contextArtifactCount": context.evidence.total_count,
            "promptSha256": sha256_text(full_prompt),
            "promptCharacterCount": len(full_prompt),
            "responseSha256": sha256_text(generated_text) if result else None,
            "responseCharacterCount": len(generated_text) if result else None,
            "executionDurationMs": result.duration_ms if result else None,
            "executionSucceeded": True,
            "commandLineArguments": data.command_line_arguments,
            "generatedArtifacts": generated_artifacts,
        }

        # CP1 references (CAP-068): additive, and only when CP1 was executed. When CP1
        # did not run, the manifest is byte-identical to before — no key is added.
        # Presentation only: the verdict is read from the CP1Result, never computed.
        if data.cp1_result is not None:
            manifest["cp1Executed"] = True
            manifest["cp1Report"] = "cp1_report.md"
            manifest["cp1Verdict"] = str(
                getattr(data.cp1_result.overall_verdict, "value", data.cp1_result.overall_verdict)
            )

        # Quality Governance references (CAP-080D, purity boundary hardened CAP-080D.1):
        # additive, and only when governance ran. When it did not, the manifest is
        # byte-identical to before — no key is added, no schema change (manifestSchemaVersion
        # stays 1.0.0). The three governance artifacts already appear in ``generatedArtifacts``
        # via the same checksum mechanism as every other file. These three keys are package
        # metadata only — a flag and two artifact filenames — never the verdict itself. The
        # canonical ``QualityDecision`` lives exclusively in ``quality_governance_result.json``
        # (ADR-0017 §D31): the manifest references that artifact, it never duplicates its
        # content.
        governance = data.quality_governance_result
        if governance is not None:
            manifest["qualityGovernanceExecuted"] = True
            manifest["qualityGovernanceReport"] = "quality_governance_report.md"
            manifest["qualityGovernanceSummary"] = "quality_governance_summary.md"

        # Requirement Enhancement references (CAP-081C): additive, and only when
        # enhancement ran. When it did not, the manifest is byte-identical to before —
        # no key is added, no schema change (manifestSchemaVersion stays 1.0.0). The
        # three enhancement artifacts already appear in ``generatedArtifacts`` via the
        # same checksum mechanism as every other file. These three keys are package
        # metadata only — a flag and two artifact filenames — never the enhancement
        # runtime state itself. The canonical enhanced requirements, relationship
        # graph, observations, findings, metrics, and summary live exclusively in
        # ``requirement_enhancement_result.json`` (ADR-0018 §D8/§D9): the manifest
        # references that artifact, it never duplicates its content.
        enhancement = data.requirement_enhancement_result
        if enhancement is not None:
            manifest["requirementEnhancementExecuted"] = True
            manifest["requirementEnhancementReport"] = "requirement_enhancement_report.md"
            manifest["requirementEnhancementMetrics"] = "requirement_enhancement_metrics.md"

        # Recommendation references (CAP-082C): additive, and only when recommendation
        # ran. When it did not, the manifest is byte-identical to before — no key is
        # added, no schema change (manifestSchemaVersion stays 1.0.0). The three
        # recommendation artifacts already appear in ``generatedArtifacts`` via the
        # same checksum mechanism as every other file. These three keys are package
        # metadata only — a flag and two artifact filenames — never the recommendation
        # runtime state itself. The canonical recommendations, groups, priorities,
        # confidence, metrics, and summary live exclusively in
        # ``recommendation_result.json`` (ADR-0019 §D9/§D10): the manifest references
        # that artifact, it never duplicates its content.
        recommendation = data.recommendation_result
        if recommendation is not None:
            manifest["recommendationExecuted"] = True
            manifest["recommendationReport"] = "recommendation_report.md"
            manifest["recommendationMetrics"] = "recommendation_metrics.md"

        # Continuous Improvement references (CAP-083C): additive, and only when
        # continuous improvement ran. When it did not, the manifest is byte-identical
        # to before — no key is added, no schema change (manifestSchemaVersion stays
        # 1.0.0). The three continuous improvement artifacts already appear in
        # ``generatedArtifacts`` via the same checksum mechanism as every other file.
        # These three keys are package metadata only — a flag and two artifact
        # filenames — never the continuous improvement runtime state itself. The
        # canonical findings, trends, opportunities, metrics, and summary live
        # exclusively in ``continuous_improvement_result.json`` (ADR-0022 §D10/§D11):
        # the manifest references that artifact, it never duplicates its content.
        continuous_improvement = data.continuous_improvement_result
        if continuous_improvement is not None:
            manifest["continuousImprovementExecuted"] = True
            manifest["continuousImprovementReport"] = "continuous_improvement_report.md"
            manifest["continuousImprovementMetrics"] = "continuous_improvement_metrics.md"

        # Knowledge Graph references (CAP-084C): additive, and only when Knowledge
        # Graph ran. When it did not, the manifest is byte-identical to before — no
        # key is added, no schema change (manifestSchemaVersion stays 1.0.0). The
        # three Knowledge Graph artifacts already appear in ``generatedArtifacts``
        # via the same checksum mechanism as every other file. These three keys are
        # package metadata only — a flag and two artifact filenames — never the
        # Knowledge Graph runtime state itself. The canonical nodes, edges,
        # subgraphs, observations, findings, metrics, and summary live exclusively
        # in ``knowledge_graph_result.json`` (ADR-0023 §D11/§D12): the manifest
        # references that artifact, it never duplicates its content.
        knowledge_graph = data.knowledge_graph_result
        if knowledge_graph is not None:
            manifest["knowledgeGraphExecuted"] = True
            manifest["knowledgeGraphReport"] = "knowledge_graph_report.md"
            manifest["knowledgeGraphMetrics"] = "knowledge_graph_metrics.md"

        # Organizational Memory references (CAP-085C): additive, and only when
        # Organizational Memory ran. When it did not, the manifest is
        # byte-identical to before — no key is added, no schema change
        # (manifestSchemaVersion stays 1.0.0). The three Organizational Memory
        # artifacts already appear in ``generatedArtifacts`` via the same checksum
        # mechanism as every other file. These three keys are package metadata
        # only — a flag and two artifact filenames — never the Organizational
        # Memory runtime state itself. The canonical experiences, lessons, best
        # practices, promotions, lifecycles, metrics, and summary live exclusively
        # in ``organizational_memory_result.json`` (ADR-0027 §D18/§D19): the
        # manifest references that artifact, it never duplicates its content.
        organizational_memory = data.organizational_memory_result
        if organizational_memory is not None:
            manifest["organizationalMemoryExecuted"] = True
            manifest["organizationalMemoryReport"] = "organizational_memory_report.md"
            manifest["organizationalMemoryMetrics"] = "organizational_memory_metrics.md"

        # Learning references (CAP-086C): additive, and only when Learning ran.
        # When it did not, the manifest is byte-identical to before — no key is
        # added, no schema change (manifestSchemaVersion stays 1.0.0). The three
        # Learning artifacts already appear in ``generatedArtifacts`` via the
        # same checksum mechanism as every other file. These three keys are
        # package metadata only — a flag and two artifact filenames — never the
        # Learning runtime state itself. The canonical candidates, learnings,
        # validations, confidences, lifecycles, metrics, and summary live
        # exclusively in ``learning_result.json`` (ADR-0029 §D28/§D29): the
        # manifest references that artifact, it never duplicates its content.
        learning = data.learning_result
        if learning is not None:
            manifest["learningExecuted"] = True
            manifest["learningReport"] = "learning_report.md"
            manifest["learningMetrics"] = "learning_metrics.md"

        return manifest
