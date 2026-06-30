"""NormalizationResult — the aggregate root and single output of the framework.

:class:`NormalizationResult` is the single artifact a
:class:`~requirement_intelligence.normalization.framework.normalization_pipeline.NormalizationPipeline`
run produces.  It assembles the configuration that governed the run, the
framework provenance, the operational statistics, the recorded observations, and
— once it exists — the canonical ``ParsedResponse``.

It is **information only** and **immutable**: assembled once, never altered.

Facts, not judgments
--------------------
Unlike the validation subsystem's ``ValidationResult``, a NormalizationResult
carries **no verdict, no summary, and no severity counts**.  Normalization
produces *facts*, not *judgments* (Response Normalization Contract §10); there is
nothing to "summarise into a verdict".  This is a deliberate deviation from the
Validation Framework (see the framework README).

The ParsedResponse placeholder
-------------------------------
``parsed_response`` is the **architecture-approved placeholder** for the
``ParsedResponse`` Core Canonical Model, which is implemented by a **separate**
task (it is *not* implemented here).  The field exists now — typed ``Any | None``
and defaulting to ``None`` — so that:

* the result's shape and public API are **stable today**, and
* when ``ParsedResponse`` lands, only the *type annotation* changes
  (``Any | None`` → ``ParsedResponse | None``); no field is added, renamed, or
  moved, so no consumer breaks.

The Phase-1 framework never populates this field — producing a ``ParsedResponse``
is the future ``ResponseNormalizer``'s responsibility, not the framework's.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import ConfigDict, Field
from pydantic.alias_generators import to_camel

from requirement_intelligence.normalization.models.normalization_configuration import (
    NormalizationConfiguration,
)
from requirement_intelligence.normalization.models.normalization_framework_metadata import (
    NormalizationFrameworkMetadata,
)
from requirement_intelligence.normalization.models.normalization_observation import (
    NormalizationObservation,
)
from requirement_intelligence.normalization.models.normalization_statistics import (
    NormalizationStatistics,
)
from shared.contracts.base import Schema


class NormalizationResult(Schema):
    """Immutable aggregate root — the single output of the Normalization Framework.

    Field names serialise as ``camelCase`` (``normalizationId``,
    ``normalizationStatistics``, ``parsedResponse``, …); Python attributes stay
    ``snake_case``.

    Fields
    ------
    normalization_id:
        Unique identity of this normalization run.
    correlation_id:
        Optional trace key stitching this run to its originating analysis and
        downstream consumers.
    normalization_configuration:
        The configuration that governed the run (referenced).
    normalization_framework_metadata:
        Provenance of the framework that produced the result (referenced).
    normalization_statistics:
        The operational telemetry of the run (owned).
    observations:
        The complete collection of Normalization Observations recorded during the
        run (owned).  An immutable tuple; an empty tuple is a valid result.
    parsed_response:
        **Placeholder** for the future ``ParsedResponse`` Core Canonical Model.
        Always ``None`` in the Phase-1 framework (the framework produces no
        ``ParsedResponse``).  Typed ``Any`` so the API is stable until the model
        lands; see the module docstring.
    started_at / completed_at:
        Wall-clock start and completion timestamps of the normalization run.
    metadata:
        Free-form metadata associated with the result.  Preserved verbatim.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    normalization_id: str
    correlation_id: str | None = None

    # Referenced.
    normalization_configuration: NormalizationConfiguration
    normalization_framework_metadata: NormalizationFrameworkMetadata

    # Owned.
    normalization_statistics: NormalizationStatistics
    observations: tuple[NormalizationObservation, ...] = Field(default_factory=tuple)

    # Placeholder for the future ParsedResponse Core Canonical Model.
    parsed_response: Any | None = None

    started_at: datetime
    completed_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)
