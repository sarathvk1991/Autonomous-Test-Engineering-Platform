# Gemini Multi-Model Evaluation — CAP-074A

Comparative evaluation of four Gemini models across the complete Requirement
Intelligence pipeline. Every claim below is supported by an execution package
stored under `output/model-eval/<model>/run-N/`.

---

## 1. Method

Each model ran the full pipeline in **API mode** against the live sources:

```text
Live Connectors → Consolidation → Requirement Analysis → Normalization
    → Validation → CP1 → Execution Package
```

**Three runs per model**, so latency variance and API stability are measured
rather than sampled once.

### Controlled variables

Only the Gemini model varied. This is not asserted — it is proven by hash:

| Control | Evidence |
| --- | --- |
| Identical input data | All 8 successful packages share one `promptSha256`: `41aefef29e62235b…` |
| Identical prompt version | `promptVersion = 1.0.0` in every manifest |
| Identical configuration | `reasoningContractVersion = 1.0.0`; temperature `0.0` |
| Identical pipeline | Same CLI invocation, same registry, same profile (`default`) |
| Identical parameters | Only `--model` differed |

The analysed artifact was the same in every run:
`cons-component-automation-poc-…-BadLoginPage.java`, risk level `critical`,
composed of **0 functional artifacts, 0 security artifacts, 71 quality
artifacts** (SonarQube findings on a Java page-object class).

That composition matters for reading the quality results below.

---

## 2. Operational metrics

| Model | Runs OK | Mean duration | Min | Max | Std dev | Retries | API stability |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `gemini-2.0-flash` | **0 / 3** | — | — | — | — | 0 | **Blocked** — `429`, free-tier limit `0` |
| `gemini-2.5-flash` | **3 / 3** | **26.11 s** | 25.94 s | 26.27 s | 0.16 s | 0 | Stable |
| `gemini-3.1-flash-lite` | **3 / 3** | **3.10 s** | 2.97 s | 3.29 s | 0.17 s | 0 | Stable |
| `gemini-3-flash-preview` | **2 / 3** | **619.93 s** | 474.60 s | 765.25 s | 205.52 s | 0 | **Unstable** — one `503 UNAVAILABLE` |

Duration is `manifest.executionDurationMs`, the wall-clock analysis phase. The
platform's own stages (validation, CP1) are sub-millisecond, so this is
effectively provider latency.

**Retry count is 0 everywhere by design.** `GeminiProvider` issues exactly one
`generate_content` call and never retries. The `gemini-3-flash-preview` `503` was
therefore fatal to that run.

### Notes on the two failures

- **`gemini-2.0-flash` never executed.** All three attempts returned
  `429 RESOURCE_EXHAUSTED` naming `GenerateRequestsPerDayPerProjectPerModel-FreeTier`
  with `limit: 0`. This is not a rate limit that clears — the model has no
  free-tier allocation on this API key. Retried past the stated `retryDelay`;
  still `429`. Evaluating it requires enabling billing.
- **`gemini-3-flash-preview` is not generally available.** No GA `gemini-3-flash`
  exists; the only candidate is the `-preview` build, which returned
  `503 … This model is currently experiencing high demand` on run 1.

### Token usage (identical input across all models)

| Model | Prompt tokens | Completion tokens | Deterministic? |
| --- | --- | --- | --- |
| `gemini-2.5-flash` | 5973 | 913, 913, 913 | **Yes** — one `responseSha256` across 3 runs |
| `gemini-3.1-flash-lite` | 5973 | 570, 570, 570 | **Yes** — one `responseSha256` across 3 runs |
| `gemini-3-flash-preview` | 5973 | 854, 758 | **No** — 2 distinct responses in 2 runs |

Determinism at `temperature = 0.0` is a reproducibility property the golden
baseline depends on. `gemini-3-flash-preview` does not hold it.

---

## 3. Engineering metrics

Identical across every successful run — the platform's gates are model-agnostic:

| Model | Validation verdict | Issues | Rule IDs | Rules executed | CP1 executed | CP1 verdict | CP1 findings |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `gemini-2.0-flash` | *not reached* | — | — | — | — | — | — |
| `gemini-2.5-flash` | `passed` | 0 | none | 13 | yes | `pass` | 0 |
| `gemini-3.1-flash-lite` | `passed` | 0 | none | 13 | yes | `pass` | 0 |
| `gemini-3-flash-preview` | `passed` | 0 | none | 13 | yes | `pass` | 0 |

