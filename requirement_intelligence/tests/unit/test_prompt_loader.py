"""Unit tests for the PromptLoader.

Covers:
- compute_sha256 determinism
- compute_sha256 consistency with hashlib
- load: success path (verifies SHA-256, returns content)
- load: missing manifest raises PromptLoaderError
- load: malformed manifest JSON raises PromptLoaderError
- load: prompt_id not in manifest raises PromptLoaderError
- load: version not in manifest raises PromptLoaderError
- load: missing file raises PromptLoaderError
- load: SHA-256 mismatch raises PromptLoaderError
- load: manifest entry missing required fields raises PromptLoaderError
- LoadedPrompt fields (content, sha256, file_path)
- SHA determinism — two loads of same file return identical sha256

All tests use tmp_path for filesystem isolation.  No network.  No LLM calls.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from requirement_intelligence.prompts.framework.prompt_exceptions import PromptLoaderError
from requirement_intelligence.prompts.framework.prompt_loader import LoadedPrompt, PromptLoader

# ===========================================================================
# Helpers
# ===========================================================================


def _write_prompt_file(directory: Path, filename: str, content: str) -> Path:
    """Write a prompt template file and return its path."""
    path = directory / filename
    path.write_text(content, encoding="utf-8", newline="")
    return path


def _compute_sha256(content: str) -> str:
    """Compute SHA-256 of the UTF-8 bytes of *content*."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _write_manifest(directory: Path, entries: list[dict]) -> Path:
    """Write manifest.json and return its path."""
    manifest = {
        "schema_version": "1.0",
        "prompts": entries,
    }
    path = directory / "manifest.json"
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return path


def _valid_versions_dir(tmp_path: Path, content: str = "Hello {artifact_context}\n") -> Path:
    """Create a self-consistent versions directory with one prompt file."""
    raw = content.encode("utf-8")
    sha256 = hashlib.sha256(raw).hexdigest()
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / "test_prompt_v1.0.0.txt").write_bytes(raw)
    _write_manifest(
        tmp_path,
        [
            {
                "prompt_id": "test_prompt",
                "version": "1.0.0",
                "file": "test_prompt_v1.0.0.txt",
                "sha256": sha256,
                "lifecycle": "Production",
                "introduced_in_release": "1.0.0",
            }
        ],
    )
    return tmp_path


# ===========================================================================
# compute_sha256
# ===========================================================================


class TestComputeSha256:
    @pytest.mark.unit
    def test_deterministic_same_input(self) -> None:
        data = b"stable content"
        assert PromptLoader.compute_sha256(data) == PromptLoader.compute_sha256(data)

    @pytest.mark.unit
    def test_consistent_with_hashlib(self) -> None:
        data = b"check consistency"
        expected = hashlib.sha256(data).hexdigest()
        assert PromptLoader.compute_sha256(data) == expected

    @pytest.mark.unit
    def test_different_data_different_sha256(self) -> None:
        assert PromptLoader.compute_sha256(b"a") != PromptLoader.compute_sha256(b"b")

    @pytest.mark.unit
    def test_returns_lowercase_hex(self) -> None:
        result = PromptLoader.compute_sha256(b"data")
        assert result == result.lower()
        assert len(result) == 64

    @pytest.mark.unit
    def test_empty_bytes_deterministic(self) -> None:
        r1 = PromptLoader.compute_sha256(b"")
        r2 = PromptLoader.compute_sha256(b"")
        assert r1 == r2
        assert len(r1) == 64


# ===========================================================================
# LoadedPrompt
# ===========================================================================


class TestLoadedPrompt:
    @pytest.mark.unit
    def test_fields_present(self, tmp_path: Path) -> None:
        versions_dir = _valid_versions_dir(tmp_path)
        loader = PromptLoader()
        result = loader.load("test_prompt", "1.0.0", versions_dir)
        assert isinstance(result, LoadedPrompt)
        assert isinstance(result.content, str)
        assert isinstance(result.sha256, str)
        assert isinstance(result.file_path, Path)

    @pytest.mark.unit
    def test_content_matches_file(self, tmp_path: Path) -> None:
        expected_content = "Template {artifact_context} body\n"
        versions_dir = _valid_versions_dir(tmp_path, content=expected_content)
        loader = PromptLoader()
        result = loader.load("test_prompt", "1.0.0", versions_dir)
        assert result.content == expected_content

    @pytest.mark.unit
    def test_sha256_matches_file_bytes(self, tmp_path: Path) -> None:
        content = "Template {artifact_context}\n"
        versions_dir = _valid_versions_dir(tmp_path, content=content)
        loader = PromptLoader()
        result = loader.load("test_prompt", "1.0.0", versions_dir)
        expected_sha = hashlib.sha256(content.encode("utf-8")).hexdigest()
        assert result.sha256 == expected_sha

    @pytest.mark.unit
    def test_file_path_is_absolute(self, tmp_path: Path) -> None:
        versions_dir = _valid_versions_dir(tmp_path)
        loader = PromptLoader()
        result = loader.load("test_prompt", "1.0.0", versions_dir)
        assert result.file_path.is_absolute()


# ===========================================================================
# Success path
# ===========================================================================


