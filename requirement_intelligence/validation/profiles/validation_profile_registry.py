"""Validation Profile Registry — sole owner of the governed profile definitions.

The :class:`ValidationProfileRegistry` is the single source of truth for the
immutable, governed :class:`ValidationProfileDefinition` set. It owns **profile
definitions only**:

* it never constructs validators,
* it never executes validation,
* it never registers rules.

Consumers (the Validation Factory, via :class:`PlatformContext`) *read* a profile
from this registry and build a validator for it; the registry itself does none of
that. New profiles are added here additively; existing profile identities never
change (a profile is a permanent governed identity, never an alias).
"""

from __future__ import annotations

from typing import ClassVar

from requirement_intelligence.validation.profiles.validation_profile_definition import (
    ValidationProfileDefinition,
)
from requirement_intelligence.validation.validation_rule_layer import ValidationLayer

# Governed profile identities (permanent). New names may be appended additively;
# existing names never change or get reused.
DEFAULT = "default"
STRICT = "strict"
TRANSPORT_ONLY = "transport-only"
SYNTAX_ONLY = "syntax-only"
SCHEMA_ONLY = "schema-only"
CONTENT_REVIEW = "content-review"

#: The implemented validation layers, in Rule-Catalog order.
_ALL_IMPLEMENTED_LAYERS: tuple[ValidationLayer, ...] = (
    ValidationLayer.TRANSPORT,
    ValidationLayer.SYNTAX,
    ValidationLayer.SCHEMA,
    ValidationLayer.CONTENT,
    ValidationLayer.REASONING,
)


class UnknownValidationProfileError(ValueError):
    """Raised when a requested profile name is not a governed profile."""


class ValidationProfileRegistry:
    """Read-only catalogue of the governed :class:`ValidationProfileDefinition` set.

    The registry owns definitions only. It is deterministic and side-effect free:
    every instance exposes the same immutable governed profiles.
    """

    # The single source of truth. Each profile is a permanent governed identity;
    # `default`, `strict`, and `content-review` intentionally enable the same
    # layers today, yet remain separate profiles so any can diverge later.
    _PROFILES: ClassVar[dict[str, ValidationProfileDefinition]] = {
        DEFAULT: ValidationProfileDefinition(
            name=DEFAULT,
            description="Runs every implemented rule (all implemented layers).",
            enabled_layers=_ALL_IMPLEMENTED_LAYERS,
        ),
        STRICT: ValidationProfileDefinition(
            name=STRICT,
            description=(
                "Runs every implemented rule. A distinct governed identity from "
                "'default' so future versions may diverge without an architectural change."
            ),
            enabled_layers=_ALL_IMPLEMENTED_LAYERS,
        ),
        TRANSPORT_ONLY: ValidationProfileDefinition(
            name=TRANSPORT_ONLY,
            description="Runs only the Transport layer.",
            enabled_layers=(ValidationLayer.TRANSPORT,),
        ),
        SYNTAX_ONLY: ValidationProfileDefinition(
            name=SYNTAX_ONLY,
            description="Runs the Transport and Syntax layers.",
            enabled_layers=(ValidationLayer.TRANSPORT, ValidationLayer.SYNTAX),
        ),
        SCHEMA_ONLY: ValidationProfileDefinition(
            name=SCHEMA_ONLY,
            description="Runs the Transport, Syntax, and Schema layers.",
            enabled_layers=(
                ValidationLayer.TRANSPORT,
                ValidationLayer.SYNTAX,
                ValidationLayer.SCHEMA,
            ),
        ),
        CONTENT_REVIEW: ValidationProfileDefinition(
            name=CONTENT_REVIEW,
            description=(
                "Runs Transport, Syntax, Schema, Content, and Reasoning. A distinct "
                "governed identity, currently equivalent in breadth to 'default'."
            ),
            enabled_layers=_ALL_IMPLEMENTED_LAYERS,
        ),
    }

    #: The default profile applied when none is explicitly requested.
    DEFAULT_PROFILE_NAME = DEFAULT

    def get(self, name: str | None = None) -> ValidationProfileDefinition:
        """Return the governed profile for *name* (default profile when ``None``).

        Parameters
        ----------
        name:
            The governed profile identity, or ``None`` for the default profile.

        Raises
        ------
        UnknownValidationProfileError
            If *name* is not a governed profile.
        """
        resolved = self.DEFAULT_PROFILE_NAME if name is None else name
        try:
            return self._PROFILES[resolved]
        except KeyError as exc:
            raise UnknownValidationProfileError(
                f"Unknown validation profile: {name!r}. "
                f"Valid profiles are: {self.names()}."
            ) from exc

    def all(self) -> tuple[ValidationProfileDefinition, ...]:
        """Return every governed profile, in declared order."""
        return tuple(self._PROFILES.values())

    def names(self) -> list[str]:
        """Return every governed profile name, in declared order."""
        return list(self._PROFILES.keys())

    def __contains__(self, name: object) -> bool:
        """Return whether *name* is a governed profile identity."""
        return name in self._PROFILES
