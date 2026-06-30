"""Abstract base class and layer model for all validation rules.

This module defines the public names that the entire validation framework
depends on:

* :class:`ValidationLayer` — the ordered enumeration of validation concerns
  (re-exported from
  :mod:`~requirement_intelligence.validation.validation_rule_layer`).
* :data:`LAYER_ORDER` — the architecture-mandated layer execution order
  (re-exported from the same module).
* :class:`ValidationRule` — the abstract contract every rule must satisfy.

``ValidationLayer`` and ``LAYER_ORDER`` are *defined* in
:mod:`~requirement_intelligence.validation.validation_rule_layer` and re-exported
here so the historical import paths (and the package root) keep working
unchanged.  The split exists only to let
:mod:`~requirement_intelligence.validation.validation_rule_metadata` share the
layer enum without an import cycle.

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

Rule Documentation Contract
---------------------------
Every concrete :class:`ValidationRule` implementation must document the following
seven sections in its class docstring.  This is a **documentation standard only**
— it is *not* enforced at runtime — but it is a conformance requirement for any
rule accepted into the framework:

1. **Purpose** — the single concern the rule validates.
2. **Validation Layer** — which :class:`ValidationLayer` the rule belongs to.
3. **Inputs** — what part of the response the rule reads.
4. **Outputs** — what findings the rule can produce.
5. **Failure Conditions** — the conditions under which the rule raises a finding.
6. **Worked Example** — a concrete passing and failing case.
7. **Architecture Reference** — the governing section of
   ``docs/architecture/ai-response-validation.md``.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from requirement_intelligence.validation.models.validation_issue import ValidationIssue
from requirement_intelligence.validation.validation_rule_layer import (
    LAYER_ORDER,
    ValidationLayer,
)
from requirement_intelligence.validation.validation_rule_metadata import (
    ValidationRuleMetadata,
)

# Re-exported for backward compatibility: callers historically import
# ``ValidationLayer`` and ``LAYER_ORDER`` from this module.
__all__ = [
    "LAYER_ORDER",
    "ValidationLayer",
    "ValidationRule",
    "ValidationRuleMetadata",
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
    2. Implement :attr:`metadata` (returning an immutable
       :class:`~requirement_intelligence.validation.validation_rule_metadata.ValidationRuleMetadata`)
       and :meth:`validate`.
    3. Document the seven Rule Documentation Contract sections (see module
       docstring) in the subclass docstring.
    4. Register the instance with
       :class:`~requirement_intelligence.validation.validation_registry.ValidationRegistry`.

    No other change is required anywhere in the framework.

    Identity comes from metadata
    ----------------------------
    A rule's descriptive identity lives in a single immutable
    :class:`~requirement_intelligence.validation.validation_rule_metadata.ValidationRuleMetadata`
    value, exposed through :attr:`metadata`.  The legacy identity properties
    (:attr:`rule_id`, :attr:`rule_name`, :attr:`validation_layer`,
    :attr:`enabled`) remain as **convenience wrappers** that simply read from
    :attr:`metadata`, so every existing caller keeps working unchanged.
    """

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    @property
    @abstractmethod
    def metadata(self) -> ValidationRuleMetadata:
        """Immutable descriptive identity of this rule.

        This is the single source of truth for the rule's identity:
        ``rule_id``, ``rule_name``, ``rule_version``, ``validation_layer``,
        ``enabled``, and the reserved extension points.  It must be an immutable
        :class:`~requirement_intelligence.validation.validation_rule_metadata.ValidationRuleMetadata`.

        Returns
        -------
        ValidationRuleMetadata
            The frozen metadata value describing this rule.  Implementations
            typically construct it once and return the same value on every
            access.
        """

    # ------------------------------------------------------------------
    # Identity — backward-compatible convenience wrappers
    # ------------------------------------------------------------------
    #
    # These properties used to be the abstract contract.  They are now thin
    # read-through accessors over :attr:`metadata`, preserved so that the
    # registry, the pipeline, and any external caller continue to work
    # unchanged.  Subclasses no longer override them; they implement
    # :attr:`metadata` instead.

    @property
    def rule_id(self) -> str:
        """Stable, unique identifier for this rule (reads :attr:`metadata`).

        Convention: ``<LAYER_PREFIX>-<NNNN>`` (e.g. ``SYNTAX-0001``).  Must not
        change once published, because it appears in validation result records.
        """
        return self.metadata.rule_id

    @property
    def rule_name(self) -> str:
        """Human-readable name for this rule (reads :attr:`metadata`)."""
        return self.metadata.rule_name

    @property
    def validation_layer(self) -> ValidationLayer:
        """The validation layer this rule belongs to (reads :attr:`metadata`)."""
        return self.metadata.validation_layer

    @property
    def rule_version(self) -> str:
        """The version of this rule's logic (reads :attr:`metadata`).

        Distinct from the Validation Contract Version (validation *semantics*)
        and the Validator Version (validator *implementation*).  See
        :mod:`~requirement_intelligence.validation.validation_rule_metadata`.
        """
        return self.metadata.rule_version

    @property
    def enabled(self) -> bool:
        """Whether this rule participates in pipeline execution (reads :attr:`metadata`).

        Disabled rules are registered but skipped by the pipeline, allowing a
        rule to be deactivated without unregistering it.
        """
        return self.metadata.enabled

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    @abstractmethod
    def validate(self, response: Any) -> list[ValidationIssue]:
        """Evaluate this rule against *response* and return findings.

        This method is the sole place where validation logic lives.  It must
        satisfy all three Rule Independence constraints (see module docstring):
        deterministic, non-mutating, and order-independent.

        Parameters
        ----------
        response:
            The analysed response to evaluate (an
            :class:`~requirement_intelligence.analysis.analysis_models.AnalysisResult`
            carrier supplied by the pipeline).  Rules must treat *response* as
            **read-only** and must not modify it.  It is typed ``Any`` here so the
            rule contract does not depend on the analysis layer's concrete shape.

        Returns
        -------
        list[ValidationIssue]
            An ordered list of canonical
            :class:`~requirement_intelligence.validation.models.validation_issue.ValidationIssue`
            findings.  An empty list means this rule observed no condition worth
            recording.

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
