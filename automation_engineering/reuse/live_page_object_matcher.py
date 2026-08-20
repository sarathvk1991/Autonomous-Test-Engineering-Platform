"""The live, page-object-scoped :class:`~automation_engineering.reuse.matcher.SemanticMatcher`
implementation -- the counterpart :mod:`.live_matcher`'s own docstring names
and defers ("Only step definitions are matched... page objects and
utilities have no comparable 'does this step match' question"). That
deferral was correct for what :mod:`.live_matcher` itself does (bind a
Gherkin step's own text against another step definition's own pattern) but
incomplete for the platform as a whole: ADR-0044 D4's clarification note
(quoted in full in
:mod:`automation_engineering.generation.page_object_orchestrator`'s own
module docstring) generalizes reuse-safety to page objects and utilities
too, and :func:`automation_engineering.reuse.engine.decide_reuse` already
calls ``matcher.match(method_need.need, catalog)`` for a page-object need
using the SAME Protocol, the SAME ``GherkinStepNeed`` (the originating
step's own text, not the specific method name -- ``method_need.method_name``
is verified separately, STRUCTURALLY, by the COARSE class-compatibility
screen already built in :func:`automation_engineering.reuse.engine.
_check_method_fit` and the PRECISE method-fit discharge already built in
:func:`automation_engineering.generation.method_fit.verify_specific_method_fit`
-- both existed and worked correctly before this module did; the ONLY thing
missing was a live ``SemanticMatcher`` that resolves the COARSE candidate
CLASS in the first place, scoped to ``catalog.page_objects`` rather than
``catalog.step_definitions``. The full chain, only the first arrow below
being this module's own job::

    a step's own text (e.g. "I am on the login page")
        --embed, cosine, THIS module--> best-matching PageObjectAsset
            (coarse, semantic)
        --_check_method_fit (already built)--> class has SOME
            shape-fitting method (coarse, structural)
        --verify_specific_method_fit (already built)--> class has
            THIS SPECIFIC method (precise, structural)

Matching is therefore a HYBRID, by design, not a choice this module makes:
SEMANTIC at the class-selection level (mirrored from :mod:`.live_matcher`,
this module's own only job), STRUCTURAL at the method-verification level
(already built elsewhere, unchanged, untouched by this module).

Mirrors :class:`~.live_matcher.LiveSemanticMatcher` structurally -- same
``SemanticMatcher`` Protocol, same
:class:`~automation_engineering.reuse.embeddings.EmbeddingProvider`/
:func:`~automation_engineering.reuse.embeddings.cosine_similarity`
primitives, same ``prime()``/whole-run-batching discipline (FIX 1),
same "empty catalog short-circuits before any embedding call" contract.
The ONLY things that differ are (1) which catalog slice is read
(``catalog.page_objects``, never ``catalog.step_definitions``) and (2) what
text represents a catalogued asset for embedding -- a
:class:`~automation_engineering.catalog.models.PageObjectAsset` has no
Cucumber-annotation ``pattern`` (:mod:`.live_matcher`'s own
``step_definition_embedding_text`` starts from), so
:func:`page_object_embedding_text` uses ``asset.semantic_tags`` alone --
already the SAME already-recorded, nothing-re-derived catalog data
``step_definition_embedding_text`` uses, just without a raw pattern to
prepend: the scanner (:func:`automation_engineering.catalog.scanner.
_extract_page_object`) already folds the class name's own camel-case words,
every method name's own camel-case words, and any javadoc's own free text
into ``semantic_tags`` at scan time (:mod:`automation_engineering.catalog.
java_source`'s ``semantic_tags_from_identifier``/``semantic_tags_from_text``)
-- the full natural-language surface a page object has to compare a step's
own text against.

Two implementations now exist for this Protocol scoped to page objects:
this one (live, embeddings-backed) and
:class:`~automation_engineering.reuse.matcher.StubSemanticMatcher`
(test/dev scaffolding, asset-kind-agnostic already -- it only ever returns
whatever a test pre-scripts, so it needed no change to serve as a
page-object matcher in tests, and did, before this module existed).
"""

from __future__ import annotations

from collections.abc import Sequence

