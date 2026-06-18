# infrastructure/config

Holds infrastructure-level configuration helpers that are **not** the
application settings themselves (those live in `app/core/settings.py`).

Use this package for things like:

- Connector-specific config dataclasses derived from `Settings`.
- Constants for external API versions / endpoints.
- Helpers that translate `Settings` into a third-party SDK's config object.

The rule: `app/core/settings.py` is the single source of validated config;
this package adapts it for individual infrastructure clients.
