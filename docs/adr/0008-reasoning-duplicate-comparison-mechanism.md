# ADR 0008 — Reasoning Duplicate Comparison Mechanism (REASONING-0002)

- **Status:** Accepted
- **Date:** 2026-07-02

## Context

The mandatory design review for **`REASONING-0002` (DuplicateRecommendationRule)** halted
on a genuine architectural gap: the frozen documents state the *concern* but not the
*comparison mechanism*.

- Validation Rule Catalog §9.8: `REASONING-0002 | DuplicateRecommendationRule | `**`No
  recommendation is duplicated.`** — the mechanism is unspecified.
- Validation Rule Catalog §8.8 (Reasoning): "Confirm the output is **internally coherent
  and self-consistent** … Detect contradictions, **duplicated conclusions**, and circular
  logic." — a coherence/semantic framing.
- AI Response Validation Architecture: Reasoning = "is the output internally coherent and
  consistent?"; the future "**Semantic validation**" capability is described as "a richer
  Reasoning layer."
- ADR-0006 classified `REASONING-0002` **Implementable** with the note "duplicate governed
  **strings** are observable" — explicitly on **information sufficiency, not mechanism**.
- ADR-0007 froze **byte-exact** comparison **only for `CONTENT-0002`**, explicitly scoped to
  that rule.

The gap is twofold. First, **no frozen document defines** whether a duplicate recommendation
is detected by byte-exact equality, normalized equality, or semantic equivalence. Second,
the Reasoning layer's own language ("duplicated conclusions", "internally coherent",
"meaning-level coherence") **points toward a semantic reading**, which pulls against the
byte-exact reading that made ADR-0006 classify the rule Implementable. Implementing without
a governed decision would either invent a comparison mechanism (prohibited by the
ADR-0005/0006 no-invention discipline) or silently resolve a Content-vs-Reasoning ownership
question. Hence the design review correctly **stopped**.

This ADR freezes the comparison mechanism so `REASONING-0002` becomes fully specified.

### Design review findings

1. **Is the comparison mechanism currently governed?** **No.** §9.8 states the concern
   only.
2. **Does the Catalog define duplicate recommendation semantics?** **No.** Neither §9.8 nor
   §8.8 defines *how* duplication is measured.
3. **Does any frozen document define byte-exact / normalized / semantic / paraphrase?**
   **No.** None is defined for `REASONING-0002`. (ADR-0007's byte-exact decision is scoped
   solely to `CONTENT-0002`.)
4. **Does Reasoning currently own semantic validation?** **No.** Semantic/meaning-level
   validation is described as a **future capability** ("a richer Reasoning layer"); it is
   not governed today.
5. **Would semantic comparison require introducing a governed comparison mechanism?**
   **Yes** — semantic equivalence/paraphrase detection would require a governed mechanism
   (embeddings, an LLM judge, or a normalization spec) that does not exist and cannot be
   invented here (ADR-0005/0006).
6. **Is an ADR therefore required?** **Yes** — to freeze the mechanism (this ADR), exactly
   as ADR-0007 was required for `CONTENT-0002`.

No additional inconsistency was discovered — only the under-specification this ADR resolves.

## Decision

**`REASONING-0002` (DuplicateRecommendationRule) compares recommendations using byte-exact
string equality only.**

Two recommendation entries are duplicates **iff** their string values are identical under
exact equality. Specifically the comparison is:

- **exact string equality**
- **case-sensitive**
- **whitespace-sensitive**
- **deterministic**
- **no normalization** (no trimming, no case folding, no Unicode normalization)
- **no semantic similarity**, **no embeddings**, **no LLM judgement**
- **no paraphrase detection**

**Semantic duplicate detection is explicitly outside the current governed architecture.**
Detecting that two differently-worded recommendations express the *same conclusion* (the
"duplicated conclusions" reading of §8.8, in its meaning-level sense) is a **future
capability** — "a richer Reasoning layer" — that requires its **own** ADR and a governed
semantic-comparison mechanism (e.g. a normalization spec, embeddings, or a deterministic
judge). Until such an ADR exists, `REASONING-0002` performs **surface-form** duplicate
detection only.

This ADR fixes only the **comparison mechanism** of an existing catalogued rule. It changes
**no** rule identity, name, severity, blocking, layer, or number, and introduces **no** new
rule.

## Ownership clarification — no overlap with CONTENT-0002

`CONTENT-0002` and `REASONING-0002` share an **identical comparison mechanism** (byte-exact
string equality, per ADR-0007 and this ADR) but own **different domains**, so ownership
remains unique (Catalog §3.1):

| Rule | Layer | Owned domain | Mechanism |
| ---- | ----- | ------------ | --------- |
| `CONTENT-0002` | Content | Duplicate **requirement** statements within one requirement collection (ADR-0007) | byte-exact string equality |
| `REASONING-0002` | Reasoning | Duplicate **recommendation** statements within the `recommendations` collection | byte-exact string equality |

- The two rules never inspect the same field: `CONTENT-0002` reads only the three
  requirement collections (`functional_/security_/quality_requirements`); `REASONING-0002`
  reads only `recommendations`. No response element is judged by both.
