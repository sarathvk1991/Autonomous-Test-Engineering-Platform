"""Layer 3's own shared transport-failure taxonomy, at the package root
because two independent seams need it -- the embedding boundary
(:mod:`.reuse.embeddings`, the MATCH call) and the four live generators
(:mod:`.generation.live_step_definition_generator`,
`.live_page_object_generator`, `.live_utility_generator`,
`.live_test_data_generator`, the GENERATE calls) -- and neither is a natural
subpackage of the other (mirrors :mod:`feature_engineering.generation.errors`'s
own role for Layer 2, generalized here to a package-level home since Layer 3
has two boundaries needing it, not one).

Raised when a MATCH or GENERATE call fails for a reason unrelated to the
content it returned -- a provider exception, a quota/rate-limit rejection, a
timeout, or a malformed/empty response at the boundary itself, before there
is any generated text or embedding vector to act on at all. Distinct from a
genuine reuse-engine escalation (:class:`~automation_engineering.reuse.models.Escalation`,
a deterministic ADR-0044 D4 judgement) or a content-shaped failure
(e.g. :class:`~automation_engineering.generation.test_data_orchestrator.TestDataBoundaryError`):
those mean the call DID return something, and that something failed a real
check. This one means no usable content/vector was returned, for a reason
that has nothing to do with what any content would have said.

A concrete live implementation's own exception (`EmbeddingCallError`,
`LiveGenerationError`) subclasses this rather than replacing it, so a caller
outside those modules -- `automation_engineering.stage.runner` -- can catch
transport failures once, at the stage's own per-need/per-specification
boundary, without importing any specific provider-backed implementation.
"""

from __future__ import annotations


class TransportFailureError(Exception):
    """A MATCH or GENERATE call failed at the transport boundary itself --
    per-need/per-specification recoverable, never stage-fatal on its own."""


__all__ = ["TransportFailureError"]
