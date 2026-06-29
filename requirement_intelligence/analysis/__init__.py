"""Requirement Analysis layer.

The single orchestration boundary for AI execution within the platform. See
``docs/architecture/requirement-analysis-service.md`` for the governing spec.

Public surface
--------------
RequirementAnalysisService — the exclusive AI orchestration entry point
AnalysisConfiguration      — the immutable execution-policy contract
AnalysisResult             — the provider-independent result carrier
AnalysisError              — base orchestration exception
AnalysisConfigurationError
PromptGenerationError
ProviderExecutionError
AnalysisExecutionError
"""

from requirement_intelligence.analysis.analysis_configuration import (
    AnalysisConfiguration,
)
from requirement_intelligence.analysis.analysis_exceptions import (
    AnalysisConfigurationError,
    AnalysisError,
    AnalysisExecutionError,
    PromptGenerationError,
    ProviderExecutionError,
)
from requirement_intelligence.analysis.analysis_models import AnalysisResult
from requirement_intelligence.analysis.requirement_analysis_service import (
    RequirementAnalysisService,
)

__all__ = [
    "AnalysisConfiguration",
    "AnalysisConfigurationError",
    "AnalysisError",
    "AnalysisExecutionError",
    "AnalysisResult",
    "PromptGenerationError",
    "ProviderExecutionError",
    "RequirementAnalysisService",
]
