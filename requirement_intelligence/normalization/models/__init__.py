"""Normalization framework information models.

The implementation-independent information model for the Response Normalization
subsystem, as governed by
``docs/architecture/response-normalization-contract.md``.

Models
------
* :class:`NormalizationObservation` — one recorded, un-judged fact (§8, §10).
* :class:`NormalizationConfiguration` — the execution policy of a run (§3).
* :class:`NormalizationStatistics` — operational telemetry for one run.
* :class:`NormalizationFrameworkMetadata` — provenance of the producing framework.
* :class:`NormalizationResult` — the aggregate root and single framework output,
  carrying the architecture-approved ``ParsedResponse`` placeholder.

These models carry **information only**: no normalization behaviour, no parsing,
no validation, no provider behaviour, no persistence, no I/O.  Per the frozen
Normalization-Validation boundary (contract §10) they carry **no verdict, no
severity, and no summary** — normalization produces facts, not judgments.

The ``ParsedResponse`` Core Canonical Model is **not** defined here; it is a
separate task.  ``NormalizationResult`` carries a typed placeholder for it.
"""

from __future__ import annotations

from requirement_intelligence.normalization.models.normalization_configuration import (
    NormalizationConfiguration,
)
from requirement_intelligence.normalization.models.normalization_framework_metadata import (
    FRAMEWORK_VERSION,
    NORMALIZATION_CONTRACT_VERSION,
    PIPELINE_VERSION,
    REGISTRY_VERSION,
    RESPONSIBILITY_CATALOG_VERSION,
    NormalizationFrameworkMetadata,
)
from requirement_intelligence.normalization.models.normalization_observation import (
    OBSERVATION_DUPLICATE_IDENTIFIER,
    OBSERVATION_ENCODING,
    OBSERVATION_MALFORMED_REPRESENTATION,
    NormalizationObservation,
)
from requirement_intelligence.normalization.models.normalization_result import (
    NormalizationResult,
)
from requirement_intelligence.normalization.models.normalization_statistics import (
    NormalizationStatistics,
)

__all__ = [
    "FRAMEWORK_VERSION",
    "NORMALIZATION_CONTRACT_VERSION",
    "OBSERVATION_DUPLICATE_IDENTIFIER",
    "OBSERVATION_ENCODING",
    "OBSERVATION_MALFORMED_REPRESENTATION",
    "PIPELINE_VERSION",
    "REGISTRY_VERSION",
    "RESPONSIBILITY_CATALOG_VERSION",
    "NormalizationConfiguration",
    "NormalizationFrameworkMetadata",
    "NormalizationObservation",
    "NormalizationResult",
    "NormalizationStatistics",
]