class TestPromptLoaderSuccess:
    @pytest.mark.unit
    def test_load_returns_loaded_prompt(self, tmp_path: Path) -> None:
        versions_dir = _valid_versions_dir(tmp_path)
        loader = PromptLoader()
        result = loader.load("test_prompt", "1.0.0", versions_dir)
        assert result is not None

    @pytest.mark.unit
    def test_sha_determinism_repeated_loads(self, tmp_path: Path) -> None:
        versions_dir = _valid_versions_dir(tmp_path)
        loader = PromptLoader()
        r1 = loader.load("test_prompt", "1.0.0", versions_dir)
        r2 = loader.load("test_prompt", "1.0.0", versions_dir)
        assert r1.sha256 == r2.sha256
        assert r1.content == r2.content

    @pytest.mark.unit
    def test_separate_loader_instances_same_result(self, tmp_path: Path) -> None:
        versions_dir = _valid_versions_dir(tmp_path)
        r1 = PromptLoader().load("test_prompt", "1.0.0", versions_dir)
        r2 = PromptLoader().load("test_prompt", "1.0.0", versions_dir)
        assert r1.sha256 == r2.sha256


# ===========================================================================
# Error paths
# ===========================================================================


class TestPromptLoaderErrors:
    @pytest.mark.unit
    def test_missing_manifest_raises(self, tmp_path: Path) -> None:
        loader = PromptLoader()
        with pytest.raises(PromptLoaderError, match="manifest not found"):
            loader.load("test_prompt", "1.0.0", tmp_path)

    @pytest.mark.unit
    def test_malformed_manifest_raises(self, tmp_path: Path) -> None:
        (tmp_path / "manifest.json").write_text("NOT JSON", encoding="utf-8")
        loader = PromptLoader()
        with pytest.raises(PromptLoaderError, match="parse"):
            loader.load("test_prompt", "1.0.0", tmp_path)

    @pytest.mark.unit
    def test_prompt_id_not_in_manifest_raises(self, tmp_path: Path) -> None:
        versions_dir = _valid_versions_dir(tmp_path)
        loader = PromptLoader()
        with pytest.raises(PromptLoaderError, match="No manifest entry"):
            loader.load("unknown_prompt", "1.0.0", versions_dir)

    @pytest.mark.unit
    def test_version_not_in_manifest_raises(self, tmp_path: Path) -> None:
        versions_dir = _valid_versions_dir(tmp_path)
        loader = PromptLoader()
        with pytest.raises(PromptLoaderError, match="No manifest entry"):
            loader.load("test_prompt", "9.9.9", versions_dir)

    @pytest.mark.unit
    def test_missing_file_raises(self, tmp_path: Path) -> None:
        raw = b"content"
        sha = hashlib.sha256(raw).hexdigest()
        _write_manifest(
            tmp_path,
            [
                {
                    "prompt_id": "p",
                    "version": "1.0.0",
                    "file": "nonexistent.txt",
                    "sha256": sha,
                }
            ],
        )
        loader = PromptLoader()
        with pytest.raises(PromptLoaderError, match="not found"):
            loader.load("p", "1.0.0", tmp_path)

    @pytest.mark.unit
    def test_sha256_mismatch_raises(self, tmp_path: Path) -> None:
        (tmp_path / "p_v1.0.0.txt").write_bytes(b"actual content")
        _write_manifest(
            tmp_path,
            [
                {
                    "prompt_id": "p",
                    "version": "1.0.0",
                    "file": "p_v1.0.0.txt",
                    "sha256": "0" * 64,  # wrong SHA
                }
            ],
        )
        loader = PromptLoader()
        with pytest.raises(PromptLoaderError, match="SHA-256 integrity check failed"):
            loader.load("p", "1.0.0", tmp_path)

    @pytest.mark.unit
    def test_manifest_entry_missing_file_field_raises(self, tmp_path: Path) -> None:
        _write_manifest(
            tmp_path,
            [
                {
                    "prompt_id": "p",
                    "version": "1.0.0",
                    # "file" key is missing
                    "sha256": "a" * 64,
                }
            ],
        )
        loader = PromptLoader()
        with pytest.raises(PromptLoaderError, match="missing required field"):
            loader.load("p", "1.0.0", tmp_path)

    @pytest.mark.unit
    def test_manifest_entry_missing_sha256_field_raises(self, tmp_path: Path) -> None:
        (tmp_path / "p_v1.0.0.txt").write_bytes(b"content")
        _write_manifest(
            tmp_path,
            [
                {
                    "prompt_id": "p",
                    "version": "1.0.0",
                    "file": "p_v1.0.0.txt",
                    # "sha256" key is missing
                }
            ],
        )
        loader = PromptLoader()
        with pytest.raises(PromptLoaderError, match="missing required field"):
            loader.load("p", "1.0.0", tmp_path)

    @pytest.mark.unit
    def test_empty_manifest_prompts_list_raises(self, tmp_path: Path) -> None:
        _write_manifest(tmp_path, [])
        loader = PromptLoader()
        with pytest.raises(PromptLoaderError, match="No manifest entry"):
            loader.load("any", "1.0.0", tmp_path)
