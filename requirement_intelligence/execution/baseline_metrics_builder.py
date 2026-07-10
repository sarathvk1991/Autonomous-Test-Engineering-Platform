"""Baseline metrics builder — responsible only for ``baseline_metrics.md``.

CP1 is deliberately **absent** here (CAP-068). Baseline metrics measure *execution
performance* of the platform pipeline (artifact counts, token/character counts,
duration) — they "do not inspect AI output". CP1 is an *engineering-readiness
assessment* of the validated requirements, not an execution-performance metric, so
its verdict/findings belong to ``cp1_report.md`` (and the summary/review references),
never to this performance table. Mixing them would conflate two different concerns.
"""

from __future__ import annotations

from requirement_intelligence.execution.execution_data import ExecutionData
from requirement_intelligence.execution.execution_metrics import (
    engineering_metrics,
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
        eng = engineering_metrics(data)
        notes = (
            f"Live execution; engineering context composed from "
            f"{eng['contributing_group_count']} of {eng['candidate_group_count']} consolidation "
            f"group(s) under policy `{eng['orchestration_policy']}`."
        )
        domains = ", ".join(eng["evidence_domains_represented"]) or "none"

        return f"""# AI Metrics

## Engineering Metrics

Derived only from the platform pipeline; these do not inspect AI output. The
artifact counts describe the **engineering context** — the evidence the reasoner
received — and are read from the orchestrator's own decisions, never re-derived.

| Metric                            | Value |
| --------------------------------- | ----- |
| Source Artifacts Processed        | {eng["source_artifacts_processed"]} |
| Consolidated Artifacts Produced   | {eng["consolidated_artifacts_produced"]} |
| Functional Artifact Count         | {eng["functional_artifact_count"]} |
| Security Artifact Count           | {eng["security_artifact_count"]} |
| Quality Artifact Count            | {eng["quality_artifact_count"]} |
| Context Artifact Count            | {eng["context_artifact_count"]} |
| Orchestration Policy              | {eng["orchestration_policy"]} |
| Selection Strategy                | {eng["selection_strategy"]} |
| Candidate Groups Ranked           | {eng["candidate_group_count"]} |
| Contributing Groups               | {eng["contributing_group_count"]} |
| Evidence Domains Represented      | {domains} |
| Coverage Complete                 | {eng["coverage_complete"]} |
| Evidence Budget Allocated         | {eng["evidence_budget_allocated"]} |
| Evidence Budget Used              | {eng["evidence_budget_used"]} |
| Evidence Budget Truncated         | {eng["evidence_budget_truncated"]} |
| Primary Consolidated Artifact     | {eng["selected_consolidated_artifact"]} |
| Primary Artifact Rank             | {eng["selected_artifact_rank"]} |
| Largest Consolidation Group       | {eng["largest_consolidation_group"]} |
| Smallest Consolidation Group      | {eng["smallest_consolidation_group"]} |
| Average Artifacts Per Group       | {eng["average_artifacts_per_group"]} |

## AI Metrics

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
