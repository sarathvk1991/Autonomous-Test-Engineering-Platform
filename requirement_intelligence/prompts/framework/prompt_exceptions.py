"""Custom exceptions for the Prompt Governance Framework.

Exception hierarchy
-------------------
::

    PromptFrameworkError
    ├── PromptRegistryError
    │   └── PromptNotFoundError
    └── PromptLoaderError

Design notes
------------
These exceptions describe **framework-level failures** — problems with how the
Prompt Governance infrastructure is configured, assembled, or invoked.  They
are deliberately separate from prompt *definitions* (which are not exceptions
but canonical :class:`~requirement_intelligence.prompts.models.PromptDefinition`
objects produced when the framework operates normally).

A :class:`PromptFrameworkError` means the framework itself could not perform its
work.  It does **not** mean that any prompt template was judged invalid; it means
the infrastructure encountered a programming error or an integrity violation.

This mirrors the exception design of the Response Validation Framework
(:mod:`requirement_intelligence.validation.validation_exceptions`) and the CP1
Framework (:mod:`requirement_intelligence.cp1.framework.framework_exceptions`).
"""

from __future__ import annotations


class PromptFrameworkError(Exception):
    """Base exception for all Prompt Governance Framework errors.

    Raise a subclass in preference to this class directly.  Catching
    :class:`PromptFrameworkError` will catch all framework-level failures.
    """


class PromptRegistryError(PromptFrameworkError):
    """Raised when the :class:`PromptRegistry` cannot fulfil a request.

    Examples
    --------
    * A :class:`PromptDefinition` is registered with a ``prompt_id`` /
      ``version`` combination that is already present.
    * An attempt is made to register into a registry that has been sealed.
    * A lookup is performed on an ambiguous identifier (multiple versions).

    This signals a programming error in how the framework is assembled, not a
    problem with any prompt's content.
    """


class PromptNotFoundError(PromptRegistryError):
    """Raised when a prompt cannot be found in the registry.

    This is a specialisation of :class:`PromptRegistryError` for the common
    case of a lookup that finds no matching registration.  Callers that need
    to distinguish "not registered" from "registry is sealed" can catch this
    subclass specifically.
    """


class PromptTemplateContractError(PromptFrameworkError):
    """Raised when a governed template violates the runtime template contract.

    The contract is defined and enforced in
    :mod:`~requirement_intelligence.prompts.framework.prompt_template_contract`.

    Examples
    --------
    * The template has no blank line, so no system/user split point exists.
    * The system prompt section spans more than one paragraph.
    * The user section is missing the ``{artifact_context}`` placeholder, or
      contains it more than once.

    A :class:`PromptTemplateContractError` means the template's *bytes* may be
    intact (its SHA-256 verified) while its *structure* cannot be interpreted by
    the runtime, so no ``PromptRequest`` can be assembled from it.
    """


class PromptLoaderError(PromptFrameworkError):
    """Raised when the :class:`PromptLoader` cannot load or verify a prompt file.

    Examples
    --------
    * The versioned template file does not exist in ``prompts/versions/``.
    * The manifest index (``manifest.json``) cannot be read or parsed.
    * The SHA-256 of the loaded file does not match the recorded fingerprint in
      the manifest — indicating the file has been tampered with or corrupted.
    * The requested ``prompt_id`` / ``version`` is not listed in the manifest.

    A :class:`PromptLoaderError` means the file-integrity guarantee of the
    Prompt Governance subsystem cannot be satisfied and no
    :class:`PromptDefinition` can be safely returned.
    """