Every model that produced a response passed Validation and CP1 with zero issues
and zero findings. **Validation and CP1 do not discriminate between these
models** — they confirm structural and contractual conformance, not requirement
quality. Quality must be judged from the content.

---

## 4. Requirement quality

### Counts

| Model | Functional | Security | Quality | Total | Risks | Recommendations | Avg words/req |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `gemini-2.5-flash` | **0** | **0** | 10 | 10 | 3 | 11 | 11.6 |
| `gemini-3.1-flash-lite` | 5 | 2 | 5 | 12 | 4 | 5 | 14.9 |
| `gemini-3-flash-preview` | 6 | 2 | 7 | 15 | 5 | 7 | 16.3 |

### The completeness finding

The input contained **zero functional and zero security artifacts**. It is
tempting to conclude that `gemini-2.5-flash` was correctly conservative and the
Gemini 3 models hallucinated. **The evidence says the opposite.**

Every entity the Gemini 3 models cited is present verbatim in the prompt:

| Token cited | Present in prompt |
| --- | --- |
| `user-name`, `password`, `login-button` | Yes |
| `standard_user`, `secret_sauce` | Yes |
| `BadLoginPage`, `checkError`, `testThing` | Yes |

The SonarQube findings embed the code context of a login page object, including
**hardcoded credentials**. From that, the Gemini 3 models correctly derived:

> *"The automation framework shall externalize all test credentials, including
> `standard_user` and `secret_sauce`, from the source code."* — `gemini-3-flash-preview`

> *"The test suite shall externalize credentials to a secure configuration store
> rather than hardcoding them in the source code."* — `gemini-3.1-flash-lite`

`gemini-2.5-flash` produced **no security requirement at all**, despite hardcoded
credentials being present in its input. It restated the SonarQube rules as
quality requirements and stopped there.

This is a **completeness failure, not caution.** The prompt asks for functional,
security, and quality requirements; the input supports all three; only the
Gemini 3 models delivered all three.

### Quality dimensions

Measured over all requirements in each response.

| Dimension | `gemini-2.5-flash` | `gemini-3.1-flash-lite` | `gemini-3-flash-preview` |
| --- | --- | --- | --- |
| **Completeness** | Poor — 0/3 categories populated | **Good** — 3/3 | **Best** — 3/3, most coverage |
| **Correctness** | Correct but narrow | Correct | Correct |
| **Clarity** | Good | Good | Good |
| **Atomicity** | **10/10 atomic** | 11/12 atomic | 12/15 atomic (3 compound) |
| **Duplication** | 0 | 0 | 0 |
| **Hallucinations** | 0 | **0** | **0** |
| **Traceability** | **0 citations** | **0 citations** | **0 citations** |
| **Formatting consistency** | Consistent (flat strings) | Consistent (flat strings) | Consistent (flat strings) |
| **Determinism** | Yes | Yes | **No** |

Two dimensions need honest qualification:

- **Vague wording.** An automated scan flagged 2 requirements from
  `gemini-3.1-flash-lite` for the word *"improve"*. On inspection both use it in
  a trailing rationale clause, not in the acceptance criterion — *"Methods shall
  be refactored to ensure a maximum length of 40 lines to improve readability"*
  is measurable at 40 lines. **Not a real defect.**
- **Traceability is zero for every model.** No model cited a SonarQube rule key
  (`java:S2925`) or any source record id. This is a **uniform gap** — it does not
  discriminate between models, but it means no generated requirement can be
  mechanically traced back to the finding that motivated it. See Risks.

---

## 5. Execution package

| Model | Artifacts | Manifest integrity | Report quality | Summary quality |
| --- | --- | --- | --- | --- |
| `gemini-2.5-flash` | 12/12 | **Verified** | Complete | Complete |
| `gemini-3.1-flash-lite` | 12/12 | **Verified** | Complete | Complete |
| `gemini-3-flash-preview` | 12/12 | **Verified** | Complete | Complete |

"Verified" means recomputed: `sha256(llm_request.prompt) == manifest.promptSha256`,
`sha256(generated_text) == manifest.responseSha256`, and
`promptCharacterCount == len(prompt)`. All 8 packages pass.

