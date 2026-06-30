"""Response Normalization subsystem.

The permanent platform subsystem that turns a provider-independent ``LLMResponse``
into the canonical, shared ``ParsedResponse`` exactly once, before any consumer
runs — governed by ``docs/architecture/response-normalization-contract.md``.

Phase 1 delivers the **framework infrastructure only**:

* :mod:`requirement_intelligence.normalization.framework` — the responsibility
  contract, registry, pipeline, layer facade, metadata, and exceptions.
* :mod:`requirement_intelligence.normalization.models` — the information models
  (observation, configuration, statistics, framework metadata, result).

It implements **no** normalization responsibility, **no** parsing, **no**
``ParsedResponse``, **no** ``ResponseNormalizer``, and **no** Syntax rule.  Those
are future tasks; this subsystem exists so they have a stable, governed
foundation to build on.
"""

from __future__ import annotations
