"""ADR-0050's artifact-generation cache, extended to page objects (this
build's own increment -- the fourth generator covered, after step-def,
feature-content, and test-data; utility remains this platform's own
carried-forward, honestly deferred scope, the same deferral every prior
page-object build in this generation package has already followed).

:class:`CachingPageObjectGenerator` satisfies
:class:`~automation_engineering.generation.page_object_generator.
PageObjectGenerator` unchanged -- a peer of ``LivePageObjectGenerator``/
``StubPageObjectGenerator`` behind the same seam, exactly the discipline
:mod:`~automation_engineering.generation.caching_step_definition_generator`
already established. Every downstream consumer
(``page_object_orchestrator.py``'s ``orchestrate_page_object_method``/
``orchestrate_page_object_class``, both of which already read a generator's
identity via ``getattr(generator, "last_identity", None)``, never a concrete
class) requires ZERO changes to consume a wrapped generator here, the same
blast-radius claim proven by construction for step definitions.

THE BIND/CACHE COMPOSITION (page-object generation's own, additional reuse
mechanism the three prior caching generators never had to compose with):
page-object reuse-decide (:func:`automation_engineering.reuse.engine.
decide_reuse`, called from ``page_object_orchestrator.py`` BEFORE any
generation) can already BIND a need to an existing tracked ``PageObjectAsset``
-- reusing an ASSET, no generation call at all. This decorator only ever
wraps the GENERATE side of that decision (``NoMatch`` -> the orchestrator's
own ``generator.generate(context)`` call) -- a bind never reaches this
class's own :meth:`generate`, so there is no double-counting and no
conflict between the two reuse mechanisms: bind answers "does an existing
ASSET already satisfy this need" (upstream, per-need, asset-level); this
cache answers "did we already GENERATE this exact thing before" (here,
per-call, generation-level). Orthogonal, composed simply by ordering --
the orchestrator's own existing NoMatch-then-generate structure is
untouched by this module.
"""

from __future__ import annotations

from automation_engineering.errors import TransportFailureError
from automation_engineering.generation.live_page_object_generator import (
    build_page_object_payload,
)
from automation_engineering.generation.page_object_generator import (
    PageObjectGenerationContext,
    PageObjectGenerator,
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
    caching_step_definition_generator.GenerationCacheIdentityMismatchError`
    -- a separate class (not reused) only because it subclasses
    :class:`TransportFailureError` for the SAME reason that one does: an
    existing per-need catch site (``automation_engineering/stage/runner.py``)
    escalates it exactly like any other generation-boundary failure, without
    a new except-clause, and a shared base class already guarantees that.
    """


class CachingPageObjectGenerator:
    """Wraps a :class:`PageObjectGenerator` with ADR-0050's artifact-level
    generation cache. Mirrors
    :class:`~automation_engineering.generation.
    caching_step_definition_generator.CachingStepDefinitionGenerator`
    exactly -- same store, same key function, same hit/miss/identity-mismatch
    discipline, same ``record_cache_hit`` instrumentation. Only the payload
    function (:func:`~automation_engineering.generation.
    live_page_object_generator.build_page_object_payload`) and the label
    (``class_name`` rather than ``step_text``) differ, because they are the
    two things that are legitimately different between a step-definition and
    a page-object generation -- not because the caching mechanism itself
    changed.

    Parameters
    ----------
    inner:
        The live (or any) :class:`PageObjectGenerator` this decorator wraps.
        On a MISS, delegated to unchanged. If it exposes its own
        ``last_identity`` property (``LivePageObjectGenerator`` does), it is
        compared against ``static_identity`` after every MISS.
    store:
        The on-disk cache (:class:`~requirement_intelligence.llm.
        generation_cache.GenerationCacheStore`) entries are read from and
        written to -- the SAME store instance the step-def/feature-content/
        test-data caching generators already use is safe to share (the key
        is a sha256 over identity+payload, so entries from different
        generators never collide by construction: a different
        ``prompt_id`` alone already changes every key).
    static_identity:
        ``inner``'s :class:`GenerationIdentity`, known WITHOUT calling the
        LLM -- resolve via :func:`~automation_engineering.generation.
        live_page_object_generator.resolve_page_object_identity`.
    usage_recorder:
        Optional. A HIT records a cache hit against ``call_type``. A MISS
        records nothing here -- ``inner`` is expected to be constructed with
        the SAME tracker for its own normal token-usage recording.
    call_type:
        The token-usage call-type key a HIT is recorded under. Defaults to
        ``LivePageObjectGenerator``'s own ``CALL_TYPE``
        (``"page_object_generation"``).
    """

    def __init__(
        self,
        inner: PageObjectGenerator,
        store: GenerationCacheStore,
        static_identity: GenerationIdentity,
        *,
        usage_recorder: TokenUsageTracker | None = None,
        call_type: str = "page_object_generation",
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

    def generate(self, context: PageObjectGenerationContext) -> str:
        """Return generated Java page-object source for ``context`` -- from
        the cache on a HIT (no LLM call), from ``inner`` on a MISS (the LLM
        call happens exactly as it would without this wrapper).

        Raises
        ------
        GenerationCacheIdentityMismatchError
            If a MISS's real identity does not match ``static_identity``
            (the pre-call assumption the key was computed from).
        """
        payload = build_page_object_payload(context)
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


__all__ = ["CachingPageObjectGenerator", "GenerationCacheIdentityMismatchError"]
