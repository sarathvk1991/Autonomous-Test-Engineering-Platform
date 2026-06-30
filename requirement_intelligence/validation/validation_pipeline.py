"""Validation pipeline — orchestrates ValidationRule execution.

The ValidationPipeline is the single point of execution for the Response
Validation Layer.  It receives a
:class:`~requirement_intelligence.validation.validation_registry.ValidationRegistry`,
asks it for the ordered set of enabled rules, invokes each rule against the AI
response, and collects the findings.

Design notes
------------
* **Orchestration only.**  The pipeline contains no validation logic, no AI
  knowledge, and no business rules.  It delegates all validation decisions to
  the rules it executes.  This mirrors the separation maintained by the LLM
  provider framework (the factory wires providers; it does not generate text)
  and the connector framework (the registry wires connectors; it does not fetch
  records).

* **Deterministic ordering.**  The pipeline trusts the registry for ordering.
  Rules arrive from
  :meth:`~requirement_intelligence.validation.validation_registry.ValidationRegistry.get_enabled_rules`
  already sorted by architecture-mandated layer order.  The pipeline does not
  re-sort.

* **Future parallel execution.**  The pipeline is designed to support parallel
  evaluation of rules *within* the same layer without any contract change.
  Rule Independence (§3.11) guarantees that parallelisation cannot change the
  finding set.  The current implementation is sequential; the signature and
  return contract are stable for a future concurrent implementation.

* **Fail Fast (§3.1).**  Foundational layers (Transport, Syntax, Schema,
  Structural) are *progression-stopping* when they produce blocking findings.
  The pipeline provides the mechanism to check for blocking findings after
  each layer and halt accordingly.  The logic that classifies a finding as
  blocking lives in the canonical models (next task); the pipeline wires the
  halt behaviour once those models are available.

* **No ValidationResult yet.**  This task establishes the framework skeleton.
  The canonical output type (ValidationResult) and finding type
  (ValidationIssue) are defined in the next task.  The pipeline's ``run()``
  method therefore returns ``list[Any]`` as a stable placeholder signature.

Relationship to other frameworks
---------------------------------
The ValidationPipeline is the structural equivalent of:

* ``RequirementAnalysisService.analyse`` — a coordinating method that calls
  subordinate concerns in order without knowing their internals.
* The consolidation engine — orchestrates a fixed set of steps without owning
  any step's logic.
"""

from __future__ import annotations

from typing import Any

from requirement_intelligence.validation.validation_exceptions import ValidationPipelineError
from requirement_intelligence.validation.validation_registry import ValidationRegistry
from requirement_intelligence.validation.validation_rule import ValidationRule


class ValidationPipeline:
    """Orchestrates the execution of registered
    :class:`~requirement_intelligence.validation.validation_rule.ValidationRule`
    instances against an AI response.

    The pipeline is the only component that calls ``rule.validate()``.  All
    other components interact with the pipeline through :meth:`run`.

    Usage
    -----
    .. code-block:: python

        registry = ValidationRegistry()
        registry.register(MyTransportRule())
        registry.register(MySyntaxRule())

        pipeline = ValidationPipeline(registry)
        findings = pipeline.run(response)

    Adding a new rule
    -----------------
    Register it with the registry before constructing the pipeline (or use
    :meth:`get_ordered_rules` to inspect the active set).  No pipeline code
    changes.
    """

    def __init__(self, registry: ValidationRegistry) -> None:
        """Construct the pipeline from a populated registry.

        Parameters
        ----------
        registry:
            The :class:`ValidationRegistry` that supplies the ordered rule set.
            The registry must be fully populated before the pipeline is
            constructed; rules registered after construction are not visible to
            this pipeline instance.

        Raises
        ------
        ValidationPipelineError
            If *registry* is not a :class:`ValidationRegistry` instance.
        """
        if not isinstance(registry, ValidationRegistry):
            raise ValidationPipelineError(
                f"ValidationPipeline requires a ValidationRegistry instance; "
                f"got {type(registry).__name__!r}."
            )
        self._registry = registry

    # ------------------------------------------------------------------
    # Inspection
    # ------------------------------------------------------------------

    def get_ordered_rules(self) -> list[ValidationRule]:
        """Return the ordered set of enabled rules the pipeline will execute.

        Rules are returned in the architecture-mandated layer order (Transport →
        … → Business Rule) with insertion order preserved within each layer.

        Returns
        -------
        list[ValidationRule]
            Enabled rules in deterministic pipeline order.
        """
        return self._registry.get_enabled_rules()

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def run(self, response: Any) -> list[Any]:
        """Execute all enabled rules against *response* and collect findings.

        Rules are executed in the order returned by :meth:`get_ordered_rules`.
        Each rule's findings are appended to the result list in the order they
        are produced.  The pipeline does not interpret findings; it collects
        and returns them.

        Future evolution
        ----------------
        * **Fail Fast** — once canonical models are available (next task), the
          pipeline will inspect each finding for its blocking indicator and halt
          progression when a foundational layer raises a blocking issue.
        * **Parallel execution** — rules within the same layer may be evaluated
          concurrently.  Rule Independence guarantees this is safe.
        * **ValidationResult** — the return type will change from ``list[Any]``
          to a ``ValidationResult`` aggregate once the canonical models are
          defined.

        Parameters
        ----------
        response:
            The AI response to validate.  Passed unchanged to each rule.  The
            pipeline never inspects or modifies *response*.

        Returns
        -------
        list[Any]
            A flat, ordered list of findings collected from every rule.  An
            empty list means no rule raised any finding.  The concrete element
            type will be ``ValidationIssue`` once canonical models are defined.

        Raises
        ------
        ValidationPipelineError
            If an unexpected error occurs during rule execution that cannot be
            attributed to a specific rule's contract violation.
        """
        findings: list[Any] = []
        for rule in self.get_ordered_rules():
            rule_findings = rule.validate(response)
            findings.extend(rule_findings)
        return findings
