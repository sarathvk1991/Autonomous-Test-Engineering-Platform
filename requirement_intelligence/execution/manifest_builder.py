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

        return {
            "platformVersion": meta.PLATFORM_VERSION,
            "baselineVersion": meta.BASELINE_VERSION,
            "executionPackageVersion": meta.EXECUTION_PACKAGE_VERSION,
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
