"""Review builder — responsible only for ``review.md``.

Writes a factual scaffold with the required headings. Qualitative observations
are authored by a human reviewer after reading the captured artifacts.
"""

from __future__ import annotations

from requirement_intelligence.execution.execution_data import ExecutionData
from requirement_intelligence.execution.execution_metrics import (
    execution_package_identifier,
    observe_response_counts,
)
from requirement_intelligence.platform import platform_metadata as meta


class ReviewBuilder:
    """Render the qualitative review scaffold (live runs)."""

    def build(self, data: ExecutionData) -> str:
        """Return the markdown content of ``review.md``."""
        selected = data.selected
        result = data.result
        counts = observe_response_counts(data.generated_text)
        json_valid = "valid" if counts["json_valid"] else "INVALID"
        package_id = execution_package_identifier(result)

        return f"""# AI Review — Version {meta.BASELINE_VERSION}

> Observation only. Nothing was modified, repaired, or tuned.
> Selected consolidated artifact: `{selected.consolidated_id}`
> (functional={len(selected.functional_artifacts)}, \
security={len(selected.security_artifacts)}, quality={len(selected.quality_artifacts)}).
> Strict JSON validity of response: {json_valid}.

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

## Executive Summary

_To be completed by the reviewer after reading the captured artifacts._

## What Worked

_TBD_

## What Did Not Work

_TBD_

## Prompt Weaknesses

_TBD_

## Hallucinations Observed

_TBD_

## Missing Requirements

_TBD_

## Missing Security Analysis

_TBD_

## Missing Quality Analysis

_TBD_

## Unexpected AI Behaviour

_TBD_

## Recommendations for Prompt Version 1.1.0

_TBD_
"""
