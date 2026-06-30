"""ValidationStatistics — operational telemetry for one validation run.

:class:`ValidationStatistics` is the conceptual realisation of the Validation
Statistics Model in ``docs/architecture/validation-canonical-models.md`` (§5).
It captures the operational facts of a run — how long it took, how much work it
did — so the gate itself can be measured and trended.

These metrics are **pure telemetry**.  They describe the run; they **never
influence the verdict**.  No downstream decision may be taken on the basis of a
statistic.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import ConfigDict, Field
from pydantic.alias_generators import to_camel

from shared.contracts.base import Schema


class ValidationStatistics(Schema):
    """Immutable operational telemetry for a single validation run.

    Field names serialise as ``camelCase`` (``validationDurationMs``,
    ``rulesExecuted``, ``validatorVersion``, …); Python attributes stay
    ``snake_case``.

    Fields
    ------
    validation_duration_ms:
        Wall-clock duration of the run, in milliseconds.
    rules_executed:
        How many rules ran.
    rules_passed:
        How many rules observed no issue.
    rules_failed:
        How many rules raised at least one issue.
    started_at / completed_at:
        Wall-clock start and completion timestamps of the run.
    validator_version:
        The validator implementation version that produced the run.
    validation_contract_version:
        The version of the validation semantics in force for the run.
    execution_id:
        Identifier stitching this run to its originating analysis and downstream.
    metadata:
        Free-form metadata associated with the statistics.  Preserved verbatim.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    validation_duration_ms: float = Field(ge=0.0)
    rules_executed: int = Field(ge=0)
    rules_passed: int = Field(ge=0)
    rules_failed: int = Field(ge=0)
    started_at: datetime
    completed_at: datetime
    validator_version: str
    validation_contract_version: str
    execution_id: str
    metadata: dict[str, Any] = Field(default_factory=dict)
