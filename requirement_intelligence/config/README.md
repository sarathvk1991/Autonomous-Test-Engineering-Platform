# Requirement Intelligence — Configuration

This directory holds the declarative configuration that drives the
connector-based ingestion architecture of the Requirement Intelligence Layer.

## `source-registry.json`

### Purpose

`source-registry.json` is the **single source of truth** for *which* external
systems the Requirement Intelligence Layer ingests from and *how* each one is
wired up. At startup the ingestion orchestrator reads this registry and, for
every enabled source, resolves the declared connector and mapper, reads from the
configured input (FILE or API), and routes the result into the declared output
category.

The registry is **configuration, not code**. It describes sources; it does not
process them.

### Anatomy of a source entry

Each object in the `sources` array describes one ingestion source:

| Field             | Meaning |
| ----------------- | ------- |
| `sourceId`        | Stable, lowercase, machine-readable identifier (used as a lookup key). |
| `sourceName`      | Human-readable display name. |
| `sourceType`      | Category of source: `REQUIREMENT_SOURCE`, `DAST_SOURCE`, or `SAST_SOURCE`. |
| `enabled`         | Whether the orchestrator loads this source. |
| `connectorClass`  | Fully-qualified import path to the connector that retrieves raw data. |
| `mapperClass`     | Fully-qualified import path to the mapper that maps raw records to the canonical `SourceArtifact`. |
| `inputMode`       | How data is acquired: `FILE` (exported dump) or `API` (live REST). |
| `inputPath`       | For `FILE` mode, the path to the exported data file. |
| `connection`      | For `API` mode, the auth type and the **names of the environment variables** holding the base URL and credentials (never the secrets themselves). |
| `api`             | For `API` mode, non-secret transport tuning: `timeoutSeconds`, `retry`, `pagination`, and optional `incremental`. |
| `outputCategory`  | Normalized output bucket: `FUNCTIONAL_REQUIREMENT`, `SECURITY_FINDING`, or `QUALITY_FINDING`. |
| `priority`        | Ingestion ordering hint (lower runs first). |
| `requiredForPhase`| Whether the source is mandatory for the current phase. |
| `description`     | Short explanation of what the source provides. |

`defaults` and `supportedInputModes` at the top of the file let new entries omit
common values and document which modes the architecture understands.

> **Secrets never live in this file.** In `API` mode the `connection` block
> stores only the *names* of environment variables (e.g. `"baseUrlEnv":
> "JIRA_BASE_URL"`, `"authTokenEnv": "JIRA_API_TOKEN"`). The connector resolves
> them from the environment at runtime, so no URL or credential is ever
> committed to code or configuration.

## Source Categories

Source categories are used for reporting, analytics, governance dashboards,
and future rule engines.

Supported categories:

- FUNCTIONAL
- SECURITY
- QUALITY

A source type identifies the technical nature of the source
(REQUIREMENT_SOURCE, DAST_SOURCE, SAST_SOURCE).

A source category identifies the business classification of the data
(FUNCTIONAL, SECURITY, QUALITY).

### Enabling and disabling a source

Toggling a source is a configuration change only — **no code change is
required**:

- **Enable:** set `"enabled": true` on the source entry.
- **Disable:** set `"enabled": false`.

Disabled sources are skipped entirely by the orchestrator. Their connector and
mapper are never imported or invoked, so a source can be left in the registry
(for documentation or staged rollout) without affecting a running pipeline.

### Adding a new source later

The registry is designed to be extended without redesign. To add a source:

1. **Implement a connector** under `requirement_intelligence/connectors/<source>/`
   that subclasses `SourceConnector`.
2. **Implement a mapper** under `requirement_intelligence/mappers/` that
   subclasses `BaseMapper` and emits canonical `SourceArtifact` records.
3. **Add an entry** to the `sources` array in `source-registry.json` with the
   fields above, pointing `connectorClass` / `mapperClass` at the new classes.
4. **Choose the input mode.** Use `FILE` with an `inputPath` for an exported
   dump, or `API` with a `connection`/`api` block for live ingestion — the entry
   shape stays the same, so switching modes is a configuration change only.
5. **Set `enabled`** to `true` when the source is ready to run.

Because connectors and mappers are referenced by fully-qualified class path, the
orchestrator never needs to know about specific sources at the code level —
adding a source is purely additive.

### Why the registry must not contain business logic

The registry stays strictly declarative for several reasons:

- **Separation of concerns.** *What* to ingest (this file) is kept apart from
  *how* to fetch it (connectors) and *how* to map it (mappers).
- **Safe to edit.** Operators can enable, disable, reorder, or repoint sources
  without touching or redeploying code, and without risk of introducing logic
  bugs into a JSON file.
- **Testable and reviewable.** Logic lives in connector/mapper classes that can
  be unit-tested in isolation; the registry stays purely declarative data.
- **Extensible by design.** New input modes and new sources are added by
  extending data, not by rewriting a dispatch block. Embedding logic here would
  couple the registry to today's sources and defeat that goal.

Keep transformations, authentication, retries, pagination, field mapping, and
any conditional handling inside connectors and mappers — never in the registry.
