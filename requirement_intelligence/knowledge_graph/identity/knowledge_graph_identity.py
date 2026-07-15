"""Strongly typed identity value objects for the Knowledge Graph Framework.

These follow the precedent set by the Engineering Context Orchestration identity
model (ADR-0015), the Grounding Framework identity model (ADR-0016), the Quality
Governance identity model (ADR-0017), the Requirement Enhancement identity model
(ADR-0018), the Recommendation Framework identity model (ADR-0019), and the
Continuous Improvement Framework identity model (ADR-0022): immutable, validated,
string-backed identifiers and semantic-version value objects, each serialising to
and validating from a **plain JSON string**.

The base classes are duplicated here rather than imported from those subsystems on
purpose — ADR-0015 §C, ADR-0016 §D6, ADR-0017 (identity module docstring), ADR-0018
§D5, ADR-0019 §D5, and ADR-0022 (identity module docstring) already made the same
call. The Knowledge Graph Framework stays self-contained: it imports no other
subsystem's identity model, and — like Continuous Improvement, unlike every Layer 1
subsystem — it imports no Layer 1 subsystem's identity model either (ADR-0021
§Stage 8: it consumes Historical Truth only).

Determinism
-----------
Every ``for_*`` factory below is a **pure function** of its inputs — no UUID, no
clock. The same historical dataset, and the same node/edge/subgraph/observation/
finding key, always mints the same id, which is what lets a ``KnowledgeGraphResult``
be compared and reproduced across builds over the same dataset (mirroring ADR-0022's
``ContinuousImprovementResultId.for_dataset`` precedent, itself lifted from ADR-0019
Recommendation 2/3 to a cross-execution scope per ADR-0021).

Version axis independence (frozen, CAP-084A, ADR-0023 §D5/§D6)
----------------------------------------------------------------
Six distinct version types exist, each evolving on its own axis — tuning one never
forces a change to any other, and vice versa:

* :class:`KnowledgeGraphFrameworkVersion` — the framework's code/contract.
* :class:`KnowledgePolicyVersion` — one governed ``KnowledgeGraphPolicy``.
* :class:`KnowledgeNodeVersion` — the ``KnowledgeNode`` schema (reserved; not yet
  stamped onto a model field, exactly as ``ImprovementTrendVersion`` was reserved by
  ADR-0022 before any model carried it).
* :class:`KnowledgeEdgeVersion` — the ``KnowledgeEdge`` schema (reserved).
* :class:`KnowledgeObservationVersion` — the ``KnowledgeObservation`` schema
  (reserved).
* :class:`KnowledgeGraphResultVersion` — the ``KnowledgeGraphResult`` runtime
  contract (the only axis actually stamped onto a model today,
  ``KnowledgeGraphResult.result_version``).

``KnowledgeSubgraph``, ``KnowledgeFinding``, and ``KnowledgeSummary`` /
``KnowledgeMetrics`` carry no version field of their own by the same design choice
ADR-0019 made for ``RecommendationGroup`` / ``RecommendationSummary`` and ADR-0022
made for ``ImprovementFinding`` / ``ImprovementSummary`` — no new version type is
invented here to cover them.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Any, ClassVar

from pydantic import GetCoreSchemaHandler
from pydantic_core import core_schema

# URL- and filename-safe identifier shape, identical to every prior subsystem's:
# lower-case, starts and ends alphanumeric, '.', '_', ':' or '-' permitted between.
_IDENTIFIER_RE = re.compile(r"^[a-z0-9](?:[a-z0-9._:-]*[a-z0-9])?$")

_SEMVER_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")


@dataclass(frozen=True)
class _StringIdentifier:
    """Base for immutable, validated, string-backed identifiers."""

    value: str

    #: Human-readable type name used in error messages.
    _LABEL: ClassVar[str] = "identifier"

    def __post_init__(self) -> None:
        """Validate the identifier's shape. Raises :class:`ValueError` if invalid."""
        if not isinstance(self.value, str) or not _IDENTIFIER_RE.match(self.value):
            raise ValueError(
                f"Invalid {self._LABEL} {self.value!r}. Expected a non-empty, "
                f"lower-case string of letters, digits, '.', '_', ':' or '-', "
                f"starting and ending with a letter or digit."
            )

    @classmethod
    def parse(cls, raw: str) -> Any:
        """Build an identifier from *raw*, tolerating surrounding whitespace."""
        if not isinstance(raw, str):
            raise ValueError(f"Invalid {cls._LABEL}: expected a string, got {type(raw).__name__}.")
        return cls(raw.strip())

    def __str__(self) -> str:
        """Return the canonical string form (round-trips through :meth:`parse`)."""
        return self.value

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        """Validate from a plain string and serialise back to a plain string."""
        from_string = core_schema.chain_schema(
            [
                core_schema.str_schema(),
                core_schema.no_info_plain_validator_function(cls.parse),
            ]
        )
        return core_schema.json_or_python_schema(
            json_schema=from_string,
            python_schema=core_schema.union_schema(
                [core_schema.is_instance_schema(cls), from_string]
            ),
            serialization=core_schema.plain_serializer_function_ser_schema(
                str, return_schema=core_schema.str_schema()
            ),
        )


