# Connector Framework

This directory contains the core abstractions and custom exceptions for integrating external source systems into the Requirement Intelligence Layer.

## Purpose

The connector layer provides a standardized integration framework for external tools. It defines a uniform contract that all source integrations (such as JIRA, OWASP ZAP, SonarQube) must implement.

### Why it exists

- **Decouple Source Systems**: Isolate external integration details (e.g. API authentication, request/response structures, parsing rules) from the core data consolidation engine.
- **Enable Plug-and-Play Development**: Connectors can be independently developed, registered, and integrated into workflows via the registry without altering orchestration code.
- **Extend Support Easily**: Add future connectors (e.g., GitHub, Azure DevOps, Veracode) by subclassing the interface, without impacting existing components.

---

## Architecture & Components

The framework is comprised of:
1. **[base.py](base.py)**: Defines `SourceConnector`, the abstract base class specifying methods for initialization, connectivity, validation, fetching, parsing, and metadata.
2. **[connector_exceptions.py](connector_exceptions.py)**: Defines a hierarchy of typed, custom exceptions for common failure modes (configuration, connectivity, fetching, parsing).

---

## Implementation Guide

To create a new source connector:
1. **Extend `SourceConnector`**: Your class must inherit from `SourceConnector` defined in `requirement_intelligence.connectors.base`.
2. **Implement All Abstract Methods**:
   - `get_source_id(self) -> str` (e.g., return `'jira'`)
   - `get_source_name(self) -> str` (e.g., return `'JIRA'`)
   - `connect(self) -> bool` (establish connection)
   - `validate_connection(self) -> bool` (validate reachability and configuration)
   - `fetch_raw_records(self) -> list[dict[str, Any]]` (retrieve raw payloads)
   - `parse_records(self, raw_records: list[dict[str, Any]]) -> list[dict[str, Any]]` (transform raw payloads to common representation)
   - `get_metadata(self) -> dict[str, Any]` (declare metadata like version, supported entities)
3. **Use Custom Exceptions**: Connectors should raise the appropriate custom exceptions from `connector_exceptions.py` when failures occur:
   - Configuration errors (missing credentials, URLs) -> `ConnectorConfigurationError`
   - Connection/reachability issues (DNS, timeout) -> `ConnectorConnectionError`
   - Fetch/API issues (unauthorized, rate limits) -> `ConnectorFetchError`
   - Processing/parsing issues (unexpected JSON, validation failure) -> `ConnectorParseError`

---

## Constraints

When working in this directory:
- **Do NOT** implement concrete connectors (e.g., JIRA, OWASP ZAP, or SonarQube) within this framework package.
- **Do NOT** write business logic, call external APIs, or perform file I/O within the abstract base definitions.
- Focus strictly on the reusable, generic contract definitions.
