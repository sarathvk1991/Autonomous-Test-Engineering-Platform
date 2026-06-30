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

from enum import Enum
from typing import Any

from requirement_intelligence.validation.validation_exceptions import ValidationPipelineError
from requirement_intelligence.validation.validation_registry import ValidationRegistry
from requirement_intelligence.validation.validation_rule import ValidationRule


class PipelineState(Enum):
    """Observable lifecycle state of a :class:`ValidationPipeline`.

    The state is **informational only**.  It is exposed for observability and
    debugging; it **never** influences validation behaviour.  No branching
    decision inside the pipeline is taken on the basis of this state, and the
    findings a run produces are identical regardless of how the state is read.

    Members
    -------
    CREATED
        The pipeline object is being constructed but is not yet ready.
    READY
        Construction succeeded; the pipeline is ready to run.  The registry has
        been sealed and the ordered rule set is available.
    RUNNING
        A :meth:`ValidationPipeline.run` call is in progress.
    COMPLETED
        The most recent :meth:`ValidationPipeline.run` call finished
        successfully.
    FAILED
        The most recent :meth:`ValidationPipeline.run` call raised before
        completing.
    DISPOSED
        Reserved for a future explicit teardown step.  Not entered by any
        current transition.

    Transitions
    -----------
    ::

        (construct) ─► CREATED ─► READY ─► RUNNING ─► COMPLETED ─► RUNNING ...
                                              │
                                              └─► FAILED ─► RUNNING ...

        DISPOSED is reserved and is not part of any current transition.
    """

    CREATED = "created"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    DISPOSED = "disposed"  # reserved — no current transition enters this state


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
            constructed.  Construction **seals** the registry: rules cannot be
            registered afterwards, which guarantees the pipeline's rule set is
            fixed for its lifetime.

        Raises
        ------
        ValidationPipelineError
            If *registry* is not a :class:`ValidationRegistry` instance.
        """
        self._state: PipelineState = PipelineState.CREATED
        if not isinstance(registry, ValidationRegistry):
            # Stay in CREATED; construction never reached READY.
            raise ValidationPipelineError(
                f"ValidationPipeline requires a ValidationRegistry instance; "
                f"got {type(registry).__name__!r}."
            )
        self._registry = registry
        # Sealing the registry freezes the rule set for this pipeline's lifetime.
        self._registry.seal()
        self._state = PipelineState.READY

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    @property
    def state(self) -> PipelineState:
        """The current observable :class:`PipelineState`.

        Informational only — reading this never changes how the pipeline
        behaves, and the pipeline never branches on it.
        """
        return self._state

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
        self._state = PipelineState.RUNNING
        try:
            findings: list[Any] = []
            for rule in self.get_ordered_rules():
                rule_findings = rule.validate(response)
                findings.extend(rule_findings)
        except BaseException:
            # State is observational; record the failure and re-raise the
            # original exception unchanged so existing error handling is
            # unaffected.
            self._state = PipelineState.FAILED
            raise
        self._state = PipelineState.COMPLETED
        return findings
