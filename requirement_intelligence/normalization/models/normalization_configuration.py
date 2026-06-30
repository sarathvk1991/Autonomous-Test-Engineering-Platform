"""NormalizationConfiguration — the execution policy of a normalization run.

:class:`NormalizationConfiguration` declares the *behaviour* of a normalization
run — what observability is captured and which contract version governs.  It
influences **execution**; it **never influences normalization semantics**, and
it can never make normalization repair, interpret, or judge anything (Response
Normalization Contract §3, §4).

Deliberate deviation from ValidationConfiguration
-------------------------------------------------
The validation configuration carries ``enabled_layers`` and ``minimum_severity``.
Normalization has **neither**:

* there are **no layers** in normalization — responsibilities execute in
  registration order (see the framework README), so there is nothing to
  enable/disable by layer; and
* there is **no severity** in normalization — observations are un-judged facts
  (contract §10), so there is no severity threshold to configure.

What remains is the fact-oriented policy: whether to collect statistics,
observations, and metadata.
"""

from __future__ import annotations

from typing import Any

from pydantic import ConfigDict, Field
from pydantic.alias_generators import to_camel

from requirement_intelligence.normalization.models.normalization_framework_metadata import (
    NORMALIZATION_CONTRACT_VERSION,
)
from shared.contracts.base import Schema


class NormalizationConfiguration(Schema):
    """Immutable execution policy for a normalization run.

    Field names serialise as ``camelCase`` (``normalizationContractVersion``,
    ``collectStatistics``, ``collectObservations``, …); Python attributes stay
    ``snake_case``.  Every field has a default, so a fully-defaulted
    configuration (``NormalizationConfiguration()``) is valid and represents
    "collect everything".

    Fields
    ------
    normalization_contract_version:
        The version of normalization semantics the run must honour.  Defaults to
        the framework's current contract version.
    collect_statistics:
        Whether operational telemetry is captured for the run.  Defaults to True.
    collect_observations:
        Whether Normalization Observations are captured for the run.  Defaults to
        True.  Affects observability only — never whether structure is recovered.
    collect_metadata:
        Whether free-form metadata is captured for the run.  Defaults to True.
    future_extensions:
        Reserved hook for forthcoming configuration without a breaking change.
    metadata:
        Free-form metadata associated with the configuration.  Preserved verbatim.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    normalization_contract_version: str = NORMALIZATION_CONTRACT_VERSION
    collect_statistics: bool = True
    collect_observations: bool = True
    collect_metadata: bool = True
    future_extensions: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
