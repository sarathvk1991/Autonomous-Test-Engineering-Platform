"""Unit tests for the Prompt Governance Framework composition helpers.

Covers:
- build_prompt_registry returns a sealed PromptRegistry
- Registry contains requirement_analysis v1.0.0
- Metadata fields for requirement_analysis are correct
- SHA-256 determinism (same call → same sha256)
- Content is non-empty and contains expected template placeholder
- Immutability: registry is sealed; register after construction raises
- Compatibility metadata is populated
- Lifecycle is Production
- build_prompt_registry is idempotent (independent invocations)
- Custom versions_dir override
- Canonical SHA-256 matches manifest

No LLM calls.  No provider references.  Minimal I/O (reads from prompts/versions/).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from requirement_intelligence.prompts.framework.composition import (
    _VERSIONS_DIR,
    build_prompt_registry,
)
from requirement_intelligence.prompts.framework.prompt_exceptions import (
    PromptLoaderError,
    PromptRegistryError,
)
from requirement_intelligence.prompts.framework.prompt_registry import (
    PromptRegistry,
    PromptRegistryState,
)
from requirement_intelligence.prompts.models.prompt_compatibility import PromptCompatibility
from requirement_intelligence.prompts.models.prompt_definition import PromptDefinition
from requirement_intelligence.prompts.models.prompt_metadata import PromptMetadata
from requirement_intelligence.prompts.models.prompt_version import PromptLifecycle

# ===========================================================================
# Canonical registry
# ===========================================================================


class TestBuildPromptRegistry:
    @pytest.mark.unit
    def test_returns_prompt_registry(self) -> None:
        r = build_prompt_registry()
        assert isinstance(r, PromptRegistry)

    @pytest.mark.unit
    def test_registry_is_sealed(self) -> None:
        r = build_prompt_registry()
        assert r.is_sealed
        assert r.state is PromptRegistryState.SEALED

    @pytest.mark.unit
    def test_register_after_build_raises(self) -> None:
        r = build_prompt_registry()
        defn = PromptDefinition(
            metadata=PromptMetadata(
                prompt_id="intruder",
                name="Intruder",
                version="1.0.0",
                owner="Test",
                lifecycle=PromptLifecycle.DRAFT,
                description="Should not register.",
                sha256="a" * 64,
                compatibility=PromptCompatibility(
                    normalization_version="1.0",
                    validation_version="1.0",
                    cp1_version="1.0",
                    golden_dataset_version="1.0.0",
                    output_schema_version="1.0.0",
                ),
                release_introduced="1.0.0",
            ),
            content="content",
        )
        with pytest.raises(PromptRegistryError, match="sealed"):
            r.register(defn)

    @pytest.mark.unit
    def test_contains_requirement_analysis(self) -> None:
        r = build_prompt_registry()
        assert r.is_registered("requirement_analysis")
        assert r.is_registered("requirement_analysis", "1.0.0")

    @pytest.mark.unit
    def test_count_is_one(self) -> None:
        r = build_prompt_registry()
        assert r.count() == 1

    @pytest.mark.unit
    def test_list_prompt_ids(self) -> None:
        r = build_prompt_registry()
        assert r.list_prompt_ids() == ["requirement_analysis"]


# ===========================================================================
# requirement_analysis metadata
# ===========================================================================


class TestRequirementAnalysisMetadata:
    @pytest.mark.unit
    def test_version(self) -> None:
        d = build_prompt_registry().get("requirement_analysis")
        assert d.metadata.version == "1.0.0"

    @pytest.mark.unit
    def test_lifecycle_is_production(self) -> None:
        d = build_prompt_registry().get("requirement_analysis")
        assert d.metadata.lifecycle == PromptLifecycle.PRODUCTION

    @pytest.mark.unit
    def test_owner(self) -> None:
        d = build_prompt_registry().get("requirement_analysis")
        assert d.metadata.owner == "Prompt Framework"

    @pytest.mark.unit
    def test_name_is_non_empty(self) -> None:
        d = build_prompt_registry().get("requirement_analysis")
        assert d.metadata.name.strip()

    @pytest.mark.unit
    def test_description_is_non_empty(self) -> None:
        d = build_prompt_registry().get("requirement_analysis")
        assert d.metadata.description.strip()

    @pytest.mark.unit
    def test_release_introduced(self) -> None:
        d = build_prompt_registry().get("requirement_analysis")
        assert d.metadata.release_introduced == "1.0.0"

    @pytest.mark.unit
    def test_release_deprecated_is_none(self) -> None:
        d = build_prompt_registry().get("requirement_analysis")
        assert d.metadata.release_deprecated is None

    @pytest.mark.unit
    def test_sha256_is_64_hex_chars(self) -> None:
        d = build_prompt_registry().get("requirement_analysis")
        sha = d.metadata.sha256
        assert len(sha) == 64
        assert all(c in "0123456789abcdef" for c in sha)


# ===========================================================================
# Compatibility
# ===========================================================================


class TestRequirementAnalysisCompatibility:
    @pytest.mark.unit
    def test_normalization_version(self) -> None:
        d = build_prompt_registry().get("requirement_analysis")
        assert d.metadata.compatibility.normalization_version == "1.0"

    @pytest.mark.unit
    def test_validation_version(self) -> None:
        d = build_prompt_registry().get("requirement_analysis")
        assert d.metadata.compatibility.validation_version == "1.0"

    @pytest.mark.unit
    def test_cp1_version(self) -> None:
        d = build_prompt_registry().get("requirement_analysis")
        assert d.metadata.compatibility.cp1_version == "1.0"

    @pytest.mark.unit
    def test_golden_dataset_version(self) -> None:
        d = build_prompt_registry().get("requirement_analysis")
        assert d.metadata.compatibility.golden_dataset_version == "1.0.0"

    @pytest.mark.unit
    def test_output_schema_version(self) -> None:
        d = build_prompt_registry().get("requirement_analysis")
        assert d.metadata.compatibility.output_schema_version == "1.0.0"


# ===========================================================================
# Content
# ===========================================================================


class TestRequirementAnalysisContent:
    @pytest.mark.unit
    def test_content_is_non_empty(self) -> None:
        d = build_prompt_registry().get("requirement_analysis")
        assert d.content.strip()

    @pytest.mark.unit
    def test_content_contains_artifact_context_placeholder(self) -> None:
        d = build_prompt_registry().get("requirement_analysis")
        assert "{artifact_context}" in d.content

    @pytest.mark.unit
    def test_content_contains_system_role(self) -> None:
        d = build_prompt_registry().get("requirement_analysis")
        assert "Requirement Intelligence analyst" in d.content

    @pytest.mark.unit
    def test_content_contains_output_rules(self) -> None:
        d = build_prompt_registry().get("requirement_analysis")
        assert "Output rules" in d.content

    @pytest.mark.unit
    def test_content_contains_json_contract(self) -> None:
        d = build_prompt_registry().get("requirement_analysis")
        assert "functional_requirements" in d.content

    @pytest.mark.unit
    def test_content_contains_cp1_guidance(self) -> None:
        d = build_prompt_registry().get("requirement_analysis")
        assert "CP1" in d.content


# ===========================================================================
# SHA-256 fingerprinting (Phase 8)
# ===========================================================================


class TestSha256Fingerprinting:
    @pytest.mark.unit
    def test_sha256_deterministic_across_builds(self) -> None:
        d1 = build_prompt_registry().get("requirement_analysis")
        d2 = build_prompt_registry().get("requirement_analysis")
        assert d1.metadata.sha256 == d2.metadata.sha256

    @pytest.mark.unit
    def test_sha256_matches_computed_from_content(self) -> None:
        d = build_prompt_registry().get("requirement_analysis")
        computed = hashlib.sha256(d.content.encode("utf-8")).hexdigest()
        assert d.metadata.sha256 == computed

    @pytest.mark.unit
    def test_sha256_matches_manifest_record(self) -> None:
        manifest_path = _VERSIONS_DIR / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        entries = {e["prompt_id"]: e for e in manifest["prompts"]}
        d = build_prompt_registry().get("requirement_analysis")
        assert d.metadata.sha256 == entries["requirement_analysis"]["sha256"]

    @pytest.mark.unit
    def test_sha256_matches_file_bytes(self) -> None:
        txt_path = _VERSIONS_DIR / "requirement_analysis_v1.0.0.txt"
        file_sha = hashlib.sha256(txt_path.read_bytes()).hexdigest()
        d = build_prompt_registry().get("requirement_analysis")
        assert d.metadata.sha256 == file_sha


# ===========================================================================
# Idempotency and independence
# ===========================================================================


class TestBuildPromptRegistryIdempotency:
    @pytest.mark.unit
    def test_repeated_builds_are_independent(self) -> None:
        r1 = build_prompt_registry()
        r2 = build_prompt_registry()
        # Different registry instances
        assert r1 is not r2

    @pytest.mark.unit
    def test_repeated_builds_produce_same_sha256(self) -> None:
        sha1 = build_prompt_registry().get("requirement_analysis").metadata.sha256
        sha2 = build_prompt_registry().get("requirement_analysis").metadata.sha256
        assert sha1 == sha2

    @pytest.mark.unit
    def test_repeated_builds_produce_same_content(self) -> None:
        c1 = build_prompt_registry().get("requirement_analysis").content
        c2 = build_prompt_registry().get("requirement_analysis").content
        assert c1 == c2


# ===========================================================================
# Custom versions_dir override
# ===========================================================================


class TestCustomVersionsDir:
    @pytest.mark.unit
    def test_custom_dir_override_not_found_raises(self, tmp_path: Path) -> None:
        # No manifest.json in tmp_path → PromptLoaderError
        with pytest.raises(PromptLoaderError):
            build_prompt_registry(versions_dir=tmp_path)

    @pytest.mark.unit
    def test_custom_dir_with_valid_content(self, tmp_path: Path) -> None:
        """A self-contained versions directory works with the override."""
        content = "Hello {artifact_context}\n"
        raw = content.encode("utf-8")
        sha = hashlib.sha256(raw).hexdigest()
        (tmp_path / "test_v1.0.0.txt").write_bytes(raw)
        manifest = {
            "schema_version": "1.0",
            "prompts": [
                {
                    "prompt_id": "requirement_analysis",
                    "version": "1.0.0",
                    "file": "test_v1.0.0.txt",
                    "sha256": sha,
                }
            ],
        }
        (tmp_path / "manifest.json").write_text(
            json.dumps(manifest), encoding="utf-8"
        )
        r = build_prompt_registry(versions_dir=tmp_path)
        assert r.is_sealed
        assert r.is_registered("requirement_analysis", "1.0.0")
