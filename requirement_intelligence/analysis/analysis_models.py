"""Analysis data model — provider-independent result of one AI analysis.

:class:`AnalysisResult` is the conceptual *carrier* described in
``docs/architecture/requirement-analysis-service.md``: it bundles the raw AI
response together with the execution metadata needed to trace and govern that
response.  It is **not** responsible for validating, interpreting, or judging the
response — it only carries execution information forward to the validation layer.

The existing :class:`~requirement_intelligence.llm.llm_models.LLMResponse` is
reused verbatim; it is never duplicated here.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import ConfigDict, Field
from pydantic.alias_generators import to_camel

from requirement_intelligence.llm.llm_models import LLMResponse
from shared.contracts.base import Schema
from shared.enums.base import ProviderType


class AnalysisResult(Schema):
    """The result of a single AI analysis execution.

    Field names serialise as ``camelCase`` (``analysisId``, ``executionId``, …);
    Python attributes stay ``snake_case``.  The model is immutable and strictly
    validated (inherited from :class:`~shared.contracts.base.Schema`).

    Fields
    ------
    analysis_id:
        Unique identity of the whole analysis operation.
    execution_id:
        Unique identity of the specific AI invocation.
    source_consolidated_id:
        Identifier of the consolidated artifact that was analysed.
    prompt_version:
        Version of the prompt contract that produced the request.
    reasoning_contract_version:
        Version of the AI Reasoning Contract in force for this execution.
    provider:
        The provider that executed the request (enum; serialises to its value).
    model:
        The specific model identity used for generation.
    started_at / completed_at:
        Wall-clock start and completion timestamps of the invocation.
    duration_ms:
        Elapsed time from dispatch to response receipt, in milliseconds.
    llm_response:
        The raw, un-validated provider-agnostic response, carried as-is.
    metadata:
        Execution metadata propagated through the orchestration.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    analysis_id: str
    execution_id: str
    source_consolidated_id: str
    prompt_version: str
    reasoning_contract_version: str
    provider: ProviderType
    model: str
    started_at: datetime
    completed_at: datetime
    duration_ms: float
    llm_response: LLMResponse
    metadata: dict[str, Any] = Field(default_factory=dict)
