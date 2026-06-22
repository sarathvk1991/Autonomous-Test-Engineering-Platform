# Connector Framework

This directory contains the base connector abstraction and connector-specific
exceptions for the Requirement Intelligence Layer.

## Purpose

The connector framework standardizes how external sources such as JIRA,
OWASP ZAP, and SonarQube are accessed.

Connectors are responsible for fetching **raw source records only**.

They must not perform canonical mapping, business logic, requirement
classification, or consolidation.

## Responsibilities

A connector should:

- Identify the source.
- Read source configuration from the source registry.
- Validate source availability.
- Fetch raw source records.
- Return connector metadata.

A connector should not:

- Convert records to canonical schema.
- Apply business rules.
- Group or consolidate records.
- Generate requirements.
- Invoke Azure OpenAI.

## Connector Contract

All connectors must extend `SourceConnector` from `base.py` and implement:

```python
get_source_id() -> str
get_source_name() -> str
validate_connection() -> bool
fetch_raw_records() -> list[dict]
get_metadata() -> dict
```

## Input Modes (FILE vs API)

Every concrete connector supports two input modes. The active mode is selected
**only** from the `inputMode` field of the source's entry in
`config/source-registry.json`. Connectors never decide the mode themselves.

- **FILE** — the **current Phase 1 implementation path**. The connector reads
  raw records from the configured `inputPath`. This is fully implemented today.
- **API** — the **planned Phase 1 end-state**. The connector will fetch raw
  records directly from JIRA, OWASP ZAP, and SonarQube APIs. API mode is
  currently **stubbed**: `_fetch_from_api()` raises `NotImplementedError`, and
  `validate_connection()` only checks that required connection fields are
  present (the live API ping is a TODO).

`inputMode` controls runtime behavior. Each connector dispatches as follows:

```text
fetch_raw_records()
    ├── inputMode == "FILE" -> _fetch_from_file()   # reads inputPath
    ├── inputMode == "API"  -> _fetch_from_api()     # stubbed for now
    └── otherwise           -> ConnectorConfigurationError

validate_connection()
    ├── FILE mode  -> inputPath exists and is readable
    ├── API mode   -> required connection fields exist (ping is TODO)
    └── invalid    -> ConnectorConfigurationError
```

Shared FILE-mode I/O, mode resolution, and API-config validation live in
`connector_io.py` so connectors stay thin and consistent.

## Downstream independence

Connectors return raw source records as `list[dict]` regardless of input mode.
The parser layer, consolidation engine, CP1 validation engine, and output writer
**must not depend on whether records came from FILE or API mode**. Switching a
source from FILE to API is a registry change only and must not require changes
in any downstream layer.

## Exceptions

Connectors raise typed exceptions from
`requirement_intelligence.connectors.connector_exceptions`:

- `ConnectorConfigurationError` — invalid or missing configuration (e.g. an
  unsupported `inputMode`, a missing `inputPath` in FILE mode, or missing API
  connection fields).
- `ConnectorConnectionError` — the source cannot be reached or validated (e.g. a
  missing or unreadable file, or an unreachable API endpoint).
- `ConnectorFetchError` — raw records cannot be read or fetched.