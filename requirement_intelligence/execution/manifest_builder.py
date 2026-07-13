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

        # Quality Governance references (CAP-080D): additive, and only when governance ran.
        # When it did not, the manifest is byte-identical to before — no key is added, no
        # schema change (manifestSchemaVersion stays 1.0.0). The three governance artifacts
        # already appear in ``generatedArtifacts`` via the same checksum mechanism as every
        # other file. Quality Governance is the terminal release authority (ADR-0017 §D30):
        # ``qualityGovernanceDecision`` is the canonical release verdict, read verbatim from
        # the recorded ``QualityDecision`` and never computed, reinterpreted, or overridden.
        governance = data.quality_governance_result
        if governance is not None:
            decision = governance.assessment.decision
            manifest["qualityGovernanceExecuted"] = True
            manifest["qualityGovernanceReport"] = "quality_governance_report.md"
            manifest["qualityGovernanceSummary"] = "quality_governance_summary.md"
            manifest["qualityGovernanceDecision"] = str(getattr(decision, "value", decision))

        return manifest
