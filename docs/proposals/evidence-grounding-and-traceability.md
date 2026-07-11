# Evidence Grounding & Traceability Framework — Design Proposal (CAP-077)

- **Status:** Proposed (design only — no implementation in this milestone)
- **Capability:** CAP-077 — the final Requirement Intelligence Layer capability
- **Governing ADR:** [ADR-0016](../adr/0016-evidence-grounding-and-traceability.md)
- **Precedent:** [ADR-0015](../adr/0015-engineering-context-orchestration-model-and-policy.md) (Engineering Context Orchestration), [Golden Baseline](../productization/golden-baseline.md), RIL RC-1 manual grounding assessment

This document is the full design for the **grounding/** subsystem. It is **design only**:
it introduces no Python, changes no runtime behaviour, and leaves every execution artifact
byte-identical. Everything below describes what CAP-077 *will* build under ADR-0016.

---

## 0. Repository Assessment (Stage 0)

### What already exists

| Asset | Where | Relevance to grounding |
|---|---|---|
| `EngineeringContext.evidence` | `context_orchestration/models/engineering_context.py` | The **evidence corpus** — the exact `SourceArtifact`s the reasoner saw, partitioned functional/security/quality, each with stable `(source_system, source_record_id)` identity, title, description, tags, rule key, severity, component, endpoint. This is the ground truth grounding matches against. |
| `AnalysisResult` | `analysis/analysis_models.py` | Carries the raw, un-validated `LLMResponse`. `source_consolidated_id`, `analysis_id`, `execution_id` give provenance. |
| Parsed requirements | `normalization/` → `ParsedResponse.normalized_structure` | The generated requirements as structured data (three category arrays). |
| `ContextGrounding` | `engineering_context.py` | **Evidence-side** grounding: "what did this session stand on?" — a measurement of the *corpus*. **Not** requirement-side. CAP-077 must not extend or reuse this; it answers a different question. |
| `ValidationResult` / `CP1Result` | `validation/`, `cp1/` | Judge **structure** and **engineering readiness**. Neither reads evidence provenance. RC-1 confirmed both pass with zero findings while grounding is entirely unassessed. |
| RC-1 manual grounding assessment | `output/releases/ril-rc1-api-validation/manual_grounding_assessment.md` | The **hand-built baseline** (Supported 21 / Partially 1 / Unsupported 0) CAP-077 automates. Defines the classification vocabulary and the 1-to-1 requirement→finding mapping to reproduce. |
| Typed identity pattern | `context_orchestration/models/context_identity.py` | The `_StringIdentifier` / `PolicyVersion` value-object pattern to reuse for grounding identifiers. |
| `Schema` base | `shared/contracts/base.py` | `frozen=True, extra="forbid"`, camelCase aliases, tuples for deep immutability, `@model_validator` invariants — the model conventions grounding follows. |

### What is missing

1. **No requirement identity.** Generated requirements are **plain positional strings** inside `functional_requirements` / `security_requirements` / `quality_requirements` — e.g. `"The login page shall provide a mechanism to input a username."` They carry no id and no evidence citation. Grounding must **mint a deterministic requirement id** and make it canonical.
2. **No requirement→evidence link.** Nothing relates a requirement to the artifact(s) that justify it. The prompt renders evidence as descriptive lines (`- (sast) …:customqa:long-method [severity=CRITICAL; component=…]  description: …`) but the model does not cite them back. Traceability must therefore be **inferred deterministically post-hoc**, not parsed from citations.
3. **No support classification, confidence, or metrics.** Grounding is measured by a human reading two JSON files. There is no governed classification, no confidence, no hallucination signal, and no metrics.

### What can be reused

- The **evidence corpus** verbatim from `EngineeringContext.evidence` (no re-fetch, no re-consolidation).
- The **identity value-object pattern** and **`Schema` conventions**.
- The **execution-package append pattern**: `validation_result.json` and `cp1_report.md` are already written conditionally; grounding artifacts follow the identical mechanism.
- The **manual assessment's classification vocabulary** as the seed for the governed enum.

### What should become canonical

- A **`GroundedRequirement`** with a stable id, its classification, its confidence, and its evidence links.
- A **`RequirementEvidenceLink`** — the first-class, auditable requirement→evidence edge.
- A **`GroundingResult`** carrier, a peer to `AnalysisResult` / `ValidationResult` / `CP1Result`.

### Assessment conclusion

Grounding is **absent, not partial**. Every input it needs already exists in canonical form; what is missing is the subsystem that consumes them. The design below is therefore purely *additive* — a new peer subsystem that reads existing models and emits new ones.

---

## 1. Architecture Proposal (Stage 1)

A new governed subsystem **`requirement_intelligence/grounding/`**, peer to `consolidation/`, `context_orchestration/`, `analysis/`, `validation/`, `cp1/`.

### Ownership — it OWNS

- **Evidence Grounding** — deciding whether each generated requirement is supported by the supplied evidence.
- **Requirement Traceability** — the requirement→evidence link graph.
- **Support Classification** — assigning a governed `SupportClassification`.
- **Confidence Calculation** — the deterministic confidence score.
- **Grounding Explainability** — the human-readable "why" for every requirement.
- **Grounding Metrics** — coverage, distribution, hallucination rate, grounding score.

### Ownership — it does NOT own

| Concern | Owner | Grounding's relationship |
|---|---|---|
| Correctness of structure | Validation (CAP-041) | Independent; grounding never judges structure |
| Engineering readiness | CP1 (CAP-060) | Independent; grounding does not gate CP1 in CAP-077 |
| Prompt construction | Prompt Builder / Governance | Consumes the response; never shapes the prompt |
| Evidence selection | Engineering Context Orchestration | **Consumes** the context's evidence; never re-selects or re-ranks |
| The AI response | Analysis | Consumes `AnalysisResult`; never re-invokes the model |
| Artifact writing | Execution Package | Emits models for the writer to serialize |

### Boundary rules (ADR-0001 compliant)

Grounding imports **models only**: `EngineeringContext`, `SourceArtifact`, `ParsedResponse`, shared enums. It imports **nothing** from `validation/`, `cp1/`, `prompts/`, `llm/`, `consolidation/`. No subsystem imports `grounding/` except `PlatformContext` (wiring) and `execution/` (serialization of the result it is handed). The dependency graph stays acyclic.

### Internal structure (proposed)

```
grounding/
├── models/
│   ├── grounding_identity.py     # GroundingAssessmentId, GroundedRequirementId, GroundingConfigVersion
│   ├── support_classification.py # SupportClassification, EvidenceRelation enums
│   ├── evidence_link.py          # EvidenceReference, RequirementEvidenceLink
│   ├── grounded_requirement.py   # GroundedRequirement, GroundingConfidence, GroundingExplanation
│   ├── grounding_metrics.py      # GroundingMetrics, GroundingStatistics, coverage models
│   └── grounding_result.py       # GroundingAssessment, GroundingResult, GroundingSummary, GroundingFinding
├── strategy/                     # GroundingStrategy contract (the matching extension point)
│   └── deterministic_text.py     # Strategy V1 — deterministic text matching (no AI)
├── classification/               # classification + confidence rules (governed, declarative)
├── explanation/                  # GroundingExplanation assembly
├── grounding_config.py           # governed thresholds/weights (data, versioned)
└── grounding_service.py          # GroundingService (ABC) + DefaultGroundingService — the
                                  #   runtime boundary: assess(engineering_context, analysis_result)
                                  #   -> GroundingResult  (abstract in CAP-077A.1; dormant)
```

### Grounding Service vs Grounding Strategy — the load-bearing separation

The subsystem is split into a stable **orchestrator** and a replaceable **matcher**, so
the architecture does not hard-code *how* links are found. `GroundingService` is
**architecture**; the concrete matcher (`Strategy V1`) is an **implementation** behind it:

```
EngineeringContext + AnalysisResult   (runtime models)
        │
        ▼
GroundingService           (orchestration — architecture, stable; CAP-077A.1)
        │  builds, via
        ▼
MatchingContextBuilder     (the one runtime→canonical boundary; CAP-077A.2)
        │  produces
        ▼
MatchingContext            (canonical matching input; fanned out to MatchingRequests)
        │  each request's text preprocessed by
        ▼
MatchingNormalizer         (preprocessing boundary — raw text → NormalizedText; CAP-077A.4)
        │  normalized inputs, governed by
        ▼
MatchingPolicy             (governed decision rules — what constitutes a match; CAP-077A.5)
        │  applied by
        ▼
GroundingStrategy          (matching contract — the extension point)
        │  implemented by
        ▼
Strategy V1                (Deterministic Text Matching — implementation, CAP-077B)
        │  returns
        ▼
MatchResult                (canonical output: links + statistics + explanation; CAP-077A.3)
        │  the FROZEN, self-contained contract (CAP-077B.1) — the ONLY thing
        │  Classification consumes; it never re-enters the matching layer
        ▼
Classification → Confidence → Metrics → GroundingResult
```

**Classification consumes only MatchResult (CAP-077C).** Support Classification is a
governed subsystem that turns a `MatchResult` into a `ClassificationResult` under a
governed `ClassificationPolicy` — the internal hand-off chain is:

```
MatchResult  →  ClassificationResult  →  Confidence  →  GroundedRequirement
```

`ClassificationResult` (internal to Grounding, never an execution artifact) records the
support verdict, the evidence links partitioned by role, and a deterministic reason. The
`SupportClassificationEngine` reads only the `MatchResult`; it owns classification only
(no matching/normalization/confidence/metrics), governed by policy thresholds and a
precedence order (CONTRADICTED → SUPPORTED → PARTIALLY → WEAKLY → UNKNOWN → UNSUPPORTED).
UNKNOWN (no evidence examined) is kept distinct from UNSUPPORTED (evidence present, none
supported) — a coverage gap is never a hallucination. The `GroundedRequirementBuilder`
now builds *from* a `ClassificationResult`; confidence stays a placeholder until CAP-077D,
which computes it *from* the `ClassificationResult` without re-classifying.

**MatchResult — the frozen Matching↔Classification contract (CAP-077B.1).** Before
Classification (CAP-077C) consumes it, `MatchResult` is frozen under four invariants:

- **Match score is deterministic evidence similarity — nothing more.** A link's
  `match_score` is *not* confidence, probability, certainty, or a support
  classification; those are computed *from* a match, downstream, on
  `GroundedRequirement`/`GroundingResult`.
- **Schema versioned independently of the strategy.** `MatchResultVersion`
  (`result_version`) versions the shape; `MatchingStrategyVersion` versions the
  producer. Either changes without forcing the other.
- **Fully explainable without re-running the strategy.** Links, `MatchStatistics`, and a
  structured `MatchEvaluationSummary` (examined/matched, highest score, winning evidence,
  governed threshold + ranking summaries) carry every fact a consumer needs.
- **One-way boundary.** Classification consumes only `MatchResult` and never invokes a
  `GroundingStrategy`, `MatchingNormalizer`, or `MatchingPolicy`. Enforced by containment
  tests.

**Closed for extension (CAP-077A.3).** Both ends of the matcher are now canonical and
frozen: the input is a `MatchingContext`/`MatchingRequest`, the output is a `MatchResult`
(`MatchStatistics` — pure observations; `MatchExplanation` — matcher-scoped structure).
`GroundingStrategy.match(request) -> MatchResult` is the **permanent** signature. Future
capabilities *populate* a `MatchResult` (CAP-077B links + statistics; semantic/hybrid
strategies richer values); they never *redefine* it. Classification, confidence, and
grounding metrics are computed by the Grounding Service *from* `MatchResult`s and live on
`GroundedRequirement`/`GroundingResult` — so the matching architecture is complete before a
single matcher is written.

**Ownership (four seams, four responsibilities).** `MatchingNormalizer` owns
**preprocessing only** (raw text → canonical `NormalizedText`; shared by every strategy so
inputs are identical). `MatchingPolicy` owns the **decision rules only** — *what constitutes
a match* (thresholds, weights, permitted relations, ranking, tie-breaking) — as governed,
versioned data with no logic. `GroundingStrategy` owns **comparison only** (apply the policy
to normalized inputs → `MatchResult`). `GroundingService` owns **orchestration only** (build
context, fan out, normalize, delegate, assemble). Both normalization and policy sit *below*
the strategy, not inside it: no strategy re-implements preprocessing or re-defines matching
rules, and tuning either is one governed, versioned decision rather than N copies. One
`MatchingPolicy` serves the deterministic, semantic, and hybrid matchers unchanged.

**Canonical matching input (CAP-077A.2).** A strategy never sees a runtime model.
`MatchingContextBuilder` is the single place that touches `EngineeringContext` and
`AnalysisResult`; it emits a `MatchingContext` — `MatchingRequirement`s (ungraded
candidates that already carry the deterministic `GroundedRequirementId`), `MatchingEvidence`
(identity + matchable text, no `SourceArtifact` leak), the governed configuration, and the
versions. `MatchingContext.to_requests()` fans it out into per-requirement `MatchingRequest`s,
and `GroundingStrategy.match(request)` consumes those. This is what makes matching
**deterministic** (no timestamps/UUIDs/mutable objects), **testable** in isolation, and
**reusable** — semantic and hybrid strategies consume the identical `MatchingContext`.

- **`GroundingService`** is the **single runtime entry point** into the subsystem and the
  permanent orchestration boundary (established in CAP-077A.1 as an abstract contract —
  `assess(engineering_context, analysis_result) -> GroundingResult`). It owns orchestration,
  lifecycle, dependency coordination, execution ordering, and result assembly: it invokes the
  configured `GroundingStrategy` for links, then applies classification, confidence,
  explanation, and metrics via its internal collaborators, and assembles the `GroundingResult`.
  It is **strategy-agnostic** — swapping the strategy changes no service code.
- **`GroundingStrategy`** owns matching only: given one requirement and the evidence corpus,
  it returns the `RequirementEvidenceLink`s. It is the single point where "how do we decide a
  requirement is supported?" is answered, and the one place a future approach plugs in (see
  [Grounding Strategy](#grounding-strategy)).
- The service's **future collaborators** — a classification engine, a confidence calculator,
  metrics and explanation assemblers, and the result builder — are **internal implementation
  details of the service**, not part of its public contract. They can be added milestone by
  milestone (CAP-077C/D) without changing the `assess` signature or any caller.

**Dependency inversion.** `GroundingService` depends on the `GroundingStrategy` *abstraction*,
never on a concrete strategy (`DeterministicTextMatchingStrategy`, `SemanticSimilarityStrategy`,
`EvidenceCitationStrategy`, `HybridStrategy`). No runtime code references a concrete strategy;
`Strategy V1` is selected and injected at composition time. This is what lets CAP-077B implement
matching, CAP-077C add classification, CAP-077D add confidence and metrics, and CAP-077E wire
runtime — each **without changing `GroundingService`**.

---

## Grounding Strategy

The **extension point** of the subsystem. Everything else in the architecture is stable;
the strategy is the deliberately replaceable seam.

**Responsibilities.** Decide which evidence artifacts support a requirement, and with what
relation and match strength. It does **not** classify, score confidence, explain, or emit
metrics — those belong to the Grounding Service. A strategy answers exactly one question:
*given this requirement and this evidence corpus, what are the links?*

**Contract (frozen — CAP-077A.2 input, CAP-077A.3 output).**

```
GroundingStrategy.match(request: MatchingRequest) -> MatchResult
```

- **Inputs** — one canonical `MatchingRequest`: a `MatchingRequirement` (text + domain +
  deterministic id) plus the read-only `MatchingEvidence` corpus (each with stable
  `(source_system, source_record_id)` identity and matchable text) and the governed
  configuration/versions. The strategy sees **only canonical grounding models** — never
  `EngineeringContext`, `AnalysisResult`, or `SourceArtifact`.
- **Output** — one canonical `MatchResult`: the `RequirementEvidenceLink`s found (zero is a
  valid, meaningful answer that drives `UNSUPPORTED`), plus `MatchStatistics` (pure
  observations) and a matcher-scoped `MatchExplanation`, stamped with the producing
  strategy's name and version. A canonical result, not a raw tuple, so a matcher can report
  more without changing the return type or any caller.

**Determinism requirements.** A strategy **must** be a pure, reproducible function of its
inputs: identical inputs produce byte-identical links, independent of iteration order.
Evidence is presented in the canonical `(source_system, source_record_id)` order and ties
are broken by that same total order. A strategy that cannot guarantee determinism (e.g. a
non-deterministic remote model) is not admissible as the sole strategy for a governed run;
it may only participate inside a hybrid strategy whose composition is itself deterministic.

**Future implementations.** The contract is fixed; the implementations evolve:

| Strategy | Approach | Status |
|---|---|---|
| **V1 — Deterministic Text Matching** | Token / term overlap between requirement text and evidence searchable fields; governed thresholds | The implementation CAP-077 will ship first |
| **Semantic Similarity** | Embedding / vector similarity for paraphrase-tolerant matching | Future — admissible only if made reproducible |
| **Evidence Citation** | Consume explicit citations if a future, separately-governed prompt change makes the model cite evidence | Future — the strongest signal, blocked today by the frozen prompt |
| **Hybrid Matching** | Compose several strategies (e.g. deterministic floor + semantic lift) under a deterministic combination rule | Future |

Because the service is strategy-agnostic, adding any of these is a change **behind the
contract** — no change to models, classification, confidence, metrics, or the execution
package. The configured strategy and its version are recorded in the `GroundingResult`, so
a historical assessment is always attributable to the matcher that produced it.

---

## 2. Canonical Model Design (Stage 2)

All models derive from `Schema` (frozen, `extra="forbid"`, camelCase aliases, enum-by-value). Collections are `tuple`. Identifiers are plain-string value objects. No model is mutated after construction; the service constructs, consumers read.

### Identity

- **`GroundedRequirementId`** — deterministic: `req-<domain>-<12hex>` where the hash is `sha256(domain + "" + normalized_text)`. Reproducible from the requirement alone; independent of run UUIDs. Matches the identifier regex (lowercase, hyphen-safe).
- **`GroundingAssessmentId`** — `grnd-<contextId>-<responseHash8>`: a pure function of the context identity and the response content, so the same response over the same context yields the same id.
- **`GroundingConfigVersion`** — a `PolicyVersion`-shaped semver for the governed thresholds/weights (see §5).

Evidence keeps its existing identity: grounding never mints ids for evidence; it references `(source_system, source_record_id)`.

### Enums

- **`SupportClassification`** — `SUPPORTED`, `PARTIALLY_SUPPORTED`, `WEAKLY_SUPPORTED`, `UNSUPPORTED`, `CONTRADICTED`, `UNKNOWN` (§4).
- **`EvidenceRelation`** — the nature of one link: `DIRECT`, `CORROBORATING`, `PARTIAL`, `DERIVED`, `CONTRADICTING`, `NEGATIVE`, `MISSING` (§3).

### Models and relationships

| Model | Purpose | Key fields |
|---|---|---|
| **`EvidenceReference`** | An immutable pointer to one `SourceArtifact` in the context | `source_system`, `source_record_id`, `source_category`, `source_type` |
| **`RequirementEvidenceLink`** | One requirement↔one evidence edge | `evidence`: `EvidenceReference`; `relation`: `EvidenceRelation`; `match_score` (int 0–100, deterministic); `matched_terms`: `tuple[str]` (explainability); `rationale`: str |
| **`GroundingConfidence`** | Deterministic confidence for one requirement | `score` (int 0–100); `band`: HIGH/MEDIUM/LOW; `components`: `tuple[ConfidenceComponent]` (each: `factor`, `delta`, `reason`); `config_version`: `GroundingConfigVersion`; `framework_version`: str |
| **`GroundingExplanation`** | Structured, human-readable "why" for one requirement (§6) | `summary`: str; `supporting_evidence`: `tuple[EvidenceReference]`; `missing_evidence`: str `\|` `tuple`; `conflicting_evidence`: `tuple[EvidenceReference]`; `confidence_breakdown`: `tuple[ConfidenceComponent]`; `recommendations`: `tuple[str]` |
| **`GroundedRequirement`** | One generated requirement, graded | `requirement_id`, `domain`, `text`, `position` (category+index), `classification`, `confidence`, `evidence_links`: `tuple[RequirementEvidenceLink]`, `explanation`: `GroundingExplanation` |
| **`GroundingFinding`** | A flag worth surfacing (hallucination signal) | `finding_id`, `requirement_id`, `classification`, `severity`, `message` — raised for `UNSUPPORTED` / `CONTRADICTED` |
| **`EvidenceCoverage`** | Per-evidence utilization | `evidence`: `EvidenceReference`; `referenced_by`: `tuple[GroundedRequirementId]`; `used`: bool |
| **`RequirementCoverage`** | Per-requirement grounded/not | `requirement_id`, `grounded`: bool, `evidence_count`, `source_count` |
| **`GroundingStatistics`** | Raw counts | totals per classification, per domain, evidence used/unused |
| **`GroundingMetrics`** | Derived metrics (§7) | coverage %, avg confidence, distributions, hallucination rate, grounding score |
| **`GroundingSummary`** | Headline for humans | totals, distribution, overall score, one-line verdict |
| **`GroundingAssessment`** | The per-run root aggregate | `assessment_id`, `context_id`, `grounded_requirements`, `findings`, `evidence_coverage`, `requirement_coverage`, `statistics`, `metrics`, `summary`, `explanation`, versions |
| **`GroundingResult`** | The carrier (peer to `AnalysisResult`) | `analysis_id`, `execution_id`, `assessment`, `grounding_framework_version`, `grounding_config_version`, `started_at`/`completed_at` |

**Relationship diagram**

```
GroundingResult
 └─ GroundingAssessment ──────── context_id → EngineeringContext (evidence corpus)
     ├─ GroundedRequirement*  (one per generated requirement)
     │    ├─ GroundingConfidence (ConfidenceComponent*; config + framework version)
     │    ├─ GroundingExplanation (summary, supporting/missing/conflicting, breakdown, recommendations)
     │    └─ RequirementEvidenceLink*  ── EvidenceReference → SourceArtifact
     ├─ GroundingFinding*  (UNSUPPORTED / CONTRADICTED)
     ├─ EvidenceCoverage*  (per evidence artifact)
     ├─ RequirementCoverage*  (per requirement)
     ├─ GroundingStatistics
     ├─ GroundingMetrics
     └─ GroundingSummary
```

### Serialization, versioning, immutability

- **Serialization** — camelCase JSON via `to_camel`; identifiers serialize to plain strings, exactly like `EngineeringContextId`. The artifact (`grounding_result.json`) is a **projection** with its own `GROUNDING_ARTIFACT_VERSION`, independent of the model version — the precedent set by `engineering_context.json`.
- **Versioning** — `GROUNDING_MODEL_VERSION` (model shape), `GROUNDING_FRAMEWORK_VERSION` (subsystem), `GROUNDING_ARTIFACT_VERSION` (JSON contract), `GroundingConfigVersion` (thresholds/weights). Advance additively; behaviour-changing bumps are ADR-gated and re-baseline the golden dataset.
- **Immutability** — every model frozen; every collection a tuple; `@model_validator(mode="after")` enforces internal consistency (e.g. `classification == UNSUPPORTED ⇒ evidence_links empty`; a `GroundingFinding` exists for exactly the `UNSUPPORTED`/`CONTRADICTED` requirements; coverage counts reconcile with links — mirroring how `EngineeringContext` self-checks).

---

## 3. Traceability Framework (Stage 3)

```
Requirement (text, domain)
        │  GroundingStrategy.match(...)   (architecture: the strategy seam)
        ▼
RequirementEvidenceLink*  ──►  EvidenceReference ──► SourceArtifact (in EngineeringContext.evidence)
```

**Architecture.** The link graph is produced by the `GroundingStrategy` seam described
above; the traceability *shape* below is independent of which strategy fills it.

**Implementation (Strategy V1 — Deterministic Text Matching).** The first strategy compares
each requirement's normalized text against each candidate evidence artifact's searchable
fields (title, description, rule key, tags, `source_type`, component, endpoint), producing a
deterministic `match_score` and the `matched_terms` that earned it. Matching is
**within-domain first** (functional requirement ↔ functional evidence) and then
**cross-domain** as `CORROBORATING` (a security requirement may also cite a functional
story). A later strategy (semantic, citation, hybrid) may fill the same link graph
differently without changing anything downstream. Every design requirement is representable
regardless of strategy:

| Requirement of the framework | How it is represented |
|---|---|
| **Multiple evidence items** | `GroundedRequirement.evidence_links` is a tuple — 0..N links |
| **Multiple source systems** | Each link's `EvidenceReference.source_system` differs freely; source diversity feeds confidence |
| **Cross-domain evidence** | A link may reference evidence from another domain with `relation = CORROBORATING` |
| **Partial grounding** | `relation = PARTIAL` + classification `PARTIALLY_SUPPORTED` (the RC-1 "cart count" case) |
| **Negative evidence** | `relation = NEGATIVE` — evidence that argues against the requirement |
| **Contradiction** | `relation = CONTRADICTING` + classification `CONTRADICTED` |
| **Missing evidence** | `relation = MISSING` synthetic link (or empty links) + classification `UNSUPPORTED` → a `GroundingFinding` (hallucination signal) |
| **Derived evidence** | `relation = DERIVED` — reasonable extrapolation from a real artifact, no direct term match |
| **Future Feature Engineering** | `EvidenceReference` is stable and portable; Feature Engineering carries the same links into feature traceability without re-deriving them |

---

## 4. Support Classification (Stage 4)

Governed, closed enum. Each class has criteria, an explanation, an example (from RC-1), and its effect on confidence.

| Class | Criteria (deterministic) | Explanation | Example | Confidence effect |
|---|---|---|---|---|
| **SUPPORTED** | ≥1 `DIRECT` link with `match_score ≥ strong_threshold`; no `CONTRADICTING`/`NEGATIVE` | Evidence directly names the capability/defect/finding | S1: CSP requirement ↔ ZAP alert 10038 | High base; bonuses for corroboration |
| **PARTIALLY_SUPPORTED** | Core matched (`DIRECT`/`PARTIAL`) but a specific qualifier is unmatched | Core grounded; a detail is a reasonable extrapolation | F4: "cart count" extrapolated from "add to cart" story | Moderate base; penalty for the gap |
| **WEAKLY_SUPPORTED** | Only low-score or `DERIVED` links, none `DIRECT` | Plausible and domain-consistent, but no artifact names it | A general "audit logging" requirement with only tangential evidence | Low base |
| **UNSUPPORTED** | No link ≥ `min_threshold` | Nothing in the evidence supports it — a **hallucination** | (none in RC-1) | Floor; raises a finding |
| **CONTRADICTED** | ≥1 `CONTRADICTING`/`NEGATIVE` link outweighs support | Evidence argues against it | A requirement asserting behaviour a defect proves absent | Floor; raises a finding |
| **UNKNOWN** | Cannot be assessed (empty text; no evidence in a domain that received none) | Distinguishes "could not judge" from "judged unsupported" | Quality requirement when the context carried no quality evidence | Neutral/withheld; never a hallucination finding |

`UNSUPPORTED` and `CONTRADICTED` are the two **hallucination** classes. `UNKNOWN` is deliberately separate so a coverage gap is never miscounted as a hallucination (the RC-1 lesson: coverage gaps are not grounding gaps).

---

## 5. Confidence Model (Stage 5)

**Deterministic. No AI. No probabilistic model. No learning.** Integer arithmetic over sorted inputs, so it is order-independent and byte-reproducible.

```
score = base[classification]
      + Σ corroboration_bonus (diminishing, capped)      # more independent evidence
      + cross_source_bonus     (if ≥2 distinct source systems)
      − partial_penalty        (per unmatched qualifier)
      − conflict_penalty       (per CONTRADICTING / NEGATIVE link)
      − derived_only_penalty   (if no DIRECT link)
score = clamp(score, 0, 100)
band  = HIGH (≥75) | MEDIUM (40–74) | LOW (<40)
```

- **Inputs**: number of evidence items, source diversity, per-link `match_score`, cross-source corroboration, conflicting evidence, missing evidence.
- **Bonuses**: corroboration (each additional independent, distinct-record evidence item, with diminishing returns and a cap); cross-source (evidence from ≥2 systems is stronger than N items from one).
- **Penalties**: partial match, conflicting evidence, derived-only support.
- **Governance**: every base value, bonus, penalty, cap, and threshold lives in `grounding_config.py` as versioned data (`GroundingConfigVersion`), never as inline literals — the same "policy is data" principle as `OrchestrationPolicy`. Changing a weight is a versioned, ADR-gated, re-baselined change.
- **Explainability**: every applied term is recorded as a `ConfidenceComponent(factor, delta, reason)`, so the final score is fully reconstructable (see §6).
- **Determinism guard**: evidence is sorted by `(source_system, source_record_id)` before scoring; ties in matching are broken by that same total order. Two runs over identical inputs produce identical scores — the property the golden baseline will assert.

### `GroundingConfidence` is self-describing about how it was computed

A `GroundingConfidence` carries not only the outcome but the **provenance of the calculation**:

| Field | Meaning |
|---|---|
| `score` | The integer 0–100 result |
| `band` | HIGH / MEDIUM / LOW derived from `score` |
| `components` | The signed `ConfidenceComponent`s that sum to `score` |
| `config_version` | The `GroundingConfigVersion` of the weights/thresholds in force |
| `framework_version` | The `GROUNDING_FRAMEWORK_VERSION` of the scoring code |

**Why version the confidence itself.** A confidence number is only interpretable against the
rules that produced it. The weights *will* be tuned over the platform's life (RC-1 is the
first calibration point; later datasets will move thresholds). Without the versions stamped
on the value, a score of `72` recorded a year ago is uncomparable to a `72` today — the same
number may mean different things under different weight sets. Stamping `config_version` and
`framework_version` onto every `GroundingConfidence` makes each historical assessment
**attributable and comparable**: an auditor can tell whether two scores are directly
comparable (same versions) or only comparable after accounting for a rule change, and a
regression in grounding quality can be pinned to a specific config or framework bump. It is
the same discipline `OrchestrationMetadata` applies to the context — a result that cannot
name the rules that produced it is not auditable.

---

## 6. Explainability Framework (Stage 6)

Every `GroundedRequirement` carries a structured `GroundingExplanation` — **not a bare
string**. Modelling the explanation as data (rather than pre-rendered prose) lets every
downstream consumer render it its own way — a report, a dashboard tile, an API field — from
one canonical source, and lets the fields be asserted in tests. It is assembled from the
requirement's links and confidence components, so it can never disagree with the numbers.

### `GroundingExplanation` (conceptual model)

> **This is an architectural model. There is no runtime implementation yet** — CAP-077 is
> design only. The fields below define the shape a later milestone will build.

| Field | Answers | Source |
|---|---|---|
| **Summary** | The one-line "why", classification-aware | derived from classification + top link |
| **Supporting Evidence** | *what evidence contributed* | `DIRECT` / `CORROBORATING` links, by `(source_system, source_record_id)` |
| **Missing Evidence** | *what was missing* / *why partially supported* | the unmatched qualifier, or "no artifact matched" for `UNSUPPORTED` |
| **Conflicting Evidence** | *what evidence conflicted* | `CONTRADICTING` / `NEGATIVE` links |
| **Confidence Breakdown** | *why confidence changed* | the `ConfidenceComponent`s, each a signed, reasoned line |
| **Recommendations** | what a human should do next | e.g. "quarantine — unsupported", "seek corroborating evidence", "accept" |

Because the explanation is structured, the `grounding_report.md` renderer and any future UI
consume the *same* `GroundingExplanation`; the prose is a projection, never a second source
of truth.

Illustrative rendering (a projection of the model):

```
[req-security-9f3c1a2b] SUPPORTED (confidence 88, HIGH)
  "The application shall set X-Content-Type-Options: nosniff …"
  Supported by:
    • owaspzap / alertRef=10021 (X-Content-Type-Options Header Missing)  [DIRECT, matched: nosniff, content-type-options]
  Confidence: base 80 (SUPPORTED) +8 single strong direct match; no conflicts.
```

The `grounding_report.md` artifact is the run-level roll-up of these per-requirement explanations plus the summary; `grounding_metrics.md` renders §7.

---

## 7. Metrics Framework (Stage 7)

All metrics are deterministic functions of the assessment. Definitions:

| Metric | Definition |
|---|---|
| **Grounding Coverage** | grounded requirements ÷ total requirements (grounded = not `UNSUPPORTED`/`UNKNOWN`) |
| **Evidence Coverage** | distinct evidence artifacts referenced ÷ evidence artifacts available |
| **Requirement Coverage** | requirements with ≥1 evidence link ÷ total requirements |
| **Average Confidence** | mean `GroundingConfidence.score` across requirements |
| **Grounding Distribution** | count per `SupportClassification` |
| **Support Distribution** | share of SUPPORTED / PARTIALLY / WEAKLY across requirements |
| **Cross-source Support %** | requirements grounded in ≥2 source systems ÷ grounded requirements |
| **Single-source Support %** | requirements grounded in exactly 1 source system ÷ grounded requirements |
| **Unsupported %** | (`UNSUPPORTED` + `CONTRADICTED`) ÷ total requirements |
| **Evidence Utilization %** | evidence artifacts referenced ≥1 time ÷ available (= Evidence Coverage, surfaced as utilization) |
| **Average Evidence Per Requirement** | total links ÷ total requirements |
| **Average Sources Per Requirement** | mean distinct source systems per grounded requirement |
| **Traceability Completeness** | requirements with a resolvable evidence link ÷ total requirements |
| **Hallucination Rate** | (`UNSUPPORTED` + `CONTRADICTED`) ÷ total requirements |
| **Grounding Score** | governed weighted roll-up (0–100): rewards coverage, average confidence, cross-source support; penalizes hallucination rate. Weights in `grounding_config.py`, versioned. |
| **Evidence Reuse Ratio** | total evidence references ÷ unique evidence artifacts referenced |

**Evidence Reuse Ratio — why it matters.** Evidence Coverage and Utilization answer *how
much* of the corpus was used; the Reuse Ratio answers *how evenly*. A ratio near `1.0` means
each cited artifact supports roughly one requirement — broad, distributed grounding. A high
ratio means a few artifacts are being cited over and over — **evidence concentration**: many
requirements leaning on the same small set of findings. Concentration is not itself a defect
(one severe defect legitimately motivates several requirements), but it is a signal worth
surfacing: it can indicate an evidence budget that admitted too narrow a slice, a strategy
over-matching a dominant artifact, or genuine risk clustering. It complements — and does not
replace — Evidence Coverage: coverage can be high while reuse is also high (much of the
corpus used, but unevenly). This metric is **additive**; it changes no existing metric.

RC-1 as the reference target: 22 requirements, 21 SUPPORTED + 1 PARTIALLY, 0 UNSUPPORTED ⇒ Hallucination Rate 0%, Grounding Coverage 100%.

---

## 8. Runtime Placement (Stage 8)

```
EngineeringContext → Prompt Builder → Gemini → Analysis → Normalization → Grounding → Validation → CP1 → Execution Package
```

- **Inputs**: the `EngineeringContext` (evidence corpus) and the normalized requirements (`ParsedResponse`). Grounding runs **after Normalization** (it needs structured requirements) and is **independent of Validation** — it neither reads nor feeds `ValidationResult`.
- **Non-gating in CAP-077**: grounding **does not** open or close any gate. Validation and CP1 are untouched; their responsibilities and contracts are unchanged. A future milestone may add a CP1 grounding criterion or a grounding gate that *consumes* `GroundingResult` — that is explicitly out of scope here.
- **Ownership/dependencies**: `grounding/` depends only on models; the graph stays acyclic. `PlatformContext` gains `create_grounding_service()` and constructs it from the same seam it already uses for the orchestrator and analysis service.
- **Failure isolation**: a grounding error is contained to the grounding artifacts (like a validation/CP1 skip); it never aborts analysis or the rest of the package.

---

## 9. Execution Package (Stage 9)

Three new **conditional** artifacts, written by the same append mechanism as `validation_result.json` / `cp1_report.md` (which are already appended only when their stage ran):

| Artifact | Content | Producer |
|---|---|---|
| `grounding_result.json` | `GroundingResult` projection (assessment, links, classifications, confidence, metrics) | `GroundingResultArtifactBuilder` |
| `grounding_report.md` | Human-readable per-requirement explanations + summary (§6) | `GroundingReportBuilder` |
| `grounding_metrics.md` | The §7 metrics table | `GroundingMetricsBuilder` |

**Additions (design; additive, re-baselined on implementation):**

- **Manifest** — the three files appear in `generatedArtifacts` with byte/sha256 like every other artifact; optional top-level `groundingExecuted` / `groundingScore` fields. Because this touches manifest generation and the golden checksums, it bumps `MANIFEST_SCHEMA_VERSION` and re-baselines the golden dataset **at implementation time**, not now.
- **Execution summary** — an optional *Grounding* section (overall score + hallucination count), added the same way CP1's *Engineering Readiness* section is — additive, and re-baselined when implemented.
- **Review** — a grounding line in the qualitative scaffold.

No existing artifact's **name** or **content** changes in this design; all additions are new files or additive fields, gated behind a re-baseline exactly as CAP-076D's `engineering_context.json` was.

---

## 11. Downstream Architecture Recommendations (Stage 11)

Two distinct roles must not be conflated:

- **`GroundingResult` is the execution artifact** — the **repository-level aggregate** for
  one run: every grounded requirement, plus findings, coverage, statistics, metrics, and the
  summary, serialized as `grounding_result.json`. It is what the Execution Package persists
  and what Quality Governance and the Governance Dashboard read *in aggregate* (metrics,
  hallucination rate, grounding score).
- **`GroundedRequirement` is the canonical downstream business object** — the unit a
  requirement-consuming phase actually works with: one requirement plus its identity,
  classification, confidence, evidence links, and explanation. Feature Engineering,
  Automation Engineering, Execution, and Failure Intelligence consume **`GroundedRequirement`s**,
  not raw LLM strings and not the whole aggregate.

The relationship: a phase reads the `GroundingResult` aggregate to obtain the run's
`GroundedRequirement`s (filtered by classification/confidence), then carries those business
objects forward. Metrics-oriented phases read the aggregate directly.

| Phase | What it consumes | How |
|---|---|---|
| **Feature Engineering (2)** | `GroundedRequirement` | Build features only from `SUPPORTED` / `PARTIALLY_SUPPORTED` requirements above a confidence threshold; carry `RequirementEvidenceLink`s into feature traceability so every feature traces to source evidence. Drop or quarantine `UNSUPPORTED` / `CONTRADICTED`. |
| **Automation Engineering (3)** | `GroundedRequirement` | Generate test assets from grounded requirements; tag each test with the `GroundedRequirementId` and its `EvidenceReference`s, giving test→requirement→evidence traceability end to end. |
| **Quality Governance (4)** | `GroundingResult` (aggregate) | Gate releases on grounding metrics (e.g. Hallucination Rate = 0, Grounding Score ≥ threshold); treat grounding findings as policy inputs. This is the natural home for the grounding *gate* CAP-077 deliberately omits. |
| **Execution (5)** | `GroundedRequirement` | Attach grounding provenance to execution evidence so a run result links back to the requirement and the source artifact that motivated it. |
| **Failure Intelligence (6)** | `GroundedRequirement` | Use evidence links to triage: a failing test's requirement and its originating defect/finding are one hop away, sharpening root-cause. |
| **Governance Dashboard (7)** | `GroundingResult` (aggregate) | Surface `GroundingMetrics` over time — grounding score, hallucination rate, cross-source support — as first-class governance views. |

**Contract summary:** `GroundingResult` = the repository-level aggregate (the execution
artifact); `GroundedRequirement` = the canonical business object phases carry forward.

---

## 12. Explicit Questions

1. **Does Grounding become a new governed subsystem?** Yes — `requirement_intelligence/grounding/`, governed by ADR-0016, peer to Consolidation/Orchestration/Analysis/Validation/CP1.
2. **Does it own traceability?** Yes — the requirement→evidence link graph (`RequirementEvidenceLink`) is its exclusive property.
3. **Should Validation remain unchanged?** Yes — untouched; grounding is independent and non-gating.
4. **Should CP1 remain unchanged?** Yes — untouched in CAP-077; a future CP1 grounding criterion is possible but out of scope.
5. **Can confidence remain deterministic?** Yes — integer arithmetic over sorted inputs with governed, versioned weights; no AI, no probability, no learning.
6. **Can Feature Engineering consume grounding directly?** Yes — it reads the `GroundingResult` aggregate and works with the `GroundedRequirement` business objects it contains (§11), which are strictly richer than raw requirement strings.
7. **Does this complete Requirement Intelligence?** Yes — grounding is the last missing capability; with it the layer ingests, orchestrates, reasons, validates, gates readiness, **and verifies evidence support**.
8. **Is the architecture ready for Phase 2?** Yes — once implemented, Feature Engineering has a stable, grounded, traceable input contract.

---

## Determinism & Constraints Recap

- **Deterministic** given fixed inputs (requirements + context); the golden stub makes it reproducible in the baseline, exactly like Validation and CP1.
- **Additive**: no change to Consolidation, Orchestration, Prompt Governance, Prompt Builder, Gemini integration, Validation, CP1, or any existing execution-artifact name/content. Manifest/summary additions are re-baselined at implementation time.
- **Design only**: this milestone writes documentation; it changes no runtime behaviour and leaves the repository byte-identical.
