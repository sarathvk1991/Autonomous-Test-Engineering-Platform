"""Exceptions for the Engineering Context Orchestration subsystem.

Follows the per-subsystem convention established by
:mod:`requirement_intelligence.consolidation.consolidation_exceptions`: one
rooted base per subsystem, subclassed where a more specific error adds value.

Malformed *identifier* input is **not** raised through this hierarchy. The
identity value objects raise :class:`ValueError` from their ``parse``
constructors, matching the convention set by
:class:`~requirement_intelligence.prompts.models.prompt_version.PromptVersion`.
"""

from __future__ import annotations


class ContextOrchestrationError(Exception):
    """Base class for every Engineering Context Orchestration error."""


class ContextConstructionError(ContextOrchestrationError):
    """Raised when an :class:`EngineeringContext` cannot be constructed.

    Covers missing, empty, or wrongly-typed builder inputs — never a policy
    *decision*, which the builder does not make.
    """


class PolicyCompatibilityError(ContextOrchestrationError):
    """Raised when an ``OrchestrationPolicy`` is incompatible with the builder.

    Compatibility is decided on the policy's **major** version, mirroring
    ``PromptVersion.is_compatible_with``.
    """


class ContextBudgetExceededError(ContextOrchestrationError):
    """Raised when the evidence handed to the builder exceeds the policy budget.

    The builder *enforces* the budget as an input contract; it never *applies*
    the budget by truncating evidence. Applying the budget is the Engineering
    Context Orchestrator's job (CAP-076C).
    """
