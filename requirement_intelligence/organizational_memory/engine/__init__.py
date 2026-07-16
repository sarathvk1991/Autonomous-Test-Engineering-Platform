"""The deterministic Organizational Memory engine and its modular collaborators
(CAP-085B, ADR-0027 §D9-§D17).

Every collaborator is engine-internal — none is exported as a runtime
contract, mirroring the Knowledge Graph Framework's own engine package
(ADR-0023 §D10).
"""

from __future__ import annotations

from requirement_intelligence.organizational_memory.engine.best_practice_generator import (
    BestPracticeGenerator,
)
from requirement_intelligence.organizational_memory.engine.deterministic_engine import (
    ORGANIZATIONAL_MEMORY_ENGINE_VERSION,
    DeterministicOrganizationalMemoryEngine,
)
from requirement_intelligence.organizational_memory.engine.experience_clusterer import (
    ExperienceClusterer,
)
from requirement_intelligence.organizational_memory.engine.experience_collector import (
    ExperienceCollector,
)
from requirement_intelligence.organizational_memory.engine.lesson_consolidator import (
    LessonConsolidator,
)
from requirement_intelligence.organizational_memory.engine.lesson_generator import LessonGenerator
from requirement_intelligence.organizational_memory.engine.lifecycle_recorder import (
    LifecycleRecorder,
)
from requirement_intelligence.organizational_memory.engine.metrics_builder import MetricsBuilder
from requirement_intelligence.organizational_memory.engine.promotion_recorder import (
    PromotionRecorder,
)
from requirement_intelligence.organizational_memory.engine.result_builder import ResultBuilder
from requirement_intelligence.organizational_memory.engine.summary_builder import SummaryBuilder

__all__ = [
    "ORGANIZATIONAL_MEMORY_ENGINE_VERSION",
    "BestPracticeGenerator",
    "DeterministicOrganizationalMemoryEngine",
    "ExperienceClusterer",
    "ExperienceCollector",
    "LessonConsolidator",
    "LessonGenerator",
    "LifecycleRecorder",
    "MetricsBuilder",
    "PromotionRecorder",
    "ResultBuilder",
    "SummaryBuilder",
]
