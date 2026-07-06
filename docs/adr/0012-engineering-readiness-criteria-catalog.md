# ADR 0012 — The Engineering Readiness Criteria Catalog

- **Status:** Accepted
- **Date:** 2026-07-06 (Proposed) · 2026-07-06 (Accepted)

## Problem

ADR-0011 established the CP1 Validation Engine and **intentionally blocked**
concrete CP1 implementation until a **governed Engineering Readiness Criteria
Catalog** exists: without it, "engineering readiness" has no governed,
deterministic definition, and any implementation would invent per-implementation
policy — the exact anti-pattern the platform forbids (ADR-0005/0006/0009/0010).

No such catalog exists. There is **no governed notion** of a readiness criterion's
identity, numbering, ownership, ordering, lifecycle, severity, or verdict
contribution. Worse, the repository already contains **implicit, aspirational
readiness language** — in the generation prompt and in stub docstrings (Context §5)
— that could be silently and non-deterministically adopted as "criteria" if the
gap is left open. This ADR establishes the governed catalog (its structure and
governance, **not** any criterion) so that CP1's readiness domain becomes governed
before it is built.

## Context

Reviewed completely: the Validation Platform architecture, the **Validation Rule
Catalog**, the AI Response Validation Architecture, ADR-0003 through ADR-0011, the
Platform Capability Matrix, the Architecture Coverage Dashboard, the Architecture
Freeze Index, the CP1 stub, and every frozen contract. The mandatory design review
findings:

1. **No existing document defines engineering-readiness criteria.** The Validation
   Rule Catalog governs *artifact-correctness* rules (`<LAYER>-NNNN`, nine layers,
   four-state verdict) for the frozen Validation Platform — a different domain. No
   readiness catalog exists. **(Continue — no STOP.)**
2. **No frozen document defines** criterion identity, numbering, ownership,
   ordering, lifecycle, severity, or verdict contribution **for CP1**. All those
   concepts exist only for validation *rules* (Rule Catalog §4/§7/§10/§11/§14/§15).
   The gap is total; ADR-0011 named the catalog as required but did not define it.
3. **CP1 criteria cannot be implemented today without inventing policy** — there is
   no governed criterion set, identity scheme, or severity/verdict mapping to
   conform to. Implementing now would require inventing thresholds/heuristics,
   which the platform's no-invention discipline forbids.
4. **Readiness criteria should be governed with the same discipline as Validation
   Rules** — identity, one-concern, determinism, additive-via-ADR growth — but in a
   **distinct namespace, domain, and verdict** (readiness, `CP1-NNNN`,
   `PASS/FAIL/WARN`), never merged with validation.
5. **Implicit readiness policy is hidden in code and must not be silently adopted:**
   - `requirement_intelligence/prompts/prompt_constants.py` instructs the AI to
     produce requirements that are "atomic, unambiguous and testable" and
     "actionable" recommendations, and to identify "missing, ambiguous, conflicting"
     gaps. **This is generation guidance to the model — non-deterministic, and not a
     gate criterion.**
   - `requirement_intelligence/services/requirement_analyzer.py` (a stub) mentions
     "quality scoring, gap detection, testability assessment" — an **aspiration**,
     not a governed criterion.
   - `requirement_intelligence/validators/cp1.py` describes CP1 as deciding whether
     a set is "good enough to proceed" — **intent without criteria**.
   These may **inform** a future criterion-definition step **through governance
   only**; none is adopted here.
6. **Criteria describe policy, not implementation** — exactly as the Validation Rule
   Catalog describes *what* a rule is responsible for, never *how* it works.
7. **Implementation cannot begin without this catalog** (ADR-0011 gate), and — because
   this ADR deliberately defines **no criterion** — cannot begin for *criteria* even
   after it, until criteria are populated through the catalog's governed process.

### Forces

1. **Determinism is platform-wide.** CP1 judgement must be deterministic and
   governed (AI Response Validation §3.4); "readiness" cannot be an invented,
   per-implementation heuristic.
2. **No-invention discipline.** Concerns are governed before they are built
   (ADR-0005/0006/0009/0010); a mechanism absent a governed definition is deferred,
   never improvised.
