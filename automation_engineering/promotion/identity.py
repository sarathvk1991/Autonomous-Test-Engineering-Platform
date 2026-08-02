"""Candidate-asset identity resolution (ADR-0045 D2(b)).

Resolves a freshly generated asset's own identity -- content-hash, class
name, destination path -- using the EXACT SAME scan the tracked-baseline
catalog uses (:func:`automation_engineering.catalog.scanner.reconcile`),
never a second, hand-rolled parsing/hashing mechanism (D2's own text: "this
ADR invents no second duplicate-detection mechanism"; Recommendation 3).

Different asset kinds hash different spans -- a step-definition's
content-hash is computed over its own ANNOTATED METHOD's span (one asset per
``@Given``/``@When``/``@Then`` method), while a page object's or utility's
is computed over its whole CLASS span
(:mod:`automation_engineering.catalog.scanner`'s own
``_extract_step_definitions`` vs. ``_extract_page_object``/
``_extract_utility``). Reproducing those per-kind rules by hand here would
be exactly the "second mechanism" D2 forbids and would drift the moment
:mod:`automation_engineering.catalog.scanner` changes. Instead, this module
writes the candidate's ``java_source`` to a throwaway directory laid out
exactly like a baseline root (``src/test/java/<package>/<ClassName>.java``)
and runs the real :func:`~automation_engineering.catalog.scanner.reconcile`
against it -- the resulting single :class:`~automation_engineering.catalog.
models.CatalogAsset` IS the candidate's identity, computed by literally the
same code path a real promotion is reconciled against on the next run.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import javalang

from automation_engineering.catalog.java_source import parse_java_file
from automation_engineering.catalog.models import CatalogAsset
from automation_engineering.catalog.scanner import JAVA_SOURCE_SUBPATH, reconcile


class CandidateIdentityError(ValueError):
    """``java_source`` does not resolve to exactly one catalog asset -- a
    promotion candidate must contain exactly one top-level class declaration
    with exactly the shape the catalog scanner already expects (a plain
    class, or a step-definition class with exactly one annotated method,
    matching the generation seam's own OUTPUT CONTRACT)."""


def _single_class_name(java_source: str) -> str:
    parsed = parse_java_file("Candidate.java", java_source)
    classes = [node for _, node in parsed.tree.filter(javalang.tree.ClassDeclaration)]
    if len(classes) != 1:
        raise CandidateIdentityError(
            f"expected exactly one top-level class declaration in candidate "
            f"java_source, found {len(classes)}"
        )
    return str(classes[0].name)


def relative_java_path(package: str, class_name: str) -> Path:
    """The path a class with this package/name occupies under
    ``src/test/java/`` -- standard one-package-per-directory Java layout,
    the same convention :mod:`automation_engineering.catalog.scanner` reads
    file positions against."""
    parts = package.split(".") if package else []
    return Path(*parts, f"{class_name}.java")


def resolve_candidate_identity(java_source: str) -> tuple[CatalogAsset, Path]:
    """Resolve ``java_source``'s own identity via a real ``reconcile()`` call.

    Returns the single :class:`~automation_engineering.catalog.models.
    CatalogAsset` the source reconciles to, plus its own path relative to
    ``src/test/java/``. Raises :class:`CandidateIdentityError` if the source
    does not resolve to exactly one asset (zero -- an unparsed/malformed
    class; more than one -- e.g. a step-definition class with more than one
    annotated method, which the generation seam's own contract never
    produces).
    """
    parsed = parse_java_file("Candidate.java", java_source)
    class_name = _single_class_name(java_source)
    relative_path = relative_java_path(parsed.package, class_name)
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_root = Path(tmp_dir)
        target = tmp_root / JAVA_SOURCE_SUBPATH / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(java_source, encoding="utf-8")
        candidate_catalog = reconcile(tmp_root)
    assets = candidate_catalog.all_assets()
    if len(assets) != 1:
        raise CandidateIdentityError(
            f"expected candidate java_source to reconcile to exactly one catalog "
            f"asset, found {len(assets)} (unparsed_files="
            f"{candidate_catalog.unparsed_files!r})"
        )
    return assets[0], relative_path


__all__ = ["CandidateIdentityError", "relative_java_path", "resolve_candidate_identity"]
