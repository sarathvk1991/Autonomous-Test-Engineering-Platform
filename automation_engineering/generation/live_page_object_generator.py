"""The live, provider-backed
:class:`~automation_engineering.generation.page_object_generator.PageObjectGenerator`
implementation.

:class:`LivePageObjectGenerator` is a peer of
:class:`~automation_engineering.generation.page_object_generator.StubPageObjectGenerator`
behind the same seam -- it satisfies
:class:`~automation_engineering.generation.page_object_generator.PageObjectGenerator`
unchanged and is the only thing this module adds. It renders the governed
``generate_page_objects`` v1.1.0 prompt with one
:class:`~automation_engineering.generation.page_object_generator.PageObjectGenerationContext`
and returns the raw response text (generated Java source); the orchestrator
(:mod:`automation_engineering.generation.page_object_orchestrator`) performs
no parsing, no compilation, and no lint of that text -- CP3/CP4 (later,
out-of-scope tasks) are where generated Java is actually verified.

ONE prompt version now, not two -- the divergence that caused a real,
live-verified defect (additive fix, this build)
--------------------------------------------------------------------------
Until this fix, this class chose between TWO governed prompt versions:
v1.0.0 (single-method, its payload carrying only ``action_text``/
``captures`` -- never ``method_name``, even though
:class:`PageObjectGenerationContext.method_name` already existed) for a
context with no ``additional_method_needs``, and v1.1.0 (multi-method, a
``methods`` list where each entry carries its OWN caller-chosen
``method_name``, used VERBATIM) for a context with two-or-more.

**A live regeneration run against the real tracked baseline measured the
cost of that split directly**: 31 of the 32 needed page-object classes went
through the single-method (v1.0.0) path, whose prompt never told the model
what method name to use -- so the model paraphrased its own name from
``action_text`` instead of using the name a real step-definition's call
site actually needed. Measured: 22 of 33 requested method calls (67%)
came back under the WRONG name, and the regenerated suite failed to
compile on exactly that mismatch (among other, independent defects tracked
separately). The multi-method path never had this problem, because it
always conveyed ``method_name``.

**The fix is not a third prompt version -- it is retiring the divergence.**
A single method is structurally just a ``methods`` list of length one; the
v1.1.0 template already handles that correctly (proven below, both by the
existing multi-method proofs and new single-method-through-v1.1.0 proofs).
This class now ALWAYS renders v1.1.0's ``methods``-list payload and ALWAYS
requires ``context.method_name`` (previously required only when
``context.additional_method_needs`` was non-empty) -- one prompt, one
payload shape, the derived method name conveyed on every call, no
divergence left for a future defect like this one to hide in.

``generate_page_objects`` v1.0.0 remains registered, byte-for-byte
unedited (ADR-0014 invariant H.1), in
:mod:`automation_engineering.prompts.composition` -- this class simply no
longer loads or calls it. It is kept for governance/audit history (the
original single-method contract, still inspectable via the registry) and
as a documented fallback should some future caller need it; whether to
formally mark it ``DEPRECATED`` is a lifecycle decision this fix does not
make (out of scope -- a governance call, not a wiring one).

Completeness, honestly bounded
-------------------------------
Every generation now verifies every requested ``method_name`` (primary +
any additional siblings) appears as a Java method declaration somewhere in
the response text, and raises :class:`LiveGenerationError` naming exactly
which are missing if not -- a deliberate, narrow exception to this
module's own "no parsing" posture, because "the model dropped or renamed a
requested method" is exactly the specific, mechanically checkable failure
mode the live run measured. This is a best-effort REGEX presence check
(:func:`_declares_method`), not a Java parse or compile -- it can be
fooled by pathological input (a method name appearing only in a comment,
say) and makes no claim about signature correctness, method BODY
correctness, or compliance with `customqa:*` -- CP3/CP4 remain the actual,
authoritative verifiers of generated Java; this check exists only to catch
the model returning an INCOMPLETE (or wrongly-named) class outright,
honestly, rather than the orchestrator silently trusting a response that
never satisfied what it asked for. Previously this check only ran for a
multi-method request (exactly one method was ever requested on the
single-method path, so nothing could go missing there) -- it now runs
unconditionally, a strictly additional safety net for the single-method
case, catching the EXACT defect this fix addresses even if the model still
ignores the verbatim instruction.

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

``generate_page_objects`` v1.1.0 conforms to the full governed system/user
template contract (exactly one ``{artifact_context}`` placeholder) --
rendered via ``render_user_prompt``, not an append-a-final-section
workaround.
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
from shared.prompts.framework.prompt_template_contract import parse_governed_template

_PROMPT_ID = "generate_page_objects"
_PROMPT_VERSION = "1.1.0"

#: Deterministic sampling by default, matching the platform-wide convention
#: (``LLMRequest.temperature`` itself defaults to 0.0).
_DEFAULT_TEMPERATURE = 0.0

_SECTION_SEPARATOR = "\n\n"


class LiveGenerationError(TransportFailureError):
    """Raised when the LLM boundary fails to produce usable content.

    Covers exactly four failure modes at this boundary -- a provider
    exception (including a timeout, which the provider wraps rather than
    letting an SDK exception escape), a non-``COMPLETED`` normalized
    execution outcome, an empty/whitespace-only response, and a response
    missing (or, per this fix, renaming) one or more of the requested
    methods outright (module docstring's own "completeness, honestly
    bounded" section). Anything else the model *did* return, however
    malformed as Java, is not this exception's concern -- that is CP3/CP4's
    job (later, out-of-scope tasks), not this boundary's.

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
    """The capture-list rendering for the ``methods`` payload's own
    per-entry ``captures`` field -- only ever called with
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
    """``generate_page_objects`` v1.1.0-backed page-object generator --
    ONE prompt version for every call, single-method or multi-method alike
    (module docstring: the divergence that caused a live-measured defect is
    retired by this fix).

    Parameters
    ----------
    provider:
        An already-constructed, already-validated
        :class:`LLMProvider` (e.g. via ``llm_factory.create_provider`` +
        ``provider.validate_connection()``). This class never selects or
        constructs a provider itself.
    prompt_registry:
        The sealed Layer 3 :class:`PromptRegistry` to resolve
        ``generate_page_objects`` v1.1.0 from. When *None*, the canonical
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

        self._definition = registry.get(_PROMPT_ID, _PROMPT_VERSION)
        self._template = parse_governed_template(self._definition.content)

        self._temperature = temperature

    def generate(self, context: PageObjectGenerationContext) -> str:
        """Return generated Java page-object source for ``context``.

        Raises
        ------
        ValueError
            If ``context.method_name`` is ``None`` -- every generated
            method (the primary and any additional siblings) must be
            caller-named, never left for the model to invent from
            ``action_text`` alone (the exact live-measured defect this fix
            closes). Raised before any provider call.
        LiveGenerationError
            If the provider call fails (including a timeout), the response's
            normalized ``execution_status`` is not ``COMPLETED``, the
            returned text is empty/whitespace-only, or the response is
            missing (or renamed) one or more of the requested methods.
        """
        if context.method_name is None:
            raise ValueError(
                f"class_name={context.class_name!r}: PageObjectGenerationContext.method_name "
                "is required -- every generated method (the primary and any additional "
                "siblings via context.additional_method_needs) must be caller-named, "
                "never left for the model to invent from action_text alone."
            )
        expected_method_names = (
            context.method_name,
            *(need.method_name for need in context.additional_method_needs),
        )

        prompt = self._build_prompt(context, expected_method_names)
        generated_text = self._execute(prompt, class_name=context.class_name)

        missing = [
            name for name in expected_method_names if not _declares_method(generated_text, name)
        ]
        if missing:
            raise LiveGenerationError(
                f"class_name={context.class_name!r}: LLM response is missing "
                f"{len(missing)} of {len(expected_method_names)} requested method(s) "
                f"{missing!r} -- expected all of {list(expected_method_names)!r}. "
                "Never silently returning an incomplete or wrongly-named class."
            )
        return generated_text

    def _build_prompt(
        self, context: PageObjectGenerationContext, expected_method_names: tuple[str, ...]
    ) -> str:
        """Render v1.1.0's own governed template -- a ``methods`` list, one
        entry per requested method (primary first, then every entry in
        ``context.additional_method_needs``, in order), each carrying its
        own caller-chosen ``method_name``. A single-method call renders a
        length-one ``methods`` list -- the same template, the same
        verbatim-naming instruction, no special-casing."""
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
        artifact_context = json.dumps(input_payload, indent=2, sort_keys=True)
        user_prompt = self._template.render_user_prompt(artifact_context)
        return f"{self._template.system_prompt}{_SECTION_SEPARATOR}{user_prompt}"

    def _execute(self, prompt: str, *, class_name: str) -> str:
        request = LLMRequest(
            request_id=str(uuid4()),
            prompt=prompt,
            temperature=self._temperature,
            metadata={
                "prompt_id": self._definition.metadata.prompt_id,
                "prompt_version": self._definition.metadata.version,
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
