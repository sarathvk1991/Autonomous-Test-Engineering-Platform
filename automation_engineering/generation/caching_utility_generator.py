"""ADR-0050's artifact-generation cache, extended to utilities -- the FIFTH
and FINAL generator this cache covers, closing the "one remaining generator"
gap every prior increment's own Consequences section named as the next
trigger. Utility generation carries a real, threaded
:class:`~requirement_intelligence.llm.generation_identity.GenerationIdentity`
as of the immediately preceding task (the twice-flagged identity gap, closed
additively on :class:`~automation_engineering.generation.models.
GeneratedUtility`) -- the prerequisite this cache increment needed and now
has.

:class:`CachingUtilityGenerator` satisfies
:class:`~automation_engineering.generation.utility_generator.UtilityGenerator`
unchanged -- a peer of ``LiveUtilityGenerator``/``StubUtilityGenerator``
behind the same seam, exactly the discipline
:mod:`~automation_engineering.generation.caching_page_object_generator`
already established for its own generator. The one downstream consumer
(``utility_orchestrator.py``'s ``orchestrate_utility_method``) requires ZERO
changes to consume a wrapped generator here -- it already calls
``generator.generate(context)`` and reads a generator's identity via
``getattr(generator, "last_identity", None)``, never a concrete class, the
same blast-radius claim proven by construction for the four prior
generators.

THE BIND/CACHE COMPOSITION (utility generation's own reuse mechanism,
mirroring page-object's, not the simpler always-generate shape the first
three generators had): utility reuse-decide
(:func:`automation_engineering.generation.utility_orchestrator.
orchestrate_utility_method`, via :func:`automation_engineering.reuse.engine.
decide_reuse`) can already BIND a need to an existing tracked ``UtilityAsset``
-- reusing an ASSET, no generation call at all, producing a
``BoundUtilityMethod`` with no ``generation_identity`` field at all (a bind
is never a generation). This decorator only ever wraps the GENERATE side of
that decision (``NoMatch`` -> the orchestrator's own ``generator.
generate(context)`` call) -- a bind never reaches this class's own
:meth:`generate`, so there is no double-counting and no conflict between the
two reuse mechanisms: bind answers "does an existing ASSET already satisfy
this need" (upstream, per-need, asset-level); this cache answers "did we
already GENERATE this exact thing before" (here, per-call, generation-level).
Orthogonal, composed simply by ordering -- ``orchestrate_utility_method``'s
own existing NoMatch-then-generate structure is untouched by this module.
"""

from __future__ import annotations

from automation_engineering.errors import TransportFailureError
from automation_engineering.generation.live_utility_generator import build_utility_payload
from automation_engineering.generation.utility_generator import (
    UtilityGenerationContext,
    UtilityGenerator,
)
from requirement_intelligence.llm.generation_cache import (
    GenerationCacheEntry,
    GenerationCacheStore,
    compute_cache_key,
)
from requirement_intelligence.llm.generation_identity import GenerationIdentity
from requirement_intelligence.llm.token_usage import TokenUsageTracker


class GenerationCacheIdentityMismatchError(TransportFailureError):
    """Raised when a MISS's real, post-call identity does not match the
    ``static_identity`` the caller supplied at construction time.

    Identical safety check, identical rationale, as
    :class:`~automation_engineering.generation.
    caching_page_object_generator.GenerationCacheIdentityMismatchError`
    -- a separate class (not reused) only because it subclasses
    :class:`TransportFailureError` for the SAME reason that one does: an
    existing per-need catch site (``automation_engineering/stage/runner.py``)
    escalates it exactly like any other generation-boundary failure, without
    a new except-clause, and a shared base class already guarantees that.
    """


