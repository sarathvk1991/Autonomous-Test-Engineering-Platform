# ADR-0050 — Artifact-Level Generation Cache

- **Status:** Accepted (first three increments, 2026-08-14; fourth increment, 2026-08-20; fifth
  and FINAL increment, 2026-08-21 -- the cache now covers ALL 5 generators D5 named -- see
  "Implementation Note," below).
- **Date:** 2026-08-14
- **Supersedes:** nothing. **Amends:** nothing.
- **Governing design:** none — this ADR *is* the governing design. It records the decisions
  reached by a design-surfacing task (`docs/architecture/mentor-feedback-scoping.md`, item #1's
  cluster, "ARTIFACT-LEVEL CACHE DESIGN SURFACED," 2026-08-14) rather than a preceding
  `docs/proposals/*.md` document — the surfacing note itself served that role, read in full
  before this ADR was written.
- **Depends on:** `requirement_intelligence/llm/generation_identity.py` (`GenerationIdentity` —
  the prompt/model identity this ADR's key relies on; additive infra, not itself ADR'd);
  ADR-0044 (Layer 3 Automation Engineering Architecture Freeze — governs the four L3 generator
  Protocols this cache wraps: `StepDefinitionGenerator`, `PageObjectGenerator`,
  `UtilityGenerator`, `TestDataGenerator`); ADR-0043 (Layer 2 Feature Engineering Architecture
  Freeze — governs `FeatureContentGenerator`, the fifth wrapped Protocol); ADR-0036 (Run and
  Stage State Model — source of `_hash_artifacts`'s content-hash *pattern*, reused here; its
  `RunStateManager` *class* is explicitly not reused, D2); ADR-0048 (Traceability Graph — sibling
  precedent for a new, standalone capability ADR written for a focused mechanism rather than a
  whole layer, and source of `change_impact_for_method`/`build_change_impact_report`, this
  cache's own downstream consumer once delta-scoped regeneration is built).
- **Runtime status: Built and tested (ALL FIVE of D5's named generators — three increments
  2026-08-14, a fourth 2026-08-20, the fifth and FINAL 2026-08-21).**
  `requirement_intelligence/llm/generation_cache.py`
  (`compute_cache_key`, `GenerationCacheEntry`, `GenerationCacheStore`) is the one shared store/key
  module all five increments reuse, unmodified. `automation_engineering/generation/
  caching_step_definition_generator.py` (`CachingStepDefinitionGenerator`, wrapping
  `LiveStepDefinitionGenerator`), `feature_engineering/generation/
  caching_feature_content_generator.py` (`CachingFeatureContentGenerator`, wrapping
  `LiveFeatureContentGenerator` — 45.4% of the measured distribution), `automation_engineering/
  generation/caching_test_data_generator.py` (`CachingTestDataGenerator`, wrapping
  `LiveTestDataGenerator` — the other near-equal sink, 43.4%), `automation_engineering/
  generation/caching_page_object_generator.py` (`CachingPageObjectGenerator`, wrapping
  `LivePageObjectGenerator` — absent from the one measured distribution, real share unmeasured, see
  the fourth Implementation Note), and `automation_engineering/generation/
  caching_utility_generator.py` (`CachingUtilityGenerator`, wrapping `LiveUtilityGenerator` — also
  absent from the one measured distribution AND not yet wired into stage 15 at all, real share
  unmeasured, see the fifth Implementation Note) all exist, implementing D1–D4 exactly as decided
  below — **the set of five generators D5 named is now complete; only the remediator stays
  unwrapped, per D5's own exclusion.** Both build-time gaps D3 named are closed for all five
  generators: `automation_engineering/generation/
  live_step_definition_generator.py` gained `resolve_step_definition_identity`/
  `build_step_definition_payload`; `feature_engineering/generation/live_content_generator.py` gained
  `resolve_feature_content_identity`/`build_feature_content_payload`; `automation_engineering/
  generation/live_test_data_generator.py` gained `resolve_test_data_identity`/
  `build_test_data_payload`; `automation_engineering/generation/live_page_object_generator.py`
  gained `resolve_page_object_identity`/`build_page_object_payload`; `automation_engineering/
  generation/live_utility_generator.py` gained `resolve_utility_identity`/`build_utility_payload`
  (Gap 1, pre-call identity, and
  the single shared payload definition closing the "serialization drift" residual risk named in D1,
  each generator's own version); `requirement_intelligence/llm/token_usage.py`'s
  `TokenUsageTotals.cache_hit_count`/`TokenUsageTracker.record_cache_hit` (Gap 2, the
  zero-cost-verified bucket) is generator-agnostic and required no change for the second through
  fifth generator to reuse. Proven by 33 (step-def) + 13 (feature-content) + 13 (test-data) + 19
  (page-object) + 19 (utility) new deterministic unit tests (`requirement_intelligence/tests/unit/
  test_generation_cache.py`, `tests/unit/
  test_automation_engineering_generation_caching_step_definition_generator.py`, `tests/unit/
  test_feature_engineering_generation_caching_feature_content_generator.py`, `tests/unit/
  test_automation_engineering_generation_caching_test_data_generator.py`, `tests/unit/
  test_automation_engineering_generation_caching_page_object_generator.py`, `tests/unit/
  test_automation_engineering_generation_caching_utility_generator.py`, plus additive
  `TestCacheHitRecording`/`TokenUsageTotals` cases) AND by three real, live measured runs
  (Implementation Notes, below — the fourth AND fifth increments are proven deterministically only,
  no live measurement yet, since neither page-object nor utility generation is activated in the
  live CLI, and utility is not even wired into stage 15 at all). **Not
  wired into any live pipeline.** `scripts/run_requirement_analysis.py` still constructs
  `LiveStepDefinitionGenerator`, `LiveFeatureContentGenerator`, and `LiveTestDataGenerator` directly,
  unwrapped (and does not construct a live page-object or utility generator/matcher pair at all
  yet); no
  `PlatformContext` composition-root method exists for this cache and none is added here — a
  future, separate milestone would wire it live, mirroring how ADR-0048's own Traceability Graph
  stayed unwired after being built and measured.

## Problem

Nitin's mentor feedback named a four-part re-run/delta-scoped-regeneration cluster; part of it —
content-addressed caching — is his own words: key each artifact on spec-slice/source-snapshot +
prompt-version + model-version, reuse anything whose inputs haven't changed, skip regeneration,
save tokens. Two prerequisites now exist: pinning (`GenerationIdentity`, threaded onto every
L2/L3 artifact record, prompt-version + model-version captured) and the token-usage
instrumentation (the scorecard this cache's savings would show against). The design-surfacing
task read the real generation pipeline — five LLM-driven generators' `generate`/`_build_prompt`
methods — against Nitin's own proposed key, and found it **silently incomplete**: `REQ-*`, the
key component the surfacing's own prior note recommended, does not cover everything a generator's
prompt actually serializes. Building the cache on that key, unexamined, would have shipped a
cache that returns wrong artifacts under real, unremarkable edits (D1). This ADR exists to record
the corrected design *before* any of it is built — ADR-first, matching this platform's standing
discipline, not the scores-first inversion `ADR-0048`'s own traceability-graph build used and
documented as a deliberate, one-time exception.

## Decision

Introduce a new, governed subsystem, **artifact-level generation caching**, wrapping the five
LLM-driven generation seams (`LiveStepDefinitionGenerator`, `LivePageObjectGenerator`,
`LiveUtilityGenerator`, `LiveTestDataGenerator`, `LiveFeatureContentGenerator`; the sixth,
`LiveFeatureRemediator`, is explicitly excluded, D5). Five decisions, each detailed below:

1. **The key** is a hash of the exact deterministic payload each generator already serializes
   immediately before its LLM call, combined with its `GenerationIdentity` — not a `REQ-*` or any
   other id-based proxy (D1, the centerpiece).
2. **The store** is on-disk and content-addressed, mirroring `atomic_write.py` +
   `_hash_artifacts`'s content-hash pattern — not `RunStateManager` itself (D2).
3. **Interception** happens at each generator's own Protocol boundary, via one small caching
   decorator per Protocol sharing one store module; a **hit** replays the stored artifact and its
   stored identity, skipping the LLM call (D3).
4. **Correctness and safety**: a hit is guaranteed (by D1's key construction) to be a genuine
   prior output for identical inputs, and flows downstream identically to a fresh generation —
   same record, same validation, same promotion (D4).
5. **Scope and sequence**: build the store, the key, and one decorator first, on one generator,
   measured — not the full five-generator wrap in one step (D5).

---

## D1 — The key, and why the obvious key was wrong (the centerpiece decision)

**The key:**

```
key = sha256(
    prompt_id + "\x00" + prompt_version + "\x00" + prompt_sha256 + "\x00"
    + provider + "\x00" + model + "\x00"
    + input_payload_json
)
```

where `input_payload_json` is the *exact* string each generator's own `_build_prompt` already
builds via `json.dumps(..., sort_keys=True)` immediately before constructing its `LLMRequest` —
for `LiveStepDefinitionGenerator`, the step text/step_type/captures/target_package/
page_object_interface/utility_interface/customqa_constraints payload; for
`LivePageObjectGenerator`, the class_name/need(s)/return_type(s)/parameters/customqa_constraints
payload (including `additional_method_needs`); for `LiveUtilityGenerator`, the equivalent
action-text/captures/class_name payload; for `LiveTestDataGenerator`, the specification/
target_class_name payload; for `LiveFeatureContentGenerator`, the title/narrative/component/
acceptance_criteria payload. `prompt_id`/`prompt_version`/`prompt_sha256`/`provider`/`model` are
exactly `GenerationIdentity`'s own five fields, already captured at every one of these call sites
(the pinning build).

**Why the naive key — `(REQ-* content hash, prompt_sha256, model)`, the prior surfacing note's own
recommendation — is wrong, checked against the real code, not assumed:**

1. **`REQ-*` under-covers even its own generator's input.** `generate_requirement_id`
   (`contracts/id_generation.py`) hashes only `normalize(title) + source_external_ids`. But
   `LiveFeatureContentGenerator._build_prompt` serializes `title`, `narrative`, `component`, *and*
   `acceptance_criteria` (`ac_id`/`statement`/`polarity_hints`) into the prompt.
   `generate_acceptance_criterion_id` is ordinal-based (`AC-<REQ short>-NN`), never content-hashed.
   **An edited `narrative`, `component`, or acceptance-criterion `statement`, with `title`
   unchanged, changes the real output but leaves `REQ-*` identical** — a cache keyed on it would
   return a stale hit, silently, with no signal anything was wrong. This is not a hypothetical edge
   case; requirement narratives and acceptance criteria are edited far more often than titles.
2. **`REQ-*` does not apply at all to the four L3 generators.** Their inputs
   (`StepDefinitionGenerationContext`, `PageObjectGenerationContext`, `UtilityGenerationContext`,
   `TestDataGenerationContext`) carry no `REQ-*`-derived field anywhere — confirmed by reading all
   four context dataclasses. A key built around `REQ-*` simply has nothing to key step-definition,
   page-object, utility, or test-data generation on.

**Why the corrected key is complete, by construction, not by argument:** `input_payload_json` is
not an approximation of what determines the generator's output — it **is** what determines it. It
is the literal string substituted into the rendered prompt (`_build_prompt` builds it, then hands
it straight to the template/LLM request). Hashing it therefore captures every input that varies
the output *to exactly the same degree the generator's own prompt construction already does* —
correctness of the key is bound to correctness of `_build_prompt`'s own serialization, a
pre-existing obligation every one of these generators already carries for the LLM call itself, not
a new one this design invents. `prompt_sha256` separately covers template-text changes (a prompt
version bump); `provider`/`model` cover a model swap. Together, the five components cover
everything a generator call is a deterministic function of.

**Two residual risks, named, not hidden:**

- **Serialization drift.** If a context dataclass ever grows a field a generator's own
  `_build_prompt` forgets to include in `input_payload`, the prompt and the cache key silently
  diverge *together* — the key would still be complete relative to what the LLM actually saw, but
  wrong relative to what the caller intended it to see. This is a code-review-time discipline for
  future context-field additions, not a design gap this ADR can close structurally.
- **Provider-level non-determinism.** Hosted model APIs do not guarantee bit-identical output
  across calls, even at `temperature=0.0`. A perfect key guarantees "this was a genuine prior
  output for these exact inputs" — never "identical to what a fresh call would produce today."
  This is inherent to any LLM-artifact cache, not a defect of this key; the existing downstream
  validation gates (CP1–CP5, promotion) are the mitigation, applied identically to cached and
  fresh artifacts (D4).

`REQ-*`/`AC-*`/`step_text`/`method_name` remain useful as a **human-readable label** stored
alongside a cache entry (diagnosis; a future "invalidate everything touching REQ-1234" tool) — they
are decided **out** of the correctness-bearing hash by this ADR, not merely deprioritized.

`temperature` is a fixed platform-wide constant (`0.0`, `LLMRequest`'s own default) today and is
therefore not part of the key; the moment it becomes a configurable per-call parameter, it must
join `input_payload_json`'s role, an amendment this ADR names in advance rather than leaving to be
rediscovered.

## D2 — The store: on-disk, content-addressed, a new sibling, not `RunStateManager`

The store persists on disk, keyed by D1's hash, surviving across process invocations — cross-run
reuse is the entire point of this capability; an in-run-only cache (a dict) would only prevent
duplicate calls within a single run, which reuse-first orchestration and per-need deduplication
already mostly do, and would not touch Nitin's actual complaint (token cost across re-runs of the
same corpus).

The store reuses `_hash_artifacts`'s (`requirement_intelligence/run_state/run_state_manager.py`)
content-hash *pattern* — sha256 over deterministically serialized content — and
`atomic_write.py`'s durable-write primitive, the same two precedents `RunStateManager` itself
already establishes. It does **not** reuse `RunStateManager` as a class: `RunStateManager.
should_skip` is keyed by `stage_id`, closed to the fixed 19-entry `STAGE_DEFINITIONS` catalogue
(`_find` raises `ValueError` on any other id) — architecturally unable to hold a per-artifact,
open-ended key space. A new, small, sibling module owns the artifact cache; `RunStateManager` is
unmodified.

Entry shape (decision, not implementation): one file per cache entry, path derived from the key
hash (avoiding one flat directory of unbounded size), storing the generated artifact text, its
`GenerationIdentity`, and the human-readable label components named in D1. Where the cache
directory itself lives (a new env var or CLi flag, sibling to how run/workspace directories are
already configured) is left to the implementation milestone — a configuration decision, not an
architectural one.

## D3 — Interception, hit consumption, and the two gaps the build must close

**Interception point.** The five wrapped generators span five distinct Protocols
(`StepDefinitionGenerator`, `PageObjectGenerator`, `UtilityGenerator`, `TestDataGenerator`,
`FeatureContentGenerator`) with different input shapes — there is no single universal wrapper
class. The decision is one small `Caching<X>Generator` decorator **per Protocol**, each
implementing that Protocol and constructor-wrapping any inner generator conforming to it (mirroring
exactly how `LiveStepDefinitionGenerator`/`StubStepDefinitionGenerator` are already interchangeable
peers behind the same seam), with all five decorators delegating their key/get/put logic to the one
shared store module from D2 — one implementation of the mechanism, five thin adapters. Rejected:
wrapping inside each live generator directly (mixes cache concerns into classes whose whole job
today is "render prompt, call provider, wrap response"); wrapping at the orchestrator layer
(`orchestrate_step_definition`, `orchestrate_page_object_method`, `orchestrate_utility_method`,
`generate_test_data_class`, `generate_feature_file` are four-plus distinct call sites — the
identical duplication problem one level up).

Because every downstream consumer (`orchestrator.py`, `runner.py`, `AssetRecord`/`FeatureRecord`
construction) already reads a generator through its Protocol or via
`getattr(generator, "last_identity", None)` — never a concrete class — **zero changes are required
at any downstream site** for this wrap to work (D4, blast radius).

**Hit consumption.** On a HIT, a decorator returns the stored artifact text and sets its own
`last_identity` from the **stored** `GenerationIdentity` — not a freshly-constructed one — so
`AssetRecord`/`FeatureRecord.generation_identity` stays populated exactly as it would for a fresh
generation. On a MISS, the decorator delegates to the wrapped live generator, stores the result and
its `last_identity` under the key, and returns it unchanged.

**Gap 1 — pre-call identity.** Today, `last_identity` populates only *after* a call returns,
because it is read off the `LLMResponse`, not off the generator's own already-fixed
construction-time state. But every component is in fact already fixed before the call:
`prompt_sha256` from the registry (`self._definition.metadata.sha256`, set in `__init__`); `model`/
`provider` from the provider's own construction-time state (`GeminiProvider.__init__` sets
`self._model_name` once and echoes it verbatim into every response, confirmed at
`gemini_provider.py:366,450` — the response never reports a model the provider wasn't already
going to use). A caching decorator must decide hit-or-miss *before* calling, so the build must
expose this pre-call identity (a small additive public accessor, or a constructor-supplied identity
prefix) rather than reading it off `last_identity` after the fact. Named here as a decision the
build must make, not solved by this ADR.

**Gap 2 — the token scorecard.** `TokenUsageTracker.record(call_type, usage)` today treats
`usage=None` as *unmeasured* (`unmeasured_call_count`, an incompleteness signal) — recording a hit
that way would make the scorecard show it as a broken measurement, the opposite of the saving this
whole capability exists to demonstrate. `TokenUsageTotals` needs a small additive third bucket
(e.g. `cache_hit_count`, distinct from both measured and unmeasured) before a hit is trustworthy in
the scorecard. Named here as a required, small, additive extension the build must make — not
performed by this ADR.

## D4 — Correctness and safety posture

A hit returns the same artifact a fresh generation would, for as long as D1's key holds (the
residual risks named there are the only ways this guarantee can fail, and both are named, not
hidden). A hit's artifact flows downstream **identically** to a fresh one: the same
`AssetRecord`/`FeatureRecord` construction, the same CP1–CP5 validation, the same promotion
pipeline — because those sites consume `.generate()`/`.last_identity` through a Protocol/`getattr`,
oblivious to cache involvement (D3). The saving is measurable, not asserted: once Gap 2 (D3) is
closed, the token scorecard shows a hit as zero new tokens against the call type it would otherwise
have cost. **A cache that returns a wrong artifact is worse than no cache** — this is why D1 is
this ADR's centerpiece, not an implementation detail subordinate to D2/D3.

## D5 — Scope and sequence: one generator, measured, before extending

**First build** (a future, separate milestone; not this ADR): the store (D2) + the key (D1) + one
decorator, wrapping `LiveStepDefinitionGenerator` — recommended over the other four for its recent
iteration volume (the live-regeneration defect-fixing line of work has repeatedly re-run step-
definition generation over the same corpus) and its existing measurement infrastructure. Measure
via the token-usage scorecard: run the same corpus twice; the second run's
`step_definition_generation` call-type totals should collapse toward the new `cache_hit_count`
bucket rather than fresh prompt/completion tokens. Only after that saving is demonstrated does
extension to the remaining four generators proceed — scores-first *within* an ADR-first capability,
not in place of one; the surfacing prompt this ADR follows was explicit that this ordering (ADR
before any code) is deliberately not the traceability graph's own scores-first inversion.

**Explicitly excluded:** `LiveFeatureRemediator`. `remediate(content, violations)` repairs a prior
attempt rather than performing first-generation; live remediation is independently known to be
rare, and re-running the identical `(content, violations)` pair across corpus re-runs is far less
likely than re-running the same first-generation call. Weak return on caching complexity; not
recommended as a target even after the five-generator wrap, absent new evidence.

**Deferred, each with its own trigger:**

- **Spec-slice (Nitin's item #4, branch-scoped vertical slices).** Not a blocker at any point in
  this design — D1's key never used `REQ-*`/source-snapshot as a proxy in the first place, so it
  needs neither #4 nor a new raw-evidence hash to be buildable.
- **Delta-scoped regeneration** (cluster item 2). The next piece after this cache exists — it would
  consume this cache as its own staleness signal and `change_impact_for_method`/
  `build_change_impact_report` (`requirement_intelligence/traceability_graph/change_impact.py`,
  built, ADR-0048's own named scope) as its blast-radius input, exactly Nitin's own model ("the
  cache tells you an artifact is stale; the change-impact graph tells you which downstream
  artifacts that staleness actually reaches").
- **The deterministic/LLM split** (cluster item 3). Orthogonal — narrows what ever needs a cache
  entry over time, but does not gate D1–D5; sequenced independently.

---

## Implementation Note (2026-08-14) — D5's first increment, built and measured

The first increment D5 names (store + key + one decorator, wrapping
`LiveStepDefinitionGenerator`, measured) was built the same day this ADR was written, closing both
D3 gaps in the process. This note records what was actually verified — decisions above stay
decisions; this is the separate record of what now backs them.

**Correctness, proven deterministically, no live LLM call involved:**
- A payload field a naive `REQ-*`/id-only key would have missed (`page_object_interface`,
  `customqa_constraints`) changes the corrected key even with the step's own `need.text` held
  fixed — the exact defect shape D1 found, proven not to recur.
- A second `generate()` call with an unchanged context HITS and skips the wrapped generator
  entirely (the inner provider's call count stays at 1, not 2).
- A changed input (page-object interface, a customqa constraint, or the step text itself) MISSES
  and regenerates — never a stale hit.
- A HIT replays the STORED `GenerationIdentity`, not a fresh one, and does so across two
  independent decorator/provider instances sharing only the on-disk store — proving cross-instance,
  not merely intra-object, reuse.
- A HIT records `TokenUsageTotals.cache_hit_count`, never `unmeasured_call_count` — the two
  buckets proven distinct.
- Every pre-existing `LiveStepDefinitionGenerator` test (`tests/unit/
  test_automation_engineering_generation_step_definition_generator.py`) passes unchanged after
  `build_step_definition_payload` was extracted from `_build_prompt` — the refactor is
  behavior-preserving, not merely believed to be.
- A MISS whose real, post-call identity does not match the caller-supplied pre-call identity raises
  (`GenerationCacheIdentityMismatchError`) rather than silently caching under the wrong key.

**The measured saving — one real, live run, not simulated.** A standalone, uncommitted harness
script (mirroring `CAP-088`'s own first-measurement precedent: real code, not committed pipeline
wiring) ran three realistic `StepDefinitionGenerationContext`s against the real, live Gemini API
twice: once against a fresh on-disk cache (every call a genuine LLM call), once against the SAME
on-disk cache from brand-new decorator and provider instances (a fresh process's own cold start,
proxied). Pass 1: 3 real LLM calls, 7003 total tokens. Pass 2: 0 new LLM calls, 0 new tokens, 3
cache hits, byte-identical artifacts to pass 1. `gemini-3.5-flash` (the platform's own
step-definition-generation default) returned transient `503 UNAVAILABLE` ("high demand") from
Google at measurement time — confirmed, by direct probe, to be model-specific, not an API-key or
connectivity problem (`gemini-2.5-flash` and the platform's `GEMINI_MODEL` default both succeeded
immediately) — so the measurement ran against `gemini-2.5-flash` instead, a harness-only
substitution with no bearing on the cache mechanism itself, which is model-agnostic by
construction (D1's key includes `model` as one of its own components precisely so a model swap is
a correctly-computed miss, never a silent hit).

**Scope held exactly as D5 decided.** Only `LiveStepDefinitionGenerator` is wrapped. The other four
generators, the remediator, delta-scoped regeneration, and the deterministic/LLM split are all
untouched by this increment — extending to them is the next, separate step D5 already named, not
performed here.

## Implementation Note (2026-08-14) — D5's second increment: `LiveFeatureContentGenerator`, built and measured

The next generator D5 named for extension — `LiveFeatureContentGenerator`, the biggest token sink
in the measured distribution (`feature_content_generation`, 22,383 tokens / 45.4% of the 20-call
sample, `docs/architecture/mentor-feedback-scoping.md`) — was wrapped the same day, repeating the
first increment's pattern exactly, not rebuilding it: the shared store/key module
(`generation_cache.py`) is reused verbatim; only a new `CachingFeatureContentGenerator` decorator
(`feature_engineering/generation/caching_feature_content_generator.py`) and the same pre-call-identity/
payload-extraction pair for this generator (`resolve_feature_content_identity`/
`build_feature_content_payload`, added to `live_content_generator.py`, mirroring
`resolve_step_definition_identity`/`build_step_definition_payload`) were built. Pre-flight confirmed
the pattern transfers directly, not merely by analogy: `LiveFeatureContentGenerator._build_prompt`
already built a deterministic `json.dumps(..., sort_keys=True)` payload immediately before its LLM
call (the same shape D1 already named this generator's payload as, above); its identity fields
(`prompt_id`/`prompt_version`/`prompt_sha256`/`provider`/`model`) are knowable pre-call the same way
(registry read in `__init__`, provider/model supplied by the caller); its Protocol boundary
(`FeatureContentGenerator.generate(requirement) -> str`) wraps with zero downstream changes, same as
`StepDefinitionGenerator`; and `TokenUsageTracker.record_cache_hit` needed no change at all — it was
already call-type-parameterized, not step-def-specific, by the first increment's own design. The one
adaptation: `GenerationCacheIdentityMismatchError` is this module's own class, subclassing
`feature_engineering.generation.errors.TransportFailureError` rather than
`automation_engineering.errors.TransportFailureError`, because the two packages carry distinct
transport-failure hierarchies — a naming/inheritance detail, not a mechanism difference.

**Correctness, proven deterministically, no live LLM call involved** (13 new tests, `tests/unit/
test_feature_engineering_generation_caching_feature_content_generator.py`, mirroring the step-def
suite's own five test classes):
- A payload field a naive `title`-only (the L2 analogue of `REQ-*`) key would have missed
  (`narrative`, an acceptance-criterion `statement`) changes the corrected key even with `title`
  held fixed — the exact defect shape D1 found for this generator specifically, proven not to recur.
- A second `generate()` call with an unchanged requirement HITS and skips the wrapped generator
  entirely (the inner provider's call count stays at 1, not 2).
- A changed input (`narrative`, an acceptance-criterion `statement`, or `title` itself) MISSES and
  regenerates — never a stale hit.
- A HIT replays the STORED `GenerationIdentity` across two independent decorator/provider instances
  sharing only the on-disk store — cross-instance reuse, not merely intra-object memoization.
- A HIT records `TokenUsageTotals.cache_hit_count` under `feature_content_generation`, never
  `unmeasured_call_count`.
- A MISS sends the identical prompt, and returns generated text verbatim, exactly as an unwrapped
  `LiveFeatureContentGenerator` would — the decorator is transparent on a MISS.
- A MISS whose real, post-call identity does not match the caller-supplied pre-call identity raises
  `GenerationCacheIdentityMismatchError` rather than silently caching under the wrong key.

**The measured saving — one real, live run against the real, biggest sink.** The same standalone,
uncommitted harness pattern (real code, not committed pipeline wiring) ran three realistic
`TestableRequirement`s (password reset, shipping-address update, search-filter) through
`CachingFeatureContentGenerator`-wrapped `LiveFeatureContentGenerator` against the real, live Gemini
API twice: once against a fresh on-disk cache, once against the SAME on-disk cache from brand-new
decorator and provider instances. Pass 1: 3 real LLM calls, 3702 total tokens (3195 prompt + 507
completion). Pass 2: 0 new LLM calls, 0 new tokens, 3 cache hits, byte-identical artifacts to pass 1.
Unlike the step-def measurement, no model substitution was needed here — the platform's own
`GEMINI_MODEL` default (`gemini-3.1-flash-lite`) succeeded on every call on the first attempt.

**Scope held exactly as this increment intended.** Only `LiveFeatureContentGenerator` is added to the
wrapped set (alongside `LiveStepDefinitionGenerator`, first increment). `LivePageObjectGenerator`,
`LiveUtilityGenerator`, `LiveTestDataGenerator`, and the remediator remain unwrapped; delta-scoped
regeneration and the deterministic/LLM split remain untouched — all still D5's own named future
work, not performed here. `test_data_generation` (21,387 tokens / 43.4%, the other near-equal sink
in the same distribution) is the natural next target, not claimed by this increment.

## Implementation Note (2026-08-14) — D5's third increment: `LiveTestDataGenerator`, built and measured

The other near-equal sink named as the natural next target above — `LiveTestDataGenerator`
(`test_data_generation`, 21,387 tokens / 43.4% of the same 20-call distribution sample) — was
wrapped the same day, the third repeat of the identical pattern. Pre-flight confirmed this
transferred even MORE directly than feature-content did: `LiveTestDataGenerator` lives in the same
package as `LiveStepDefinitionGenerator` (`automation_engineering.generation`), uses the same
governed system/user template contract (unlike feature-content's append-a-final-section
workaround), and subclasses the SAME `automation_engineering.errors.TransportFailureError`
hierarchy — so the third increment's `GenerationCacheIdentityMismatchError` is REUSED from the
step-def caching module rather than defined a third time (`CachingTestDataGenerator` imports it
directly). `_build_prompt` already built a deterministic `json.dumps(..., sort_keys=True)` payload
right before the LLM call (the `requirement_id`/`target_class_name`/`target_package`/`fields`/
`customqa_constraints` payload D1 already named for this generator, above); its identity fields are
knowable pre-call the same way as the other two; its Protocol boundary
(`TestDataGenerator.generate(context) -> str`) wraps with zero downstream changes; and
`test_data_generation` was already a registered call type, so `TokenUsageTracker.record_cache_hit`
needed no change at all.

Built: `automation_engineering/generation/caching_test_data_generator.py`
(`CachingTestDataGenerator`), reusing `generation_cache.py`'s store/key unmodified and
`caching_step_definition_generator.py`'s `GenerationCacheIdentityMismatchError` unmodified;
`live_test_data_generator.py` gained `resolve_test_data_identity`/`build_test_data_payload`.

**Correctness, proven deterministically, no live LLM call involved** (13 new tests, `tests/unit/
test_automation_engineering_generation_caching_test_data_generator.py`, mirroring the step-def
suite's own five test classes exactly): a `fields` change with `requirement_id` held fixed MISSES
(this generator's own version of the naive-key defect D1 found); a HIT skips the wrapped generator
and returns the identical artifact; a changed `customqa_constraints`/`class_name` MISSES; a HIT
replays the STORED identity across independent instances sharing only the on-disk store; a HIT
records the cache-hit bucket under `test_data_generation`, never `unmeasured`; a MISS is
byte-identical to an unwrapped `LiveTestDataGenerator` call; a genuine identity mismatch on a MISS
raises rather than silently caching under the wrong key.

**The measured saving — the third biggest sink, and the ~89%-coverage milestone.** The same
standalone, uncommitted harness pattern ran three realistic `TestDataGenerationContext`s (checkout
credentials, shipping-address postal code, search-filter category) against the real Gemini API
twice. Pass 1: 3 real LLM calls, 3402 total tokens (3065 prompt + 337 completion). Pass 2 (fresh
decorator + fresh provider instance, same on-disk cache): 0 new calls, 0 new tokens, 3 hits,
byte-identical artifacts to pass 1. No model substitution was needed — the platform's own
`GEMINI_MODEL` default (`gemini-3.1-flash-lite`) succeeded on every call on the first attempt, as it
did for feature-content. Feature-content (45.4%) and test-data (43.4%) together already accounted
for ~89% of that measured run's own token total on their own (the run's own reported figure, above)
— `step_definition_generation` recorded ZERO tokens in that specific run (30 of 60 step-def needs
were reuse hits, the other 30 escalated before reaching the generator; nothing to do with this
cache). With this increment, all three of the run's non-zero/non-L1 generator call types
(`feature_content_generation`, `test_data_generation`) that dominate that distribution are cached,
plus `step_definition_generation` itself (first increment) for whichever future run's catalog is
colder and does reach the generator — the two still-unwrapped generators
(`page_object_generation`, `utility_generation`) were absent from this particular distribution
entirely (not live-constructed in `handle_analyze` at measurement time, a pre-existing, separately
tracked gap), so their real share is unmeasured, not small-by-measurement.

**Scope held exactly as this increment intended.** Only `LiveTestDataGenerator` is added to the
wrapped set (alongside step-def and feature-content, first two increments).
`LivePageObjectGenerator`, `LiveUtilityGenerator`, and the remediator remain unwrapped; delta-scoped
regeneration and the deterministic/LLM split remain untouched — all still D5's own named future
work, not performed here.

## Implementation Note (2026-08-20) — the fourth increment: `LivePageObjectGenerator`, built, NOT yet measured live

The page-object live-wiring arc (stage 15's own co-generation chain, the live page-object
`SemanticMatcher`, and the `GenerationIdentity`-threading fix that immediately preceded this
increment) unblocked exactly what D5 named as future work for this generator: page-object
generation now carries a real `GenerationIdentity` on both `GeneratedPageObject` and
`CoGeneratedStepDefinition`, so it is cache-keyable the same way the first three generators already
were. The same pattern transferred directly a fourth time: `_build_prompt`'s own inline
`input_payload` dict (`class_name`/`target_package`/`customqa_constraints`/`methods` — the D1
payload this generator's own INPUT CONTRACT already names) was extracted, unmodified in content,
into a public `build_page_object_payload(context)`, mirroring `build_step_definition_payload`'s own
extraction exactly; `resolve_page_object_identity` mirrors `resolve_step_definition_identity`
verbatim; `CachingPageObjectGenerator` reuses `generation_cache.py`'s store/key unmodified and
defines its own `GenerationCacheIdentityMismatchError` (a separate class, for the same
`TransportFailureError`-subclass reason `caching_test_data_generator.py` gives for reusing rather
than redefining where the hierarchy already matches — here it does not need to, since a fresh
subclass costs nothing and keeps this module self-contained).

**The one genuinely new wrinkle this generator has that the prior three did not: a SECOND reuse
mechanism, upstream of the cache.** Page-object generation is reuse-first at the ASSET level too
(`automation_engineering.reuse.engine.decide_reuse`, called from `page_object_orchestrator.py`
BEFORE any generation decision) — a semantic-plus-structural match can BIND a need to an existing
tracked `PageObjectAsset` with no generation call at all. This is answered, not merely asserted: the
orchestrator's own NoMatch-then-generate control flow was read directly (pre-flight) and found to
already isolate the two mechanisms structurally — `decide_reuse` runs first and only a `NoMatch`
ever reaches `generator.generate(context)`, the exact point this cache wraps. Proven by test, not
just by reading the code: a `TrustedReuse` bind against a real `PageObjectAsset` with the specific
method needed never touches the wrapped `CachingPageObjectGenerator.generate` at all — zero LLM
calls, `last_identity` stays `None`, nothing written to the store — while a sibling `NoMatch` need in
the same test reaches the cache normally. Bind answers "does an existing ASSET already satisfy this
need" (asset-level, upstream); this cache answers "did we already GENERATE this exact thing before"
(call-level, at the generation seam) — orthogonal by construction, not by convention.

Built: `automation_engineering/generation/caching_page_object_generator.py`
(`CachingPageObjectGenerator`); `live_page_object_generator.py` gained
`resolve_page_object_identity`/`build_page_object_payload` (additive — `_build_prompt` now calls the
extracted function instead of building the dict inline; behavior-identical, proven by the 53
pre-existing `LivePageObjectGenerator` tests passing unmodified).

**Correctness, proven deterministically, no live LLM call involved** (19 new tests, `tests/unit/
test_automation_engineering_generation_caching_page_object_generator.py`, mirroring the step-def
suite's own test-class shape plus the bind/cache-composition section above): a changed
`method_name`/`class_name`/`return_type`/`additional_method_needs` (the "class + method needs +
signatures" payload, D1's own generalized language) with everything else held fixed MISSES; two
independently-constructed, content-identical contexts HIT regardless of object identity; a HIT
returns the byte-identical artifact a fresh generation would; a HIT replays the STORED identity
across independent instances sharing only the on-disk store; a HIT records the cache-hit bucket
under `page_object_generation`, never `unmeasured`; a MISS is byte-identical to an unwrapped
`LivePageObjectGenerator` call; a genuine identity mismatch on a MISS raises rather than silently
caching under the wrong key; a two-pass, three-artifact proof shows pass 2 (fresh decorator/provider
instance, same on-disk store) makes zero generation calls and returns byte-identical output to pass
1 — the same deterministic shape the prior three increments' own live measurements exhibited.

**No live measurement this increment — an honest, deliberate gap, not an oversight.** The prior
Implementation Note (above) already recorded that `page_object_generation` was ABSENT from the one
measured live distribution entirely ("not live-constructed in `handle_analyze` at measurement
time... their real share is unmeasured, not small-by-measurement") — that gap is UNCHANGED by this
increment, because `scripts/run_requirement_analysis.py`'s own stage-15 call site still does not
supply a `page_object_matcher`/`page_object_generator` at all (the live-wiring ADR's own note on
this: activating page-object generation live is a separate, deliberate decision, not yet made). The
cache is READY — correct, tested, wired to wrap whichever `LivePageObjectGenerator` instance a
future caller constructs — but has nothing live to measure until that separate activation happens.
This is the identical "cache built ahead of the traffic that will exercise it" posture D5 itself
anticipated, made explicit rather than left implicit.

**Scope held exactly as this increment intended.** Only `LivePageObjectGenerator` is added to the
wrapped set (alongside step-def, feature-content, and test-data — the first three increments). The
matcher/bind reuse path, the generation chain's own logic, and `GenerationIdentity`'s shape are all
untouched. `LiveUtilityGenerator` and the remediator remain unwrapped — utility caching is the fifth
and last of D5's originally named four remaining generators, still future work.

## Implementation Note (2026-08-21) — the fifth and FINAL increment: `LiveUtilityGenerator`, built, NOT yet measured live — the set of 5 is complete

The immediately preceding task (the twice-flagged `generation_identity` gap on `GeneratedUtility`,
step 1 of the identity → cache → eval sequence) closed exactly the prerequisite this increment
needed: utility generation now carries a real `GenerationIdentity`, so it is cache-keyable the same
way the other four generators already were.

**Utility's shape was CONFIRMED, not assumed, before wrapping anything (pre-flight).** Two
questions, both answered directly against the real code:

1. **The payload.** `LiveUtilityGenerator._build_prompt`'s own inline `input_payload` dict —
   `action_text` (the need's own text), `captures` (the need's own ordered capture list —
   `index`/`style`/`expression_type` per entry), `class_name`, `target_package`, and
   `customqa_constraints` — is the exact, complete generation input, the same "complete-by-
   construction, not a naive re-derivation" discipline D1 requires. Extracted, content-unmodified,
   into a public `build_utility_payload(context)`, mirroring `build_page_object_payload`'s own
   extraction exactly.
2. **The reuse shape.** Utility generation is confirmed reuse-first at the ASSET level too, the
   IDENTICAL shape page-object has, not the simpler always-generate shape the first three
   generators had: `utility_orchestrator.orchestrate_utility_method` calls
   `automation_engineering.reuse.engine.decide_reuse` BEFORE any generation decision, and a
   `TrustedReuse` whose specific method fits BINDS to an existing tracked `UtilityAsset` (via
   `verify_specific_method_fit`, reused unchanged from page objects) with NO generation call at
   all, producing a `BoundUtilityMethod` that carries no `generation_identity` field whatsoever (a
   bind is never a generation — confirmed directly in the immediately preceding identity task).
   Only a `NoMatch` ever reaches `generator.generate(context)`, the exact point this cache wraps —
   the SAME bind/cache orthogonality page-object's own fourth increment already proved, now proven
   a second time for a different generator.

`resolve_utility_identity` mirrors `resolve_page_object_identity`/`resolve_step_definition_identity`
verbatim; `CachingUtilityGenerator` reuses `generation_cache.py`'s store/key unmodified and defines
its own `GenerationCacheIdentityMismatchError` (a separate class, for the same
`TransportFailureError`-subclass reason the fourth increment's own note gives).

Built: `automation_engineering/generation/caching_utility_generator.py`
(`CachingUtilityGenerator`); `live_utility_generator.py` gained `resolve_utility_identity`/
`build_utility_payload` (additive — `_build_prompt` now calls the extracted function instead of
building the dict inline; behavior-identical, proven by every pre-existing
`LiveUtilityGenerator`/`utility_orchestrator` test passing unmodified).

**Correctness, proven deterministically, no live LLM call involved** (19 new tests, `tests/unit/
test_automation_engineering_generation_caching_utility_generator.py`, mirroring the page-object
suite's own test-class shape, including its own bind/cache-composition section): a changed
`action_text`/`class_name`/`target_package`/`customqa_constraints`/capture shape (the real utility
payload's own fields) with everything else held fixed MISSES; two independently-constructed,
content-identical contexts HIT regardless of object identity; a HIT returns the byte-identical
artifact a fresh generation would; a HIT replays the STORED identity across independent instances
sharing only the on-disk store; a HIT records the cache-hit bucket under `utility_generation`,
never `unmeasured`; a MISS is byte-identical to an unwrapped `LiveUtilityGenerator` call; a genuine
identity mismatch on a MISS raises rather than silently caching under the wrong key; a two-pass,
three-artifact proof shows pass 2 (fresh decorator/provider instance, same on-disk store) makes
zero generation calls and returns byte-identical output to pass 1; a `TrustedReuse` bind against a
real `UtilityAsset` with the specific method needed never touches the wrapped
`CachingUtilityGenerator.generate` at all (zero LLM calls, `last_identity` stays `None`, nothing
written to the store), while a sibling `NoMatch` need in the same test reaches the cache normally
— the SAME contrast proof page-object's own increment established.

**No live measurement this increment — an honest, deliberate gap, EARLIER than page-object's own.**
Utility generation is not merely absent from the one measured live distribution
(`page_object_generation`'s own prior finding) — it is not wired into stage 15 AT ALL: the
immediately preceding identity task confirmed `run_automation_engineering_stage` accepts no
`utility_matcher`/`utility_generator` parameters, and `stage/models.py`'s own `AssetRecord`
docstring states plainly "no utility `AssetRecord` is ever produced here." The cache is READY —
correct, tested, wired to wrap whichever `LiveUtilityGenerator` instance a future caller
constructs — but has nothing live to measure until BOTH stage-15 wiring AND live CLI activation
happen, two separate, undone decisions, not one. This is the same "cache built ahead of the
traffic that will exercise it" posture the fourth increment already named, one step further back.

**Scope held exactly as this increment intended.** Only `LiveUtilityGenerator` is added to the
wrapped set — the fifth and FINAL generator D5 originally named. The matcher/bind reuse path, the
generation chain's own logic, and `GenerationIdentity`'s shape are all untouched. The remediator
remains the one generator D5 explicitly excludes (repairs a prior attempt, independently rare) —
there is no sixth generator left to wrap under this ADR's own named scope.

## Consequences

- **Enables, proven for the first increment, extends to the rest by the same pattern:**
  cross-run artifact reuse, with a measurable token saving actually shown by the token-usage
  scorecard (Implementation Notes, above) for `LiveStepDefinitionGenerator`,
  `LiveFeatureContentGenerator`, and `LiveTestDataGenerator`; the identical pattern also wraps
  `LivePageObjectGenerator` (fourth Implementation Note) and `LiveUtilityGenerator` (fifth and FINAL
  Implementation Note, above) — both correctness-proven deterministically, neither yet measured
  live (page-object is not activated in the live CLI; utility is not even wired into stage 15 at
  all) — **the full five-generator wrap D5 named is now complete**; and the staleness signal
  delta-scoped regeneration will consume next.
- **Corrects a real design defect before it shipped.** The prior surfacing note's own recommended
  key would have produced silent stale hits on ordinary narrative/acceptance-criterion edits (D1).
  This ADR's key is the one any future build must implement — the corrected key is now the
  governed decision, not the prior note's.
- **Both named build-time gaps are closed (Implementation Notes, above), now for ALL FIVE named
  generators.** Pre-call identity exposure (D3, Gap 1 — a `resolve_*_identity` function per
  generator: `resolve_step_definition_identity`, `resolve_feature_content_identity`,
  `resolve_test_data_identity`, `resolve_page_object_identity`, `resolve_utility_identity`) and the
  token-scorecard cache-hit bucket (D3, Gap 2 — `TokenUsageTotals.cache_hit_count`) are both built,
  additive, and proven by test for step-definition, feature-content, test-data, page-object, and
  utility generation. Neither gap has any remaining generator left to extend to under this ADR's
  own named scope.
- **Dependencies, satisfied or explicitly not required:** pinning (`GenerationIdentity`) is built
  and sufficient for D1's identity component; `_hash_artifacts`'s pattern and `atomic_write.py` are
  built and reusable for D2; the token-usage scorecard is built and is D5's measurement instrument.
  Spec-slice (#4) is confirmed not required (D5).
- **Governance follow-ons, recommended, not performed here** (mirroring exactly how ADR-0048 named
  its own matrix/register follow-ons as separate actions): (1) a
  `docs/governance/platform-capability-matrix.md` entry for **CAP-089** — Artifact-Level
  Generation Cache — confirmed the next unused id after `CAP-088` (Traceability Graph) in the
  open-ended `CAP-060…` block (§3.1); status `Accepted`/`Implementation` (updated from this ADR's
  original `Proposed`/`Architecture` framing, above, now that the first increment is built and
  measured — Implementation Note), mirroring `CAP-088`'s own row shape for a built-and-measured,
  not-yet-wired capability rather than `CAP-087`'s pure-paper-freeze shape; (2) a
  `docs/architecture/architecture-baseline-v2.md` register entry recording this ADR, mirroring how
  ADR-0048's own entry was added in a later, separate task. Neither changes this ADR's Decision
  text if performed later.
- **Became Accepted the same day** (Implementation Note, above): the store, the key, and the first
  decorator (D5) were built directly against this design, both named gaps (D3) were closed, and the
  first real token saving was measured — the exact Proposed-to-Accepted path this ADR named in
  advance, mirroring ADR-0030's own convention. A second decorator (`CachingFeatureContentGenerator`,
  wrapping one of the distribution's two co-dominant sinks) and a third
  (`CachingTestDataGenerator`, wrapping the other) were added the same day, each repeating the same
  pattern and the same measured-saving proof (second and third Implementation Notes, above).
  A fourth decorator (`CachingPageObjectGenerator`) was added on 2026-08-20, once the page-object
  live-wiring arc closed the `GenerationIdentity` prerequisite this generator was missing —
  correctness proven the same deterministic way, live measurement deferred (fourth Implementation
  Note, above) since that generator is not yet activated in the live CLI. A fifth and FINAL
  decorator (`CachingUtilityGenerator`) was added on 2026-08-21, once the utility identity task
  closed the identical prerequisite for utilities — correctness proven the same deterministic way,
  live measurement deferred even further (fifth Implementation Note, above) since utility
  generation is not even wired into stage 15 yet. Accepted status covers
  these five increments' own scope only (`LiveStepDefinitionGenerator`, `LiveFeatureContentGenerator`,
  `LiveTestDataGenerator`, `LivePageObjectGenerator`, `LiveUtilityGenerator`) — **the full
  five-generator wrap D5 named**; the remediator stays future, separate work (D5's own explicit
  exclusion), not implicitly authorized by this status change.
- **Relationship to the mentor cluster.** This is the second of Nitin's (one mentor) four-part
  re-run cluster to receive its own decision record — pinning was built without a dedicated ADR
  (additive infra, precedented shape); this cache, a new store/key/interception mechanism, is not.
  The sequencing recommendation in D5 (this generator first, delta-regen next, the split in
  parallel) is this ADR's own reading of the dependency shape, not something Nitin weighed in on
  directly — the same caveat the surfacing note itself already flagged.

## Ownership, runtime position, governance

- **Owns:** the artifact-level generation cache's key construction (D1), store shape (D2),
  interception pattern and hit-consumption contract (D3), correctness/safety posture (D4), and
  build sequence (D5) — decisions only.
- **Does not own:** `GenerationIdentity`, any live generator, any orchestrator, `RunStateManager`,
  `TokenUsageTracker`'s existing measured/unmeasured buckets (extended, not owned, by D3's Gap 2),
  or delta-scoped regeneration (a future, separate capability that consumes this one once built).
- **Runtime position (built for ALL FIVE generators; not live-wired):** generator
  construction site → `Caching<X>Generator` → key (D1) → store (D2) lookup → HIT: stored artifact +
  stored identity, LLM call skipped; MISS: wrapped live generator called, result stored → identical
  downstream flow either way (D3/D4, proven — all five Implementation Notes). This chain exists and
  is tested for step-definition generation (`CachingStepDefinitionGenerator`), feature-content
  generation (`CachingFeatureContentGenerator`), test-data generation (`CachingTestDataGenerator`),
  page-object generation (`CachingPageObjectGenerator`), and utility generation
  (`CachingUtilityGenerator`) — every `Caching<X>Generator` D5 named now exists. No `PlatformContext`
  method, no
  pipeline stage, no Execution Package artifact exists for this capability today —
  `scripts/run_requirement_analysis.py` constructs none of `CachingStepDefinitionGenerator`,
  `CachingFeatureContentGenerator`, `CachingTestDataGenerator`, `CachingPageObjectGenerator`, or
  `CachingUtilityGenerator`.
- **Governance:** recommended `CAP-089` (not yet entered — Consequences) for the Requirement
  Intelligence Platform. This ADR is **Accepted** for all five increments (all five
  Implementation Notes, above) — it now clears the same bar ADR-0048 cleared (built, tested, and, for
  three of the five, measured against real data — the fourth and fifth, page-object and utility,
  proven deterministically only), for the FULL scope D5 defined — **the five-generator wrap is
  complete.** Only the remediator, D5's own explicit, permanent exclusion, remains unwrapped — not a
  gap, a decision. `LiveUtilityGenerator` remains unmeasured live (not merely uncached-until-now):
  absent from the one real distribution measured to date (not live-constructed in
  `handle_analyze`), AND not wired into stage 15 at all — its real token share stays unmeasured
  until both gaps close, a separate, later decision from this cache's own build.
