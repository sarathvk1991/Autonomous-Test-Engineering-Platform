"""The live, provider-backed
:class:`~automation_engineering.generation.page_object_generator.PageObjectGenerator`
implementation.

:class:`LivePageObjectGenerator` is a peer of
:class:`~automation_engineering.generation.page_object_generator.StubPageObjectGenerator`
behind the same seam -- it satisfies
:class:`~automation_engineering.generation.page_object_generator.PageObjectGenerator`
unchanged and is the only thing this module adds. It renders one of TWO
governed prompt versions with one
:class:`~automation_engineering.generation.page_object_generator.PageObjectGenerationContext`
and returns the raw response text (generated Java source); the orchestrator
(:mod:`automation_engineering.generation.page_object_orchestrator`) performs
no parsing, no compilation, and no lint of that text -- CP3/CP4 (later,
out-of-scope tasks) are where generated Java is actually verified.

Two governed prompt versions, one generator (this build's own extension)
--------------------------------------------------------------------------
``generate_page_objects`` v1.0.0 is single-action-shaped (module history:
built first, and left byte-for-byte frozen per ADR-0014 invariant H.1 --
never edited). ``generate_page_objects`` v1.1.0 is the MINOR, additive
multi-method extension this build registers (`automation_engineering.
prompts.composition`): it takes an ordered ``methods`` list of caller-named
method specs and produces one class exposing all of them.

This class chooses per call, based on ``context.additional_method_needs``:

* empty -- exactly the ORIGINAL, unchanged single-method path: v1.0.0's own
  template, v1.0.0's own INPUT CONTRACT shape (``action_text``/``captures``
  at the top level, no ``methods`` list). Byte-identical to this module's
  behavior before this build; every pre-existing single-method test still
  passes unmodified.
* non-empty -- the NEW multi-method path: v1.1.0's own template, a
  ``methods`` list built from ``context.method_name``/``context.need``
  (the primary) followed by every entry in ``context.additional_method_needs``
  (each already carrying its own ``method_name``/``need``). Previously this
  branch unconditionally raised ``NotImplementedError``; that guard is gone
  now that v1.1.0 exists to actually serve the request.

Both paths share one provider-call/response-handling core (:meth:`_execute`)
-- the exception types, error messages, and metadata shape for the
single-method path are UNCHANGED from before this build.

Completeness, honestly bounded
-------------------------------
The multi-method path additionally verifies every requested ``method_name``
(primary + additional) appears as a Java method declaration somewhere in the
response text, and raises :class:`LiveGenerationError` naming exactly which
are missing if not -- a deliberate, narrow exception to this module's own
"no parsing" posture (module docstring above), because "the model silently
dropped one of several requested methods" is a specific, mechanically
checkable, and uniquely likely failure mode for a multi-method response that
never existed for the single-method path (exactly one method was ever
requested there, so nothing could go missing). This is a best-effort
REGEX presence check (:func:`_declares_method`), not a Java parse or
compile -- it can be fooled by pathological input (a method name appearing
only in a comment, say) and makes no claim about signature correctness,
method BODY correctness, or compliance with `customqa:*` -- CP3/CP4 remain
the actual, authoritative verifiers of generated Java; this check exists
only to catch the model returning an INCOMPLETE class outright, honestly,
rather than the orchestrator silently trusting a response that never
contained everything it asked for.

Same mechanism as the step-definition live generator, not a parallel one
------------------------------------------------------------------------------
Mirrors
:class:`~automation_engineering.generation.live_step_definition_generator.LiveStepDefinitionGenerator`'s
own boundary exactly: an
:class:`~requirement_intelligence.llm.providers.base_provider.LLMProvider` is
constructor-injected, never constructed here -- provider selection
(``llm_factory.create_provider``) and ``validate_connection()`` are the
caller's responsibility. This module never imports ``llm_factory``, and
performs no retries.

Both ``generate_page_objects`` v1.0.0 and v1.1.0 conform to the full
governed system/user template contract (exactly one ``{artifact_context}``
placeholder) -- rendered via ``render_user_prompt``, not an
append-a-final-section workaround.
"""

from __future__ import annotations

import json
import re
from uuid import uuid4

from automation_engineering.errors import TransportFailureError
from automation_engineering.generation.page_object_generator import (
    PageObjectGenerationContext,
)
from automation_engineering.prompts.composition import build_prompt_registry
from requirement_intelligence.llm.llm_models import LLMRequest
from requirement_intelligence.llm.providers.base_provider import LLMProvider
from shared.enums.base import ExecutionStatus
from shared.prompts.framework.prompt_registry import PromptRegistry
from shared.prompts.framework.prompt_template_contract import (
    GovernedTemplate,
    parse_governed_template,
)
from shared.prompts.models.prompt_definition import PromptDefinition

