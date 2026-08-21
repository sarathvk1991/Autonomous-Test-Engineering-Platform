"""The live, provider-backed
:class:`~automation_engineering.generation.utility_generator.UtilityGenerator`
implementation.

:class:`LiveUtilityGenerator` is a peer of
:class:`~automation_engineering.generation.utility_generator.StubUtilityGenerator`
behind the same seam -- it satisfies
:class:`~automation_engineering.generation.utility_generator.UtilityGenerator`
unchanged and is the only thing this module adds. It renders the governed
``generate_utilities`` prompt (v1.0.0) with one
:class:`~automation_engineering.generation.utility_generator.UtilityGenerationContext`
and returns the raw response text (generated Java source); the orchestrator
(:mod:`automation_engineering.generation.utility_orchestrator`) performs no
parsing, no compilation, and no lint of that text -- CP3/CP4 (later,
out-of-scope tasks) are where generated Java is actually verified.

Same mechanism as the other two live generators, not a parallel one
------------------------------------------------------------------------
Mirrors
:class:`~automation_engineering.generation.live_page_object_generator.LivePageObjectGenerator`'s
own boundary exactly: an
:class:`~requirement_intelligence.llm.providers.base_provider.LLMProvider` is
constructor-injected, never constructed here -- provider selection
(``llm_factory.create_provider``) and ``validate_connection()`` are the
caller's responsibility. This module never imports ``llm_factory``, and
performs no retries.

``generate_utilities`` v1.0.0 conforms to the full governed system/user
template contract (exactly one ``{artifact_context}`` placeholder), the same
as the other two Layer 3 prompts.

``build_utility_payload``/``resolve_utility_identity`` (additive, the
artifact-cache extension -- the 5th and final generator, closing ADR-0050's
own "one remaining generator" gap) mirror
:func:`~.live_page_object_generator.build_page_object_payload`/
:func:`~.live_page_object_generator.resolve_page_object_identity` exactly:
the FORMER extracts :meth:`LiveUtilityGenerator._build_prompt`'s own inline
payload dict, content-unmodified, to a public, standalone function -- the
one, single definition of "what determines this generator's output," usable
by a caching decorator that never constructs a live generator; the LATTER
resolves this generator's :class:`~requirement_intelligence.llm.
generation_identity.GenerationIdentity` WITHOUT calling the LLM (ADR-0050
D3's own "Gap 1" -- the pre-call identity a caching decorator needs to
compute a key BEFORE deciding hit-or-miss).
"""

from __future__ import annotations

import json
from uuid import uuid4

from automation_engineering.errors import TransportFailureError
from automation_engineering.generation.utility_generator import UtilityGenerationContext
from automation_engineering.prompts.composition import build_prompt_registry
from requirement_intelligence.llm.generation_identity import GenerationIdentity
from requirement_intelligence.llm.llm_models import LLMRequest
from requirement_intelligence.llm.providers.base_provider import LLMProvider
from requirement_intelligence.llm.token_usage import TokenUsageTracker
from shared.enums.base import ExecutionStatus
from shared.prompts.framework.prompt_registry import PromptRegistry
from shared.prompts.framework.prompt_template_contract import parse_governed_template

_PROMPT_ID = "generate_utilities"
_PROMPT_VERSION = "1.0.0"

#: This generator's own token-usage call-type identifier (token-usage-by-stage
#: instrumentation, 2026-08-12 -- Nitin's "Critically"-flagged clarification).
CALL_TYPE = "utility_generation"

#: Deterministic sampling by default, matching the platform-wide convention
#: (``LLMRequest.temperature`` itself defaults to 0.0).
_DEFAULT_TEMPERATURE = 0.0

_SECTION_SEPARATOR = "\n\n"


class LiveGenerationError(TransportFailureError):
    """Raised when the LLM boundary fails to produce usable content.

    Covers exactly three failure modes at this boundary -- a provider
    exception (including a timeout, which the provider wraps rather than
    letting an SDK exception escape), a non-``COMPLETED`` normalized
    execution outcome, and an empty/whitespace-only response. Anything the
    model *did* return, however malformed as Java, is not this exception's
    concern -- that is CP3/CP4's job (later, out-of-scope tasks), not this
    boundary's.

    Subclasses :class:`~automation_engineering.errors.TransportFailureError`
    (2026-08-05, the free-tier survivability build) -- see
    :mod:`.live_step_definition_generator`'s own note for the rationale,
    identical here.
    """


