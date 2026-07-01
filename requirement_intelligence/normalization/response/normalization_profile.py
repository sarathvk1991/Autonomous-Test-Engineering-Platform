"""Normalization Profiles — named, immutable selections of normalization breadth.

A :class:`NormalizationProfile` is the normalization sibling of the Validation
Profile (``docs/architecture/response-validator.md`` §6): a profile *names* a
breadth of normalization, the Response Normalizer selects exactly one profile per
run, and the responsibilities never know which profile invoked them.

Scope of this module
--------------------
This module provides the **four canonical profiles** as immutable metadata only:

* ``MINIMAL`` · ``STANDARD`` · ``STRICT`` · ``ENTERPRISE``

It carries **no responsibility lists yet** — responsibility discovery and
selection arrive with the first concrete ``NORMALIZATION-00NN`` responsibilities.
The public contract is the profile *name set*, the :class:`NormalizationProfile`
shape, and :func:`resolve_profile`.  Future profile expansion (new canonical
profiles, custom profiles) must extend this set without changing that contract.

Deliberate deviation from Validation Profiles
---------------------------------------------
The validation profiles include a ``COMPLIANCE`` name because validation carries
Organization/compliance *rules*.  Normalization has **no rules, no layers, and no
severity** (Response Normalization Contract §10) — a profile only names how much
*structure-recovery breadth* a future responsibility set will apply — so the
canonical set is the four breadth-oriented names above, without ``COMPLIANCE``.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import ConfigDict
from pydantic.alias_generators import to_camel

from requirement_intelligence.normalization.response.response_normalizer_exceptions import (
    ProfileResolutionError,
)
from shared.contracts.base import Schema


class NormalizationProfileName(StrEnum):
    """The canonical normalization profile names.

    Lowercase string values serialise cleanly and compare equal to their value.
    New names may be appended in future without changing the public contract.
    """

    MINIMAL = "minimal"
    STANDARD = "standard"
    STRICT = "strict"
    ENTERPRISE = "enterprise"


#: The profile applied when none is explicitly requested.
DEFAULT_PROFILE_NAME = NormalizationProfileName.STANDARD


class NormalizationProfile(Schema):
    """An immutable, named selection of normalization breadth.

    Field names serialise as ``camelCase`` (``name``, ``description``); Python
    attributes stay ``snake_case``.  The model is immutable and strictly validated
    (inherited from :class:`~shared.contracts.base.Schema`).

    Fields
    ------
    name:
        The canonical profile name.
    description:
        A human-readable statement of the profile's intent.

    Notes
    -----
    The profile carries metadata only.  It deliberately holds **no responsibility
    list**; which responsibilities a profile selects is resolved by the framework
    when concrete responsibilities exist.  Adding such selection later is an
    additive change behind this same shape.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    name: NormalizationProfileName
    description: str


#: The canonical profiles, keyed by name.  Single source of truth for the profiles
#: the Response Normalizer may select.
_CANONICAL_PROFILES: dict[NormalizationProfileName, NormalizationProfile] = {
    NormalizationProfileName.MINIMAL: NormalizationProfile(
        name=NormalizationProfileName.MINIMAL,
        description="The lightest structure recovery; core normalization responsibilities only.",
    ),
    NormalizationProfileName.STANDARD: NormalizationProfile(
        name=NormalizationProfileName.STANDARD,
        description="The default balanced breadth; core plus common normalization "
        "responsibilities.",
    ),
    NormalizationProfileName.STRICT: NormalizationProfile(
        name=NormalizationProfileName.STRICT,
        description="Maximum breadth for high-stakes analysis; core plus all normalization "
        "responsibilities.",
    ),
    NormalizationProfileName.ENTERPRISE: NormalizationProfile(
        name=NormalizationProfileName.ENTERPRISE,
        description="Organization-wide breadth; core plus all normalization responsibilities "
        "and organization-specific observations.",
    ),
}


def all_profiles() -> tuple[NormalizationProfile, ...]:
    """Return every canonical profile, in declared name order."""
    return tuple(_CANONICAL_PROFILES[name] for name in NormalizationProfileName)


def resolve_profile(
    name: NormalizationProfileName | str | None = None,
) -> NormalizationProfile:
    """Resolve a Normalization Profile by name.

    Parameters
    ----------
    name:
        The profile to resolve.  Accepts a :class:`NormalizationProfileName`, its
        string value, or ``None``.  When ``None``, the default profile
        (:data:`DEFAULT_PROFILE_NAME`, i.e. Standard) is resolved.

    Returns
    -------
    NormalizationProfile
        The immutable canonical profile for *name*.

    Raises
    ------
    ProfileResolutionError
        If *name* does not correspond to a canonical profile.
    """
    resolved_name = DEFAULT_PROFILE_NAME if name is None else name
    if not isinstance(resolved_name, NormalizationProfileName):
        try:
            resolved_name = NormalizationProfileName(resolved_name)
        except ValueError as exc:
            raise ProfileResolutionError(
                f"Unknown normalization profile: {name!r}. "
                f"Valid profiles are: {[p.value for p in NormalizationProfileName]}."
            ) from exc
    try:
        return _CANONICAL_PROFILES[resolved_name]
    except KeyError as exc:  # pragma: no cover - guards against an unmapped name
        raise ProfileResolutionError(
            f"No canonical profile is defined for {resolved_name!r}."
        ) from exc
