# ADR 0001 — Modular Monolith as a Single Deployable Unit

- **Status:** Accepted
- **Date:** 2026-06-18

## Context
The platform spans seven cooperating layers that share a domain model and a
single end-to-end pipeline. The team is small and the boundaries between layers
are still firming up.

## Decision
Build a **modular monolith** deployed as **one FastAPI application**. Each layer
is an isolated Python package that communicates with others only through
`shared/contracts`. External systems are reached through the connector
framework, with low-level clients in `infrastructure/`.

## Consequences
- ✅ One thing to build, run, and deploy; simple local development.
- ✅ Strong internal modularity keeps a future extraction to services cheap.
- ✅ Shared kernel prevents divergent models across layers.
- ⚠️ Discipline required: enforce layer isolation in review and via lint rules.
- ⚠️ All layers scale together until/unless a layer is extracted.

## Alternatives considered
- **Microservices from day one** — rejected: premature operational complexity
  for unclear boundaries.
- **Unstructured monolith** — rejected: would not support phased, independent
  layer delivery.
