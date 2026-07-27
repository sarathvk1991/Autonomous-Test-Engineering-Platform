"""Feature Engineering (Layer 2) governed prompts.

Layer 2's own prompt *content* (`versions/`, `composition.py`), consuming the
shared prompt-governance mechanism at `shared.prompts.*` (ADR-0014, ADR-0043
D4) exactly as `requirement_intelligence.prompts` now does. No prompt is run
here — see `composition.py` for what this package owns and does not own.
"""

from __future__ import annotations

from feature_engineering.prompts.composition import build_prompt_registry

__all__ = [
    "build_prompt_registry",
]
