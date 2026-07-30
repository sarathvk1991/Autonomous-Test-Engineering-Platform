"""The Layer 3 asset catalog and run-start reconciliation (ADR-0044 D3).

This package builds ONLY the catalog and its reconciliation from the
tracked baseline's committed Java. It deliberately does not build:

* semantic matching / MATCH lookup (ADR-0044 D3's own remaining TBD --
  embeddings vs. per-step LLM call);
* the reuse-safety trust model (ADR-0044 D4 -- confidence threshold,
  content-hash validation, signature/parameter fit);
* generation of any kind, CP3/CP4, or promotion (ADR-0045).

Those all sit on top of this module and are future work. The interface a
future reuse-discovery module calls against is exactly:

* :func:`reconcile` -- "give me the current catalog," scanning a baseline
  root fresh every time (ADR-0044 D3's run-start reconciliation).
* :class:`AssetCatalog` -- the read-only result: ``.step_definitions``,
  ``.page_objects``, ``.utilities`` (the query shape a future semantic
  MATCH step iterates over), ``.get(asset_id)`` (identity lookup),
  ``.by_content_hash(...)`` (the exact identity check ADR-0045 D2(b)
  reuses, unchanged, as its promotion-time anti-duplicate gate).
"""

from __future__ import annotations

from automation_engineering.catalog.models import (
    AssetCatalog,
    AssetKind,
    CatalogAsset,
    JavaField,
    JavaMethod,
    JavaParameter,
    PageObjectAsset,
    StepDefinitionAsset,
    UtilityAsset,
)
from automation_engineering.catalog.scanner import reconcile

__all__ = [
    "AssetCatalog",
    "AssetKind",
    "CatalogAsset",
    "JavaField",
    "JavaMethod",
    "JavaParameter",
    "PageObjectAsset",
    "StepDefinitionAsset",
    "UtilityAsset",
    "reconcile",
]