3. **The proven governance pattern already exists.** The Validation Rule Catalog is
   the platform's reference for governing a set of single-concern units by identity,
   lifecycle, classification, and additive growth. Reuse the pattern, do not reinvent.
4. **Two verdict vocabularies stay separate.** CP1 owns `PASS/FAIL/WARN`; the
   catalog must never re-derive or merge the four-state validation verdict.
5. **CP1 has no governed layer taxonomy.** Unlike validation's nine-layer
   foundational→semantic pipeline, readiness is (today) a single domain; inventing
   layers would invent policy (force 2).
6. **A catalog is a living document, not a point-in-time decision.** Criteria will
   grow additively for years; their home must be a standalone governed catalog, not
   frozen inside an ADR.

## Decision

Establish the **Engineering Readiness Criteria Catalog** as a standalone,
governed architecture document
(`docs/architecture/engineering-readiness-criteria-catalog.md`) — the CP1 analogue
of the Validation Rule Catalog — and govern it by the following decisions. **This
ADR establishes the catalog's structure and governance; it defines no criterion,
threshold, heuristic, or PASS/FAIL policy** (out of scope).

### D1. What an Engineering Readiness Criterion is

A **single, atomic, deterministic** statement of one concern that **validated**
requirements must satisfy to be fit for downstream engineering. It reads the
validated requirements (via `CP1Input`) and produces findings. It **never**
re-validates artifact correctness, repairs requirements, or generates features.

### D2. What belongs inside one criterion — and what never does

- **Inside:** exactly one readiness concern; its identity, name, purpose,
  ownership; its severity and verdict contribution; a deterministic judgement; a
  worked example.