- **A concern is owned by exactly one rule** (Catalog §3.1): "duplicate requirements" →
  `CONTENT-0002`; "duplicate recommendations" → `REASONING-0002`. Sharing a *mechanism* is
  not sharing a *concern* — mechanism is implementation detail; the owned datum is the
  identity. (Analogy: `SYNTAX-0002` and both duplicate rules all detect "sameness," yet each
  owns a distinct datum.)
- The Catalog's placement is preserved: requirement-entry duplication is a **Content**
  concern (§8.5 "duplicated entries"); recommendation duplication is catalogued under
  **Reasoning** (§9.8) as the surface-form precursor to the future semantic
  "duplicated conclusions" capability. This ADR keeps `REASONING-0002` exactly where the
  frozen Catalog assigns it and does not move any concern between layers.

## Architecture impact

This ADR is **governance only**. It makes:

- **no canonical model changes** (`ValidationInput`, `ParsedResponse`, `NormalizationResult`
  unchanged);
- **no framework changes**; **no pipeline changes**; **no validator changes**;
- **no Rule Catalog changes** (identity, concern, severity, blocking, and number are
  untouched; the mechanism is fixed here, in the ADR record);
- **no Validation Rule / Schema Implementation Contract changes**;
- **no code and no test changes**.

## Alternatives considered

- **A — Semantic equivalence / paraphrase detection.** **Rejected (for now):** matches
  §8.8's meaning-level intent but requires a governed semantic-comparison mechanism
  (embeddings/LLM judge/normalization) that does not exist; inventing one violates the
  ADR-0005/0006 no-invention discipline and the determinism requirement (AI Response
  Validation §"Semantic validation … must remain deterministic"). Reserved as a future
  capability behind its own ADR.
- **B — Normalized string equality** (trim/case-fold/Unicode-normalize before comparing).
  **Rejected:** normalization is a governed transformation the architecture has not defined
  for validation; choosing a normalization form would itself be an invented mechanism.
  Byte-exact is the only mechanism requiring no invented specification.
- **C — Leave the mechanism undefined.** **Rejected:** two implementers could build
  incompatible validators (byte-exact vs semantic), producing divergent verdicts for
  identical responses — defeating determinism and audit (Catalog §16).
- **D — Chosen: byte-exact string equality, semantic deferred to a future ADR.**
  **Accepted:** deterministic, invention-free, consistent with ADR-0007's `CONTENT-0002`
  decision, and it preserves the semantic reading as an explicitly-reserved future
  capability.

## Consequences

- ✅ Once **Accepted**, `REASONING-0002` is **fully specified**: identity/severity/blocking
  (Catalog §9.8, §14, §15) + **comparison mechanism (this ADR)**. Implementation is then
  mechanical — the same shape as `CONTENT-0002`, applied to `recommendations`: one
  `ValidationIssue` per duplicate occurrence (second and subsequent identical entries),
  byte-exact, defer on absent structure, raise only on absent `ParsedResponse`.
- ✅ Semantic "duplicated conclusions" has a clean future home (its own ADR + governed
  mechanism) without disturbing `REASONING-0002`'s identity.
- ✅ Ownership stays unique and layer placement unchanged (Catalog §3.1, §8.5, §8.8).
- ✅ **Status is Accepted.** `REASONING-0002` is implementable under this mechanism and is
  **implemented + tested**; it is marked implemented in governance.
- ⚠️ **Version impact:** this ADR clarifies the comparison mechanism of an existing
  catalogued rule without changing its concern's *meaning*, severity, blocking, identity,
  number, or any canonical model. On acceptance it advances **no** version (Rule Catalog
  Version, Validation Contract Version, Validator Version, Rule Version all unchanged;
  Catalog §20). It is a governance clarification recorded so implementations are
  deterministic.

## Governance registration

On this ADR being Accepted, the following governance documents register it (no
code, no Rule Catalog, no contract, no canonical-model changes):

- `docs/governance/architecture-freeze-index.md` — §6 Relationship to ADRs registers
  ADR-0008; the Validation Rule Catalog artifact row references it.
- `docs/governance/platform-capability-matrix.md` — the CAP-049 (Reasoning Layer) note
  records the byte-exact mechanism for `REASONING-0002`; it is marked **implemented**.
- `docs/governance/architecture-coverage-dashboard.md` — the readiness notes record the
  byte-exact mechanism and that `REASONING-0002` is **implemented** under it.

## Scope note

This ADR decides **only** the comparison mechanism of `REASONING-0002`. It does **not**
implement `REASONING-0002` (or any rule), create or modify tests, or change any code,
framework, `ValidationInput`, `ParsedResponse`, `NormalizationResult`, `ResponseValidator`,
`ResponseNormalizer`, canonical model, the Rule Catalog, or the Validation Rule / Schema
Implementation Contracts. It changes no rule identity, number, severity, or blocking.
Implementation of `REASONING-0002` is a separate, subsequent task, contingent on this ADR
being **Accepted**.
