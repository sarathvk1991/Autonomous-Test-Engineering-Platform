# ADR 0002 — Response Normalization: Framework Infrastructure vs. Normalization Component Boundary

- **Status:** Accepted
- **Date:** 2026-07-01

## Context

The Response Normalization subsystem is composed of two things that operate at
**different levels of abstraction**, and until now that distinction was never made
explicit. The ambiguity surfaced while preparing the Normalization Assembly
Contract and the implementation of `NORMALIZATION-0001…0005`.

Two frozen documents described the same five responsibilities in structurally
incompatible ways:

- The **Normalization Responsibility Catalog** (`docs/architecture/normalization-responsibility-catalog.md`)
  defines `NORMALIZATION-0001…0005` as a **forward-only dependency chain**:
  `0002` reads the result of `0001`, `0005` assembles the `ParsedResponse` from the
  facts of `0001`, `0002`, and `0004` (Catalog §4.1, §5, §6, frozen §11).
- The **Response Normalization Framework** defines its `NormalizationResponsibility`
  contract as **order-independent** and dependent **only on `source`** — "depends
  only on the source, never on the outcome of any other responsibility"; "any
  permutation yields the same observations" — returning
  `list[NormalizationObservation]`, with a pipeline that aggregates observations and
  **never** assembles a `ParsedResponse` (`parsed_response` is always `None`).

A single execution unit cannot be both order-independent/observation-only **and**
a forward-dependent producer of the `ParsedResponse`. The framework's contract can
faithfully express only `NORMALIZATION-0003` (Capture Observations); it cannot
express `0001`, `0002`, `0004`, or `0005`. Yet the framework README and the
Catalog §10 asserted the framework "registers and executes" the five and produces
the `ParsedResponse`. That assertion cannot hold under the framework's own frozen
contract.

The root cause is a missing architectural statement: **the Response Normalization
Framework and the Response Normalizer are not the same thing and do not operate at
the same level.** One is generic execution infrastructure; the other is a concrete
normalization component built on top of it. The five catalog entries belong to the
component, not to the framework.

## Decision

Make the abstraction boundary **explicit and permanent**. This ADR is an
**architecture clarification only**: it resolves the ambiguity without changing any
frozen contract, any public API, or any production code.

The following become permanent architectural principles:

1. **The Response Normalization Framework provides the execution infrastructure for
   normalization components.** It owns generic execution concerns only:
   registration, lifecycle, the execution pipeline, execution context,
   configuration, metadata, observability, and exception translation. It remains
   generic, provider-independent, format-independent, implementation-independent,
   and reusable.

2. **A normalization component may internally coordinate multiple architectural
   stages without exposing those stages to the framework.** Internal stage
   collaboration is a component concern; the framework neither sees nor governs it.

3. **The `ResponseNormalizer` is the concrete normalization component responsible
   for AI response normalization.** It is the single orchestration boundary of the
   subsystem, built on top of the framework.

4. **`NORMALIZATION-0001` through `NORMALIZATION-0005` are internal architectural
   stages of the `ResponseNormalizer`.** They are **not** independent framework
   execution units and are **not** registered as framework `NormalizationResponsibility`
   instances. Their identity, single concern, ownership, dependencies, and ordering
   are governed **exclusively** by the Normalization Responsibility Catalog; their
   ordering is internal to the `ResponseNormalizer`, not to the framework registry
   or pipeline.

5. **The `ResponseNormalizer` owns the Assembly State and coordinates the execution
   of the five normalization stages.** The Assembly State is the component-internal
   collaboration medium through which stage facts flow before the `ParsedResponse`
   is assembled. It is never a canonical model and is never exposed outside the
   `ResponseNormalizer` boundary.

6. **`ParsedResponse` assembly remains entirely within the `ResponseNormalizer`
   boundary.** Stage `0005` (Assemble `ParsedResponse`) executes inside the
   component; the framework never assembles a `ParsedResponse`.

7. **The Response Normalization Framework remains completely unaware of the Assembly
   State, `ParsedResponse` construction, and the internal collaboration of the
   normalization stages.** The framework's pipeline continues to assemble only the
   generic `NormalizationResult` (observations, telemetry, framework metadata); its
   `parsed_response` field remains the architecture-approved placeholder until the
   `ResponseNormalizer` populates it within its own boundary.

