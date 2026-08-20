# Layer 1 — Requirement Intelligence Layer (As-Built LLD)

| Field | Value |
|---|---|
| Status | **As-built.** Documents verified current reality; not a proposal, requires no approval, and freezes nothing new. |
| Type | As-Built Low-Level Design |
| Layer | Layer 1 — Requirement Intelligence (ADR-0031) |
| Source | Direct read of `requirement_intelligence/`, `scripts/run_requirement_analysis.py`, `shared/prompts/`, `contracts/`, and the governing ADRs under `docs/adr/` — **not** the source deck |
| As of | 2026-08-20 |
| Supersedes | `layer-1-requirement-intelligence-layer-lld.pptx` as the current record for Layer 1 (the deck is retained, untouched, as proposal history only — see §12) |
| Governs | Nothing. This document records what is already built and already Accepted; it makes no new decision. |

---

## 0. Why this document exists, and why it isn't a transcription

`docs/architecture/lld-review-findings.md` (§2) found that Layer 1 is the one built layer that
never got the treatment every other built layer (L2, L3, L4) received: a committed transcription
of its source deck plus a Reviewer's note reconciling it against later decisions, feeding an
architecture-freeze ADR. Layer 1 has ADR-0032 (Layer 1 Capability Freeze), but that ADR bounds
*future* growth — it does not describe L1's *current* architecture the way L2/L3/L4's reviewed
transcriptions describe theirs.

The review's own recommendation was to create this document **from code**, not as a transcription:
*"nearly every concrete claim in \[the deck] is contradicted by the real, built code"* — a faithful
transcription of a deck that wrong would not be useful, and L2/L3's Reviewer's-note pattern exists
to flag *localized* drift in an otherwise-sound document, not to carry a document this far from
reality. So unlike L2/L3's frozen transcription-plus-note, this document states L1's real
architecture directly, in the sections below, and reserves the deck-comparison work for a single
reconciliation appendix (§12) — exactly the shape the review itself proposed.

**Timing.** The review's own lean was "create-with-#3" — wait for mentor item #3 (corpus-level
requirement completeness), since that item was scoped as a design task that might reshape what L1
owns, and writing this document twice would be worse than writing it once, correctly, after item
#3 resolved. Item #3 resolved as the traceability graph build (CAP-088, ADR-0048,
`requirement_intelligence/traceability_graph/` — §10): a real, additive, L1-resident capability now
folded into the "as-built" picture below. This document is written after that landed, per the
review's own lean, not as a stopgap ahead of it.

---

## 1. Purpose and scope

Layer 1 ingests requirement and finding data from three governed external sources, consolidates it
deterministically, reasons over it with a governed LLM call, and — subject to a chain of
deterministic quality gates — emits a `TestableRequirementSet`: the sole, typed, versioned contract
Layer 2 (Feature Engineering) is permitted to consume (ADR-0032 carve-out 1, ADR-0034).

L1 also owns a cluster of "Historical Truth" sub-capabilities (Continuous Improvement, Knowledge
Graph, Organizational Memory, Learning), two governed platform-wide services it is the origin point
for (the Prompt Registry, the LLM provider layer), and — as of CAP-088 — a requirement-to-execution
traceability graph. None of this appears in the source deck at all (§12).

L1 does **not** generate scenarios, Gherkin, page objects, step definitions, or execute anything —
see §13 for the explicit non-scope, since the deck's own boundary claims are among its most
contradicted content.

---

## 2. Inputs — real sources, not the deck's

`requirement_intelligence/config/source-registry.json` declares exactly **three** sources, each
mapped to a real connector and mapper class:

| `sourceId` | `sourceName` | `sourceCategory` | Connector | Mapper |
|---|---|---|---|---|
| `jira` | JIRA | FUNCTIONAL | `connectors/jira/connector.py` | `mappers/jira_mapper.py` |
| `owasp_zap` | OWASP ZAP | SECURITY | `connectors/zap/connector.py` | `mappers/zap_mapper.py` |
| `sonarqube` | SonarQube | QUALITY | `connectors/sonarqube/connector.py` | `mappers/sonar_mapper.py` |

**No HP ALM connector exists or has ever existed.** The only trace of it anywhere in the codebase
is a reserved `SourceSystem.HP_ALM` enum member (`models/enums.py`, `models/source_artifact.py`)
docstringed as a "future" placeholder — never a live connector, never registered, never invoked.
ADR-0031 freezes exactly these three sources.

**Ingestion mode** is a single global toggle, not per-source: `EXECUTION_MODE=FILE|API`, stamped
onto every source by `RegistryLoader`. FILE mode reads static JSON dumps from hard-coded paths
(`input/jira/jira-issues.json`, `input/zap/zap-alerts.json`, `input/sonar/sonar-issues.json`); API
mode calls the real REST APIs using credentials named — never stored — in the registry (env-var
references only, e.g. `JIRA_BASE_URL`/`JIRA_EMAIL`/`JIRA_API_TOKEN`). Every connector implements
one shared `SourceConnector` ABC (`connectors/base.py`): `validate_connection`,
`fetch_raw_records`, `get_metadata` — no canonical transformation and no business rules live in a
connector; that is the mapper's and Consolidation's job respectively.

This is the one item the LLD review found the deck got right in shape (source registry +
connector-interface extensibility), plus one thing the deck never anticipated: the
`EXECUTION_MODE` toggle itself.

---

## 3. High-level flow — the real, live pipeline