- **Never:** two or more concerns ("and"); any algorithm, threshold, or data
  structure; the CP1 verdict itself (owned by the engine's aggregation); any
  non-deterministic mechanism (LLM/embedding/NLP heuristic); artifact-correctness
  re-checks (owned by Validation rules); requirement repair or feature synthesis.

### D3. Identity scheme — flat `CP1-NNNN`

Criteria carry a stable **`CP1-NNNN`** identity in a **single flat namespace**,
with numbers allocated from **classification-reserved ranges** (`0001–0099` Core,
`0100–0199` Extended, `0200–0299` Organization, `0300–0899` future, `0900–0999`
reserved). IDs never change and are never reused; names may evolve.

> **Justification (flat, not layered).** The Validation Rule Catalog uses
> `<LAYER>-NNNN` because the validation pipeline has nine governed layers
> (Transport→Business) with a foundational→semantic ordering. **CP1 has no such
> governed taxonomy** (force 5); minting readiness "layers" now would invent policy
> (force 2). A flat namespace is the honest, minimal scheme. A dimension token may
> be added **additively via a future ADR** should a governed readiness taxonomy
> ever emerge; it is not presumed here.

### D4. Ordering and independence

Catalog ordering **exists** (by Criterion ID) and is **deterministic**, for
reproducible `CP1Result` presentation and audit. **Execution outcome does not
depend on order:** every criterion is deterministic, stateless, idempotent,
independent, parallelizable, and non-mutating (the six properties of Validation
Rule Catalog §16). Registration preserves catalog order; the pipeline never
re-sorts. CP1 recognises **no** fail-fast layer halting — all criteria are peers.

### D5. Lifecycle

`Draft → Approved → Implemented → Deprecated → Retired`, plus the **Reserved ·
Deferred** disposition (an Approved identity with no governed deterministic
mechanism yet — the ADR-0005/0006/0009/0010 pattern). IDs are frozen forever and
never reassigned. Identity outlives activity.

### D6. Severity and verdict contribution are governed **per criterion**

Each criterion's finding carries a **severity** that **contributes** to the CP1
`PASS/FAIL/WARN` verdict; the **aggregation** into the single verdict is owned by
the CP1 engine (ADR-0011), never by a criterion. This ADR fixes **that** severity
and verdict contribution are governed per-criterion; it fixes **no** concrete
mapping, threshold, or PASS/FAIL policy (out of scope).

### D7. Policy, not implementation

The catalog describes **what** each criterion is responsible for, **never how** it
works or what numeric policy it applies — exactly the Validation Rule Catalog's
§1.2/§2.2 stance. A responsibility is a stable architectural fact; mechanism and
thresholds are replaceable detail, governed only when a criterion is defined.

### D8. The catalog is established **empty**, and grows only through governance

The catalog is established at **Catalog Version 1.0.0 with zero criteria**. New
criteria are added **additively** through a dedicated governance step (a
criterion-definition ADR, or the catalog's governed approval process), each
supplying complete metadata (§6) including its severity/verdict contribution. **No
criterion, threshold, or policy is ever introduced in code ahead of its catalog
definition.** The aspirational readiness language already in the prompt/analyzer/
stub (Context §5) is **explicitly not adopted**; it may inform a future
criterion-definition ADR through governance only.

## Ownership

| Concern | Owner |
| ------- | ----- |
| Criterion **identity** | This catalog (architecture governance). |
| Criterion **wording / purpose** | This catalog (architecture). |
| Criterion **policy** (what "ready" means for the concern) | This catalog + the criterion-definition ADR that adds it (governance) — **not** implementation. |
| Criterion **implementation** (mechanism) | Future CP1 criterion implementations, governed by this catalog; not defined here. |
| Criterion **execution** | The CP1 engine — Registry / Pipeline (ADR-0011). |
| Criterion **reporting** | `CP1Result` / `CP1Finding` (identified by ADR-0011). |
| Criterion **documentation** | This catalog + each criterion's metadata record (§6). |

## Catalog Structure

Established in `docs/architecture/engineering-readiness-criteria-catalog.md`:
Purpose (§1), Scope (§2), Criterion Philosophy (§3), Identity Standard (§4),
Ordering & Independence (§5), Metadata Standard (§6), Lifecycle (§7), Severity &
Verdict Contribution (§8), **empty** Initial Catalog (§9), Classification &
Profiles (§10), Evolution & Governance (§11), Relationship to the Validation Rule
Catalog (§12), Relationship to the CP1 Engine (§13).

## Relationship to ADR-0011

ADR-0011 **mandated** this catalog as the gate before any CP1 criterion is
implemented, and defined the CP1 engine pattern (Criterion → Registry → Pipeline →
Aggregate Result) and the `CP1Input`/`CP1Result` models. This ADR **fulfils** that
mandate for the catalog's *existence and governance*. The engine executes what
this catalog defines; this catalog defines what the engine executes. Neither
crosses into the other.

## Relationship to the Validation Rule Catalog

Same **governance discipline** (identity, one-concern, determinism, lifecycle,
additive-via-ADR growth); **different domain, namespace, verdict, and position**
(readiness vs artifact-correctness; `CP1-NNNN` vs `<LAYER>-NNNN`; `PASS/FAIL/WARN`
vs four-state; between Validation and Feature Generation vs between generation and
CP1). The two are **never merged**: a readiness concern is never a validation rule.
CP1 **trusts** the validation verdict and never re-validates. (See catalog §12.)

## Alternatives Considered

- **A1 — Define concrete readiness criteria now (in this ADR).** **Rejected:**
  explicitly out of scope, and it would force inventing thresholds/heuristics
  (force 2). Criteria must be added through the governed process with complete
  metadata, one deliberate decision at a time.
- **A2 — Adopt the prompt's / analyzer's aspirational language as the criteria.**
  **Rejected:** that language is **non-deterministic generation guidance and stub
  aspiration**, not governed deterministic policy (Context §5). Silently adopting it
  would import ungoverned, non-reproducible judgement — the anti-pattern this
  catalog exists to prevent.
- **A3 — Reuse the Validation Rule Catalog / `<LAYER>-NNNN` scheme for CP1.**
  **Rejected:** it merges two domains and two verdicts, and imposes a nine-layer
  taxonomy CP1 does not have (force 5). Same discipline, separate catalog.
- **A4 — Put the catalog *inside* this ADR rather than a standalone document.**
  **Rejected:** a catalog is a **living** artifact that grows for years; freezing it
  inside a point-in-time ADR would fight additive growth (force 6). The platform's
  own pattern is a standalone `docs/architecture/*-catalog.md`.
- **A5 — Introduce readiness "layers"/dimensions pre-emptively.** **Rejected:** no
  governed readiness taxonomy exists; inventing one is inventing policy (force 2).
  A flat namespace now; dimensions additively later if ever governed.

## Architectural Consequences

- ✅ CP1's readiness domain is **governed before it is built**: identity, lifecycle,
  ownership, ordering, severity/verdict contribution, and additive growth are fixed.
- ✅ The implicit readiness aspirations in code are **recorded and quarantined**, not
  silently promoted to criteria.
- ✅ The catalog reuses the platform's proven governance pattern while keeping the
  readiness domain, namespace, and verdict cleanly separate from validation.
- ✅ Future criteria have a real, living home and a governed additive process.
- ⚠️ **The catalog is empty by design.** Establishing it does **not** by itself make
  CP1 *criteria* implementable — criteria must still be defined through §11 (see
  *Implementation Readiness*).
- ⚠️ **Governed amendments follow from this ADR** (to be applied on acceptance, not by
  this document): a capability row for the catalog (next Downstream ID `CAP-061`) in
  the Platform Capability Matrix and Architecture Coverage Dashboard, per Matrix §8.

## Migration Impact

- **Code:** none. No criteria are defined; nothing is implemented; `validators/cp1.py`
  is untouched. Its "good enough" docstring intent is **superseded** by governed
  criteria (future), not edited here.
- **Implicit policy:** the prompt/analyzer aspirational language (Context §5) is
  **not migrated into** the catalog; it remains generation/stub guidance and may only
  enter as governed criteria through §11.
- **Documentation/governance:** register ADR-0012 and the new catalog (see *Governance
  Registration*); the `CAP-061` rows are the deferred amendment above.

## Future Extension Points

All **identified, none designed**: new **criteria** (next free `CP1-NNNN` per
classification, via governed addition); **CP1 profiles** (named criterion subsets,
the readiness analogue of Validation Profiles); a possible **dimension token** in
the identity scheme should a governed readiness taxonomy emerge (additive, via
ADR); **versioning** via an independent Catalog Version and per-Criterion Version.

## Version Impact

Introduces a **new governance artifact** (Engineering Readiness Criteria Catalog)
at **Catalog Version 1.0.0 with zero criteria**, and a new capability lineage
(`CAP-061`, to be registered on acceptance). It advances **no** existing version and
touches **no** frozen contract, canonical model, or the Validation Platform.

## Implementation Readiness

- ✅ **May proceed (per ADR-0011, unchanged by this ADR):** CP1 canonical-model
  definitions (`CP1Input`/`CP1Result`/`CP1Finding` shapes), CP1 engine scaffolding
  (Criterion contract → sealed Registry → Pipeline → aggregate result), the
  Validation → CP1 seam and gating, and the stub reconciliation.
- 🛑 **Still blocked — by design:** any **concrete CP1 criterion**. This ADR
  establishes the catalog's **governance and empty structure**; it defines **no
  criterion**. Because a criterion cannot be implemented before it is defined, CP1
  *criteria* implementation remains blocked until at least one criterion is added
  through the catalog's governed process (§11) — a **subsequent, dedicated governance
  step** this ADR authorizes but does not perform.

This is a **stated remaining gate, not a silent resolution.** The catalog now exists
and is governed; it is deliberately empty, and the first criteria must be defined
before CP1 can judge anything.

## Governance Registration

On this ADR being recorded (Proposed), the minimal registration applied now:

- `docs/architecture/engineering-readiness-criteria-catalog.md` — created (Draft;
  structure only; zero criteria).
- `docs/governance/architecture-freeze-index.md` §6 — a row registering ADR-0012 and
  the new catalog.

Deferred to acceptance (a separate, ratified step — consistent with ADR-0003/0011):
the `CAP-061` capability rows in the Platform Capability Matrix and Architecture
Coverage Dashboard.

## Scope Note

This ADR decides **the establishment and governance of the Engineering Readiness
Criteria Catalog** — its identity scheme, ordering, lifecycle, ownership, severity/
verdict-contribution model, classification, and growth process. It does **not**
define any criterion, threshold, heuristic, algorithm, or PASS/FAIL policy;
implement CP1 or any framework; create `CP1Input`/`CP1Result`/`CP1Finding`; modify
`validators/cp1.py`, the Validation Platform, Response Normalization, or any frozen
contract or canonical model. Defining the first readiness criteria is a **future**
governed step under §11 of the catalog.
