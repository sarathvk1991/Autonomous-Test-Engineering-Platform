# Requirement Intelligence Layer — Operations Runbook

For operators running the platform, not for developers changing it. Every
procedure here is a command you run and an outcome you check.

If you have never run the platform before, read the
[demo guide](../demo/demo-guide.md) first.

---

## 1. Startup

The platform is a **batch CLI**. There is no long-running process to start; each
invocation runs once and exits. (`app/main.py` exposes a FastAPI app with a
`/health` liveness probe, but the Requirement Intelligence pipeline is not
wired to it and is not served over HTTP.)

### Normal startup sequence

```bash
cd "Autonomous Test Engineering Platform"
source .venv/bin/activate

# 1. Confirm the sources before doing any work.
python scripts/run_requirement_analysis.py health

# 2. Run the pipeline.
python scripts/run_requirement_analysis.py analyze --validate
```

Startup validation runs automatically before any source is contacted. It checks:

| Check | FILE | API |
| --- | --- | --- |
| Source registry parses, ≥ 1 source enabled | ✓ | ✓ |
| Prompt registry composes, SHA-256 verified | ✓ | ✓ |
| Every input file exists and is readable | ✓ | — |
| Every required credential resolves | — | ✓ |
| Every base URL is a valid `http(s)` endpoint | — | ✓ |

A failure prints every problem at once, as plain text, and exits `2`. It never
prints a stack trace and never prints a credential value — only the *name* of
an environment variable that is unset.

### Exit codes

| Code | Meaning |
| --- | --- |
| `0` | Success |
| `1` | Runtime failure (source unreachable, provider error, mapping failure) |
| `2` | Configuration error (startup validation, bad flag, unknown mode) |

`health` exits `0` only when every enabled source is `READY`. Use it as a
deployment or pre-demo gate:

```bash
python scripts/run_requirement_analysis.py health || echo "sources not ready"
```

---

## 2. Shutdown

Each run terminates on its own. To stop a run in progress, send `SIGINT`
(`Ctrl-C`).

Interrupting is safe. There is no database, no lock file, and no external state
to reconcile. The only side effects are:

- Files under `output/`. A partially written execution package may remain; it is
  never read back by the platform. Delete the directory.
- HTTP requests already issued to JIRA, SonarQube, ZAP, or Gemini. All are reads.
  Gemini has already been billed for any call that started.

`output/latest/` is overwritten by the next successful run.

---

## 3. Configuration

Two files, and nothing else.

| File | Purpose | Committed |
| --- | --- | --- |
| `.env` | Credentials, model, execution mode | **No** (gitignored) |
| `requirement_intelligence/config/source-registry.json` | Which sources exist, their connectors, timeouts, retry policy | Yes |

Copy `.env.example` to `.env` and fill it in. `.env.example` is the canonical
list of every variable the platform reads; it contains placeholders only.

### Changing the execution mode

`EXECUTION_MODE` is the **only** control. It applies to every source at once —
sources are never configured independently.

```bash
EXECUTION_MODE=FILE   # default; read exported artifacts from disk
EXECUTION_MODE=API    # fetch live from JIRA, SonarQube, OWASP ZAP
```

Set it in `.env`, or per-invocation:

```bash
EXECUTION_MODE=API python scripts/run_requirement_analysis.py analyze --validate
```

Anything other than `FILE` or `API` (case-insensitive) is rejected at startup
with exit `2`. An unset or empty value means `FILE`.

### Enabling or disabling a source

Edit `"enabled"` in `source-registry.json`. Disabling a source removes it from
ingestion, health checks, and startup validation.

### Changing the model

Set `GEMINI_MODEL` in `.env`, or override for one run:

```bash
python scripts/run_requirement_analysis.py analyze --validate --model gemini-2.5-flash
```

---

## 4. Environment variables

### Always

| Variable | Required | Notes |
| --- | --- | --- |
| `GOOGLE_API_KEY` | Yes (not for `--dry-run`) | Google AI Studio key |
| `GEMINI_MODEL` | No | Defaults to `gemini-2.5-pro` |
| `EXECUTION_MODE` | No | `FILE` (default) or `API` |

### `EXECUTION_MODE=API` only

| Variable | Source | Required |
| --- | --- | --- |
| `JIRA_BASE_URL` | JIRA | Yes — bare site root, **no** `/jira` suffix |
| `JIRA_EMAIL` | JIRA | Yes |
| `JIRA_API_TOKEN` | JIRA | Yes |
| `JIRA_PROJECT_KEY` | JIRA | No — the project **key**, not its name |
| `SONAR_BASE_URL` | SonarQube | Yes |
| `SONAR_TOKEN` | SonarQube | Yes |
| `SONAR_PROJECT_KEY` | SonarQube | **Yes** |
| `SONAR_BRANCH` | SonarQube | No |
| `ZAP_BASE_URL` | OWASP ZAP | Yes |
| `ZAP_API_KEY` | OWASP ZAP | Yes |
| `ZAP_TARGET_URL` | OWASP ZAP | No |