@dataclass(frozen=True)
class KnowledgePolicyId(_StringIdentifier):
    """The permanent, governed identity of a ``KnowledgeGraphPolicy``.

    A policy id is an identity, never an alias: two policies may currently express
    identical rules yet remain distinct ids, mirroring ``ImprovementPolicyId``.
    """

    _LABEL: ClassVar[str] = "knowledge policy id"


@dataclass(frozen=True)
class KnowledgeGraphId(_StringIdentifier):
    """The deterministic identity of one canonical platform graph.

    A pure function of the historical dataset the graph is built from — the same
    dataset always names the same graph, mirroring
    ``ContinuousImprovementResultId.for_dataset``.
    """

    _LABEL: ClassVar[str] = "knowledge graph id"

    @classmethod
    def for_dataset(cls, dataset_id: str) -> KnowledgeGraphId:
        """Mint the deterministic graph id for *dataset_id*."""
        dataset = str(dataset_id).strip()
        if not dataset:
            raise ValueError("Cannot mint a knowledge graph id from an empty dataset id.")
        digest = hashlib.sha256(dataset.encode()).hexdigest()
        return cls(f"kg-{digest[:12]}")


@dataclass(frozen=True)
class KnowledgeNodeId(_StringIdentifier):
    """The deterministic identity of one ``KnowledgeNode``.

    A pure function of the node's governed type and the id of the platform entity
    it references — no UUID, no clock. A future engine mints these; this class only
    shapes them.
    """

    _LABEL: ClassVar[str] = "knowledge node id"

    @classmethod
    def for_entity(cls, node_type: str, referenced_id: str) -> KnowledgeNodeId:
        """Mint the deterministic id for the node naming *referenced_id* of *node_type*."""
        node_type_value = str(node_type).strip()
        referenced = str(referenced_id).strip()
        if not node_type_value:
            raise ValueError("Cannot mint a knowledge node id from an empty node type.")
        if not referenced:
            raise ValueError("Cannot mint a knowledge node id from an empty referenced id.")
        digest = hashlib.sha256(f"{node_type_value}:{referenced}".encode()).hexdigest()
        return cls(f"kn-{digest[:12]}")


@dataclass(frozen=True)
class KnowledgeEdgeId(_StringIdentifier):
    """The deterministic identity of one ``KnowledgeEdge``.

    A pure function of the edge's governed type and its two endpoint node ids —
    no UUID, no clock.
    """

    _LABEL: ClassVar[str] = "knowledge edge id"

    @classmethod
    def for_relationship(
        cls, edge_type: str, source_node_id: str, target_node_id: str
    ) -> KnowledgeEdgeId:
        """Mint the deterministic id for the *edge_type* edge from *source* to *target*."""
        edge_type_value = str(edge_type).strip()
        source = str(source_node_id).strip()
        target = str(target_node_id).strip()
        if not edge_type_value:
            raise ValueError("Cannot mint a knowledge edge id from an empty edge type.")
        if not source or not target:
            raise ValueError("Cannot mint a knowledge edge id from an empty endpoint node id.")
        digest = hashlib.sha256(f"{edge_type_value}:{source}:{target}".encode()).hexdigest()
        return cls(f"ke-{digest[:12]}")


