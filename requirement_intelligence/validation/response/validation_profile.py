"""Validation Profiles — named, immutable selections of validation rules.

A :class:`ValidationProfile` is the conceptual realisation of the Validation
Profile described in ``docs/architecture/response-validator.md`` (§6) and
``docs/architecture/validation-rule-catalog.md`` (§13).  A profile *names* a
breadth of validation; the Response Validator selects exactly one profile per
run, and the rules never know which profile invoked them.

Scope of this module
--------------------
This module provides the **five canonical profiles** as immutable metadata only:

* ``MINIMAL`` · ``STANDARD`` · ``STRICT`` · ``COMPLIANCE`` · ``ENTERPRISE``

It carries **no rule lists yet** — rule discovery and selection arrive with the
first concrete rules.  The public contract is the profile *name set*, the
:class:`ValidationProfile` shape, and :func:`resolve_profile`.  Future profile
expansion (new canonical profiles, custom profiles) must extend this set without
changing that contract.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import ConfigDict
from pydantic.alias_generators import to_camel

from requirement_intelligence.validation.response.response_validator_exceptions import (
    ProfileResolutionError,
)
from shared.contracts.base import Schema


class ValidationProfileName(StrEnum):
    """The canonical validation profile names.

    Lowercase string values serialise cleanly and compare equal to their value.
    New names may be appended in future without changing the public contract.
    """

    MINIMAL = "minimal"
    STANDARD = "standard"
    STRICT = "strict"
    COMPLIANCE = "compliance"
    ENTERPRISE = "enterprise"


#: The profile applied when none is explicitly requested
#: (``docs/architecture/response-validator.md`` §6.2).
DEFAULT_PROFILE_NAME = ValidationProfileName.STANDARD


class ValidationProfile(Schema):
    """An immutable, named selection of validation rules.

    Field names serialise as ``camelCase`` (``name``, ``description``); Python
    attributes stay ``snake_case``.  The model is immutable and strictly
    validated (inherited from :class:`~shared.contracts.base.Schema`).

    Fields
    ------
    name:
        The canonical profile name.
    description:
        A human-readable statement of the profile's intent.

    Notes
    -----
    The profile carries metadata only.  It deliberately holds **no rule list**;
    which rules a profile selects is resolved by the framework when concrete
    rules exist.  Adding such selection later is an additive change behind this
    same shape.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    name: ValidationProfileName
    description: str


#: The canonical profiles, keyed by name.  This is the single source of truth for
#: the profiles the Response Validator may select.
_CANONICAL_PROFILES: dict[ValidationProfileName, ValidationProfile] = {
    ValidationProfileName.MINIMAL: ValidationProfile(
        name=ValidationProfileName.MINIMAL,
        description="The lightest viable gate; Core rules only.",
    ),
    ValidationProfileName.STANDARD: ValidationProfile(
        name=ValidationProfileName.STANDARD,
        description="The default balanced gate; Core plus common Extended rules.",
    ),
    ValidationProfileName.STRICT: ValidationProfile(
        name=ValidationProfileName.STRICT,
        description="Maximum depth for high-stakes analysis; Core plus all Extended rules.",
    ),
    ValidationProfileName.COMPLIANCE: ValidationProfile(
        name=ValidationProfileName.COMPLIANCE,
        description="Coverage tuned to regulatory obligations; Core, Extended, and "
        "Organization (compliance) rules.",
    ),
    ValidationProfileName.ENTERPRISE: ValidationProfile(
        name=ValidationProfileName.ENTERPRISE,
        description="Organization-wide policy enforcement; Core, Extended, and "
        "Organization rules.",
    ),
}


def all_profiles() -> tuple[ValidationProfile, ...]:
    """Return every canonical profile, in declared name order."""
    return tuple(_CANONICAL_PROFILES[name] for name in ValidationProfileName)


def resolve_profile(name: ValidationProfileName | str | None = None) -> ValidationProfile:
    """Resolve a Validation Profile by name.

    Parameters
    ----------
    name:
        The profile to resolve.  Accepts a :class:`ValidationProfileName`, its
        string value, or ``None``.  When ``None``, the default profile
        (:data:`DEFAULT_PROFILE_NAME`, i.e. Standard) is resolved.

    Returns
    -------
    ValidationProfile
        The immutable canonical profile for *name*.

    Raises
    ------
    ProfileResolutionError
        If *name* does not correspond to a canonical profile.
    """
    resolved_name = DEFAULT_PROFILE_NAME if name is None else name
    if not isinstance(resolved_name, ValidationProfileName):
        try:
            resolved_name = ValidationProfileName(resolved_name)
        except ValueError as exc:
            raise ProfileResolutionError(
                f"Unknown validation profile: {name!r}. "
                f"Valid profiles are: {[p.value for p in ValidationProfileName]}."
            ) from exc
    try:
        return _CANONICAL_PROFILES[resolved_name]
    except KeyError as exc:  # pragma: no cover - guards against an unmapped name
        raise ProfileResolutionError(
            f"No canonical profile is defined for {resolved_name!r}."
        ) from exc
