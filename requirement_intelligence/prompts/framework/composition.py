"""Prompt Governance Framework composition helpers.

This module is the **canonical composition root** for the Prompt Governance
subsystem.  It assembles the canonical :class:`PromptRegistry` that the
platform should use for all governed prompt resolution.

Responsibilities
----------------
1. Define the canonical metadata for every governed prompt (hardcoded,
   explicit — no reflection, no filesystem discovery).
2. Invoke :class:`PromptLoader` to load and verify each versioned template
   from ``prompts/versions/``.
3. Assemble :class:`PromptDefinition` instances.
4. Register them in a :class:`PromptRegistry`.
5. Seal the registry to prevent further modification.
6. Return the sealed registry.

Non-responsibilities
--------------------
* This module knows nothing about LLM providers.
* It does not invoke any LLM.
* It does not import or modify the Validation, CP1, Normalization,
  Analysis, or Execution Package subsystems.
* It does not change the runtime behaviour of
  :class:`~requirement_intelligence.prompts.requirement_prompt_builder.RequirementPromptBuilder`.

Design note
-----------
The canonical metadata for each prompt is defined directly in Python (not
read from a file) — exactly as CP1 criteria define their own metadata as
Python constants.  This keeps metadata governance in code where it is
version-controlled, reviewable, and testable.  The :class:`PromptLoader`
verifies the *content* (SHA-256 file integrity); the metadata in Python
governs the *identity* (lifecycle, compatibility, ownership).
"""

from __future__ import annotations

from pathlib import Path

from requirement_intelligence.prompts.framework.prompt_loader import PromptLoader
from requirement_intelligence.prompts.framework.prompt_registry import PromptRegistry
from requirement_intelligence.prompts.models.prompt_compatibility import PromptCompatibility
from requirement_intelligence.prompts.models.prompt_definition import PromptDefinition
from requirement_intelligence.prompts.models.prompt_metadata import PromptMetadata
from requirement_intelligence.prompts.models.prompt_version import PromptLifecycle

# ---------------------------------------------------------------------------
# Canonical versions directory
# ---------------------------------------------------------------------------

_VERSIONS_DIR: Path = Path(__file__).parent.parent / "versions"

# ---------------------------------------------------------------------------
# Canonical metadata declarations
# ---------------------------------------------------------------------------
# Each prompt's metadata is declared here explicitly.  No metadata is derived
# at runtime from the file content; metadata is a governed architecture record.

_REQUIREMENT_ANALYSIS_COMPATIBILITY = PromptCompatibility(
    # Normalization contract version this prompt was verified against.
    # Source: NORMALIZATION_CONTRACT_VERSION in response-normalization-contract.md
    normalization_version="1.0",
    # Validation contract version this prompt was verified against.
    # Source: DEFAULT_VALIDATION_CONTRACT_VERSION in ai-response-validation.md
    validation_version="1.0",
    # CP1 criteria contract version this prompt was verified against.
    # Source: DEFAULT_CP1_CRITERIA_CONTRACT_VERSION (ADR-0012)
    cp1_version="1.0",
    # Golden dataset version the prompt's regression suite used.
    # Source: GOLDEN_DATASET_VERSION in golden-baseline.md
    golden_dataset_version="1.0.0",
    # Output schema version this prompt targets.
    # Defined by JSON_RESPONSE_REQUIREMENTS in prompt_constants.py:
    # summary, functional_requirements, security_requirements,
    # quality_requirements, risks, recommendations.
    output_schema_version="1.0.0",
)

# v1.1.0 is an additive, wording-only clarification of v1.0.0 (CAP-073 Prompt
# Evaluation & Tuning).  The output schema is byte-for-byte identical, so every
# compatibility dimension — including output_schema_version — is preserved.
_REQUIREMENT_ANALYSIS_V110_COMPATIBILITY = _REQUIREMENT_ANALYSIS_COMPATIBILITY

# ---------------------------------------------------------------------------
# Canonical composition entry point
# ---------------------------------------------------------------------------


def build_prompt_registry(
    versions_dir: Path | None = None,
) -> PromptRegistry:
    """Build and return the canonical sealed :class:`PromptRegistry`.

    Loads every governed prompt from the versioned storage directory,
    verifies SHA-256 integrity, assembles :class:`PromptDefinition` objects,
    registers them, seals the registry, and returns it.

    Parameters
    ----------
    versions_dir:
        Override the default ``prompts/versions/`` directory.  Used in tests
        to point at a temporary fixture directory.  When ``None``, the
        canonical ``prompts/versions/`` directory relative to this package
        is used.

    Returns
    -------
    PromptRegistry
        A sealed registry containing all governed prompt definitions.

    Raises
    ------
    PromptLoaderError
        If any versioned file fails to load or its SHA-256 does not match the
        manifest.
    """
    resolved_dir = versions_dir if versions_dir is not None else _VERSIONS_DIR

    loader = PromptLoader()
    registry = PromptRegistry()

    # --- requirement_analysis v1.0.0 -----------------------------------
    loaded = loader.load(
        prompt_id="requirement_analysis",
        version="1.0.0",
        versions_dir=resolved_dir,
    )
    metadata = PromptMetadata(
        prompt_id="requirement_analysis",
        name="Requirement Analysis Prompt",
        version="1.0.0",
        owner="Prompt Framework",
        lifecycle=PromptLifecycle.PRODUCTION,
        description=(
            "Provider-agnostic analysis prompt that turns a ConsolidatedArtifact "
            "into a structured JSON response containing functional, security, and "
            "quality requirements, risks, and recommendations.  Used by the "
            "RequirementAnalysisService via the RequirementPromptBuilder."
        ),
        sha256=loaded.sha256,
        compatibility=_REQUIREMENT_ANALYSIS_COMPATIBILITY,
        release_introduced="1.0.0",
    )
    registry.register(PromptDefinition(metadata=metadata, content=loaded.content))

    # --- requirement_analysis v1.1.0 -----------------------------------
    # Governed candidate produced by CAP-073 (Prompt Evaluation & Tuning).
    # Evidence-driven, conservative wording clarification of v1.0.0 with an
    # identical output schema.  Registered as APPROVED — approved for
    # production but not yet the live runtime prompt.  Since CAP-075 the
    # runtime resolves its prompt from this registry, pinned explicitly to
    # v1.0.0; promoting v1.1.0 is a deliberate, separate governed change.
    # v1.0.0 remains PRODUCTION.
    loaded_v110 = loader.load(
        prompt_id="requirement_analysis",
        version="1.1.0",
        versions_dir=resolved_dir,
    )
    metadata_v110 = PromptMetadata(
        prompt_id="requirement_analysis",
        name="Requirement Analysis Prompt",
        version="1.1.0",
        owner="Prompt Framework",
        lifecycle=PromptLifecycle.APPROVED,
        description=(
            "Conservative wording clarification of the v1.0.0 requirement "
            "analysis prompt (CAP-073).  Adds a coverage objective, normative "
            "MUST/MUST NOT phrasing, an explicit no-duplication rule, "
            "deterministic array ordering, measurability guidance, and inline "
            "evidence citation.  The output schema is unchanged from v1.0.0."
        ),
        sha256=loaded_v110.sha256,
        compatibility=_REQUIREMENT_ANALYSIS_V110_COMPATIBILITY,
        release_introduced="1.1.0",
    )
    registry.register(PromptDefinition(metadata=metadata_v110, content=loaded_v110.content))

    # Seal to prevent any future modification.
    registry.seal()
    return registry