The canonical stage list lives in `requirement_intelligence/run_state/stages.py`
(`STAGE_DEFINITIONS`, governed by ADR-0036). Its own module docstring records a real divergence:
ADR-0036's table numbers stages 1–13 in a fixed order, but stage 9 ("Execution Package (write)")
actually runs **last** in the live CLI, after stages 10–13 — because the execution package is
assembled once, in memory, only after every phase has completed. `stages.py` therefore orders
`STAGE_DEFINITIONS` by real execution/dependency sequence, not ADR-0036's literal numbering, and
carries each stage's ADR-0036 `#` only as a citation field. The flow below follows that real order.

```
Connectors (JIRA / ZAP / Sonar)
  → Mappers (raw → canonical SourceArtifact)
  → Consolidation (deterministic grouping, §5)
  → [1] Engineering Context Orchestration (ADR-0015, §6)
  → Prompt Build (Prompt Registry, §7) → [2] Requirement Analysis — the Gemini call (§8)
  → [3] Requirement Enhancement (ADR-0018, §9) — best-effort, never fatal
  → [4] Grounding (ADR-0016, §10) — best-effort, never fatal
  → [5] Validation (13 rules, §11) ─┐  opt-in: both gated on the
  → [6] CP1 (1 criterion, §12)     ─┘  --validate CLI flag (default off)
  → [7] Requirement Quality Governance (18 QG-* rules, §13) —
        runs only when Grounding + Validation + CP1 all produced a result
        (i.e. also effectively requires --validate)
  → TestableRequirementSet Emission (§14) —
        runs only when Quality Governance's decision is pass / pass_with_warnings
  → [8] Recommendation (ADR-0019, §15) —
        runs once Enhancement + Grounding + Validation + CP1 + Quality Governance all exist
  → [10] Continuous Improvement → [11] Knowledge Graph
        → [12] Organizational Memory → [13] Learning   (§16 — unconditional, not --validate-gated)
  → [9] Execution Package write (§17) — the actual last step; hard-fail only
  → [if TestableRequirementSet was emitted] Layer 2 — Feature Engineering (stage 14, ADR-0043)
  → [--with-automation-engineering] Layer 3 — Automation Engineering (stage 15, ADR-0044)
  → [--with-suite-quality-governance] Layer 4 — Suite Quality Governance (stage 16)
```

Numbers in brackets are `stages.py`'s `stage_number` (its ADR-0036 citation), included so this flow
is traceable back to the governing document, not because they reflect real execution order (they
mostly do — the one exception, stage 9, is called out explicitly above and in `stages.py`'s own
docstring).

**Every non-terminal L1 phase — Enhancement, Grounding, Validation, CP1, Quality Governance,
Recommendation, Continuous Improvement, Knowledge Graph, Organizational Memory, Learning — is
best-effort**: a phase's own exception is caught, logged to `run_state.json`, and surfaced to the
console, but never aborts the run. Only `execution_package_write` is hard-fail — if it fails,
nothing is persisted for that run. This uniform "surface, never abort" discipline is stated
explicitly, phase by phase, in `handle_analyze`'s own inline comments.

**A load-bearing consequence worth stating plainly:** Validation and CP1 run only when the CLI is
invoked with `--validate` (default off). Quality Governance requires all three of
Grounding+Validation+CP1 to have produced a result — so it, too, is effectively gated on
`--validate`. TestableRequirementSet emission requires a Quality Governance decision. **Without
`--validate`, no `TestableRequirementSet` is ever emitted, and Layer 2 never runs for that
requirement set** — `--validate` is not merely a diagnostic flag; it is the switch that makes the
L1→L2 boundary reachable at all.

---

## 4. Components — the real package inventory

`requirement_intelligence/` has 28 top-level packages (confirmed by reading every `__init__.py`).
The deck names roughly a dozen conceptual components across its Consolidation/Enrichment/CP1
slides; the real inventory is substantially larger, and the packages below with no analogue in the
deck at all are marked **(absent from the deck)**.

| Package | Real purpose |
|---|---|
| `analysis/` | `RequirementAnalysisService` — the sole AI-orchestration boundary (§8) |
| `api/` | FastAPI router/routes/schemas — thin HTTP surface |
| `config/` | `source-registry.json` (§2) |
| `connectors/` | JIRA/ZAP/SonarQube connectors + shared base/exceptions/IO (§2) |
| `consolidation/` | Deterministic, non-AI grouping of `SourceArtifact` → `ConsolidatedArtifact` (§5) |
| `context_orchestration/` | **(absent from the deck)** Engineering Context Orchestration — governed evidence selection into `EngineeringContext` (§6) |
| `continuous_improvement/` | **(absent from the deck)** CAP-083, ADR-0022 — recurrence/trend/opportunity detection (§16) |
| `cp1/` | Engineering-readiness gate (ADR-0011/0012/0013) — one live criterion (§12) |
| `enhancement/` | **(absent from the deck)** CAP-081, ADR-0018 — deterministic enrichment (§9) |
| `execution_package/` | Writes every run's output artifacts (§17) |
| `grounding/` | **(absent from the deck)** CAP-077, ADR-0016 — requirement-to-evidence traceability, confidence, classification (§10) |
| `input/` | Static FILE-mode input JSON (data, not code) |
| `knowledge_graph/` | **(absent from the deck)** CAP-084, ADR-0023 — structural graph over Historical Truth (§16) |
| `learning/` | **(absent from the deck)** CAP-086, ADR-0029 (§16) |
| `llm/` | Provider registry/factory, Gemini (live) + Azure OpenAI (stub) providers, `GenerationIdentity`, generation cache, token usage tracker (§8, §18) |
| `mappers/` | Per-source raw → canonical translation, shape-only |
| `models/` | Canonical domain models/enums |
| `normalization/` | Provider-independent `LLMResponse` → canonical `ParsedResponse`, exactly once |
| `organizational_memory/` | **(absent from the deck)** CAP-085, ADR-0027 (§16) |
| `platform/` | `PlatformContext` — the single construction/composition hub |
| `prompts/` | **(absent from the deck, in this exact shape)** L1's registration of the governed Prompt Registry (§7) |
| `recommendation/` | **(absent from the deck)** CAP-082, ADR-0019 (§15) |
| `registry/` | `ConnectorRegistry`, `EXECUTION_MODE` resolution |
| `requirement_quality_governance/` | CAP-080, ADR-0017 — the real, terminal quality gate (§13); package name is *not* the deck's "CP1 rules" |
| `run_state/` | `run_state.json` lifecycle (ADR-0036), `RunStateManager`, `RunLock`, atomic writes, `STAGE_DEFINITIONS` |
| `testable_requirement/` | Emits `TestableRequirementSet` — the L1→L2 boundary (§14) |
| `traceability_graph/` | **(absent from the deck; built after it)** CAP-088, ADR-0048 (§10) |
| `validation/` | Response Validation Framework — the mandatory AI-output quality gate, opt-in via `--validate` (§11) |
| `tests/` | Test suite |

