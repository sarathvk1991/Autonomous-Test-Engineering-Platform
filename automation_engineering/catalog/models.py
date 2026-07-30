"""Asset catalog data shapes (ADR-0044 D3).

The catalog records three kinds of reusable asset -- step definitions, page
objects, and utilities (the same three named in ADR-0044 D1's Validated
Automation Package) -- scanned from the tracked baseline's committed Java.

Two identity concepts are kept deliberately distinct, because ADR-0044 D4's
reuse-safety model needs both and conflating them breaks it:

* ``asset_id`` -- a STABLE identity key, content-addressed over the asset's
  *declared identity* (fully-qualified class name, plus method name for a
  step definition) -- never over its body. The same step definition keeps
  the same ``asset_id`` across edits to its implementation.
* ``content_hash`` -- a sha256 digest over the asset's *exact extracted
  source span* (annotations/modifiers through the closing brace). This
  changes whenever the asset's actual code changes.

This split is what makes ADR-0044 D4(b) ("content-hash validation that the
catalogued code is current") a meaningful check at all: a future reuse
lookup finds an entry by its stable ``asset_id`` (or by semantic match, once
built), then compares its *current* ``content_hash`` against what was
recorded when the match was made. If ``asset_id`` were itself
content-derived, every edit would mint a new id and there would be no prior
entry left to call "stale" against.

No field here carries a wall-clock timestamp or any other run-varying value
-- the catalog must be byte-identical across repeated scans of unchanged
source (ADR-0044 D3's reconciliation determinism).
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from enum import StrEnum


class AssetKind(StrEnum):
    """The three reusable-asset kinds ADR-0044 D1 names as Layer 3 output."""

    STEP_DEFINITION = "step_definition"
    PAGE_OBJECT = "page_object"
    UTILITY = "utility"


@dataclass(frozen=True, slots=True)
class JavaParameter:
    """One method parameter, in declared order."""

    name: str
    java_type: str


@dataclass(frozen=True, slots=True)
class JavaMethod:
    """One non-step-bound method on a page object or utility class."""

    name: str
    parameters: tuple[JavaParameter, ...]
    return_type: str


@dataclass(frozen=True, slots=True)
class JavaField:
    """One field on a page object or utility class."""

    name: str
    java_type: str
    is_locator: bool


@dataclass(frozen=True, slots=True)
class StepDefinitionAsset:
    """One Cucumber-annotated step-definition method -- the unit ADR-0044 D3's
    semantic reuse matching binds a Gherkin step to, and D4's signature-fit
    check (D4(c)) validates parameter shape against.
    """

    asset_id: str
    class_name: str
    method_name: str
    step_type: str
    pattern: str
    parameters: tuple[JavaParameter, ...]
    return_type: str
    source_file: str
    content_hash: str
    semantic_tags: tuple[str, ...] = field(default_factory=tuple)
    kind: AssetKind = AssetKind.STEP_DEFINITION


@dataclass(frozen=True, slots=True)
class PageObjectAsset:
    """One class extending the tracked baseline's ``BasePage``."""

    asset_id: str
    class_name: str
    extends: str | None
    fields: tuple[JavaField, ...]
    locators: tuple[JavaField, ...]
    methods: tuple[JavaMethod, ...]
    source_file: str
    content_hash: str
    semantic_tags: tuple[str, ...] = field(default_factory=tuple)
    kind: AssetKind = AssetKind.PAGE_OBJECT


@dataclass(frozen=True, slots=True)
class UtilityAsset:
    """A generated helper class that is neither a step-definition glue class
    nor a page object (e.g. a future ``DataProvider``/``Constants`` class,
    ADR-0044 D7)."""

    asset_id: str
    class_name: str
    fields: tuple[JavaField, ...]
    methods: tuple[JavaMethod, ...]
    source_file: str
    content_hash: str
    semantic_tags: tuple[str, ...] = field(default_factory=tuple)
    kind: AssetKind = AssetKind.UTILITY


CatalogAsset = StepDefinitionAsset | PageObjectAsset | UtilityAsset


