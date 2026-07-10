"""The governed runtime template contract.

A governed prompt template is a single versioned text file under
``prompts/versions/``.  Its **structure** — not merely its bytes — is part of
Prompt Governance, because the runtime depends on that structure to reconstruct
the system prompt and the user prompt that the execution package records
separately.

The contract
------------
A conforming template is::

    <system prompt>            ← exactly one paragraph, no blank line inside
                               ← exactly one split point (the first blank line)
    <user prompt>              ← contains exactly one {artifact_context}

Formally:

1. There is **exactly one split point**: the *first* blank line (``"\\n\\n"``).
   Everything before it is the system prompt; everything after it is the user
   template.  Uniqueness holds by construction — the split is performed with
   ``maxsplit=1``, so later blank lines are ordinary user-prompt paragraph
   breaks and never additional split points.
2. The system prompt section is **exactly one section** and is non-empty.
3. The user template is **exactly one section** and is non-empty.
4. The user template contains the artifact placeholder **exactly once**.
5. A trailing newline is a text-file convention, not prompt wording, and is not
   part of either section.

Limit of structural enforcement
------------------------------
Because the split point is positional, a template *authored* with a
multi-paragraph system prompt is indistinguishable from a conforming one: its
second paragraph would silently become the head of the user prompt.  No
structural check can detect this, so "the system prompt is one paragraph" is a
**review-time governance rule**, not a runtime-enforceable invariant.  Every
other clause above is enforced here.

Ownership
---------
This module owns the contract.  It is the **only** place the split rule and the
placeholder token are defined, and the only place they are enforced.  The
runtime builder consumes :func:`parse_governed_template`; it neither restates
nor re-validates the rule.  A template that violates the contract cannot be
used to construct a builder, so the failure surfaces at composition time rather
than mid-execution.

Substitution
------------
:func:`render_user_prompt` substitutes with :meth:`str.replace`, never
:meth:`str.format`.  Governed templates embed a literal JSON contract, so their
braces are **not** format fields; ``str.format`` would raise ``KeyError`` on the
first JSON key.
"""

from __future__ import annotations

from dataclasses import dataclass

from requirement_intelligence.prompts.framework.prompt_exceptions import (
    PromptTemplateContractError,
)

#: The single placeholder a governed template exposes for artifact injection.
ARTIFACT_CONTEXT_PLACEHOLDER = "{artifact_context}"

#: The blank line that separates the system prompt from the user template.
SECTION_SEPARATOR = "\n\n"


@dataclass(frozen=True)
class GovernedTemplate:
    """A governed template parsed into its two runtime sections.

    Fields
    ------
    system_prompt:
        The role-establishing section — the template's first paragraph.
    user_template:
        The remainder, containing exactly one
        :data:`ARTIFACT_CONTEXT_PLACEHOLDER`.
    """

    system_prompt: str
    user_template: str

    def render_user_prompt(self, artifact_context: str) -> str:
        """Return the user prompt with *artifact_context* substituted in."""
        return self.user_template.replace(ARTIFACT_CONTEXT_PLACEHOLDER, artifact_context)


def parse_governed_template(content: str) -> GovernedTemplate:
    """Parse and validate *content* against the governed template contract.

    Parameters
    ----------
    content:
        The raw template text, as loaded and SHA-verified by
        :class:`~requirement_intelligence.prompts.framework.prompt_loader.PromptLoader`.

    Raises
    ------
    PromptTemplateContractError
        If the template has no split point, an empty system prompt, an empty
        user template, or a number of artifact placeholders other than exactly
        one.
    """
    normalized = content.rstrip("\n")

    parts = normalized.split(SECTION_SEPARATOR, 1)
    if len(parts) != 2:
        raise PromptTemplateContractError(
            "Governed template has no split point: expected a system-prompt "
            "paragraph followed by a blank line and a user-prompt body."
        )

    system_prompt, user_template = parts

    if not system_prompt.strip():
        raise PromptTemplateContractError("Governed template has an empty system prompt section.")
    if not user_template.strip():
        raise PromptTemplateContractError("Governed template has an empty user prompt section.")

    occurrences = user_template.count(ARTIFACT_CONTEXT_PLACEHOLDER)
    if occurrences != 1:
        raise PromptTemplateContractError(
            f"Governed template must contain exactly one "
            f"{ARTIFACT_CONTEXT_PLACEHOLDER!r} placeholder; found {occurrences}."
        )

    return GovernedTemplate(system_prompt=system_prompt, user_template=user_template)
