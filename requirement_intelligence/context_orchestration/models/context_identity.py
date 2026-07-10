"""Strongly typed identity value objects for Engineering Context Orchestration.

Before this module, **every identifier in the platform was a raw ``str``** —
``ConsolidatedArtifact.consolidated_id``, ``PromptMetadata.prompt_id``,
``CP1Result.cp1_id``, ``ValidationResult.validation_id``. A raw string is
opaque: nothing prevents a policy id being passed where a context id is
expected, and nothing validates its shape at the boundary.

These are the platform's first strongly typed identifiers. They are scoped to
this subsystem only — **no existing identifier is retyped** (ADR-0015 §D5).

Convention
----------
There was no pre-existing *identifier* pattern to follow, but there was a
pre-existing **value object** pattern:
:class:`~requirement_intelligence.prompts.models.prompt_version.PromptVersion`
is an immutable, comparable ``@dataclass(frozen=True, order=True)`` with a
validating :meth:`parse` classmethod, a canonical :meth:`__str__` round-trip,
and :class:`ValueError` on malformed input. This module adopts that pattern
rather than inventing a second one.

Serialization
-------------
Each identifier serialises to, and validates from, a **plain JSON string** —
never a nested object. So ``EngineeringContext.model_dump(mode="json")``
produces ``{"contextId": "ctx-authentication-4f2a1c9b7e05"}``, which keeps the
platform's JSON contract unchanged in shape and keeps identifiers greppable in
an execution package.

Immutability & equality
-----------------------
All three types are frozen (hashable, usable as dict keys). Equality is
**type-safe by construction**: a dataclass ``__eq__`` compares
``other.__class__ is self.__class__`` first, so ``EngineeringContextId("x")``
never equals ``OrchestrationPolicyId("x")``. That is precisely the confusion a
raw ``str`` permits and this module forbids.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, ClassVar

from pydantic import GetCoreSchemaHandler
from pydantic_core import core_schema

# A conservative, URL- and filename-safe identifier shape. Lower-case only, so
# equality never depends on casing; must start and end alphanumeric, so a value
# can be embedded in a slug, a path, or a manifest key without escaping.
_IDENTIFIER_RE = re.compile(r"^[a-z0-9](?:[a-z0-9._:-]*[a-z0-9])?$")

_SEMVER_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")


@dataclass(frozen=True)
class _StringIdentifier:
    """Base for immutable, validated, string-backed identifiers.

    Subclasses set :attr:`_LABEL` for error messages. Each subclass must itself
    be decorated with ``@dataclass(frozen=True)`` so it generates its own
    ``__eq__`` / ``__hash__`` and therefore compares unequal to every sibling
    identifier type, however identical the underlying string.

    Construction does **not** normalise. Call :meth:`parse` to accept
    surrounding whitespace; the constructor validates and nothing more, so a
    value that round-trips through ``str()`` is always byte-identical.
    """

    value: str

    #: Human-readable type name used in error messages.
    _LABEL: ClassVar[str] = "identifier"

    def __post_init__(self) -> None:
        """Validate the identifier's shape. Raises :class:`ValueError` if invalid."""
        if not isinstance(self.value, str) or not _IDENTIFIER_RE.match(self.value):
            raise ValueError(
                f"Invalid {self._LABEL} {self.value!r}. Expected a non-empty, "
                f"lower-case string of letters, digits, '.', '_', ':' or '-', "
                f"starting and ending with a letter or digit (e.g. 'coverage')."
            )

    @classmethod
    def parse(cls, raw: str) -> Any:
        """Build an identifier from *raw*, tolerating surrounding whitespace.

        Raises:
            ValueError: If *raw* is not a string, or does not match the
                identifier shape once stripped.
        """
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
class EngineeringContextId(_StringIdentifier):
    """The stable, deterministic identity of one :class:`EngineeringContext`.

    Minted by :class:`EngineeringContextBuilder` as a pure function of the
    context's subject and its contributing consolidation groups — never from a
    UUID or a clock, so it satisfies Invariant 7 (Reproducible).
    """

    _LABEL: ClassVar[str] = "engineering context id"


@dataclass(frozen=True)
class OrchestrationPolicyId(_StringIdentifier):
    """The permanent, governed identity of an ``OrchestrationPolicy``.

    A policy id is an identity, never an alias: two policies may currently
    express identical rules yet remain distinct ids, so one can diverge later
    without an architectural change. This mirrors the governed-identity rule
    already applied to ``ValidationProfileDefinition.name``.
    """

    _LABEL: ClassVar[str] = "orchestration policy id"


@dataclass(frozen=True, order=True)
class PolicyVersion:
    """Immutable, comparable semantic version of an ``OrchestrationPolicy``.

    Deliberately mirrors
    :class:`~requirement_intelligence.prompts.models.prompt_version.PromptVersion`
    (same shape, same ``parse``/``__str__`` contract, same major-version
    compatibility rule) rather than importing it, which would couple this
    subsystem to Prompt Governance. ADR-0015 §C records the resulting
    duplication and names ``shared/`` as its eventual home.

    Versioning rules
    ----------------
    PATCH
        Editorial change to the policy's description or reason template that
        cannot change which evidence is selected.
    MINOR
        A rule addition that cannot narrow the evidence a prior version
        selected (e.g. raising a budget).
    MAJOR
        Any change that can alter selected evidence, ordering, or identifiers.
        Every prior baseline is invalidated and must be regenerated.
    """

    major: int
    minor: int
    patch: int

    def __post_init__(self) -> None:
        """Reject negative components. Raises :class:`ValueError` if invalid."""
        if self.major < 0 or self.minor < 0 or self.patch < 0:
            raise ValueError(
                f"Invalid policy version {self.major}.{self.minor}.{self.patch}: "
                f"components must be non-negative."
            )

    @classmethod
    def parse(cls, version_string: str) -> PolicyVersion:
        """Parse ``MAJOR.MINOR.PATCH`` into a :class:`PolicyVersion`.

        Raises:
            ValueError: If *version_string* is not a well-formed semantic version.
        """
        if not isinstance(version_string, str):
            raise ValueError(
                f"Invalid policy version: expected a string, got {type(version_string).__name__}."
            )
        match = _SEMVER_RE.match(version_string.strip())
        if not match:
            raise ValueError(
                f"Invalid policy version string {version_string!r}. Expected "
                f"MAJOR.MINOR.PATCH with non-negative integers (e.g. '1.0.0')."
            )
        return cls(int(match.group(1)), int(match.group(2)), int(match.group(3)))

    def __str__(self) -> str:
        """Return the canonical ``MAJOR.MINOR.PATCH`` string form."""
        return f"{self.major}.{self.minor}.{self.patch}"

    def is_compatible_with(self, other: PolicyVersion) -> bool:
        """Return ``True`` when this version is backwards-compatible with *other*.

        Compatibility is major-version equality, exactly as
        ``PromptVersion.is_compatible_with`` defines it.
        """
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
