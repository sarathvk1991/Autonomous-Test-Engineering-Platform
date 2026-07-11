"""Concrete GroundingStrategy implementations."""

from __future__ import annotations

from requirement_intelligence.grounding.strategies.deterministic_text_strategy import (
    STRATEGY_NAME,
    STRATEGY_VERSION,
    DeterministicTextMatchingStrategy,
)

__all__ = [
    "STRATEGY_NAME",
    "STRATEGY_VERSION",
    "DeterministicTextMatchingStrategy",
]