class CachingUtilityGenerator:
    """Wraps a :class:`UtilityGenerator` with ADR-0050's artifact-level
    generation cache. Mirrors
    :class:`~automation_engineering.generation.
    caching_page_object_generator.CachingPageObjectGenerator` exactly --
    same store, same key function, same hit/miss/identity-mismatch
    discipline, same ``record_cache_hit`` instrumentation. Only the payload
    function (:func:`~automation_engineering.generation.
    live_utility_generator.build_utility_payload`) and the label
    (``class_name`` rather than ``step_text``) differ, because they are the
    two things that are legitimately different between a page-object and a
    utility generation -- not because the caching mechanism itself changed.

    Parameters
    ----------
    inner:
        The live (or any) :class:`UtilityGenerator` this decorator wraps.
        On a MISS, delegated to unchanged. If it exposes its own
        ``last_identity`` property (``LiveUtilityGenerator`` does), it is
        compared against ``static_identity`` after every MISS.
    store:
        The on-disk cache (:class:`~requirement_intelligence.llm.
        generation_cache.GenerationCacheStore`) entries are read from and
        written to -- the SAME store instance the step-def/feature-content/
        test-data/page-object caching generators already use is safe to
        share (the key is a sha256 over identity+payload, so entries from
        different generators never collide by construction: a different
        ``prompt_id`` alone already changes every key).
    static_identity:
        ``inner``'s :class:`GenerationIdentity`, known WITHOUT calling the
        LLM -- resolve via :func:`~automation_engineering.generation.
        live_utility_generator.resolve_utility_identity`.
    usage_recorder:
        Optional. A HIT records a cache hit against ``call_type``. A MISS
        records nothing here -- ``inner`` is expected to be constructed with
        the SAME tracker for its own normal token-usage recording.
    call_type:
        The token-usage call-type key a HIT is recorded under. Defaults to
        ``LiveUtilityGenerator``'s own ``CALL_TYPE`` (``"utility_generation"``).
    """

    def __init__(
        self,
        inner: UtilityGenerator,
        store: GenerationCacheStore,
        static_identity: GenerationIdentity,
        *,
        usage_recorder: TokenUsageTracker | None = None,
        call_type: str = "utility_generation",
    ) -> None:
        self._inner = inner
        self._store = store
        self._static_identity = static_identity
        self._usage_recorder = usage_recorder
        self._call_type = call_type
        self._last_identity: GenerationIdentity | None = None

    @property
    def last_identity(self) -> GenerationIdentity | None:
        """The identity of the most recent :meth:`generate` call -- the
        STORED identity on a HIT, ``inner``'s own real identity on a MISS.
        ``None`` until the first call completes."""
        return self._last_identity

    def generate(self, context: UtilityGenerationContext) -> str:
        """Return generated Java utility source for ``context`` -- from the
        cache on a HIT (no LLM call), from ``inner`` on a MISS (the LLM call
        happens exactly as it would without this wrapper).

        Raises
        ------
        GenerationCacheIdentityMismatchError
            If a MISS's real identity does not match ``static_identity``
            (the pre-call assumption the key was computed from).
        """
        payload = build_utility_payload(context)
        key = compute_cache_key(self._static_identity, payload)

        cached = self._store.get(key)
        if cached is not None:
            self._last_identity = cached.identity
            if self._usage_recorder is not None:
                self._usage_recorder.record_cache_hit(self._call_type)
            return cached.generated_text

        generated_text = self._inner.generate(context)

        actual_identity = getattr(self._inner, "last_identity", None)
        if actual_identity is not None and actual_identity != self._static_identity:
            raise GenerationCacheIdentityMismatchError(
                f"class_name={context.class_name!r}: the wrapped generator's real "
                f"identity ({actual_identity!r}) does not match the identity this "
                f"decorator was constructed with ({self._static_identity!r}) -- the "
                "cache key was computed from the wrong identity; refusing to store "
                "under it rather than risk a future silent wrong hit."
            )
        identity_to_store = (
            actual_identity if actual_identity is not None else self._static_identity
        )

        self._store.put(
            key,
            GenerationCacheEntry(
                generated_text=generated_text,
                identity=identity_to_store,
                label={"class_name": context.class_name},
            ),
        )
        self._last_identity = identity_to_store
        return generated_text


__all__ = ["CachingUtilityGenerator", "GenerationCacheIdentityMismatchError"]
