"""Observation-only metric helpers for the execution package.

Pure functions used by the manifest and the markdown builders to derive simple,
deterministic facts about a prompt and a response. These perform **no** repair,
no validation, and no business logic — they only observe.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any


def sha256_text(text: str) -> str:
    """Return the hex SHA-256 of *text* (UTF-8)."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def observe_response_counts(generated_text: str) -> dict[str, Any]:
    """Strictly inspect a model response without repairing it.

    Performs a strict ``json.loads`` (no fence-stripping). When the response is
    valid JSON, array lengths are counted; otherwise each count is ``"N/A"`` and
    ``json_valid`` is ``False``.
    """
    result: dict[str, Any] = {
        "json_valid": False,
        "functional_requirements": "N/A",
        "security_requirements": "N/A",
        "quality_requirements": "N/A",
        "risks": "N/A",
        "recommendations": "N/A",
    }
    try:
        parsed = json.loads(generated_text)
    except (json.JSONDecodeError, TypeError):
        return result
    if not isinstance(parsed, dict):
        return result
    result["json_valid"] = True
    for key in (
        "functional_requirements",
        "security_requirements",
        "quality_requirements",
        "risks",
        "recommendations",
    ):
        value = parsed.get(key)
        result[key] = len(value) if isinstance(value, list) else "N/A"
    return result


def usage_tokens(result: Any) -> tuple[Any, Any]:
    """Return ``(prompt_tokens, completion_tokens)`` or ``("N/A", "N/A")``."""
    usage = getattr(result.llm_response, "usage", None)
    prompt_tokens = usage.prompt_tokens if usage and usage.prompt_tokens is not None else "N/A"
    completion_tokens = (
        usage.completion_tokens if usage and usage.completion_tokens is not None else "N/A"
    )
    return prompt_tokens, completion_tokens


def _group_total(artifact: Any) -> int:
    """Total grouped source artifacts in one consolidated artifact."""
    return (
        len(artifact.functional_artifacts)
        + len(artifact.security_artifacts)
        + len(artifact.quality_artifacts)
    )


def engineering_metrics(data: Any) -> dict[str, Any]:
    """Compute engineering-pipeline metrics from *data*.

    These are derived solely from the platform pipeline (source artifacts and
    consolidated groups). They never inspect AI output. Values that cannot be
    computed (e.g. the consolidated list was not supplied) are ``"N/A"``.
    """
    selected = data.selected
    consolidated = list(data.consolidated_artifacts or [])

    metrics: dict[str, Any] = {
        "source_artifacts_processed": (
            data.source_artifact_count if data.source_artifact_count is not None else "N/A"
        ),
        "consolidated_artifacts_produced": len(consolidated) if consolidated else "N/A",
        "functional_artifact_count": len(selected.functional_artifacts),
        "security_artifact_count": len(selected.security_artifacts),
        "quality_artifact_count": len(selected.quality_artifacts),
        "selected_consolidated_artifact": selected.consolidated_id,
        "selected_artifact_rank": "N/A",
        "largest_consolidation_group": "N/A",
        "smallest_consolidation_group": "N/A",
        "average_artifacts_per_group": "N/A",
    }

    if not consolidated:
        return metrics

    totals = [_group_total(c) for c in consolidated]
    metrics["largest_consolidation_group"] = max(totals)
    metrics["smallest_consolidation_group"] = min(totals)
    metrics["average_artifacts_per_group"] = round(sum(totals) / len(totals), 2)

    # Rank by group size: largest first, tie-break by id. This *mirrors* the ranking
    # of the active LegacySelectionPolicy rather than reading it, so it reports the
    # selected group's size rank, not its rank under whichever policy actually chose
    # it. The two coincide today and will diverge the moment a risk-ranked policy is
    # activated (CAP-076D), at which point this metric must read the rank the
    # orchestrator already records in ContextContribution.inclusion_reason.
    ordered = sorted(consolidated, key=lambda c: (-_group_total(c), c.consolidated_id))
    for index, candidate in enumerate(ordered, start=1):
        if candidate.consolidated_id == selected.consolidated_id:
            metrics["selected_artifact_rank"] = index
            break
    return metrics


def execution_package_identifier(result: Any) -> str:
    """Return a human-readable package id: ``EP-YYYYMMDD-HHMMSS-XXXXXXXX``.

    ``XXXXXXXX`` is the first eight characters of the execution id. This is for
    human traceability only and does not replace ``executionId``.
    """
    stamp = result.started_at.strftime("%Y%m%d-%H%M%S")
    short_id = str(result.execution_id)[:8]
    return f"EP-{stamp}-{short_id}"
