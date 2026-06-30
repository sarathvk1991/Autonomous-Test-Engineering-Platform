"""NormalizationStatistics — operational telemetry for one normalization run.

:class:`NormalizationStatistics` captures the operational facts of a run — how
long it took, how much work it did — so the subsystem can be measured and
trended.

These metrics are **pure telemetry**.  They describe the run; they carry no
judgement and never influence any consumer's decision (Response Normalization
Contract §3, §10).

Deliberate deviation from ValidationStatistics
----------------------------------------------
The validation statistics record ``rules_passed`` / ``rules_failed`` — a rule
"fails" when it raises an issue.  Normalization has **no pass/fail**: a
responsibility neither passes nor fails, it simply executes and may *record*
observations (facts).  The fact-oriented analogues are therefore
``responsibilities_executed`` and ``observations_recorded``.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import ConfigDict, Field
from pydantic.alias_generators import to_camel

from shared.contracts.base import Schema


class NormalizationStatistics(Schema):
    """Immutable operational telemetry for a single normalization run.

    Field names serialise as ``camelCase`` (``normalizationDurationMs``,
    ``responsibilitiesExecuted``, ``observationsRecorded``, …); Python attributes
    stay ``snake_case``.

    Fields
    ------
    normalization_duration_ms:
        Wall-clock duration of the run, in milliseconds.
    responsibilities_executed:
        How many normalization responsibilities ran.
    observations_recorded:
        How many Normalization Observations were recorded across the run.
    started_at / completed_at:
        Wall-clock start and completion timestamps of the run.
    framework_version:
        The framework implementation version that produced the run.
    normalization_contract_version:
        The version of the normalization semantics in force for the run.
    normalization_id:
        Identity of this normalization run.
    correlation_id:
        Optional trace key stitching this run to its originating analysis and
        downstream consumers.
    metadata:
        Free-form metadata associated with the statistics.  Preserved verbatim.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    normalization_duration_ms: float = Field(ge=0.0)
    responsibilities_executed: int = Field(ge=0)
    observations_recorded: int = Field(ge=0)
    started_at: datetime
    completed_at: datetime
    framework_version: str
    normalization_contract_version: str
    normalization_id: str
    correlation_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
