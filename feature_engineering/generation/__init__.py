"""Layer 2 feature generation core.

One `TestableRequirement` in, one validated `.feature` file out. See
`assembler.py` for the deterministic, platform-owned mechanics,
`content_generator.py` for the seam, and `live_content_generator.py` for the
llm_factory-backed implementation that plugs into it.
"""

from __future__ import annotations

from feature_engineering.generation.assembler import (
    DEFAULT_FEATURES_ROOT,
    generate_feature_file,
    write_generated_feature,
)
from feature_engineering.generation.content_generator import (
    FeatureContentGenerator,
    StubFeatureContentGenerator,
)
from feature_engineering.generation.errors import FeatureGenerationError
from feature_engineering.generation.live_content_generator import (
    LiveFeatureContentGenerator,
    LiveGenerationError,
)
from feature_engineering.generation.models import GeneratedFeature, ScenarioAssignment

__all__ = [
    "DEFAULT_FEATURES_ROOT",
    "FeatureContentGenerator",
    "FeatureGenerationError",
    "GeneratedFeature",
    "LiveFeatureContentGenerator",
    "LiveGenerationError",
    "ScenarioAssignment",
    "StubFeatureContentGenerator",
    "generate_feature_file",
    "write_generated_feature",
]