_PROMPT_ID = "generate_page_objects"
_SINGLE_METHOD_PROMPT_VERSION = "1.0.0"
_MULTI_METHOD_PROMPT_VERSION = "1.1.0"

#: Deterministic sampling by default, matching the platform-wide convention
#: (``LLMRequest.temperature`` itself defaults to 0.0).
_DEFAULT_TEMPERATURE = 0.0

_SECTION_SEPARATOR = "\n\n"


class LiveGenerationError(TransportFailureError):
    """Raised when the LLM boundary fails to produce usable content.

    Covers exactly four failure modes at this boundary -- a provider
    exception (including a timeout, which the provider wraps rather than
    letting an SDK exception escape), a non-``COMPLETED`` normalized
    execution outcome, an empty/whitespace-only response, and (multi-method
    requests only) a response missing one or more of the requested methods
    outright (module docstring's own "completeness, honestly bounded"
    section). Anything else the model *did* return, however malformed as
    Java, is not this exception's concern -- that is CP3/CP4's job (later,
    out-of-scope tasks), not this boundary's.

    Subclasses :class:`~automation_engineering.errors.TransportFailureError`
    (2026-08-05, the free-tier survivability build) -- see
    :mod:`.live_step_definition_generator`'s own note for the rationale,
    identical here.
    """


def _declares_method(java_source: str, method_name: str) -> bool:
    """Best-effort, regex-based presence check for one Java method
    declaration's own name -- NOT a Java parse or compile (module
    docstring's own "completeness, honestly bounded" section states the
    limits explicitly). Matches ``method_name`` immediately followed by an
    opening parenthesis (optionally separated by whitespace), the shape any
    method DECLARATION or invocation of that name takes in Java source."""
    return re.search(rf"\b{re.escape(method_name)}\s*\(", java_source) is not None


def _capture_payload(need_captures: object) -> list[dict[str, object]]:
    """Shared capture-list rendering for both prompt versions' own payload
    shape -- identical field set, only ever called with
    ``GherkinStepNeed.captures``."""
    return [
        {
            "index": capture.index,
            "style": capture.style,
            "expression_type": capture.expression_type,
        }
        for capture in need_captures  # type: ignore[attr-defined]
    ]