Note the asymmetry: SonarQube's project key is **mandatory** (its issue search
requires a component), JIRA's is optional. Startup validation enforces exactly
what each connector requires — it never guesses.

---

## 5. Logging

Console output is intentionally concise: a banner stating what the run is
configured to do, one line per pipeline stage, and the verdicts.

- **Credentials are never logged.** Not in the banner, not in errors, not in the
  execution package. Only environment-variable *names* appear.
- **Base URLs** appear only in `health --verbose` output.
- Connector HTTP attempts and failures are logged through the
  `requirement_intelligence.connectors.api` logger. Raise `LOG_LEVEL` to `DEBUG`
  in `.env` to see each attempt.

`--verbose` on `analyze` adds artifact counts; on `health` it adds a detail line
per source.

Durable evidence lives in the execution package, not the console:
`manifest.json` records versions, prompt/response SHA-256 hashes, wall-clock
duration, and both verdicts.

---

## 6. Connector troubleshooting

Always start here:

```bash
EXECUTION_MODE=API python scripts/run_requirement_analysis.py health --verbose
```

| Status | Meaning | Action |
| --- | --- | --- |
| `READY` | Endpoint answered | None |
| `MISCONFIGURED` | Config wrong; source never contacted | Fix `.env` / registry |
| `UNREACHABLE` | Config fine; source did not answer | Start the service |

The probe issues one unauthenticated `GET` at the base URL and treats *any* HTTP
response as proof the endpoint is up. A `401`/`403` therefore reports `READY`
with the code shown — the service is running, it simply rejected an anonymous
request. That distinction is deliberate: it separates "the service is down" from
"my token is wrong".

### JIRA

| Symptom | Cause | Fix |
| --- | --- | --- |
| `malformed JSON in response from …/jira/rest/api/…` | `JIRA_BASE_URL` has a `/jira` suffix, so JIRA returns its HTML web UI with `HTTP 200` | Use the bare root: `https://your-org.atlassian.net` |
| `HTTP 410` | You are on an old build using `/rest/api/2/search`, which Atlassian removed | Upgrade; the connector now uses `/rest/api/2/search/jql` |
| Zero issues ingested | `JIRA_PROJECT_KEY` is the project *name* | Use the key (e.g. `SCRUM`) |
| `Unsupported JIRA issue type 'Task'` | The project holds issue types the mapper does not canonicalise | Already scoped by `api.jql` in the registry; widen it only if the mapper supports the type |
| `401`/`403` | Bad email or API token | Regenerate the token; `JIRA_EMAIL` must own it |

### SonarQube

| Symptom | Cause | Fix |
| --- | --- | --- |
| `Environment variable(s) not set: SONAR_PROJECT_KEY` | Mandatory for SonarQube | Set it |
| `UNREACHABLE` | Server not started | Start SonarQube; default `http://localhost:9000` |
| `401`/`403` at fetch | Token lacks *Browse* on the project | Re-issue a token with project access |
| Zero issues | Wrong `SONAR_PROJECT_KEY`, or the branch has no analysis | Verify in the UI; check `SONAR_BRANCH` |

### OWASP ZAP

| Symptom | Cause | Fix |
| --- | --- | --- |
| `UNREACHABLE` | ZAP daemon not running | Start ZAP; confirm the port matches `ZAP_BASE_URL` |
| Port mismatch | `.env.example` suggests `8080`; your daemon may use `8081` | Set `ZAP_BASE_URL` to the real port |
| Zero alerts | No scan has run against the target | Run a scan; check `ZAP_TARGET_URL` |

---

## 7. Gemini troubleshooting

| Symptom | Cause | Action |
| --- | --- | --- |
| `GOOGLE_API_KEY is not set` | Key absent | Set it, or use `--dry-run` |
| `429 RESOURCE_EXHAUSTED … limit: 0` | The model has **no free-tier quota** on your key. Not transient — retrying never succeeds | Choose another model, or enable billing |
| `429 … retryDelay: 25s` with a non-zero limit | Genuine rate limit | Wait and re-run |
| `503 UNAVAILABLE … high demand` | Transient capacity shortage, common on `-preview` models | Re-run. **The provider call is not retried automatically** |
| `Gemini client initialisation failed` | Malformed key, or `google-genai` not installed | `pip install google-genai`; check the key |
| `Could not extract text from Gemini response` | Response blocked or truncated | Inspect `raw_llm_response.json` for the finish reason |
| `Gemini model name must not be empty` | `GEMINI_MODEL` set to an empty string | Unset it, or give a real model id |

Distinguish the two `429`s by reading the message. `limit: 0` means the model is
not available to your key at all; any other limit means slow down.

---

## 8. Authentication troubleshooting

Authentication failures never retry — a bad credential does not become good.
`401` and `403` raise immediately as connection errors.

Order of diagnosis:

1. `health --verbose`. If the source is `UNREACHABLE`, it is not an auth problem.
2. If `READY` with `HTTP 401`, the endpoint is up and the credential is being
   rejected. Confirm the token independently:

   ```bash
   curl -s -o /dev/null -w '%{http_code}\n' -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
       "$JIRA_BASE_URL/rest/api/2/myself"
   curl -s -o /dev/null -w '%{http_code}\n' -u "$SONAR_TOKEN:" \
       "$SONAR_BASE_URL/api/authentication/validate"
   ```