class LiveUtilityGenerator:
    """``generate_utilities`` v1.0.0-backed utility generator.

    Parameters
    ----------
    provider:
        An already-constructed, already-validated
        :class:`LLMProvider` (e.g. via ``llm_factory.create_provider`` +
        ``provider.validate_connection()``). This class never selects or
        constructs a provider itself.
    prompt_registry:
        The sealed Layer 3 :class:`PromptRegistry` to resolve
        ``generate_utilities`` v1.0.0 from. When *None*, the canonical
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
        usage_recorder: TokenUsageTracker | None = None,
    ) -> None:
        self._provider = provider
        registry = prompt_registry if prompt_registry is not None else build_prompt_registry()
        definition = registry.get(_PROMPT_ID, _PROMPT_VERSION)
        self._definition = definition
        self._template = parse_governed_template(definition.content)
        self._temperature = temperature
        self._usage_recorder = usage_recorder
        self._last_identity: GenerationIdentity | None = None

    @property
    def last_identity(self) -> GenerationIdentity | None:
        """The prompt/model identity of the most recent successful
        :meth:`generate` call — ``None`` until the first call completes.
        Purely additive (mirrors ``LiveStepDefinitionGenerator.last_identity``'s
        own discipline)."""
        return self._last_identity

    def generate(self, context: UtilityGenerationContext) -> str:
        """Return generated Java utility source for ``context``.

        Raises
        ------
        LiveGenerationError
            If the provider call fails (including a timeout), the response's
            normalized ``execution_status`` is not ``COMPLETED``, or the
            returned text is empty/whitespace-only.
        """
        request = LLMRequest(
            request_id=str(uuid4()),
            prompt=self._build_prompt(context),
            temperature=self._temperature,
            metadata={
                "prompt_id": self._definition.metadata.prompt_id,
                "prompt_version": self._definition.metadata.version,
                "class_name": context.class_name,
            },
        )

        try:
            response = self._provider.generate(request)
        except Exception as exc:  # provider boundary catch-all, mirroring
            # LivePageObjectGenerator.generate -- no provider-specific
            # exception (including an SDK timeout) is allowed to cross this
            # boundary unwrapped.
            raise LiveGenerationError(
                f"class_name={context.class_name!r}: LLM provider call failed: {exc}"
            ) from exc

        if self._usage_recorder is not None:
            self._usage_recorder.record(CALL_TYPE, response.usage)
        self._last_identity = GenerationIdentity(
            prompt_id=self._definition.metadata.prompt_id,
            prompt_version=self._definition.metadata.version,
            prompt_sha256=self._definition.metadata.sha256,
            provider=str(response.provider),
            model=response.model,
        )

        if response.execution_status != ExecutionStatus.COMPLETED:
            raise LiveGenerationError(
                f"class_name={context.class_name!r}: LLM execution did not "
                f"complete (execution_status={response.execution_status!r})."
            )

        generated_text = response.generated_text
        if not generated_text or not generated_text.strip():
            raise LiveGenerationError(
                f"class_name={context.class_name!r}: LLM returned an empty response."
            )
        return generated_text

    def _build_prompt(self, context: UtilityGenerationContext) -> str:
        """Render the governed template's system prompt plus its user
        template, with the structured generation context substituted into
        the single ``{artifact_context}`` placeholder -- only the fields
        ``generate_utilities`` v1.0.0's own INPUT CONTRACT names.
        """
        input_payload = build_utility_payload(context)
        artifact_context = json.dumps(input_payload, indent=2, sort_keys=True)
        user_prompt = self._template.render_user_prompt(artifact_context)
        return f"{self._template.system_prompt}{_SECTION_SEPARATOR}{user_prompt}"


def build_utility_payload(context: UtilityGenerationContext) -> dict[str, object]:
    """The exact, deterministic payload :meth:`LiveUtilityGenerator.
    _build_prompt` serializes into the LLM call -- extracted to a public,
    standalone function so there is exactly ONE definition of "what
    determines this generator's output," the same discipline
    :func:`~.live_step_definition_generator.build_step_definition_payload`/
    :func:`~.live_page_object_generator.build_page_object_payload` already
    established (used both to render the prompt and, by
    :mod:`automation_engineering.generation.caching_utility_generator`, to
    compute the artifact-generation cache key, ADR-0050 D1). A pure function
    of ``context`` alone (never ``self``) -- content-unmodified from the
    inline dict this function replaces, so this extraction is behavior-
    preserving by construction, not a re-derivation.
    """
    return {
        "action_text": context.need.text,
        "captures": [
            {
                "index": capture.index,
                "style": capture.style,
                "expression_type": capture.expression_type,
            }
            for capture in context.need.captures
        ],
        "class_name": context.class_name,
        "target_package": context.target_package,
        "customqa_constraints": list(context.customqa_constraints),
    }


def resolve_utility_identity(
    *,
    provider: str,
    model: str,
    prompt_registry: PromptRegistry | None = None,
) -> GenerationIdentity:
    """The ``generate_utilities`` v1.0.0 :class:`GenerationIdentity`,
    resolved WITHOUT calling the LLM (ADR-0050 D3's "Gap 1" -- the pre-call
    identity a caching decorator needs to compute a key BEFORE deciding
    hit-or-miss). Mirrors
    :func:`~.live_page_object_generator.resolve_page_object_identity`
    exactly, scoped to this generator's own prompt id/version.

    ``prompt_id``/``prompt_version``/``prompt_sha256`` are read straight off
    the registry -- the same, already-sealed source
    :class:`LiveUtilityGenerator` itself reads in ``__init__``, never
    re-derived. ``provider``/``model`` are supplied by the SAME caller that
    already chose them when constructing the live provider -- not invented
    here; a caller that supplies a value the provider will not actually echo
    back produces a caching decorator that raises on its first MISS (the
    decorator's own identity-mismatch safety check), never a silent wrong
    cache entry.
    """
    registry = prompt_registry if prompt_registry is not None else build_prompt_registry()
    definition = registry.get(_PROMPT_ID, _PROMPT_VERSION)
    return GenerationIdentity(
        prompt_id=definition.metadata.prompt_id,
        prompt_version=definition.metadata.version,
        prompt_sha256=definition.metadata.sha256,
        provider=provider,
        model=model,
    )


__all__ = [
    "LiveGenerationError",
    "LiveUtilityGenerator",
    "build_utility_payload",
    "resolve_utility_identity",
]
