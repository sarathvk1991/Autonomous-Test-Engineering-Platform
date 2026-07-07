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

        manifest: dict[str, Any] = {
            "manifestSchemaVersion": meta.MANIFEST_SCHEMA_VERSION,
            "platformVersion": meta.PLATFORM_VERSION,
            "baselineVersion": meta.BASELINE_VERSION,
            "executionPackageVersion": meta.EXECUTION_PACKAGE_VERSION,
            "connectorRegistryVersion": meta.CONNECTOR_REGISTRY_VERSION,
            "mapperVersion": meta.MAPPER_VERSION,
            "consolidationEngineVersion": meta.CONSOLIDATION_ENGINE_VERSION,
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
            "selectedArtifactId": data.selected.consolidated_id,
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

        return manifest