3. Check the variable is actually exported. Startup validation reports an unset
   variable, but not one set to a stale value.
4. Rotate the credential. Never paste it into a ticket, a log, or a commit.

Each source uses a different scheme: JIRA is HTTP Basic (email + API token),
SonarQube is a bearer-style token as the Basic username with an empty password,
ZAP is an `apikey` query parameter.

---

## 9. Retry behaviour

Two different policies. Know which applies.

### Connector HTTP calls — retried

Governed per source by the `api.retry` block in `source-registry.json`:

| Setting | Default |
| --- | --- |
| `maxAttempts` | `3` |
| `backoffSeconds` | `1.0` (exponential: 1s, 2s, 4s …) |
| `maxBackoffSeconds` | `30.0` (cap) |

Retried: network errors, `429`, `500`, `502`, `503`, `504`.
**Not** retried: `401`, `403`, `404`, and malformed JSON.

Worst case per source with defaults: 3 attempts, ~3 s of backoff, plus timeouts.

### The Gemini provider call — *not* retried

`GeminiProvider` performs **exactly one** `generate_content` call and wraps any
failure. A transient `503` fails the whole run.

This is a real operational gap, and it is the most likely cause of a demo
failure on a `-preview` model. Mitigations, in order of preference:

1. Use a generally-available model (`gemini-2.5-flash`), not a `-preview` one.
2. Re-run. The failure is transient and the pipeline is deterministic up to the
   provider call.
3. Run the analysis before the demo and present the saved execution package.

---

## 10. Timeout behaviour

| Boundary | Timeout | Configurable |
| --- | --- | --- |
| Connector HTTP request | 30 s | `api.timeoutSeconds` per source |
| Health-check probe | 10 s | No — fixed, so `health` returns fast |
| Gemini call | SDK default | No |

A connector timeout is transient and is retried under the policy above. After
`maxAttempts` it raises `ConnectorConnectionError` and the run exits `1`.

A slow source stalls the whole run: connectors execute sequentially in registry
priority order (JIRA, then ZAP, then SonarQube).

---

## 11. Common operational failures

| Failure | Exit | Diagnosis | Recovery |
| --- | --- | --- | --- |
| Startup validation lists unset variables | `2` | Read the names; they are exact | Set them in `.env`; re-run |
| `EXECUTION_MODE=… is not a supported execution mode` | `2` | Typo | Use `FILE` or `API` |
| `Source ingestion failed … Cannot reach <url>` | `1` | Service down | Start it; verify with `health` |
| `Source ingestion failed … 401` | `1` | Bad credential | Section 8 |
| `Source mapping failed … Unsupported JIRA issue type` | `1` | Unsupported data in the source | Narrow `api.jql` |
| `Analysis failed … 429 … limit: 0` | `1` | No free-tier quota for the model | Change model or enable billing |
| `Analysis failed … 503 UNAVAILABLE` | `1` | Transient Gemini capacity | Re-run |
| `Response validation failed: …` | `0` | Validation phase errored; the analysis still completed and was written | Inspect the package; re-run with `--verbose` |
| `Skipped — validation verdict 'failed' does not open the CP1 gate` | `0` | Working as designed: `FAILED`/`BLOCKED` never reaches CP1 | Read `validation_report.md` |

A `FAILED` validation verdict is **not** an operational failure. The run
succeeded, wrote its package, and correctly withheld CP1.

---

## 12. Recovery procedures

### A run failed part-way

Nothing to clean up. Fix the cause and re-run. The pipeline is deterministic up
to the Gemini call: the same inputs select the same artifact and build a
byte-identical prompt (compare `promptSha256` across packages).

### `output/latest/` looks wrong

It always holds the most recent run, successful or not. Prefer a named package:

```bash
python scripts/run_requirement_analysis.py analyze --validate --execution-name incident-42
```

Named executions never overwrite; a collision appends `-1`, `-2`, ….

### Verifying the platform after a change

```bash
ruff check .    # lint
pytest -q       # full suite
python scripts/run_requirement_analysis.py health
python scripts/run_requirement_analysis.py analyze --validate --dry-run
```

`--dry-run` exercises everything up to the provider call and needs no API key,
so it validates connectors, mappers, consolidation, and prompt construction for
free.

### A source must be taken out of service

Set `"enabled": false` for it in `source-registry.json`. The pipeline, health
check, and startup validation all skip it. Consolidation degrades gracefully —
fewer artifacts, no error.

### The API key was leaked

1. Revoke it in Google AI Studio immediately.
2. Issue a new key; update `.env`.
3. Confirm `.env` is not in git: `git check-ignore -v .env`.
4. It has never been written to an execution package or a log.

---

## 13. See also

- [Demo guide](../demo/demo-guide.md)
- [Requirement Analysis CLI](../user-guide/requirement-analysis-cli.md)
- [Golden baseline](../productization/golden-baseline.md)
