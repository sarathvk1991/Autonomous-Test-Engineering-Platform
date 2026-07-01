"""Response Normalization subsystem.

The permanent platform subsystem that turns a provider-independent ``LLMResponse``
into the canonical, shared ``ParsedResponse`` exactly once, before any consumer
runs — governed by ``docs/architecture/response-normalization-contract.md``.

The subsystem is complete and operational:

* :mod:`requirement_intelligence.normalization.framework` — the generic execution
  infrastructure (responsibility contract, registry, pipeline, layer facade,
  metadata, and exceptions).
* :mod:`requirement_intelligence.normalization.models` — the information models
  (observation, configuration, statistics, framework metadata, result).
* :mod:`requirement_intelligence.normalization.response` — the ``ResponseNormalizer``
  and its five internal stages (``NORMALIZATION-0001…0005``), coordinated through a
  transient Assembly State to assemble the ``ParsedResponse`` within the component
  boundary (ADR-0002).

Per **ADR-0002** the five stages are internal to the ``ResponseNormalizer``, not
framework responsibilities.  Downstream Syntax validation — which *reads* the
``ParsedResponse`` and observations — is a separate subsystem and remains future
work.
"""

from __future__ import annotations