Execution-package generation is **model-independent** — as designed.

---

## 6. Category winners

| Category | Winner | Evidence |
| --- | --- | --- |
| **Fastest** | `gemini-3.1-flash-lite` | 3.10 s mean — 8.4× faster than `2.5-flash`, 200× faster than `3-flash-preview` |
| **Lowest latency** | `gemini-3.1-flash-lite` | 2.97 s minimum |
| **Highest quality** | `gemini-3-flash-preview` | 15 requirements across all 3 categories; broadest coverage |
| **Best engineering output** | *Tie* | All three: Validation `passed`/0 issues, CP1 `pass`/0 findings |
| **Most reliable** | `gemini-2.5-flash` and `gemini-3.1-flash-lite` | 3/3 runs, deterministic output |
| **Best value** | `gemini-3.1-flash-lite` | 570 completion tokens for 12 requirements vs 913 for 10 |

---

## 7. Recommendations

### Demo model: `gemini-3.1-flash-lite`

- **3.10 s** mean end-to-end. A live demo does not stall.
- **3/3 successful runs**, standard deviation **0.17 s**. Predictable on stage.
- **Deterministic** — the same input produces a byte-identical response, so a
  rehearsed demo is the demo you get.
- Populates **all three** requirement categories, including the security
  requirement about hardcoded credentials — the most compelling thing to show.
- Zero duplication, zero hallucination, Validation `passed`, CP1 `pass`.

The one model that beats it on raw coverage, `gemini-3-flash-preview`, averages
**over ten minutes** per run and failed one run outright. It is unusable live.

### Production model: `gemini-2.5-flash` — with a caveat

For production, reliability and support status outweigh a few seconds of latency:

- Generally available; **not** a `-preview` build subject to withdrawal.
- **3/3 runs, deterministic**, 0.16 s standard deviation.
- Proven at 26 s — acceptable for batch or CI use, where nothing waits on it.

**The caveat is material.** `gemini-2.5-flash` produced **zero functional and
zero security requirements** on this input, missing hardcoded credentials that
both Gemini 3 models caught. For a platform whose purpose is requirement
intelligence, that is a serious completeness gap.

Therefore:

> **Recommended production model: `gemini-2.5-flash` today**, because it is GA,
> stable, and deterministic. **`gemini-3.1-flash-lite` is the stronger technical
> candidate** — faster, cheaper, and materially more complete — and should be
> promoted to production **as soon as its GA and support status are confirmed**
> under a governed provider-change milestone.

This evaluation **does not** change the default model. Per CAP-074A, any
production-provider change remains a future governed milestone.

### Not recommended

- **`gemini-2.0-flash`** — cannot execute on the current API key (free-tier
  limit `0`). Unevaluated. Also the oldest model of the four.
- **`gemini-3-flash-preview`** — preview status, non-deterministic,
  10-minute mean latency, 205 s standard deviation, and a `503` failure in 3 runs.

---

## 8. Risks surfaced by this evaluation

1. **No retry around the provider call.** `GeminiProvider` calls the model once.
   A transient `503` fails the entire run, as it did for `gemini-3-flash-preview`.
   Connector HTTP calls retry; the provider call does not. This asymmetry is the
   single largest demo risk.
2. **Zero requirement traceability.** No model cites the source finding a
   requirement derives from. Requirements cannot be mechanically traced to the
   SonarQube rule or JIRA issue that motivated them. This is a prompt/contract
   concern, not a model defect — every model behaved the same way.
3. **Validation and CP1 do not measure requirement quality.** Both passed for a
   response containing **zero functional and zero security requirements**. The
   gates verify structure and contract, not coverage. Do not read
   "Validation PASS, CP1 PASS" as "the requirements are good."
4. **Model availability is account-scoped.** `gemini-2.0-flash` is unavailable on
   this key. Verify any model against the actual demo key before relying on it.

---

## 9. Reproducing this evaluation

```bash
EXECUTION_MODE=API python scripts/run_requirement_analysis.py analyze --validate \
    --model gemini-3.1-flash-lite \
    --output-dir output/model-eval/gemini-3.1-flash-lite \
    --execution-name run-1
```

Packages are never overwritten; a repeated `--execution-name` appends `-1`, `-2`, ….
Compare any two runs by `promptSha256` (input identity) and `responseSha256`
(output identity).
