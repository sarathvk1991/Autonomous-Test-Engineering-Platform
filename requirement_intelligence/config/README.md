# Requirement Intelligence — Configuration

This directory holds the declarative configuration that drives the
connector-based ingestion architecture of the Requirement Intelligence Layer.

## `source-registry.json`

### Purpose

`source-registry.json` is the **single source of truth** for *which* external
systems the Requirement Intelligence Layer ingests from and *how* each one is
wired up. At startup the ingestion orchestrator reads this registry and, for
every enabled source, resolves the declared connector and parser, reads from the
configured input, and routes the result into the declared output category.

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
| `parserClass`     | Fully-qualified import path to the parser that normalizes raw data. |
| `inputMode`       | How data is acquired: `FILE` (Phase 1 POC) or `API` (future). |
| `inputPath`       | For `FILE` mode, the path to the exported data file. |
| `outputCategory`  | Normalized output bucket: `FUNCTIONAL_REQUIREMENT`, `SECURITY_FINDING`, or `QUALITY_FINDING`. |
| `priority`        | Ingestion ordering hint (lower runs first). |
| `requiredForPhase`| Whether the source is mandatory for the current phase. |
| `description`     | Short explanation of what the source provides. |

`defaults` and `supportedInputModes` at the top of the file let new entries omit
common values and document which modes the architecture understands.

### Enabling and disabling a source

Toggling a source is a configuration change only — **no code change is
required**:

- **Enable:** set `"enabled": true` on the source entry.
- **Disable:** set `"enabled": false`.

Disabled sources are skipped entirely by the orchestrator. Their connector and
parser are never imported or invoked, so a source can be left in the registry
(for documentation or staged rollout) without affecting a running pipeline.

### Adding a new source later

The registry is designed to be extended without redesign. To add a source:

1. **Implement a connector** under `requirement_intelligence/connectors/<source>/`
   that subclasses `BaseConnector`.
2. **Implement a parser** under `requirement_intelligence/parsers/<source>/`
   that subclasses `BaseParser` and emits one of the supported output
   categories.
3. **Add an entry** to the `sources` array in `source-registry.json` with the
   fields above, pointing `connectorClass` / `parserClass` at the new classes.
4. **Choose the input mode.** Use `FILE` with an `inputPath` for the POC. When
   API ingestion lands, switch `inputMode` to `API` and add the connection
   details the connector expects — the entry shape stays the same, so no
   structural migration is needed.
5. **Set `enabled`** to `true` when the source is ready to run.

Because connectors and parsers are referenced by fully-qualified class path, the
orchestrator never needs to know about specific sources at the code level —
adding a source is purely additive.

### Why the registry must not contain business logic

The registry stays strictly declarative for several reasons:

- **Separation of concerns.** *What* to ingest (this file) is kept apart from
  *how* to ingest it (connectors) and *how* to interpret it (parsers).
- **Safe to edit.** Operators can enable, disable, reorder, or repoint sources
  without touching or redeploying code, and without risk of introducing logic
  bugs into a JSON file.
- **Testable and reviewable.** Logic lives in connector/parser classes that can
  be unit-tested in isolation; the registry can be validated against a schema.
- **Extensible by design.** New input modes (e.g. `API`) and new sources are
  added by extending data, not by rewriting a dispatch block. Embedding logic
  here would couple the registry to today's sources and defeat that goal.

Keep transformations, authentication, retries, pagination, field mapping, and
any conditional handling inside connectors and parsers — never in the registry.