---

## 5. Consolidation — the real deterministic algorithm

`consolidation/consolidation_rules.py`'s own module docstring states plainly: *"there is no AI, no
I/O and no source-specific branching."* `derive_grouping_key` applies a fixed cascade — the first
dimension that yields a value wins:

1. **`component`** (owning module), if present.
2. **Alphabetically-first `tag`**, if no component.
3. **`endpoint`** (normalized URL path, from ZAP's `location`/`url`), if no tag.
4. **`risk` category** (severity/priority normalized to CRITICAL/HIGH/MEDIUM/LOW across JIRA
   priority, ZAP risk, and Sonar severity vocabularies), as the last-resort bucket.

Group ids are deterministic slugs (`cons-{dimension}-{slug}`) — the same input always produces the
same group id across runs, never a random UUID. This confirms the review's own finding precisely:
grouping exists, but it is deliberately non-semantic — the opposite of what the deck's
"module/feature-intent/functional-similarity/security-relevance/quality-relevance/risk-level"
language implies about AI-driven grouping.

---

## 6. Engineering Context Orchestration (ADR-0015) — absent from the deck entirely

`context_orchestration/engineering_context_orchestrator.py` sits between Consolidation and
Analysis: `list[ConsolidatedArtifact] → EngineeringContextOrchestrator → EngineeringContext`.
Stateless and deterministic, it runs one governed `OrchestrationPolicy`. Two real policies exist
(`context_orchestration/policy/default_policy.py`):

| | `LegacySelectionPolicy` (retained as the control arm) | `DefaultOrchestrationPolicy` (**active**) |
|---|---|---|
| Selection | `SINGLE_LARGEST` (one group wins) | `COVERAGE_GUARANTEED` — every domain with evidence is represented |
| Coverage rule | — | `ALL_PRESENT_CATEGORIES` |
| Ranking | Artifact count desc, then id | Risk level desc, then artifact count desc, then id |
| Evidence budget | 1000/domain, 1000 total (never truncates) | 25/domain, 60 total (water-filled) |
| Evidence ordering | `GROUP_ORDER` | `RISK_THEN_RECORD_ID` |

`DefaultOrchestrationPolicy`'s own class docstring calls itself "the policy that repairs the
CAP-074B defect" — the earlier bug where Consolidation's own grouping meant only one domain's
evidence ever reached the LLM. The 25/domain budget is footnoted in-code against a real
71-artifact single-domain baseline (~5.3k tokens), sized so a 3-domain context stays comparably
sized. Determinism is a stated invariant ("CAP-076A Invariant 7"): every ranking key is a total
order, budget allocation is integer water-filling over a fixed domain order, and evidence ordering
is a stable sort — two runs over the same consolidated artifacts produce byte-identical selection.

The resulting `EngineeringContext` is what §7's prompt builder consumes.

---

## 7. LLM provider layer and Prompt Registry

**Provider selection** (`llm/provider_registry.py`): resolved via config → `LLM_PROVIDER` env var →
hardcoded fallback `"gemini"`. Every provider implements one `LLMProvider` ABC
(`llm/providers/base_provider.py`).

**Live provider — `llm/providers/gemini_provider.py`**: uses the official `google-genai` SDK.
Code default model is `_DEFAULT_MODEL = "gemini-2.5-pro"`, overridable via `GEMINI_MODEL`
(`.env.example` also documents `gemini-2.5-pro` as the reference default; this environment's local
`.env` currently overrides it to `gemini-3.1-flash-lite` for live runs — a deployment-time choice,
not a code default). It is the single shared `generate_content` call site for the entire platform
— L1 (this layer), L2, and L3 all inject the same `GeminiProvider`; L3's step-definition generator
alone applies a second, independent override (`STEP_DEF_GEMINI_MODEL`, an L3 concern, not L1's).
Built-in resilience: proactive pacing (12 calls/min default, trailing 60s window, a defensive
margin under the observed free-tier quota) and reactive retry-with-backoff (up to 4 retries on
429/`RESOURCE_EXHAUSTED` and 5xx/`UNAVAILABLE`, honoring the SDK's own `retryDelay` when present).
It also guards a real, previously-observed defect: Gemini's `MALFORMED_RESPONSE` finish reason
returns `.text is None` with no exception — the provider raises a typed `ProviderGenerationError`
instead of letting `None` crash an untyped pydantic `ValidationError` downstream. Real token usage
(`LLMUsage`) is extracted from `raw.usage_metadata` on every call.

**Stub provider — `llm/providers/azure_openai_provider.py`**: implements the same interface;
**every method unconditionally raises `NotImplementedError`.** Docstring: "Licensing status: NOT
YET AVAILABLE — stub only." It exists only so `"azure_openai"` is a referenceable provider name for
tests/factories, never for a live call. **Confirmed: the deck's "Enrichment via Azure OpenAI" claim
is contradicted outright.**

**Prompt Registry (ADR-0014)** — the real, governed framework lives at `shared/prompts/framework/`
+ `shared/prompts/models/`, a **platform-wide shared service**, not an L1-local one (this directly
corrects the deck's "build a new Prompt Registry" framing — one registry exists, and every layer,
including L2's own deck, was wrong to propose building another). `PromptRegistry` supports explicit
registration only (no reflection, no filesystem scanning), a one-directional `OPEN → SEALED`
lifecycle, and a `(prompt_id, version)` index with no implicit "latest" resolution. `PromptMetadata`
carries id/name/version/owner/lifecycle/SHA-256/compatibility fields; `PromptLifecycle` is
`Draft → Experimental → Approved → Production → Deprecated → Archived`.

L1's own composition root, `requirement_intelligence/prompts/framework/composition.py`
(`build_prompt_registry`), loads versioned templates from `prompts/versions/`, verifies each
against `versions/manifest.json`'s SHA-256, and registers them. Two versions of the
`requirement_analysis` prompt are registered — v1.0.0 (`PRODUCTION`) and v1.1.0 (`APPROVED`,
CAP-073's wording clarification, byte-identical output schema) — and the runtime is **explicitly
pinned to v1.0.0**, a deliberate, separately governed decision, not an oversight.

`requirement_intelligence/prompts/requirement_prompt_builder.py`'s `RequirementPromptBuilder` is
pure assembly: it turns `EngineeringContext` into a provider-agnostic `PromptRequest`, resolving
all fixed wording from the registry above. It authors no content, knows nothing about
Gemini/Azure/Anthropic, and makes no API calls. Its own docstring records the CAP-076C history: it
used to render a single `ConsolidatedArtifact` (the CAP-074B defect's root — only one group's
evidence ever reached the reasoner); it now renders the multi-group `EngineeringContext` §6
produces.

---

## 8. Requirement Analysis — the real LLM call

`analysis/requirement_analysis_service.py`'s `RequirementAnalysisService` is the sole
AI-orchestration boundary in L1. The real path:
`EngineeringContext → RequirementPromptBuilder.build() → PromptRequest.to_llm_request() →
GeminiProvider.generate() → LLMResponse → normalization/ (exactly once) → ParsedResponse →
AnalysisResult`. `normalization/` is what converts a provider-independent `LLMResponse` into the
canonical `ParsedResponse` shape every downstream L1 phase consumes — a real seam absent from the
deck entirely.

---

## 9. Requirement Enhancement (ADR-0018, CAP-081) — absent from the deck

Deterministic enrichment, relationship derivation, and observation generation over the completed
`AnalysisResult` — no LLM call of its own. Runs unconditionally whenever a live (non-dry-run)
result exists, immediately after Analysis, strictly upstream of Grounding. Best-effort: a failure
is surfaced but never fails the run.

---

## 10. Grounding (ADR-0016, CAP-077)

`grounding/grounding_service.py`'s `DefaultGroundingService.assess(engineering_context,
analysis_result) -> GroundingResult` delegates to a private `GroundingPipeline`
(`grounding/pipeline.py`), a fixed sequential stage chain: `MatchingContextBuilder →
GroundingStrategy → SupportClassificationEngine → ConfidenceCalculator →
GroundedRequirementBuilder → GroundingMetricsBuilder → GroundingResultBuilder`. Matching today uses
exactly one concrete strategy, `DeterministicTextMatchingStrategy` — deterministic text matching,
not semantic/AI matching (the module's own docstring lists `SemanticSimilarityStrategy` etc. as
future-only). Confidence is likewise non-AI: a declarative `ConfidencePolicy` (base scores per
support classification, bonuses/penalties, band thresholds) applied by a pure
`ConfidenceCalculator` — no LLM call anywhere in the grounding path. A requirement that can't be
grounded degrades to `UNSUPPORTED`/0-confidence rather than failing the run; `CONTRADICTED`
classifications raise a `CRITICAL` finding, other hallucination classes raise `WARNING`.

**Wiring status — corrects both prior project memory and the module's own internal docstring.**
`grounding/__init__.py` and `grounding/grounding_service.py` both still assert *"not yet wired into
any execution pipeline... nothing calls assess at runtime."* This is **stale**:
`scripts/run_requirement_analysis.py` calls `context.create_grounding_service().assess(...)`
unconditionally whenever a live result exists (immediately after Requirement Enhancement, before
Validation), writing `grounding_result.json` plus two Markdown reports. Grounding is live, wired,
and best-effort — see §19 for why this documentation lag exists and where else it recurs.

This is also the CP1-adjacent subsystem the traceability graph (§10 of the code tree, not this
document's own numbering — see the dedicated `traceability_graph/` package below) deliberately does
**not** reuse, since Grounding answers "is this requirement supported by evidence," a different
question from "is this requirement's chain to a step reachable."

---

## 11. Validation — 13 rules, opt-in

`validation/rules/` holds **13** rule files across 5 categories (confirmed by direct file count):

| Category | Rules |
|---|---|
| `transport/` (4) | `timeout`, `provider_failure`, `empty_response`, `response_exists` |
| `content/` (2) | `duplicate_requirement`, `empty_requirement` |
| `reasoning/` (1) | `duplicate_recommendation` |
| `schema/` (3) | `required_arrays`, `field_types`, `required_sections` |
| `syntax/` (3) | `duplicate_keys`, `encoding`, `valid_structure` |

Runs only with `--validate` (§3), producing a `ValidationResult` that CP1 (§12) consumes directly
as `CP1Input`.

---

## 12. CP1 — the real, single-criterion taxonomy

**The deck's 7-rule taxonomy (Mandatory Field / Ambiguity / Acceptance Criteria / Traceability /
Risk Coverage / Duplicate / Confidence Check) does not exist.** `cp1/engine/cp1_engine.py`'s own
module docstring is explicit: the `CP1Engine` performs orchestration and verdict aggregation only —
"it contains no readiness logic, no threshold, no heuristic, no scoring." All engineering policy
lives in registered criteria, and exactly **one** is registered today
(`cp1/response/cp1_composition.py`): `EngineeringInputAvailabilityCriterion` (**CP1-0001**,
ADR-0013) — the pooled count of functional + security + quality requirements must be ≥ 1, else a
single FAIL finding.

Verdict aggregation (`CP1Engine._derive_verdict`) is a fixed, order-independent rule with no
weighting: any FAIL finding → overall FAIL; else any WARN → overall WARN; else PASS. Runs only with
`--validate`, immediately after Validation.

This is a genuinely different, and much smaller, taxonomy from the one below — the two are easy to
conflate because both are described loosely as "quality rules" and both are named "CP1" in one
sense or another; §13 draws the boundary explicitly.

---

## 13. Requirement Quality Governance (ADR-0017, CAP-080) — the terminal release authority

Not to be confused with CP1 (§12) — `requirement_quality_governance/` is a separate package with
its own, larger rule catalog: **18** `QG-*` rules (confirmed by direct grep of registered rule ids)
across 6 categories:

| Category | Count | Ids |
|---|---|---|
| Grounding | 6 | `QG-GRD-001`–`006` (score/hallucination-rate fail/warn bars, average confidence, evidence coverage) |
| Validation | 3 | `QG-VAL-001`–`003` (critical/error/warning count budgets) |
| CP1 | 2 | `QG-CP1-001`–`002` (blocking/warn finding budgets) |
| Cross-subsystem | 2 | `QG-XSS-001`–`002` (anomalies, e.g. validation passed while grounding failed) |
| Mandatory release | 4 | `QG-REL-001`–`004` (hard gates: hallucination, validation failure, CP1 failure, readiness) |
| Advisory | 1 | `QG-ADV-001` (info-level, never a release action) |

It is the **terminal decision layer**: it consumes the three already-completed peer results —
`GroundingResult` + `ValidationResult` + `CP1Result` — and runs only once all three exist (i.e.,
also effectively gated on `--validate`, since Grounding always runs but Validation/CP1 do not).
Its decision (`pass` / `pass_with_warnings` / other) is the **sole** gate on whether a
`TestableRequirementSet` is ever emitted (`testable_requirement/emitter.py`'s
`gate_permits_emission`) — confirmed live by the direct call chain in `handle_analyze`, matching
prior project memory's "terminal release authority" characterization exactly.

---

## 14. TestableRequirementSet Emission — the real L1 → L2 boundary

`testable_requirement/emitter.py`'s `emit_testable_requirement_set()` builds a
`TestableRequirementSet(run_id, generated_at, provenance, requirements, risks)` — nothing like the
deck's untyped `riskBasedScenarios`/criteria-array shape. `TestableRequirementSetProvenance`
carries `prompt_id`, `prompt_version`, `prompt_sha256` (the registry's real fingerprint — §7),
`provider`, `model`, `requirement_quality_governance_decision`, and `governance_report_ref`. Gated
strictly on `gate_permits_emission`: only `pass`/`pass_with_warnings` governance decisions emit
anything (ADR-0034 property 4); a FAIL decision emits nothing, and Layer 2 does not run.
`traces_to` (per-requirement source provenance) is built from the **full evidence set the reasoner
actually saw across every contributing consolidation group** — deliberately broader than just the
single primary group — deduplicated and sorted by `(source_system, source_record_id)` for
reproducibility. `functional_tag` is a pure deterministic slug of `component`; no LLM signal
participates in it.

---

## 15. Recommendation (ADR-0019, CAP-082) — absent from the deck

Runs once Enhancement + Grounding + Validation + CP1 + Quality Governance have all produced a
result — meaning it, too, effectively requires `--validate`.

---

## 16. The Historical Truth cluster — Continuous Improvement, Knowledge Graph, Organizational Memory, Learning

Four packages, none mentioned in the deck at all, each a real deterministic engine behind a frozen
contract, and — unlike §11–§15 — **each runs unconditionally on every live (non-dry-run) run,
never gated on `--validate`**:

| Package | ADR | CAP | What it does |
|---|---|---|---|
| `continuous_improvement/` | ADR-0022 | CAP-083 | Recurrence/trend/opportunity detection over a Historical Dataset |
| `knowledge_graph/` | ADR-0023 | CAP-084 | `DeterministicKnowledgeGraphEngine` — projects nodes/edges, detects connected-component subgraphs, generates structural observations/findings from a governed rule catalog and policy; zero AI/heuristics |
| `organizational_memory/` | ADR-0027 | CAP-085 | Fans in Continuous Improvement + Knowledge Graph results |
| `learning/` | ADR-0028/0029 | CAP-086 | Consumes Organizational Memory's result |

**A real data-maturity caveat, not a build gap:** each engine consumes a `HistoricalDatasetReference`
that is today minted per-execution, from the *current run's own* `execution_id`
(`_knowledge_graph_historical_dataset_reference_for_execution` and its siblings in
`scripts/run_requirement_analysis.py`) — because no real, persisted, multi-run Historical Dataset
store exists yet (ADR-0021 §Stage 6 is reserved, not built). Every one of these engines is real,
tested, and live-wired; what they are fed today is a single-execution stand-in for genuine
cross-run history, so their outputs are currently structurally sound but substantively thin — an
honest state, not a hidden gap.

**A terminology trap worth flagging explicitly**: all four packages' own docstrings describe
themselves as *"the Nth Layer 2 capability defined by ADR-0020."* That is legacy vocabulary.
**ADR-0031 (Accepted, supersedes ADR-0020 in full) redesignates CAP-083–086 as Layer-1
sub-capabilities** — frozen under ADR-0032 alongside the rest of L1 — while ADR-0031's own "Layer
2" now means Feature Engineering (BDD generation), an unrelated layer. Reading any of these four
packages' docstrings literally will misplace them; ADR-0031 D3 is the authority.

**Wiring-status correction, same shape as §10:** `knowledge_graph/__init__.py`'s own docstring
still says *"still not wired into any execution pipeline — nothing calls build at runtime."* This
is false against the current CLI, which calls `run_knowledge_graph_phase` unconditionally. The same
pattern — a "not wired" docstring contradicted by a live call site — recurs for
`continuous_improvement/`, `organizational_memory/`, and `learning/` as well; see §19.

---

## 17. Traceability Graph (ADR-0048, CAP-088) — the most recently built L1 capability

`requirement_intelligence/traceability_graph/` (`models.py`, `identity.py`, `completeness.py`,
`change_impact.py`, `projection.py`, `traversal.py`, `serialization.py`) builds a
`requirement → scenario → step` reachability graph plus a `CompletenessReport`, then extends it
with step-definition binding-completeness and method-level change-impact
(`PAGE_OBJECT_METHOD`/`CALLS_METHOD` nodes and edges, reusing the same L3 request-derivation logic
Layer 3's page-object work already established).

**Report-only, no gate anywhere.** `completeness.py`'s own docstring is explicit: "No threshold, no
gate, no fail logic exists anywhere here." It is not called from `handle_analyze` at all — a
standalone, additive capability layered on top of L1's own outputs, not part of the unconditional
pipeline in §3.

**Deliberately does not import `knowledge_graph/`.** It reuses that package's typed-node/typed-edge/
SHA-256-identity/BFS *pattern* only, because Knowledge Graph's live entry point is frozen to
Historical-Truth-only consumption (ADR-0023 D2, Article II of ADR-0049's Truth Hierarchy — §18),
while `traceability_graph`'s real source data (`TestableRequirementSet`, `.feature` files) is
per-run **Runtime** Truth, which that boundary forbids reading through Knowledge Graph.

**Layer placement is genuinely, deliberately left open — stated honestly, not resolved here.**
ADR-0048 D2 itself frames this as "Layer-2-*adjacent*, not a Layer 2 peer" in ADR-0021's strict
sense: it reuses Layer 2's sub-capability *pattern* to satisfy the Truth Hierarchy, but physically
reads Layer 1/Layer 2 Runtime Truth directly, closer to Layer 1. The package's own `__init__.py`
calls itself "a new, standalone Layer 2 peer" — using ADR-0020's old sub-capability sense of "Layer
2," not ADR-0031's Feature Engineering sense, and even that description is softened by ADR-0048 D2
itself. This document presents the placement question as open, mirroring ADR-0048's own posture
(the same shape as CAP-087/"Layer 2.5" in ADR-0031 D4) rather than forcing a clean answer that
doesn't yet exist. CAP-088 is registered in the platform capability matrix §5.11 and at the top of
`architecture-baseline-v2.md` §3.

---

## 18. Cross-layer infrastructure L1 originates: identity, cache, token accounting

Three primitives live in `requirement_intelligence/llm/` but are consumed across L1, L2, and L3 —
worth documenting here since L1 is where they are defined and governed:

- **`generation_identity.py`** — `GenerationIdentity` (`prompt_id`, `prompt_version`,
  `prompt_sha256`, `provider`, `model`), captured verbatim at the call site from the resolved
  `PromptDefinition.metadata` and the `LLMResponse` — "nothing here is invented, inferred, or
  recomputed" per its own docstring. Built for the re-run/delta-regen pinning work. Today, L1
  itself persists this identity in exactly one place — `TestableRequirementSetProvenance` (§14) —
  once per run.
- **`generation_cache.py`** — the generic content-addressed cache primitive behind ADR-0050.
  Deliberately reuses `run_state.atomic_write` for durable writes rather than `RunStateManager`
  itself, since `RunStateManager` is architecturally closed to the fixed 19-entry
  `STAGE_DEFINITIONS` catalogue (§3), not a general-purpose cache.
- **`token_usage.py`** — `TokenUsageTracker`/`TokenUsageTotals`: aggregates `LLMUsage` per named
  call type across a run (`call_count`, `unmeasured_call_count`, `cache_hit_count`,
  prompt/completion/total tokens, per-call-type `.distribution()`). Threaded as an optional
  collaborator into every LLM-calling generator platform-wide, written to a sibling
  `token_usage.json` artifact (§17 below), never touching `run_state.json`/`manifest.json`'s own
  governed schema.

L1 owns and exports these generic primitives; **L2 and L3 do not reimplement them** — each wraps
its own generator with a thin decorator that calls into L1's shared cache
(`CachingFeatureContentGenerator` in L2; `CachingStepDefinitionGenerator` and
`CachingTestDataGenerator` in L3) — a genuine cross-layer reuse relationship (Article XI of the
Engineering Constitution, §20), not an L1-internal-only feature.

---

## 19. Real output artifacts

`execution_package/execution_writer.py` writes, per run:

**Unconditional core:** `manifest.json`, `consolidated_artifact.json`, `engineering_context.json`,
`llm_request.json`, `analysis_result.json`, `raw_llm_response.json`, `execution_summary.md`,
`baseline_metrics.md`, `review.md`.

**Conditional, one set per phase that actually produced a result:** `validation_result.json` +
`validation_report.md`; `cp1_report.md`; `grounding_result.json` + `grounding_report.md` +
`grounding_metrics.md`; `quality_governance_result.json` + `quality_governance_report.md` +
`quality_governance_summary.md`; `requirement_enhancement_result.json` + 2 reports;
`recommendation_result.json` + 2 reports; `continuous_improvement_result.json` + 2 reports;
`knowledge_graph_result.json` + 2 reports; `organizational_memory_result.json` + 2 reports;
`learning_result.json` + 2 reports; `testable_requirement_set.json`.

**Sibling artifacts written directly by the CLI, not by `ExecutionWriter`:** `run_state.json` (via
`RunStateManager`), `token_usage.json` (when any call was recorded).

**Confirmed by a repository-wide search: none of the deck's named output files
(`raw-records.json`, `canonical-requirements.json`, `consolidated-requirements.json`,
`requirement-analysis-report.json`, `cp1-validation-report.json`, `validated-requirement-model.json`)
exist anywhere in this repository outside `docs/proposals/` itself.** The real output concept is an
"Execution Package," not the deck's ad hoc file list.

---

## 20. Governance — the real ADRs

| ADR | Subject | Status |
|---|---|---|
| ADR-0011/0012/0013 | CP1 pattern and criteria | Accepted |
| ADR-0014 | Prompt Governance Subsystem | Accepted |
| ADR-0015 | Engineering Context Orchestration | Accepted |
| ADR-0016 | Grounding | Accepted |
| ADR-0017 | Requirement Quality Governance | Accepted |
| ADR-0018 | Requirement Enhancement | Accepted |
| ADR-0019 | Recommendation | Accepted |
| ADR-0021 | Cross-Execution Data Architecture & Historical Intelligence Constitution | Accepted (ratified by ADR-0049) |
| ADR-0022 | Continuous Improvement | Accepted |
| ADR-0023 | Knowledge Graph Framework | Accepted |
| ADR-0024/0025/0026 | Historical-Truth-cluster supporting decisions | Accepted (ratified by ADR-0049) |
| ADR-0027 | Organizational Memory | Accepted |
| ADR-0028 | Learning Framework (design) | Accepted (ratified by ADR-0049) |
| ADR-0029 | Learning Runtime | Accepted, live |
| ADR-0030 | Executable Specification Engineering | **Proposed — not Accepted** |
| ADR-0031 | Authoritative Layer Model | Accepted (supersedes ADR-0020) |
| ADR-0032 | Layer 1 Capability Freeze | Accepted, in force |
| ADR-0034 / ADR-0042 | `TestableRequirementSet` contract | Accepted |
| ADR-0036 | Run/Stage State Model | Accepted |
| ADR-0048 | Traceability Graph | Accepted |
| ADR-0049 | Engineering Constitution | Accepted |
| ADR-0050 | Artifact Cache | Accepted (for the scope built) |

**ADR-0032 — the freeze in force today.** No new capability number in the L1 series
(CAP-001–073, CAP-081–086) may be added until a lifting ADR satisfies three preconditions: Layer 2
must reach Runtime Integration, Architecture Review Board approval, and explicit CAP number(s)
named. Five carve-outs are permitted without lifting the freeze: (1) emitting
`TestableRequirementSet` (ADR-0034), (2) run/stage-state integration (ADR-0036), (3) the ADR-0033
package renames, (4) bugfixes, (5) tests. CAP-088 (traceability graph) sits **above** the frozen
081–086 range, consistent with being treated as new/separately scoped rather than a further
addition inside the frozen series.

**Article relevance from ADR-0049 (Engineering Constitution).** Of its 12 articles, the ones most
load-bearing for L1 specifically: **Article I** (Layer Isolation & Upward-Only Dependency — governs
why `traceability_graph/` does not import `knowledge_graph/`, §17); **Article II** (the Truth
Hierarchy, Runtime → Historical → Derived — explains the "referentially synthetic" Historical
Dataset in §16 and the Runtime-vs-Historical boundary §17 respects); **Article VII** (Deterministic
Gates Decide — CP1's single criterion, §12, and Grounding's non-AI matching, §10); **Article IX**
(Single Canonical Owner Per Responsibility — one Prompt Registry, §7, one `generate_content` call
site, §7); **Article XI** (Reuse Before Regeneration — the shared cache primitive, §18).

---

## 21. Known internal documentation lag — a real, present-day finding

Six package `__init__.py`/service docstrings inside `requirement_intelligence/` — `grounding/`,
`knowledge_graph/`, `continuous_improvement/`, `organizational_memory/`, `learning/`, and
`requirement_quality_governance/` — currently assert some form of *"not wired into any execution
pipeline… nothing calls X at runtime."* Every one of these claims is demonstrably false against the
current `scripts/run_requirement_analysis.py`, which calls all six (unconditionally for Enhancement/
Grounding/Continuous Improvement/Knowledge Graph; conditionally, gated on `--validate` and/or peer
results, for Validation/CP1/Quality Governance/Organizational Memory/Learning/Recommendation).

This is a real, present-day finding, not carried forward from the stale-deck problem this document
exists to fix: each docstring was written and frozen at that subsystem's own architecture-freeze
milestone (its "B" build task) and never updated at its later runtime-integration milestone (its
"C"/"D" wiring task). It shares the shape of the deck's own staleness — a document describing an
earlier state of the system, trusted past its shelf life — but at module-docstring granularity
rather than deck granularity. Flagged here so a reader of the code directly is not misled the same
way a reader of the deck would be; **this LLD's own claims about wiring status (§10, §16) were
verified against the live call sites in `scripts/run_requirement_analysis.py`, not against these
docstrings.**

---

## 22. Deck reconciliation — what the PPTX got wrong, stated once, precisely

| Deck claim | Real, as documented above |
|---|---|
| Sources: HP ALM Trial, OWASP ZAP, SonarQube | JIRA, ZAP, SonarQube (§2). No HP ALM connector has ever existed. |
| Enrichment via Azure OpenAI | Gemini is the live, default provider; Azure OpenAI is an explicit `NotImplementedError` stub (§7). |
| Consolidation groups by module/feature-intent/functional-similarity/security-relevance/quality-relevance/risk-level (implying semantic/AI grouping) | A deterministic, non-AI cascade: component → tag → endpoint → risk category (§5). |
| Named output files (`raw-records.json`, `canonical-requirements.json`, etc.) | None exist. The real concept is an Execution Package with a different, real file set (§19). |
| CP1's 7 named rules | CP1 has exactly one live criterion, CP1-0001 (§12). A different, larger 18-rule taxonomy exists one layer downstream, in Requirement Quality Governance (§13) — not the same thing as CP1. |
| Generic "source registry + connector interface" extensibility pattern | Matches, plus an `EXECUTION_MODE=FILE\|API` toggle the deck never anticipated (§2). |

**Built with zero mention in the deck at all:** the Prompt Registry (§7), the LLM provider layer's
resilience/instrumentation (§7, §18), Engineering Context Orchestration (§6), Grounding (§10),
Requirement Enhancement (§9), Requirement Quality Governance (§13) as distinct from CP1,
Recommendation (§15), the entire Continuous Improvement / Knowledge Graph / Organizational Memory /
Learning cluster (§16), and the Traceability Graph (§17). Per ADR-0031 D3, several of these are
entire redesignated sub-capabilities (CAP-081 through CAP-086) with their own multi-milestone ADR
arcs — none of it existed as a concept when the deck was written.

---

## 23. What Layer 1 does not do

- **No scenario, Gherkin, or BDD generation.** L1 emits requirements (and, via Requirement
  Enhancement, deterministic enrichment of them) — scenario generation lives entirely in Layer 2
  (confirmed independently by L2's own Reviewer's note: *"Layer 1 emits risks; Layer 2 owns all
  scenario generation... scenario generation lives in exactly one layer"*).
- **No page objects, step definitions, or automation code.** Layer 3's job.
- **No suite-wide quality governance** (Sonar rating gates, compile checks, near-duplicate
  sweeps). Layer 4's job — a differently-named, differently-scoped "quality governance" from L1's
  own Requirement Quality Governance (§13); the two share a phrase, not a boundary.
- **No test execution, browser automation, or SUT interaction of any kind.** Layer 5's job.
- **No semantic/AI evidence matching in Grounding today** — deterministic text matching only
  (§10); semantic strategies are named as future work in the code itself, not built.
- **No genuine cross-run organizational history yet** — the Continuous Improvement / Knowledge
  Graph / Organizational Memory / Learning cluster is real and live, but its Historical Dataset
  input is a per-execution stand-in, not a persisted multi-run store (§16).
- **No gating from the Traceability Graph** — report-only, by design, today (§17).

---

## 24. Confirmation

- Clean tree, `main`, pushed tip, at the point this document was written. `make lint`: clean.
  `make test`: 5982 passed. Documentation-only task; no source file under test was touched.
- Every architectural claim above was verified directly against the real code in this session —
  connector registry, consolidation rules, the CP1 engine, the Requirement Quality Governance rule
  catalog, the LLM providers, the Prompt Registry composition root, the grounding pipeline, the
  orchestration policies, the Historical Truth cluster, the traceability graph, the execution
  writer's output list, and every cited ADR's status line — not carried forward from memory or from
  the source deck.
- Two corrections against prior project memory, made explicit rather than silently applied: the
  real code default for `GEMINI_MODEL` is `gemini-2.5-pro` (this environment's local `.env`
  currently overrides it to `gemini-3.1-flash-lite` for live runs — both facts are stated, §7); and
  the real rule counts are 13 Validation rules and 18 Quality Governance `QG-*` rules (not the
  11/17 figures in some prior notes), confirmed by direct file/id counts, §11, §13.
- This document is additive: the source deck (`layer-1-requirement-intelligence-layer-lld.pptx`)
  is untouched, retained as proposal history only, and marked superseded in
  `docs/proposals/README.md` — the same disposition L2/L3's own PPTs already carry.
