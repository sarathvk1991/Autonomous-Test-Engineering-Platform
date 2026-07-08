"""Prompt file loader with SHA-256 integrity verification.

:class:`PromptLoader` is the file-system boundary of the Prompt Governance
subsystem.  It is the **only** component permitted to read from
``prompts/versions/``.

Responsibilities
----------------
1. Read the version manifest (``manifest.json``) to discover the canonical
   file path and recorded SHA-256 fingerprint for a given prompt.
2. Read the versioned template file from ``prompts/versions/``.
3. Compute the SHA-256 of the file bytes.
4. Verify the computed fingerprint against the recorded fingerprint.
5. Return the content and the verified fingerprint.

Non-responsibilities
--------------------
The loader knows nothing about:

* The :class:`~requirement_intelligence.prompts.framework.prompt_registry.PromptRegistry`.
* :class:`~requirement_intelligence.prompts.models.PromptMetadata` or
  :class:`~requirement_intelligence.prompts.models.PromptDefinition` — it
  returns raw content; the caller assembles the model.
* Any LLM provider.
* The Runtime Prompt Builder (:class:`RequirementPromptBuilder`).

SHA-256 policy
--------------
The fingerprint is computed over the **raw bytes** of the versioned file
(``Path.read_bytes()``), encoded as a lowercase hex string.  This is the same
algorithm used to produce the fingerprint stored in the manifest.  A mismatch
indicates the file was tampered with or corrupted since the manifest was last
generated; the loader raises :class:`PromptLoaderError` and no content is
returned.

This SHA-256 (the *template fingerprint*) is **distinct** from the
per-execution ``promptSha256`` recorded in ``execution/manifest.json``, which
fingerprints the fully assembled prompt (template + injected artifact context).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from requirement_intelligence.prompts.framework.prompt_exceptions import PromptLoaderError


@dataclass(frozen=True)
class LoadedPrompt:
    """The result of a successful :class:`PromptLoader` load operation.

    Fields
    ------
    content:
        The template text decoded from the versioned file (UTF-8).
    sha256:
        Hex SHA-256 of the raw file bytes — the *verified* fingerprint.
    file_path:
        Absolute path to the file that was loaded.
    """

    content: str
    sha256: str
    file_path: Path


class PromptLoader:
    """File-based prompt loader with SHA-256 integrity verification.

    Stateless.  Every call to :meth:`load` is independent; the loader holds
    no cached state.

    Usage
    -----
    >>> loader = PromptLoader()
    >>> loaded = loader.load("requirement_analysis", "1.0.0", versions_dir)
    >>> loaded.content  # template text
    >>> loaded.sha256   # verified fingerprint
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load(
        self,
        prompt_id: str,
        version: str,
        versions_dir: Path,
    ) -> LoadedPrompt:
        """Load and verify a versioned prompt template file.

        Parameters
        ----------
        prompt_id:
            The stable prompt identifier (e.g. ``"requirement_analysis"``).
        version:
            The version to load (e.g. ``"1.0.0"``).
        versions_dir:
            Path to the directory that contains ``manifest.json`` and the
            versioned ``.txt`` files.

        Returns
        -------
        LoadedPrompt
            The decoded template content and the verified SHA-256 fingerprint.

        Raises
        ------
        PromptLoaderError
            * ``manifest.json`` cannot be read or is malformed.
            * The ``(prompt_id, version)`` pair is not listed in the manifest.
            * The versioned file does not exist.
            * The computed SHA-256 does not match the recorded fingerprint.
        """
        manifest = self._read_manifest(versions_dir)
        entry = self._find_entry(manifest, prompt_id, version, versions_dir)
        file_path = versions_dir / entry["file"]
        return self._load_file(file_path, expected_sha256=entry["sha256"])

    @staticmethod
    def compute_sha256(data: bytes) -> str:
        """Return the lowercase hex SHA-256 of *data*.

        This is the canonical fingerprinting function for the Prompt
        Governance subsystem.  All SHA-256 values stored in the manifest
        and carried on :class:`PromptMetadata` must be produced by this
        function (or the equivalent ``hashlib.sha256(data).hexdigest()``).
        """
        return hashlib.sha256(data).hexdigest()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _read_manifest(self, versions_dir: Path) -> dict[str, Any]:
        """Read and parse the version manifest."""
        manifest_path = versions_dir / "manifest.json"
        if not manifest_path.exists():
            raise PromptLoaderError(
                f"Prompt version manifest not found: {manifest_path}. "
                f"Ensure the versions directory is correctly set up."
            )
        try:
            raw = manifest_path.read_text(encoding="utf-8")
            data: dict[str, Any] = json.loads(raw)
        except (OSError, json.JSONDecodeError) as exc:
            raise PromptLoaderError(
                f"Failed to read or parse prompt manifest at {manifest_path}: {exc}"
            ) from exc
        return data

    def _find_entry(
        self,
        manifest: dict[str, Any],
        prompt_id: str,
        version: str,
        versions_dir: Path,
    ) -> dict[str, Any]:
        """Locate the manifest entry for (prompt_id, version)."""
        prompts: list[dict[str, Any]] = manifest.get("prompts", [])
        for entry in prompts:
            if entry.get("prompt_id") == prompt_id and entry.get("version") == version:
                for required in ("file", "sha256"):
                    if required not in entry:
                        raise PromptLoaderError(
                            f"Manifest entry for prompt_id={prompt_id!r} "
                            f"version={version!r} is missing required field "
                            f"{required!r} in {versions_dir / 'manifest.json'}."
                        )
                return entry
        raise PromptLoaderError(
            f"No manifest entry found for prompt_id={prompt_id!r} "
            f"version={version!r} in {versions_dir / 'manifest.json'}."
        )

    def _load_file(self, file_path: Path, expected_sha256: str) -> LoadedPrompt:
        """Read a file, verify its SHA-256, and return a :class:`LoadedPrompt`."""
        if not file_path.exists():
            raise PromptLoaderError(f"Versioned prompt file not found: {file_path}.")
        try:
            raw_bytes = file_path.read_bytes()
        except OSError as exc:
            raise PromptLoaderError(
                f"Failed to read versioned prompt file {file_path}: {exc}"
            ) from exc

        computed = self.compute_sha256(raw_bytes)
        if computed != expected_sha256:
            raise PromptLoaderError(
                f"SHA-256 integrity check failed for {file_path}. "
                f"Expected {expected_sha256!r} (from manifest) but computed "
                f"{computed!r}. The file may have been tampered with or corrupted."
            )
        return LoadedPrompt(
            content=raw_bytes.decode("utf-8"),
            sha256=computed,
            file_path=file_path,
        )
