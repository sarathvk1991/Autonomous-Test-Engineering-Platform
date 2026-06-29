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
