"""The validation layer enumeration and its canonical execution order.

This module holds the two names that describe *where* in the progressive
validation pipeline a concern sits:

* :class:`ValidationLayer` — the ordered enumeration of validation concerns.
* :data:`LAYER_ORDER` — the authoritative, architecture-mandated execution order.

It is intentionally **dependency-free** so that both
:mod:`~requirement_intelligence.validation.validation_rule` and
:mod:`~requirement_intelligence.validation.validation_rule_metadata` can import
it without creating an import cycle.

Backward compatibility
----------------------
``ValidationLayer`` and ``LAYER_ORDER`` remain importable from
:mod:`~requirement_intelligence.validation.validation_rule` (which re-exports
them) and from the package root.  This module is the new *definition* site; the
historical import paths are unchanged.
"""

from __future__ import annotations

from enum import Enum


class ValidationLayer(Enum):
    """Ordered enumeration of validation concerns.

    Each member corresponds to one layer in the progressive validation pipeline.
    The semantic order (foundational → semantic) is captured in
    :data:`LAYER_ORDER`; the enum itself does not imply ordering.

    Members
    -------
    TRANSPORT
        Was a usable, non-empty response payload actually received?
    SYNTAX
        Is the payload well-formed structured data that can be parsed without
        ambiguity?
    SCHEMA
        Does the parsed structure conform to the expected, versioned schema?
    STRUCTURAL
        Are the required containers, sections, and parent-child relationships
        present and correctly nested?
    CONTENT
        Do individual field values meet type, range, format, and presence
        expectations?
    EVIDENCE
        Are conclusions accompanied by the evidence references the platform
        requires?
    TRACEABILITY
        Does every element carry the links needed to trace it to its source and
        context?
    REASONING
        Is the output internally coherent — free of contradictions, orphaned
        references, and severity mismatches?
    BUSINESS_RULE
        Are declared, platform-level structural policies satisfied?
    """

    TRANSPORT = "transport"
    SYNTAX = "syntax"
    SCHEMA = "schema"
    STRUCTURAL = "structural"
    CONTENT = "content"
    EVIDENCE = "evidence"
    TRACEABILITY = "traceability"
    REASONING = "reasoning"
    BUSINESS_RULE = "business_rule"


#: The authoritative, architecture-mandated execution order for validation
#: layers, from the most foundational concern to the most semantic.
#:
#: The :class:`~requirement_intelligence.validation.validation_registry.ValidationRegistry`
#: uses this list to sort rules deterministically.  The
#: :class:`~requirement_intelligence.validation.validation_pipeline.ValidationPipeline`
#: relies on registry ordering and never re-sorts.
LAYER_ORDER: list[ValidationLayer] = [
    ValidationLayer.TRANSPORT,
    ValidationLayer.SYNTAX,
    ValidationLayer.SCHEMA,
    ValidationLayer.STRUCTURAL,
    ValidationLayer.CONTENT,
    ValidationLayer.EVIDENCE,
    ValidationLayer.TRACEABILITY,
    ValidationLayer.REASONING,
    ValidationLayer.BUSINESS_RULE,
]
