"""Baseline metrics builder — responsible only for ``baseline_metrics.md``."""

from __future__ import annotations

from requirement_intelligence.execution.execution_data import ExecutionData
from requirement_intelligence.execution.execution_metrics import (
    observe_response_counts,
    usage_tokens,
)
from requirement_intelligence.platform import platform_metadata as meta


class BaselineMetricsBuilder:
    """Render the metrics table (live runs)."""

    def build(self, data: ExecutionData) -> str:
        """Return the markdown content of ``baseline_metrics.md``."""
        result = data.result
        full_prompt = data.full_prompt
        generated_text = data.generated_text
        counts = observe_response_counts(generated_text)
        prompt_tokens, response_tokens = usage_tokens(result)
        notes = (
            "Live execution; selected consolidated artifact "
            f"`{data.selected.consolidated_id}`."
        )

        return f"""# AI Metrics

| Metric                            | Value |
| --------------------------------- | ----- |
| Baseline Version                  | {meta.BASELINE_VERSION} |
| Execution Timestamp               | {result.started_at.isoformat()} |
| Analysis ID                       | {result.analysis_id} |
| Execution ID                      | {result.execution_id} |
| Provider                          | {result.provider} |
| Model                             | {result.model} |
| Prompt Version                    | {result.prompt_version} |
| Reasoning Contract Version        | {result.reasoning_contract_version} |
| Prompt Characters                 | {len(full_prompt)} |
| Prompt Words                      | {len(full_prompt.split())} |
| Prompt Tokens (if available)      | {prompt_tokens} |
| Response Characters               | {len(generated_text)} |
| Response Words                    | {len(generated_text.split())} |
| Response Tokens (if available)    | {response_tokens} |
| Execution Time (ms)               | {result.duration_ms} |
| Functional Requirements Generated | {counts["functional_requirements"]} |
| Security Requirements Generated   | {counts["security_requirements"]} |
| Quality Requirements Generated    | {counts["quality_requirements"]} |
| Risks Identified                  | {counts["risks"]} |
| Recommendations Generated         | {counts["recommendations"]} |
| Overall JSON Validity             | {"Valid" if counts["json_valid"] else "Invalid"} |
| Hallucinations Observed           | See review.md (qualitative) |
| Notes                             | {notes} |
"""