from automation_engineering.catalog.models import AssetCatalog, PageObjectAsset
from automation_engineering.reuse.embeddings import EmbeddingProvider, cosine_similarity
from automation_engineering.reuse.models import GherkinStepNeed, MatchCandidate


def page_object_embedding_text(asset: PageObjectAsset) -> str:
    """The text embedded for one page-object asset -- its own recorded
    semantic tags (class name plus every method name, camel-case split, and
    any javadoc, already combined at scan time,
    :func:`automation_engineering.catalog.scanner._extract_page_object`).
    Already-recorded catalog data; nothing re-derived here -- the same
    discipline :mod:`.live_matcher`'s own ``step_definition_embedding_text``
    follows for step definitions."""
    return " ".join(asset.semantic_tags)


class LivePageObjectSemanticMatcher:
    """Embeddings-backed :class:`~automation_engineering.reuse.matcher.SemanticMatcher`,
    scoped to ``catalog.page_objects`` -- see this module's own docstring
    for the coarse-semantic/precise-structural split this implementation is
    only the first half of.

    Parameters
    ----------
    embedding_provider:
        An already-constructed :class:`EmbeddingProvider` (e.g.
        :class:`~automation_engineering.reuse.embeddings.GeminiEmbeddingProvider`).
        This class never selects or constructs a provider itself, mirroring
        :class:`~.live_matcher.LiveSemanticMatcher`'s own constructor-
        injection discipline exactly. Passing the SAME provider instance
        this run's step-definition ``LiveSemanticMatcher`` already uses is
        safe and expected (:class:`EmbeddingProvider` is stateless per call;
        this class keeps its own, separate vector cache) -- the two
        matchers never share a cache, since a step-definition's own pattern
        text and a page object's own tag-bag text could otherwise collide
        by coincidence and serve a stale hit across the wrong asset kind.
    """

    def __init__(self, embedding_provider: EmbeddingProvider) -> None:
        self._embedding_provider = embedding_provider
        self._vector_cache: dict[str, tuple[float, ...]] = {}

    def prime(self, needs: Sequence[GherkinStepNeed], catalog: AssetCatalog) -> None:
        """Warm the whole run's vector cache in as few `embed(...)` calls as
        the provider needs, instead of one call per later `match()`. Safe to
        call with an empty `needs`/`catalog.page_objects` (embeds nothing);
        safe to call more than once (only ever embeds texts not already
        cached). Mirrors :meth:`~.live_matcher.LiveSemanticMatcher.prime`
        exactly, scoped to ``catalog.page_objects``."""
        texts = [need.text for need in needs]
        texts.extend(page_object_embedding_text(asset) for asset in catalog.page_objects)
        self._embed_and_cache(texts)

    def match(self, need: GherkinStepNeed, catalog: AssetCatalog) -> tuple[MatchCandidate, ...]:
        assets = catalog.page_objects
        if not assets:
            return ()

        texts = [need.text, *(page_object_embedding_text(asset) for asset in assets)]
        self._embed_and_cache(texts)
        need_vector, *asset_vectors = (self._vector_cache[text] for text in texts)

        scored = [
            MatchCandidate(
                asset_id=asset.asset_id,
                confidence=cosine_similarity(need_vector, asset_vector),
                content_hash=asset.content_hash,
            )
            for asset, asset_vector in zip(assets, asset_vectors, strict=True)
        ]
        scored.sort(key=lambda candidate: candidate.confidence, reverse=True)
        return tuple(scored)

    def _embed_and_cache(self, texts: list[str]) -> None:
        """Embed every text in `texts` not already in the cache, in ONE
        `EmbeddingProvider.embed(...)` call (deduplicated), and cache the
        result. A no-op when every text is already cached. Mirrors
        :meth:`~.live_matcher.LiveSemanticMatcher._embed_and_cache`
        verbatim."""
        missing = list(dict.fromkeys(text for text in texts if text not in self._vector_cache))
        if not missing:
            return
        vectors = self._embedding_provider.embed(missing)
        self._vector_cache.update(zip(missing, vectors, strict=True))


__all__ = ["LivePageObjectSemanticMatcher", "page_object_embedding_text"]