@dataclass(frozen=True)
class KnowledgeSubgraphId(_StringIdentifier):
    """The deterministic identity of one ``KnowledgeSubgraph``.

    A pure function of the graph it belongs to and a stable per-graph ordinal,
    exactly mirroring ``ImprovementFindingId.for_ordinal``.
    """

    _LABEL: ClassVar[str] = "knowledge subgraph id"

    @classmethod
    def for_ordinal(cls, graph_id: str, ordinal: int) -> KnowledgeSubgraphId:
        """Mint the deterministic id for the *ordinal*-th subgraph of *graph_id*."""
        graph = str(graph_id).strip()
        if not graph:
            raise ValueError("Cannot mint a knowledge subgraph id from an empty graph id.")
        if ordinal < 0:
            raise ValueError("Cannot mint a knowledge subgraph id from a negative ordinal.")
        digest = hashlib.sha256(f"{graph}:{ordinal}".encode()).hexdigest()
        return cls(f"ks-{digest[:12]}")


@dataclass(frozen=True)
class KnowledgeObservationId(_StringIdentifier):
    """The deterministic identity of one ``KnowledgeObservation``.

    A pure function of the graph it belongs to and a stable per-graph ordinal,
    exactly mirroring ``KnowledgeSubgraphId.for_ordinal``.
    """

    _LABEL: ClassVar[str] = "knowledge observation id"

    @classmethod
    def for_ordinal(cls, graph_id: str, ordinal: int) -> KnowledgeObservationId:
        """Mint the deterministic id for the *ordinal*-th observation of *graph_id*."""
        graph = str(graph_id).strip()
        if not graph:
            raise ValueError("Cannot mint a knowledge observation id from an empty graph id.")
        if ordinal < 0:
            raise ValueError("Cannot mint a knowledge observation id from a negative ordinal.")
        digest = hashlib.sha256(f"{graph}:{ordinal}".encode()).hexdigest()
        return cls(f"ko-{digest[:12]}")


@dataclass(frozen=True)
class KnowledgeFindingId(_StringIdentifier):
    """The deterministic identity of one ``KnowledgeFinding``.

    A pure function of the graph it belongs to and a stable per-graph ordinal,
    exactly mirroring ``KnowledgeSubgraphId.for_ordinal``.
    """

    _LABEL: ClassVar[str] = "knowledge finding id"

    @classmethod
    def for_ordinal(cls, graph_id: str, ordinal: int) -> KnowledgeFindingId:
        """Mint the deterministic id for the *ordinal*-th finding of *graph_id*."""
        graph = str(graph_id).strip()
        if not graph:
            raise ValueError("Cannot mint a knowledge finding id from an empty graph id.")
        if ordinal < 0:
            raise ValueError("Cannot mint a knowledge finding id from a negative ordinal.")
        digest = hashlib.sha256(f"{graph}:{ordinal}".encode()).hexdigest()
        return cls(f"kf-{digest[:12]}")


@dataclass(frozen=True)
class KnowledgeGraphResultId(_StringIdentifier):
    """The deterministic identity of one ``KnowledgeGraphResult``.

    A pure function of the graph it was assembled for, exactly mirroring
    ``ContinuousImprovementResultId.for_dataset`` — one level down the reference
    chain (``HistoricalDatasetReference`` names the dataset, ``KnowledgeGraphId``
    names the graph built from it, and this id names one build's result).
    """

    _LABEL: ClassVar[str] = "knowledge graph result id"

    @classmethod
    def for_graph(cls, graph_id: str) -> KnowledgeGraphResultId:
        """Mint the deterministic result id for *graph_id*."""
        graph = str(graph_id).strip()
        if not graph:
            raise ValueError("Cannot mint a knowledge graph result id from an empty graph id.")
        digest = hashlib.sha256(graph.encode()).hexdigest()
        return cls(f"kgr-{digest[:12]}")


