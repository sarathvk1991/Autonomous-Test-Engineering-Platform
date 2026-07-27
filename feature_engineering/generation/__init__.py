"""Layer 2 feature generation core.

One `TestableRequirement` in, one validated `.feature` file out. See
`assembler.py` for the deterministic, platform-owned mechanics, and
`content_generator.py` for the seam a live LLM-backed implementation plugs
into (a separate, later task -- not built here).
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
from feature_engineering.generation.models import GeneratedFeature, ScenarioAssignment

__all__ = [
    "DEFAULT_FEATURES_ROOT",
    "FeatureContentGenerator",
    "FeatureGenerationError",
    "GeneratedFeature",
    "ScenarioAssignment",
    "StubFeatureContentGenerator",
    "generate_feature_file",
    "write_generated_feature",
]
