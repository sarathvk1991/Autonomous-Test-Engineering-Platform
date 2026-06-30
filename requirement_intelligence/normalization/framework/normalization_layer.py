"""NormalizationLayer — the framework seat of the Response Normalization subsystem.

:class:`NormalizationLayer` is the thin orchestration facade that composes a
:class:`~requirement_intelligence.normalization.framework.normalization_registry.NormalizationRegistry`
with a
:class:`~requirement_intelligence.normalization.framework.normalization_pipeline.NormalizationPipeline`
and exposes a single :meth:`normalize` entry point.  It is the structural seat of
the *permanent subsystem* the architecture calls the **Response Normalization
Layer** (Response Normalization Contract §4).

What it is — and is NOT
-----------------------
This class is **pure framework orchestration**.  It contains:

* **no normalization logic** — it never recovers structure, determines an
  outcome, or records observations;
* **no parsing**, **no provider interaction**, **no format knowledge**;
* **no ``ParsedResponse`` creation** — it produces only the framework's
  ``NormalizationResult`` (whose ``parsed_response`` placeholder stays ``None``);
* **no registered responsibilities** — callers register their own.

It is therefore **NOT** the ``ResponseNormalizer``.  The ``ResponseNormalizer``
is a **future** concrete component that will *use* this framework: it will
register the real ``NORMALIZATION-0001…0005`` responsibilities, own the
provider-/format-facing concerns, and produce a real ``ParsedResponse``.  This
facade is the stable seat it will build upon — exactly as the validation
framework's pipeline is the seat the ``ResponseValidator`` builds upon.

Why a facade in addition to the pipeline
----------------------------------------
The pipeline is the *execution* component (it runs responsibilities).  The layer
is the *subsystem boundary*: it owns registry composition and the build →
execute lifecycle as one cohesive entry point, so that future callers (the
``ResponseNormalizer``) — and tests — interact with a single object rather than
wiring a registry and a pipeline by hand each time.
"""

from __future__ import annotations

from typing import Any

from requirement_intelligence.normalization.framework.normalization_pipeline import (
    NormalizationPipeline,
)
from requirement_intelligence.normalization.framework.normalization_registry import (
    NormalizationRegistry,
)
from requirement_intelligence.normalization.framework.normalization_responsibility import (
    NormalizationResponsibility,
)
from requirement_intelligence.normalization.models import (
    NormalizationConfiguration,
    NormalizationResult,
)


class NormalizationLayer:
    """Framework facade composing a registry and pipeline into one subsystem seat.

    Usage
    -----
    .. code-block:: python

        layer = NormalizationLayer()
        layer.register(MyResponsibility())
        result = layer.normalize(source)

    Or from a pre-populated registry:

    .. code-block:: python

        layer = NormalizationLayer(registry)
        result = layer.normalize(source)

    Lifecycle
    ---------
    The layer is **OPEN** for registration until it is *built*.  Building
    constructs the pipeline (which seals the registry); the first
    :meth:`normalize` call builds lazily if :meth:`build` was not called
    explicitly.  After building, :meth:`register` raises — the responsibility set
    is fixed for the layer's lifetime, which is what makes a run reproducible.
    """

    def __init__(self, registry: NormalizationRegistry | None = None) -> None:
        """Construct the facade.

        Parameters
        ----------
        registry:
            An optional pre-populated :class:`NormalizationRegistry`.  When
            omitted, a fresh empty registry is created and responsibilities may be
            added via :meth:`register`.
        """
        self._registry = registry if registry is not None else NormalizationRegistry()
        self._pipeline: NormalizationPipeline | None = None

    # ------------------------------------------------------------------
    # Composition
    # ------------------------------------------------------------------

    @property
    def registry(self) -> NormalizationRegistry:
        """The registry this layer composes."""
        return self._registry

    @property
    def is_built(self) -> bool:
        """``True`` once the pipeline has been built (and the registry sealed)."""
        return self._pipeline is not None

    def register(self, responsibility: NormalizationResponsibility) -> None:
        """Register a responsibility before the layer is built.

        A convenience that delegates to the underlying registry.

        Raises
        ------
        NormalizationRegistryError
            If the layer has been built (the registry is sealed) or the
            ``responsibility_id`` is already registered.
        """
        self._registry.register(responsibility)

    def build(self) -> NormalizationPipeline:
        """Build (or return) the pipeline, sealing the registry.

        Idempotent: the first call constructs the pipeline; subsequent calls
        return the same instance.

        Returns
        -------
        NormalizationPipeline
            The pipeline that executes this layer's responsibilities.
        """
        if self._pipeline is None:
            self._pipeline = NormalizationPipeline(self._registry)
        return self._pipeline

    @property
    def pipeline(self) -> NormalizationPipeline:
        """The pipeline, building it lazily on first access."""
        return self.build()

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def normalize(
        self,
        source: Any,
        configuration: NormalizationConfiguration | None = None,
        *,
        correlation_id: str | None = None,
    ) -> NormalizationResult:
        """Run the subsystem over *source* and return the ``NormalizationResult``.

        Builds the pipeline lazily if needed, then delegates to
        :meth:`NormalizationPipeline.run`.  This facade adds **no** behaviour of
        its own beyond composition — it never parses, judges, or creates a
        ``ParsedResponse``.

        Parameters
        ----------
        source:
            The normalization input (an ``LLMResponse`` in production).
        configuration:
            Optional execution policy; a fully-defaulted one is used when omitted.
        correlation_id:
            Optional trace key carried onto the result.

        Returns
        -------
        NormalizationResult
            The single, immutable framework output.
        """
        return self.build().run(
            source, configuration, correlation_id=correlation_id
        )
