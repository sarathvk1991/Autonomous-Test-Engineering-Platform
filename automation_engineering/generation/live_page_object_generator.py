"""The live, provider-backed
:class:`~automation_engineering.generation.page_object_generator.PageObjectGenerator`
implementation.

:class:`LivePageObjectGenerator` is a peer of
:class:`~automation_engineering.generation.page_object_generator.StubPageObjectGenerator`
behind the same seam -- it satisfies
:class:`~automation_engineering.generation.page_object_generator.PageObjectGenerator`
unchanged and is the only thing this module adds. It renders the governed
``generate_page_objects`` v1.2.0 prompt with one
:class:`~automation_engineering.generation.page_object_generator.PageObjectGenerationContext`
and returns the raw response text (generated Java source); the orchestrator
(:mod:`automation_engineering.generation.page_object_orchestrator`) performs
no parsing, no compilation, and no lint of that text -- CP3/CP4 (later,
out-of-scope tasks) are where generated Java is actually verified.

ONE prompt version now, not two -- the divergence that caused a real,
live-verified defect (additive fix)
--------------------------------------------------------------------------
This class used to choose between TWO governed prompt versions: v1.0.0
(single-method, its payload carrying only ``action_text``/``captures`` --
never ``method_name``, even though
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

**The fix was not a third prompt version -- it was retiring the divergence.**
A single method is structurally just a ``methods`` list of length one; the
v1.1.0 template already handled that correctly (proven below, both by the
existing multi-method proofs and single-method-through-the-same-template
proofs). This class ALWAYS renders the ``methods``-list payload and ALWAYS
requires ``context.method_name`` (previously required only when
``context.additional_method_needs`` was non-empty) -- one prompt, one
payload shape, the derived method name conveyed on every call, no
divergence left for a future defect like this one to hide in.

``generate_page_objects`` v1.0.0 and v1.1.0 both remain registered,
byte-for-byte unedited (ADR-0014 invariant H.1), in
:mod:`automation_engineering.prompts.composition` -- this class simply no
longer loads or calls them. They are kept for governance/audit history
(the prior contracts, still inspectable via the registry) and as
documented fallbacks should some future caller need them; whether to
formally mark either ``DEPRECATED`` is a lifecycle decision this fix does
not make (out of scope -- a governance call, not a wiring one).

v1.1.0 -> v1.2.0 -- the real BasePage inventory (additive fix)
--------------------------------------------------------------------------
v1.1.0's own CONSTRAINTS section told the model every locator interaction
"must go through the inherited BasePage helpers" without ever listing what
those helpers ARE. With no real inventory supplied, the model fell back on
Selenium-POM training conventions -- ``isElementDisplayed``, ``sendKeys``,
``click``, ``findElement``, ``getText``, and similar -- that this
platform's real ``BasePage`` (``test-suite-baseline/src/test/java/com/
automation/base/BasePage.java``) does not have; it exposes only
``open(String)``, ``currentTitle()``, and the inherited ``protected final``
``driver``/``wait`` fields. **Measured live**: 31 of 32 generated page-object
classes called at least one such fictional helper and failed to compile
(``cannot find symbol``). v1.2.0 is purely additive over v1.1.0 -- same
``methods``-list request shape, same one-class-extending-BasePage response
shape -- it adds a BASEPAGE'S REAL INHERITED API section hardcoding the
complete real inventory and instructs the model to use ONLY those real
helpers (or this class's own ``driver``/``wait`` fields directly for
anything BasePage doesn't cover), never an invented one. This class now
ALWAYS renders v1.2.0, not v1.1.0 -- the same "one prompt version, not a
divergence" discipline the method-name fix above already established.
**This is the input-side fix only**: it proves the real inventory reaches
the prompt. Whether the model actually stops inventing helpers is proven
by the live regeneration re-run (a separate, later task), not by this
change.

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

``generate_page_objects`` v1.2.0 conforms to the full governed system/user
template contract (exactly one ``{artifact_context}`` placeholder) --
rendered via ``render_user_prompt``, not an append-a-final-section
workaround.

v1.2.0 -> v1.3.0 -- the derived verification-method return type (additive,
defect-4 fix)
--------------------------------------------------------------------------
A live regeneration run (after the defect-2/defect-3 fixes above) found a
fourth, independent compile-breaking mismatch: the step-definition
generator's own verification calls assume a boolean return
(``Assertions.assertTrue(page.isDisplayed())``), while this generator was
never told what that call site expects back, so it was free to declare
``isDisplayed()`` ``void`` -- self-asserting internally instead of
returning a value. Neither prompt conveyed its own assumption to the
other; measured live on 5 of 30 (17%) ``is...``/``verify...`` methods.

No ADR and no working reference example specifies this contract (the same
``SmokePage.java``/``SmokeSteps.java`` reference that anchored the
defect-2 fix has no verification method at all, only a plain getter), but
it is cleanly DERIVABLE from the step-definition's own call-site usage --
the exact mechanism ``method_name`` derivation already uses
(:mod:`.page_object_reference_derivation`), extended to also derive the
return type the call site's own usage implies (see that module's own
"RETURN-TYPE DERIVATION" section). ``PageObjectMethodNeed.return_type``/
``PageObjectGenerationContext.return_type`` carry that derived value (or
``None`` when the usage was not cleanly derivable) through to this
generator, which now conveys it as an OPTIONAL ``return_type`` field per
``methods`` entry -- ``v1.3.0``'s only addition over ``v1.2.0``, otherwise
byte-identical request/response shape. This class now ALWAYS renders
v1.3.0, the same "one prompt version, not a divergence" discipline the
method-name and BasePage-inventory fixes above already established. This
is the INPUT-side fix only: it proves the derived return type reaches the
prompt; whether the model actually declares the matching signature is
proven by the (separate, later) live regeneration re-run.

Still v1.3.0 -- the derived call-site parameter shape (additive, no new
prompt version, the captures-arity fix)
--------------------------------------------------------------------------
The SAME live regeneration run found a fifth, independent compile-breaking
mismatch, this one in the WIRING rather than in either generated Java
side: 2 of 30 (6.7%) pairs failed with "argument lists differ in length"
-- the ``methods`` payload's own ``captures`` field was always built from
``GherkinStepNeed.captures`` (the outer Gherkin step's total capture
count), never from the call site's own real argument count, which can
genuinely differ (a step-def that routes a captured value into
``Assertions.assertEquals(expected, page.getX())`` rather than passing it
to ``page.getX(...)`` calls that method with ZERO arguments even though
the step's own text carries one capture). See
:mod:`.page_object_reference_derivation`'s own "CAPTURES-ARITY
DERIVATION" section for the full root-cause account.

``PageObjectMethodNeed.parameters``/``PageObjectGenerationContext.parameters``
(additive, ``None`` default) now carry the call-site-derived argument
shape when available. This method builds the ``captures`` payload entry
from ``parameters`` (via ``_capture_payload_from_parameters``) WHENEVER it
is supplied, falling back to the pre-existing ``need.captures``-based
``_capture_payload`` only when it is not -- the SAME JSON key the v1.3.0
template's own INPUT CONTRACT already documents, no new field, **no new
prompt version**: this is a Python-side data-source correction (which
value populates an existing payload key), never a change to the governed
prompt TEXT itself (ADR-0014's frozen-wording invariant governs the
static template, not the caller-supplied JSON substituted into
``{artifact_context}`` at render time). ``expression_type`` now carries a
real Java type string when parameter-sourced (``"String"``, ``"boolean"``,
``"Object"`` for an unresolvable argument -- the SAME honest fallback
``_resolve_argument_type`` already uses) rather than a Cucumber Expression
type; the model reads either as a self-explanatory type hint. This is the
INPUT-side fix only: it proves the call-site-derived arity reaches the
prompt; whether the model actually declares the matching signature is
proven by the next live regeneration re-run, not by this change.
"""

