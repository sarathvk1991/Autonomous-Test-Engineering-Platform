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