@dataclass(frozen=True, slots=True)
class AssetCatalog:
    """The reconciled catalog (ADR-0044 D3) -- the read-only result of one
    scan of the tracked baseline. Carries no cross-run state of its own; the
    tracked baseline's committed Java is the thing that actually persists
    across runs (see ``scanner.reconcile``'s docstring for the storage-
    location decision this resolves).
    """

    baseline_root: str
    step_definitions: tuple[StepDefinitionAsset, ...] = ()
    page_objects: tuple[PageObjectAsset, ...] = ()
    utilities: tuple[UtilityAsset, ...] = ()
    #: Files under scan scope that a real Java-syntax parse failed on (e.g. a
    #: language construct javalang's grammar does not support), skipped
    #: rather than crashing the whole reconciliation. Reported explicitly --
    #: an empty catalog must always mean "no assets found," never "scanning
    #: silently failed."
    unparsed_files: tuple[str, ...] = ()

    def all_assets(self) -> tuple[CatalogAsset, ...]:
        return (*self.step_definitions, *self.page_objects, *self.utilities)

    def get(self, asset_id: str) -> CatalogAsset | None:
        for asset in self.all_assets():
            if asset.asset_id == asset_id:
                return asset
        return None

    def by_content_hash(self, content_hash: str) -> tuple[CatalogAsset, ...]:
        """Assets currently recorded under this exact content-hash.

        This is the identity lookup ADR-0045 D2(b) reuses (unchanged, not
        duplicated) as its promotion-time anti-duplicate check -- a
        candidate whose own computed content-hash appears here already
        exists in the tracked baseline under that identity.
        """
        return tuple(a for a in self.all_assets() if a.content_hash == content_hash)

    def to_json(self) -> str:
        """Canonical, deterministic JSON serialization -- sorted keys, stable
        key order from field declaration, no run-varying data. Used only as
        an inspectable snapshot; reconciliation never reads this back as an
        authoritative source (see ``scanner.reconcile``)."""
        payload = {
            "baseline_root": self.baseline_root,
            "step_definitions": [asdict(a) for a in self.step_definitions],
            "page_objects": [asdict(a) for a in self.page_objects],
            "utilities": [asdict(a) for a in self.utilities],
            "unparsed_files": list(self.unparsed_files),
        }
        return json.dumps(payload, indent=2, sort_keys=True)

    @classmethod
    def from_json(cls, text: str) -> AssetCatalog:
        payload = json.loads(text)
        return cls(
            baseline_root=payload["baseline_root"],
            step_definitions=tuple(
                _step_definition_from_dict(d) for d in payload["step_definitions"]
            ),
            page_objects=tuple(_page_object_from_dict(d) for d in payload["page_objects"]),
            utilities=tuple(_utility_from_dict(d) for d in payload["utilities"]),
            unparsed_files=tuple(payload.get("unparsed_files", ())),
        )


def _without_kind(d: dict[str, object]) -> dict[str, object]:
    return {k: v for k, v in d.items() if k != "kind"}


def _parameters_from_dicts(params: list[dict[str, object]]) -> tuple[JavaParameter, ...]:
    return tuple(JavaParameter(**p) for p in params)  # type: ignore[arg-type]


def _methods_from_dicts(methods: list[dict[str, object]]) -> tuple[JavaMethod, ...]:
    return tuple(
        JavaMethod(
            name=m["name"],  # type: ignore[arg-type]
            parameters=_parameters_from_dicts(m["parameters"]),  # type: ignore[arg-type]
            return_type=m["return_type"],  # type: ignore[arg-type]
        )
        for m in methods
    )


def _fields_from_dicts(fields: list[dict[str, object]]) -> tuple[JavaField, ...]:
    return tuple(JavaField(**f) for f in fields)  # type: ignore[arg-type]


def _step_definition_from_dict(d: dict[str, object]) -> StepDefinitionAsset:
    base = _without_kind(d)
    return StepDefinitionAsset(
        **{
            **base,
            "parameters": _parameters_from_dicts(d["parameters"]),  # type: ignore[arg-type]
            "semantic_tags": tuple(d["semantic_tags"]),  # type: ignore[arg-type]
        }
    )


def _page_object_from_dict(d: dict[str, object]) -> PageObjectAsset:
    base = _without_kind(d)
    return PageObjectAsset(
        **{
            **base,
            "fields": _fields_from_dicts(d["fields"]),  # type: ignore[arg-type]
            "locators": _fields_from_dicts(d["locators"]),  # type: ignore[arg-type]
            "methods": _methods_from_dicts(d["methods"]),  # type: ignore[arg-type]
            "semantic_tags": tuple(d["semantic_tags"]),  # type: ignore[arg-type]
        }
    )


def _utility_from_dict(d: dict[str, object]) -> UtilityAsset:
    base = _without_kind(d)
    return UtilityAsset(
        **{
            **base,
            "fields": _fields_from_dicts(d["fields"]),  # type: ignore[arg-type]
            "methods": _methods_from_dicts(d["methods"]),  # type: ignore[arg-type]
            "semantic_tags": tuple(d["semantic_tags"]),  # type: ignore[arg-type]
        }
    )


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
]