class LivePageObjectGenerator:
    """``generate_page_objects``-backed page-object generator -- v1.0.0 for
    the single-method case, v1.1.0 for the multi-method case (module
    docstring).

    Parameters
    ----------
    provider:
        An already-constructed, already-validated
        :class:`LLMProvider` (e.g. via ``llm_factory.create_provider`` +
        ``provider.validate_connection()``). This class never selects or
        constructs a provider itself.
    prompt_registry:
        The sealed Layer 3 :class:`PromptRegistry` to resolve BOTH
        ``generate_page_objects`` versions from. When *None*, the canonical
        registry is composed via
        :func:`~automation_engineering.prompts.composition.build_prompt_registry`.
    temperature:
        Sampling temperature forwarded to the provider. Defaults to ``0.0``,
        matching :class:`LLMRequest`'s own platform-wide default.
    """

    def __init__(
        self,
        provider: LLMProvider,
        *,
        prompt_registry: PromptRegistry | None = None,
        temperature: float = _DEFAULT_TEMPERATURE,
    ) -> None:
        self._provider = provider
        registry = prompt_registry if prompt_registry is not None else build_prompt_registry()

        self._single_definition = registry.get(_PROMPT_ID, _SINGLE_METHOD_PROMPT_VERSION)
        self._single_template = parse_governed_template(self._single_definition.content)

        self._multi_definition = registry.get(_PROMPT_ID, _MULTI_METHOD_PROMPT_VERSION)
        self._multi_template = parse_governed_template(self._multi_definition.content)

        self._temperature = temperature

    def generate(self, context: PageObjectGenerationContext) -> str:
        """Return generated Java page-object source for ``context``.

        Raises
        ------
        ValueError
            If ``context.additional_method_needs`` is non-empty but
            ``context.method_name`` is ``None`` -- a multi-method request
            must name every method, including the primary; raised before
            any provider call.
        LiveGenerationError
            If the provider call fails (including a timeout), the response's
            normalized ``execution_status`` is not ``COMPLETED``, the
            returned text is empty/whitespace-only, or (multi-method only)
            the response is missing one or more of the requested methods.
        """
        if context.additional_method_needs:
            return self._generate_multi_method(context)
        return self._generate_single_method(context)

    # ------------------------------------------------------------------
    # Single-method path -- UNCHANGED behavior (v1.0.0)
    # ------------------------------------------------------------------

    def _generate_single_method(self, context: PageObjectGenerationContext) -> str:
        prompt = self._build_single_method_prompt(context)
        return self._execute(
            prompt, definition=self._single_definition, class_name=context.class_name
        )

    def _build_single_method_prompt(self, context: PageObjectGenerationContext) -> str:
        """Render v1.0.0's own governed template -- only the fields
        ``generate_page_objects`` v1.0.0's own INPUT CONTRACT names, exactly
        as before this build."""
        input_payload: dict[str, object] = {
            "action_text": context.need.text,
            "captures": _capture_payload(context.need.captures),
            "class_name": context.class_name,
            "target_package": context.target_package,
            "customqa_constraints": list(context.customqa_constraints),
        }
        return self._render(self._single_template, input_payload)

    # ------------------------------------------------------------------
    # Multi-method path -- NEW (v1.1.0), this build
    # ------------------------------------------------------------------

    def _generate_multi_method(self, context: PageObjectGenerationContext) -> str:
        if context.method_name is None:
            raise ValueError(
                f"class_name={context.class_name!r}: a multi-method generation "
                "context (context.additional_method_needs is non-empty) requires "
                "context.method_name for the PRIMARY method too -- every method in "
                "a multi-method class must be caller-named, never left for the "
                "model to invent while its siblings are named."
            )
        expected_method_names = (
            context.method_name,
            *(need.method_name for need in context.additional_method_needs),
        )

        prompt = self._build_multi_method_prompt(context, expected_method_names)
        generated_text = self._execute(
            prompt, definition=self._multi_definition, class_name=context.class_name
        )

        missing = [
            name for name in expected_method_names if not _declares_method(generated_text, name)
        ]
        if missing:
            raise LiveGenerationError(
                f"class_name={context.class_name!r}: LLM response is missing "
                f"{len(missing)} of {len(expected_method_names)} requested method(s) "
                f"{missing!r} -- expected all of {list(expected_method_names)!r}. "
                "Never silently returning an incomplete class."
            )
        return generated_text

    def _build_multi_method_prompt(
        self, context: PageObjectGenerationContext, expected_method_names: tuple[str, ...]
    ) -> str:
        """Render v1.1.0's own governed template -- a ``methods`` list, one
        entry per requested method (primary first, then every entry in
        ``context.additional_method_needs``, in order), each carrying its
        own caller-chosen ``method_name``."""
        method_needs = (
            context.need,
            *(need.need for need in context.additional_method_needs),
        )
        methods_payload = [
            {
                "method_name": method_name,
                "action_text": need.text,
                "captures": _capture_payload(need.captures),
            }
            for method_name, need in zip(expected_method_names, method_needs, strict=True)
        ]
        input_payload: dict[str, object] = {
            "class_name": context.class_name,
            "target_package": context.target_package,
            "customqa_constraints": list(context.customqa_constraints),
            "methods": methods_payload,
        }
        return self._render(self._multi_template, input_payload)

    # ------------------------------------------------------------------
    # Shared rendering / provider-call core
    # ------------------------------------------------------------------

    @staticmethod
    def _render(template: GovernedTemplate, input_payload: dict[str, object]) -> str:
        artifact_context = json.dumps(input_payload, indent=2, sort_keys=True)
        user_prompt = template.render_user_prompt(artifact_context)
        return f"{template.system_prompt}{_SECTION_SEPARATOR}{user_prompt}"

    def _execute(self, prompt: str, *, definition: PromptDefinition, class_name: str) -> str:
        """Shared provider-call/response-handling core for BOTH prompt
        versions -- identical exception types, error message shape, and
        request-metadata shape as the single-method path always had; only
        ``definition``/``prompt`` vary by caller."""
        request = LLMRequest(
            request_id=str(uuid4()),
            prompt=prompt,
            temperature=self._temperature,
            metadata={
                "prompt_id": definition.metadata.prompt_id,
                "prompt_version": definition.metadata.version,
                "class_name": class_name,
            },
        )

        try:
            response = self._provider.generate(request)
        except Exception as exc:  # provider boundary catch-all, mirroring
            # LiveStepDefinitionGenerator.generate -- no provider-specific
            # exception (including an SDK timeout) is allowed to cross this
            # boundary unwrapped.
            raise LiveGenerationError(
                f"class_name={class_name!r}: LLM provider call failed: {exc}"
            ) from exc

        if response.execution_status != ExecutionStatus.COMPLETED:
            raise LiveGenerationError(
                f"class_name={class_name!r}: LLM execution did not "
                f"complete (execution_status={response.execution_status!r})."
            )

        generated_text = response.generated_text
        if not generated_text or not generated_text.strip():
            raise LiveGenerationError(f"class_name={class_name!r}: LLM returned an empty response.")
        return generated_text


__all__ = ["LiveGenerationError", "LivePageObjectGenerator"]