from __future__ import annotations

import json
import re
from collections.abc import Sequence
from uuid import uuid4

from automation_engineering.catalog.models import JavaParameter
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
_PROMPT_VERSION = "1.3.0"

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
    ``GherkinStepNeed.captures``. The FALLBACK source (module docstring's
    own "captures-arity fix" note below): used only when no call-site-
    derived ``parameters`` is available for this method."""
    return [
        {
            "index": capture.index,
            "style": capture.style,
            "expression_type": capture.expression_type,
        }
        for capture in need_captures  # type: ignore[attr-defined]
    ]


def _capture_payload_from_parameters(
    parameters: Sequence[JavaParameter],
) -> list[dict[str, object]]:
    """The SAME ``methods`` payload entry's own ``captures`` field, built
    from the call-site-derived ``PageObjectMethodNeed.parameters``
    instead of ``GherkinStepNeed.captures`` (module docstring's own
    "captures-arity fix" -- the PREFERRED source whenever it is available:
    the real argument count the step-def's own call site passes, which can
    genuinely differ from the outer step's total capture count). Reuses
    the SAME JSON shape (``index``/``style``/``expression_type``) the
    Gherkin-capture payload already uses -- one payload key, two possible
    sources, never both at once -- so the model reads the exact same field
    it always has; only ``expression_type`` now carries a real Java type
    string (``"String"``, ``"int"``, ``"Object"``, ...) rather than a
    Cucumber Expression type, which the model resolves identically either
    way (both are self-explanatory type hints)."""
    return [
        {"index": index, "style": "call_site", "expression_type": parameter.java_type}
        for index, parameter in enumerate(parameters)
    ]


class LivePageObjectGenerator:
    """``generate_page_objects`` v1.2.0-backed page-object generator --
    ONE prompt version for every call, single-method or multi-method alike
    (module docstring: the divergence that caused a live-measured defect is
    retired), now also supplying BasePage's real inherited method inventory
    (module docstring's own "v1.1.0 -> v1.2.0" section).

    Parameters
    ----------
    provider:
        An already-constructed, already-validated
        :class:`LLMProvider` (e.g. via ``llm_factory.create_provider`` +
        ``provider.validate_connection()``). This class never selects or
        constructs a provider itself.
    prompt_registry:
        The sealed Layer 3 :class:`PromptRegistry` to resolve
        ``generate_page_objects`` v1.2.0 from. When *None*, the canonical
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
        """Render v1.2.0's own governed template -- a ``methods`` list, one
        entry per requested method (primary first, then every entry in
        ``context.additional_method_needs``, in order), each carrying its
        own caller-chosen ``method_name``. A single-method call renders a
        length-one ``methods`` list -- the same template, the same
        verbatim-naming instruction, no special-casing."""
        method_needs = (
            context.need,
            *(need.need for need in context.additional_method_needs),
        )
        expected_return_types = (
            context.return_type,
            *(need.return_type for need in context.additional_method_needs),
        )
        expected_parameters = (
            context.parameters,
            *(need.parameters for need in context.additional_method_needs),
        )
        methods_payload = [
            {
                "method_name": method_name,
                "action_text": need.text,
                "captures": (
                    _capture_payload_from_parameters(parameters)
                    if parameters is not None
                    else _capture_payload(need.captures)
                ),
                "return_type": return_type,
            }
            for method_name, need, return_type, parameters in zip(
                expected_method_names,
                method_needs,
                expected_return_types,
                expected_parameters,
                strict=True,
            )
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
