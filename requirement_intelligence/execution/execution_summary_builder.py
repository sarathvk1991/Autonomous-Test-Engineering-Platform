"""Execution summary builder — responsible only for ``execution_summary.md``."""

from __future__ import annotations

from requirement_intelligence.execution.execution_data import ExecutionData
from requirement_intelligence.execution.execution_metrics import (
    execution_package_identifier,
    observe_response_counts,
)
from requirement_intelligence.platform import platform_metadata as meta


class ExecutionSummaryBuilder:
    """Render the human-readable execution summary (live runs)."""

    def build(self, data: ExecutionData) -> str:
        """Return the markdown content of ``execution_summary.md``."""
        result = data.result
        full_prompt = data.full_prompt
        generated_text = data.generated_text
        counts = observe_response_counts(generated_text)
        json_valid = "valid" if counts["json_valid"] else "INVALID"
        package_id = execution_package_identifier(result)

        return f"""# AI Execution — Summary

## Execution Package Identity

| Field                      | Value |
| -------------------------- | ----- |
| Execution Package Id       | {package_id} |
| Platform Version           | {meta.PLATFORM_VERSION} |
| Execution Package Version  | {meta.EXECUTION_PACKAGE_VERSION} |
| Manifest Schema Version    | {meta.MANIFEST_SCHEMA_VERSION} |
| Prompt Version             | {result.prompt_version} |
| Reasoning Contract Version | {result.reasoning_contract_version} |
| Provider                   | {result.provider} |
| Model                      | {result.model} |

## Execution Detail

| Field                      | Value |
| -------------------------- | ----- |
| Execution Timestamp        | {result.started_at.isoformat()} |
| Analysis ID                | {result.analysis_id} |
| Execution ID               | {result.execution_id} |
| Provider                   | {result.provider} |
| Model                      | {result.model} |
| Prompt Version             | {result.prompt_version} |
| Reasoning Contract Version | {result.reasoning_contract_version} |
| Execution Duration         | {result.duration_ms} ms |
| Prompt Length              | {len(full_prompt)} characters |
| Response Length            | {len(generated_text)} characters |
| Execution Succeeded        | True |

## Warnings

- Strict JSON validity of the model response: {json_valid}.
- Observation-only run; no validation, parsing, or repair was performed.
"""