8. **All existing framework contracts remain unchanged.** The framework's public
   APIs, registry, pipeline, metadata, execution context, lifecycle, and
   `NormalizationResponsibility` contract are not altered by this ADR.

9. **This clarification is architectural only.** No production Python changes as a
   consequence of this ADR.

### Consequence for the five stages and the generic responsibility contract

The framework's `NormalizationResponsibility` remains a **generic** execution unit
(an order-independent, observation-producing component) and is valid, reusable
infrastructure. It is **not** the vehicle for `NORMALIZATION-0001…0005`. The five
catalog stages are coordinated internally by the `ResponseNormalizer` through the
Assembly State; the forward-only dependency chain (Catalog §4.1) lives **inside**
the component, where forward dependencies are legitimate — not inside the
framework, whose independence guarantee is therefore never violated.

## Consequences

- ✅ The ambiguity between execution infrastructure and normalization component is
  permanently removed; the framework and the `ResponseNormalizer` have unambiguous,
  disjoint responsibilities.
- ✅ The framework stays generic and reusable; it is not coupled to one normalization
  workflow, the Assembly State, or `ParsedResponse` construction.
- ✅ The forward-only stage dependency chain (Catalog §4.1) is honoured **inside** the
  `ResponseNormalizer`, without contradicting the framework's frozen Responsibility
  Independence.
- ✅ The Normalization Assembly Contract can now be written as a component-internal
  contract governing the five stages and the Assembly State, with no framework
  changes required.
- ✅ No frozen contract is changed; the freezes remain intact. This ADR **clarifies**
  them.
- ⚠️ Architecture and governance documents that implied the framework "registers/executes"
  the five stages or "assembles the `ParsedResponse`" are corrected to attribute
  those to the `ResponseNormalizer` component. (See "Documentation alignment" below.)
- ⚠️ Any future example must not present `NORMALIZATION-000N` as a framework
  `NormalizationResponsibility` registration; that would re-introduce the conflation.

## Alternatives considered

- **Extend the framework responsibility contract** so responsibilities can read
  prior facts and produce non-observation facts, and have the pipeline assemble the
  `ParsedResponse` — **rejected**: it breaks the framework's frozen Responsibility
  Independence and the pipeline's placeholder guarantee, and couples generic
  infrastructure to one workflow.
- **Introduce two kinds of framework responsibility** (observation vs. assembly) —
  **rejected**: unnecessary complexity inside the framework for a distinction that
  belongs *above* it, at the component level.
- **Make the framework pipeline aware of Assembly State / `ParsedResponse`** —
  **rejected**: the same coupling, from the other direction.
- **Leave the ambiguity and resolve it in implementation** — **rejected**: it would
  bake a silent, undocumented reconciliation into code and violate the freeze
  philosophy (architecture decided before implementation).

## Documentation alignment

As a consequence of this ADR, the following documents are aligned so their
terminology and execution model are internally consistent (no freeze is broken; the
freezes are clarified, not changed):

- `docs/architecture/response-normalizer.md` — `ParsedResponse` assembly and the
  five stages are attributed to the `ResponseNormalizer` component, not the
  framework.
- `docs/architecture/normalization-responsibility-catalog.md` — the ordering and
  execution of the five stages are described as **internal to the `ResponseNormalizer`**
  and governed by this catalog, not executed by the framework registry.
- `requirement_intelligence/normalization/framework/README.md` — the framework is
  described as generic execution infrastructure; the five stages are internal
  `ResponseNormalizer` stages, not framework responsibilities.
- `docs/governance/architecture-freeze-index.md` and
  `docs/governance/platform-capability-matrix.md` — notes reference this ADR for the
  framework-vs-component boundary.

## Scope note

This ADR does **not** define the Assembly State's fields, the stage-to-stage data
flow, invariants, or failure semantics. Those belong to the forthcoming
**Normalization Assembly Contract**, a component-internal contract that this ADR
makes it possible to write without any further framework change.