@dataclass(frozen=True, order=True)
class _SemanticVersion:
    """Base for immutable, comparable ``MAJOR.MINOR.PATCH`` version value objects."""

    major: int
    minor: int
    patch: int

    _LABEL: ClassVar[str] = "version"

    def __post_init__(self) -> None:
        """Reject negative components. Raises :class:`ValueError` if invalid."""
        if self.major < 0 or self.minor < 0 or self.patch < 0:
            raise ValueError(
                f"Invalid {self._LABEL} {self.major}.{self.minor}.{self.patch}: "
                f"components must be non-negative."
            )

    @classmethod
    def parse(cls, version_string: str) -> Any:
        """Parse ``MAJOR.MINOR.PATCH`` into a version value object."""
        if not isinstance(version_string, str):
            raise ValueError(
                f"Invalid {cls._LABEL}: expected a string, got {type(version_string).__name__}."
            )
        match = _SEMVER_RE.match(version_string.strip())
        if not match:
            raise ValueError(
                f"Invalid {cls._LABEL} string {version_string!r}. Expected "
                f"MAJOR.MINOR.PATCH with non-negative integers (e.g. '1.0.0')."
            )
        return cls(int(match.group(1)), int(match.group(2)), int(match.group(3)))

    def __str__(self) -> str:
        """Return the canonical ``MAJOR.MINOR.PATCH`` string form."""
        return f"{self.major}.{self.minor}.{self.patch}"

    def is_compatible_with(self, other: _SemanticVersion) -> bool:
        """Return ``True`` when this version is backwards-compatible with *other*."""
        return self.major == other.major

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        """Validate from a ``"1.0.0"`` string and serialise back to one."""
        from_string = core_schema.chain_schema(
            [
                core_schema.str_schema(),
                core_schema.no_info_plain_validator_function(cls.parse),
            ]
        )
        return core_schema.json_or_python_schema(
            json_schema=from_string,
            python_schema=core_schema.union_schema(
                [core_schema.is_instance_schema(cls), from_string]
            ),
            serialization=core_schema.plain_serializer_function_ser_schema(
                str, return_schema=core_schema.str_schema()
            ),
        )


@dataclass(frozen=True, order=True)
class KnowledgeGraphFrameworkVersion(_SemanticVersion):
    """Semantic version of the Knowledge Graph Framework's code/contract."""

    _LABEL: ClassVar[str] = "knowledge graph framework version"


@dataclass(frozen=True, order=True)
class KnowledgePolicyVersion(_SemanticVersion):
    """Semantic version of one governed ``KnowledgeGraphPolicy``.

    Advances independently of :class:`KnowledgeGraphFrameworkVersion` and
    :class:`KnowledgeGraphResultVersion` (ADR-0021 §Stage 9: no shared version
    axis). Tuning a threshold or a capability switch is a policy-version change,
    never a framework change.
    """

    _LABEL: ClassVar[str] = "knowledge policy version"


@dataclass(frozen=True, order=True)
class KnowledgeNodeVersion(_SemanticVersion):
    """Semantic version of the ``KnowledgeNode`` schema.

    Reserved for a future milestone, exactly as ``ImprovementTrendVersion`` was
    reserved by ADR-0022 §D5 without yet being stamped onto a model field.
    """

    _LABEL: ClassVar[str] = "knowledge node version"


@dataclass(frozen=True, order=True)
class KnowledgeEdgeVersion(_SemanticVersion):
    """Semantic version of the ``KnowledgeEdge`` schema. Reserved (see
    :class:`KnowledgeNodeVersion`)."""

    _LABEL: ClassVar[str] = "knowledge edge version"


@dataclass(frozen=True, order=True)
class KnowledgeObservationVersion(_SemanticVersion):
    """Semantic version of the ``KnowledgeObservation`` schema. Reserved."""

    _LABEL: ClassVar[str] = "knowledge observation version"


@dataclass(frozen=True, order=True)
class KnowledgeGraphResultVersion(_SemanticVersion):
    """Semantic version of the ``KnowledgeGraphResult`` **runtime contract**.

    Independent of the framework, the policy, and every node/edge/observation
    schema version; a change here never forces any of those to change, and vice
    versa — the direct analogue of ``ContinuousImprovementResultVersion``.
    """

    _LABEL: ClassVar[str] = "knowledge graph result version"
