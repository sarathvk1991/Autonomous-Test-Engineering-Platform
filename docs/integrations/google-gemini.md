# Google Gemini Integration

| Attribute       | Value                                                        |
| --------------- | ------------------------------------------------------------ |
| Document type   | Integration / Operational Configuration Guide                |
| Provider        | Google Gemini (`gemini`)                                     |
| SDK             | `google-genai` (Google's current official Python SDK)         |
| Status          | Live — first production AI provider                          |
| Audience        | Developers · DevOps Engineers · Future Contributors          |

This guide explains how to configure and operate the Google Gemini provider. It
is an **operational** document — it describes the provider implementation and how
to run it. It does **not** define platform behaviour; see
[Relationship to Platform Architecture](#2-relationship-to-platform-architecture).

---

## 1. Overview

The **Gemini Provider** is a *thin adapter* between the platform's
provider-agnostic LLM Framework and Google's Gemini API. It owns **provider
communication only**:

- validates provider configuration,
- converts a provider-agnostic `LLMRequest` into a Gemini request,
- performs **exactly one** Gemini call (no retries, no fallback),
- converts the Gemini response back into a provider-agnostic `LLMResponse`.

It contains no prompt logic, no orchestration, no validation, and no knowledge of
Requirement Analysis or any downstream component.

```text
   Requirement Analysis Service        (orchestration — single AI entry point)
              │  LLMRequest
              ▼
       Gemini Provider                 (thin adapter — this integration)
              │  Gemini request (model · contents · config)
              ▼
     Google Gemini API                 (Google-hosted model)
              │  raw response
              ▼
        LLMResponse                     (provider-agnostic result)
```

The rest of the platform never imports the Gemini SDK and never sees a Gemini
type — only `LLMRequest` and `LLMResponse` cross the provider boundary, and no
SDK exception escapes it.

---

## 2. Relationship to Platform Architecture

This document is governed by — and does not replace — the platform's architecture
specifications:

| Architecture document | Role |
| --------------------- | ---- |
| [`docs/architecture/ai-reasoning-contract.md`](../architecture/ai-reasoning-contract.md) | Defines *how the platform reasons*. The provider is unaffected by and indifferent to reasoning rules. |
| [`docs/architecture/requirement-analysis-service.md`](../architecture/requirement-analysis-service.md) | Defines the single AI orchestration boundary. The provider is invoked **only** through this service. |
| LLM Provider Framework | Defines the provider-agnostic `LLMProvider` abstraction, `LLMRequest`, and `LLMResponse` that this provider implements. |

> **Scope note**
> This guide covers the Gemini **provider implementation and operational
> configuration** only. Reasoning, orchestration, and prompt construction are
> defined elsewhere and are not affected by which provider is active.

---

## 3. Prerequisites

| Requirement | Detail |
| ----------- | ------ |
| Python      | 3.11 or newer |
| SDK         | `google-genai` (declared in `requirements.txt`) |
| Account     | A Google AI Studio account able to issue API keys |
| Network     | Outbound HTTPS access to Google's Gemini endpoint |

---

## 4. Obtaining an API Key

1. Sign in to **Google AI Studio** at <https://aistudio.google.com/>.
2. Open **Get API key** (left navigation) → **Create API key**.
3. Select or create a Google Cloud project to associate with the key.
4. Copy the generated key and store it in your secret manager.

**Required permissions:** the key only needs access to the **Generative Language
API** (Gemini) for the associated project. Grant least privilege — no broader
Cloud permissions are required for this integration.

> ⚠️ **Never paste a real API key into source code, docs, tickets, or chat.**
> This guide intentionally contains no credentials.

---

## 5. Environment Variables

The provider reads its configuration from the environment. Credentials are
**never** hardcoded.

| Variable          | Required | Default          | Purpose |
| ----------------- | -------- | ---------------- | ------- |
| `GOOGLE_API_KEY`  | Yes      | —                | API key used to authenticate with Gemini. |
| `GEMINI_MODEL`    | No       | `gemini-2.5-pro` | Model identifier to use for generation. |

**How configuration is read.** On construction the provider resolves:

- the API key from an explicitly supplied value, otherwise from `GOOGLE_API_KEY`;
- the model from an explicitly supplied value, otherwise from `GEMINI_MODEL`,
  otherwise the default `gemini-2.5-pro`.

If the API key is absent when an analysis runs, the provider raises a
**configuration error** *before* any network call is attempted.

Example (do not commit real values):

```bash
export GOOGLE_API_KEY="<your-api-key>"
export GEMINI_MODEL="gemini-2.5-pro"   # optional
```

---

## 6. Supported Models

Any current Gemini text model accepted by the `google-genai` SDK may be used.
Commonly used options:

| Model              | Typical use |
| ------------------ | ----------- |
| `gemini-2.5-pro`   | Default. Highest-quality reasoning for requirement analysis. |
| `gemini-2.5-flash` | Faster / lower-cost; suitable for high-volume or latency-sensitive runs. |

**Configuring a different model** — set the `GEMINI_MODEL` environment variable:

```bash
export GEMINI_MODEL="gemini-2.5-flash"
```

The model name is forwarded verbatim to the Gemini API and is echoed back on the
`LLMResponse.model` field for traceability.

---

## 7. Local Setup

1. **Install dependencies** (from the repository root):

   ```bash
   pip install -r requirements.txt
   ```

   This installs the `google-genai` SDK along with the rest of the platform.

2. **Configure environment variables:**

   ```bash
   export GOOGLE_API_KEY="<your-api-key>"
   export GEMINI_MODEL="gemini-2.5-pro"   # optional
   ```

   A local `.env` file (loaded via `python-dotenv`) may be used instead — ensure
   it is git-ignored.

3. **Run the platform** as you normally would (the active provider defaults to
   `gemini`).

4. **Verify startup** by running the smoke test in the next section.

---

## 8. Smoke Test

The following minimal script verifies **authentication**, **request execution**,
and a **successful response** through the provider — without exercising the full
Requirement Analysis pipeline.

```python
"""Gemini connectivity smoke test. Requires GOOGLE_API_KEY in the environment."""

from requirement_intelligence.llm.llm_models import LLMRequest
from requirement_intelligence.llm.providers.gemini_provider import GeminiProvider


def main() -> None:
    provider = GeminiProvider()  # reads GOOGLE_API_KEY / GEMINI_MODEL from env

    # 1. Authentication / configuration check (constructs an SDK client).
    provider.validate_connection()

    # 2. Request execution (exactly one Gemini call).
    request = LLMRequest(
        request_id="smoke-test-1",
        prompt="Reply with the single word: pong",
        temperature=0.0,
    )
    response = provider.generate(request)

    # 3. Successful response.
    print("provider:", response.provider)
    print("model:   ", response.model)
    print("text:    ", response.generated_text)


if __name__ == "__main__":
    main()
```

Run it:

```bash
python smoke_test_gemini.py
```

A successful run prints `provider: gemini`, the configured model, and a short
generated reply. Any failure surfaces as a platform provider exception (see
Troubleshooting) — never as a raw SDK error.

---

## 9. Troubleshooting

| Symptom | Likely cause | Resolution |
| ------- | ------------ | ---------- |
| **Configuration error mentioning `GOOGLE_API_KEY`** | Environment variable not set / empty | Export `GOOGLE_API_KEY` in the running shell or `.env`. |
| **Configuration error mentioning `google-genai`** | SDK not installed | `pip install -r requirements.txt` (or `pip install google-genai`). |
| **Authentication failure** | Invalid, revoked, or wrong-project API key | Re-issue a key in Google AI Studio; confirm the Generative Language API is enabled for the project. |
| **Unsupported / unknown model** | `GEMINI_MODEL` set to an unavailable name | Use a supported model (e.g. `gemini-2.5-pro`); check spelling. |
| **Quota exceeded** | Project rate/usage limits reached | Wait and retry later, request a quota increase, or switch to a lower-cost model. Surfaces as a *generation* error. |
| **Network failure / timeout** | No outbound connectivity to Google | Verify egress / proxy settings and DNS; retry once connectivity is restored. |

All provider-side failures are wrapped in the platform's provider exception
hierarchy (configuration vs. connection vs. generation). No `google-genai`
exception type is ever raised to callers.

---

## 10. Security Considerations

- **Never commit API keys.** Keep them out of source, tests, fixtures, and docs.
- **Use environment variables / a secret manager.** The provider reads
  `GOOGLE_API_KEY` from the environment by design.
- **Rotate credentials** on a regular schedule and immediately on suspected
  exposure.
- **Apply least privilege.** Scope the key to the Generative Language API for a
  single project only.
- **Never log secrets.** The provider performs no logging and never includes the
  API key in any response, error message, or `raw_response` payload.
- **Keep `.env` files git-ignored** and out of build artifacts and images.

---

## 11. Future Migration

The platform depends on the provider-agnostic `LLMProvider` abstraction, not on
Gemini. Migrating to **Azure OpenAI** — or any future provider — requires
implementing that abstraction once and selecting it via configuration.

When the active provider changes, **only the provider implementation changes.**
The following remain untouched:

| Component | Stays unchanged |
| --------- | --------------- |
| `LLMProvider` abstraction | The contract every provider implements. |
| Requirement Analysis Service | The single orchestration entry point. |
| Prompt Framework | Prompt construction and versioning. |
| `LLMRequest` / `LLMResponse` | The provider-agnostic request/response contracts. |

```text
   Requirement Analysis Service        (unchanged)
              │
              ▼
        LLMProvider                    (unchanged abstraction)
        ╱        ╲
  Gemini Provider   Azure OpenAI Provider   …future providers
   (swap here only — everything above is unaffected)
```

Because no downstream component imports the Gemini SDK or references Gemini
types, swapping providers has zero impact on reasoning, orchestration, or
prompting.
