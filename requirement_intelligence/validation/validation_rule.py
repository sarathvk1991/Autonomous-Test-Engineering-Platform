"""Abstract base class and layer model for all validation rules.

This module defines two public names that the entire validation framework
depends on:

* :class:`ValidationLayer` — the ordered enumeration of validation concerns.
* :class:`ValidationRule` — the abstract contract every rule must satisfy.

No concrete rule implementation belongs here.  This module is the single stable
contract that :class:`~requirement_intelligence.validation.validation_registry.ValidationRegistry`
and :class:`~requirement_intelligence.validation.validation_pipeline.ValidationPipeline`
depend on.  Concrete rules are registered, never imported directly.

Rule Independence
-----------------
The platform architecture mandates **Rule Independence** (AI Response Validation
Architecture §3.11).  Every ValidationRule must satisfy all three constraints:

1. **Deterministic** — given the same response and schema version, a rule always
   produces the same findings.  It depends only on the response being validated,
   never on the outcome of any other rule.

2. **Stateless / non-mutating** — a rule must never modify the response it
   receives, accumulate state between invocations, or write to any shared
   mutable structure.  The response the rule reads is identical to the response
   every sibling rule reads.

3. **Order-independent** — because rules neither share state nor observe each
   other's output, any permutation of a layer's rules yields an identical set of
   findings.  This is the prerequisite for future parallel execution.

These constraints are not enforced at runtime (enforcement would add overhead
and complexity); they are structural requirements of the contract that rule
authors must honour.  A rule that violates any of them is non-conforming and
will break determinism.

Layered validation
------------------
The nine layers are ordered from the most foundational concern (transport
delivery) to the most semantic (platform business rules).  The pipeline executes
layers in this fixed order so that a foundational failure halts progression
before meaningless secondary errors are accumulated — consistent with the
Fail Fast principle (§3.1).

The authoritative layer order is exposed as :data:`LAYER_ORDER`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any


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


# ---------------------------------------------------------------------------
# Canonical layer ordering
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Abstract ValidationRule
# ---------------------------------------------------------------------------


class ValidationRule(ABC):
    """Abstract contract every validation rule must satisfy.

    A ValidationRule encapsulates **exactly one validation concern** and
    evaluates it against a single AI response.  It is the fundamental building
    block of the Response Validation Layer.

    Design philosophy
    -----------------
    The ValidationRule mirrors the design philosophy of the platform's other
    extensible framework contracts:

    * :class:`~requirement_intelligence.connectors.base.SourceConnector` —
      one source system, one connection concern.
    * :class:`~requirement_intelligence.llm.providers.base_provider.LLMProvider` —
      one provider, one generation concern.
    * :class:`~requirement_intelligence.mappers.base_mapper.BaseMapper` —
      one source shape, one transformation concern.

    Like those contracts, ValidationRule is the stable abstraction that the
    registry and pipeline depend on.  New rules are added by implementing this
    class and registering the instance; no framework code changes.

    Rule Independence (§3.11)
    -------------------------
    Every conforming implementation must satisfy all three Rule Independence
    constraints — see the module docstring for the full rationale.

    In summary:
    * A rule reads the response; it **never mutates it**.
    * A rule depends only on the response and the schema; **never on sibling
      rule output or execution order**.
    * A rule holds **no mutable instance state** that persists between calls.

    Adding a new rule
    -----------------
    1. Subclass :class:`ValidationRule`.
    2. Implement :attr:`rule_id`, :attr:`rule_name`, :attr:`validation_layer`,
       and :meth:`validate`.
    3. Optionally override :attr:`enabled` (default ``True``).
    4. Register the instance with
       :class:`~requirement_intelligence.validation.validation_registry.ValidationRegistry`.

    No other change is required anywhere in the framework.
    """

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    @property
    @abstractmethod
    def rule_id(self) -> str:
        """Stable, unique identifier for this rule.

        The identifier is used by the registry, the pipeline, and any future
        observability tooling to reference this specific rule unambiguously.

        Naming convention
        -----------------
        ``<LAYER_PREFIX>-<NNNN>`` — for example ``SYNTAX-0001``,
        ``EVIDENCE-0042``.  The prefix is the layer name in upper case; the
        suffix is a zero-padded sequential number within that layer.

        Returns
        -------
        str
            A non-empty, stable identifier.  Must not change between releases
            once published, because it appears in validation result records.
        """

    @property
    @abstractmethod
    def rule_name(self) -> str:
        """Human-readable name for this rule.

        Used in log output, pipeline summaries, and future observability
        dashboards.

        Returns
        -------
        str
            A short, descriptive label.  Example: ``"Syntax: Well-formed JSON"``.
        """

    @property
    @abstractmethod
    def validation_layer(self) -> ValidationLayer:
        """The validation layer this rule belongs to.

        The registry uses this to group rules by layer; the pipeline uses the
        layer ordering to ensure deterministic, progressive execution.

        Returns
        -------
        ValidationLayer
            One of the nine pipeline layers.
        """

    # ------------------------------------------------------------------
    # Lifecycle control
    # ------------------------------------------------------------------

    @property
    def enabled(self) -> bool:
        """Whether this rule participates in pipeline execution.

        Disabled rules are registered but skipped by the pipeline.  This
        allows rules to be temporarily deactivated without unregistering them
        — useful during phased rollouts or when a rule is pending a schema
        update.

        Subclasses may override this property to tie enablement to
        configuration flags, feature toggles, or contract versions.

        Returns
        -------
        bool
            ``True`` (default) — the rule participates in every pipeline run.
            ``False`` — the registry excludes this rule from enabled queries.
        """
        return True

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    @abstractmethod
    def validate(self, response: Any) -> list[Any]:
        """Evaluate this rule against *response* and return findings.

        This method is the sole place where validation logic lives.  It must
        satisfy all three Rule Independence constraints (see module docstring):
        deterministic, non-mutating, and order-independent.

        Parameters
        ----------
        response:
            The AI response to evaluate.  The exact type is determined by the
            canonical models introduced in the next task.  Rules must treat
            *response* as **read-only** and must not modify it.

        Returns
        -------
        list[Any]
            An ordered list of findings.  An empty list means this rule
            observed no condition worth recording.

            The concrete element type will be ``ValidationIssue`` once the
            canonical models are defined (next task).  Until then, ``Any``
            acts as the open placeholder to preserve a stable signature.

        Notes
        -----
        * **Never mutate** *response* — validation observes, it does not edit
          (Preserve Original Response, §3.3).
        * **Never read or write shared state** — findings from this call must
          not influence or be influenced by sibling rule calls.
        * **Raise**
          :class:`~requirement_intelligence.validation.validation_exceptions.ValidationRuleError`
          only for unexpected internal failures; do not raise for normal
          validation findings (those are returned, not raised).
        """
