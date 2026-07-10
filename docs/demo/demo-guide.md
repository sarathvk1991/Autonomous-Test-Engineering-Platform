# Requirement Intelligence Layer — Demo Guide

A first-time walkthrough. It assumes you have just cloned the repository, know
nothing about its internals, and want to demonstrate it to someone within the
hour.

Everything below has been executed end to end. Timings are real, measured on a
developer laptop.

---

## 1. Overview

The Requirement Intelligence Layer ingests engineering signals from three
sources, consolidates them, reasons over them with Google Gemini, then
normalizes, validates, and gates the result before writing a reproducible
**execution package** to disk.

```text
JIRA + SonarQube + OWASP ZAP
        ↓  Connectors  (FILE or API)
        ↓  Mappers
        ↓  Consolidation Engine
        ↓  Requirement Analysis Service  →  Gemini
        ↓  Response Normalization
        ↓  Response Validation           →  PASS / FAIL
        ↓  CP1 Engineering Readiness     →  PASS / FAIL
        ↓  Execution Package
```

The single most important idea for a demo: **one environment variable decides
where the data comes from.**

| `EXECUTION_MODE` | Sources read from | Credentials needed | Network |
| --- | --- | --- | --- |
| `FILE` *(default)* | Bundled sample exports on disk | Gemini only | Gemini only |
| `API` | Live JIRA, SonarQube, OWASP ZAP | All | Yes |

Nothing downstream of the connectors knows which mode ran. The prompt, the
validation rules, CP1, and the execution package are identical in both.

---

## 2. Repository prerequisites

- **Python 3.11+** (3.11 or newer; the code uses `contextlib.chdir`)
- A **Google AI Studio API key** — <https://aistudio.google.com/>
- For `EXECUTION_MODE=API` only: reachable JIRA, SonarQube, and OWASP ZAP

Azure OpenAI is **not** used. It exists only as an unimplemented, reserved
provider stub.

```bash
git clone <repo-url>
cd "Autonomous Test Engineering Platform"

python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt

cp .env.example .env      # then edit .env
```

---

## 3. Environment variables

Edit `.env`. It is gitignored — never commit it.

### Always required

| Variable | Purpose |
| --- | --- |
| `GOOGLE_API_KEY` | Gemini API key from Google AI Studio |
| `GEMINI_MODEL` | Model to use, e.g. `gemini-2.5-flash` |

### Selects the ingestion mode

| Variable | Values | Default |
| --- | --- | --- |
| `EXECUTION_MODE` | `FILE` or `API` | `FILE` |

### Required only when `EXECUTION_MODE=API`

| Source | Variables |
| --- | --- |
| JIRA | `JIRA_BASE_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN`, `JIRA_PROJECT_KEY` |
| SonarQube | `SONAR_BASE_URL`, `SONAR_TOKEN`, `SONAR_PROJECT_KEY` |
| OWASP ZAP | `ZAP_BASE_URL`, `ZAP_API_KEY` |

Two details that cost people time:

- **`JIRA_BASE_URL` must be the bare site root** — `https://your-org.atlassian.net`,
  with no `/jira` path suffix. A suffix makes JIRA return its web UI as HTML with
  `HTTP 200`, which surfaces as a confusing "malformed JSON" error.
- **`JIRA_PROJECT_KEY` is the project *key*, not its name** — `SCRUM`, not
  `My Automation Product`. A wrong key silently returns zero issues.

You do not have to memorise which variables a mode needs. Startup validation
names every missing one before anything runs.

---

## 4. FILE mode execution

The default. No source system needs to exist; sample exports ship in the repo.

```bash
python scripts/run_requirement_analysis.py analyze --validate
```

Expected: `Validation PASS`, `CP1 PASS`, an execution package on disk.
**~30 seconds**, almost all of it the Gemini call.

---

## 5. API mode execution

Identical command; one variable changes.

```bash
EXECUTION_MODE=API python scripts/run_requirement_analysis.py analyze --validate
```

Always run the health check first (next section) — it is the difference between
a clean demo and debugging a connection in front of an audience.

**~30 seconds.** Live ingestion adds roughly 2 seconds over FILE mode.

---

## 6. Health check

Verifies JIRA, SonarQube, and OWASP ZAP. It runs **no** pipeline stage — no
consolidation, no Gemini call, no validation, no CP1, no execution package. It
costs nothing and produces nothing.

```bash
python scripts/run_requirement_analysis.py health                       # FILE
EXECUTION_MODE=API python scripts/run_requirement_analysis.py health    # API
```

```text
====================================================
  Execution Mode        : API
====================================================
  JIRA .................. READY
  OWASP ZAP ............. READY
  SonarQube ............. READY
====================================================

All 3 source(s) READY.
```

| Status | Meaning | What to do |
| --- | --- | --- |
| `READY` | The source can be read from | Nothing |
| `MISCONFIGURED` | Configuration is wrong; the source was never contacted | Fix `.env` or the source registry |
| `UNREACHABLE` | Configuration is fine; the source did not answer | Start the service, check the network |

Exit code is `0` only when every source is `READY`, so `health` works as a
pre-demo gate or a deployment check. Add `--verbose` to see the detail line for
each source.

---

## 7. Expected outputs

Every successful `analyze` prints a banner, then progresses through the pipeline:

```text
====================================================
  Version               : 1.0.0
  Execution Mode        : FILE
  Prompt Version        : 1.0.0
  LLM Provider          : gemini (gemini-2.5-flash)
  Registered Sources    : JIRA, OWASP ZAP, SonarQube
  Validation            : ENABLED
  CP1                   : ENABLED
  Execution Package     : ENABLED
====================================================
  JIRA .................. READY
  OWASP ZAP ............. READY
  SonarQube ............. READY
====================================================

Starting execution...

Running Connectors...
  ✓ JIRA
  ✓ OWASP ZAP
  ✓ SonarQube
Running Consolidation...
  ✓ 23 Consolidated Artifacts
...
Running Response Validation...
  ✓ Overall Verdict : passed
Running CP1 Engineering-Readiness Evaluation...
  ✓ Overall Verdict : pass
Writing Execution Package...
  ✓ Complete
```

In the banner, per-source status means what startup validation actually proved.
In FILE mode the input file was opened, so it reads `READY`. In API mode only
the credentials were resolved, so it reads `CONFIGURED` — use `health` to prove
an endpoint is live.

Artifact counts differ by mode because the data differs: the bundled exports
produce **23** consolidated artifacts; a live SonarQube with more findings
produces more (**47** in our rehearsal). Both are correct.

---

## 8. Generated execution artifacts

Written to `output/latest/` and, when named, `output/executions/<name>/`.

| File | Contents |
| --- | --- |
| `manifest.json` | Canonical entry point: versions, hashes, timings, verdicts |
| `consolidated_artifact.json` | The consolidation group that was analysed |
| `engineering_context.json` | The orchestrated evidence, the policy that selected it, and why |
| `prompt.txt` | The exact prompt sent |
| `llm_request.json` | The provider-agnostic request |
| `raw_llm_response.json` | The unmodified provider response |
| `analysis_result.json` | The analysis result, with token usage |
| `validation_result.json` | Full validation result and every issue |
| `validation_report.md` | Human-readable validation report |
| `cp1_report.md` | CP1 engineering-readiness report |
| `review.md` | Reviewer-facing summary |
| `execution_summary.md` | One-page execution summary |
| `baseline_metrics.md` | Metrics against the golden baseline |

Start at `manifest.json`. `promptSha256` and `responseSha256` make any two runs
directly comparable.

```bash
python scripts/run_requirement_analysis.py analyze --validate \
    --execution-name my-demo
# → output/executions/my-demo/
```

A named execution never overwrites an existing one; it appends `-1`, `-2`, ….

---

## 9. Common troubleshooting

| Symptom | Cause | Fix |
| --- | --- | --- |
| `GOOGLE_API_KEY is not set` | No key in env or `.env` | Set it, or use `--dry-run` |
| `Startup validation failed (API mode)` listing a variable | That variable is unset | Set it in `.env`; the message names it |
| `EXECUTION_MODE='api-mode' is not a supported execution mode` | Typo | Use exactly `FILE` or `API` |
| `malformed JSON in response from …/jira/rest/…` | `JIRA_BASE_URL` has a `/jira` suffix | Use the bare site root |
| JIRA returns 0 issues | `JIRA_PROJECT_KEY` is a project *name* | Use the key (e.g. `SCRUM`) |
| `Source ingestion failed … Cannot reach` | Service is down | Start it; confirm with `health` |
| `429 RESOURCE_EXHAUSTED … limit: 0` | Model not in your Gemini free tier | Pick another model or enable billing |
| `Unsupported JIRA issue type 'Task'` | JIRA holds unsupported issue types | Already scoped away by `api.jql`; see Known limitations |

No expected configuration error prints a Python stack trace. If you see a
traceback, that is a defect — report it.

---

## 10. Recommended demo flow

1. Show `version` — the platform states its own capabilities.
2. Show `health` in FILE mode — everything `READY`, instantly.
3. Run `analyze --validate` in FILE mode — the full pipeline, no dependencies.
4. Open `output/latest/manifest.json` — versions, hashes, verdicts.
5. Show `health` in API mode — the same command, live systems.
6. Run `analyze --validate` in API mode — same command, more artifacts.
7. Point out that only `EXECUTION_MODE` changed.

---

## 11. Five-minute demo walkthrough

```bash
# 0:00 — the platform describes itself
python scripts/run_requirement_analysis.py version

# 0:30 — are the sources ready? (no pipeline runs)
python scripts/run_requirement_analysis.py health

# 0:45 — full pipeline on bundled data: Gemini → Validation → CP1 → package
python scripts/run_requirement_analysis.py analyze --validate \
    --execution-name demo-file

# 1:20 — the evidence
cat output/executions/demo-file/manifest.json | head -30
cat output/executions/demo-file/cp1_report.md | head -12

# 2:30 — same command, live systems. Only EXECUTION_MODE changed.
EXECUTION_MODE=API python scripts/run_requirement_analysis.py health
EXECUTION_MODE=API python scripts/run_requirement_analysis.py analyze --validate \
    --execution-name demo-api

# 4:00 — compare: more artifacts, same verdicts, same contract
diff <(jq -r '.promptVersion,.reasoningContractVersion' output/executions/demo-file/manifest.json) \
     <(jq -r '.promptVersion,.reasoningContractVersion' output/executions/demo-api/manifest.json)
```

### Expected timing

Nearly all wall-clock time is the single Gemini call, so the model you pick
dominates the demo.

| Step | `gemini-3.1-flash-lite` | `gemini-2.5-flash` |
| --- | --- | --- |
| `version` | < 1 s | < 1 s |
| `health` (FILE) | < 1 s | < 1 s |
| `health` (API) | ~1 s, three HTTP probes | ~1 s |
| `analyze --validate` (FILE) | **~4 s** | ~29 s |
| `analyze --validate` (API) | **~5 s** | ~30 s |
| Validation | < 1 ms | < 1 ms |
| CP1 | < 1 ms | < 1 ms |

**Use `gemini-3.1-flash-lite` for a live demo** — it is roughly 8× faster,
deterministic, and produces functional, security, *and* quality requirements.
See the [Gemini model evaluation](gemini-model-evaluation.md) for the evidence.

```bash
python scripts/run_requirement_analysis.py analyze --validate \
    --model gemini-3.1-flash-lite
```

Do **not** demo on `gemini-3-flash-preview` (averages over 10 minutes and failed
1 of 3 runs) or `gemini-2.0-flash` (no free-tier quota).

---

## 12. Known limitations

- **JIRA issue types.** `JiraMapper` canonicalises `Story`, `Bug`, and `Epic`
  only, and raises rather than silently dropping anything else. API mode
  therefore scopes retrieval with `api.jql: "issuetype in (Story, Bug, Epic)"` in
  `source-registry.json`. A JIRA project consisting entirely of `Task` issues
  will ingest **zero** functional artifacts.
- **JIRA Cloud endpoint.** The connector uses `/rest/api/2/search/jql` with cursor
  pagination. The older `/rest/api/2/search` has been removed by Atlassian and
  answers `HTTP 410`.
- **Gemini free-tier quotas.** Some models (notably the `gemini-2.0-*` family)
  have a free-tier request limit of **0** and return `429` regardless of retry.
  Verify your key against a model before demonstrating with it.
- **API-mode banner status.** Reads `CONFIGURED`, not `READY` — startup
  validation deliberately makes no network call. Use `health` for reachability.
- **No retry around the provider call.** The Gemini call is made exactly once;
  a transient `503` fails the run. Connector HTTP calls *are* retried.
- **`analyze` selects one artifact.** The one with the most grouped findings,
  ties broken by id. Use `--artifact-id` to pick another, `list-artifacts` to see
  them all.

---

## 13. See also

- [Operations runbook](../operations/runbook.md) — running and troubleshooting
- [Requirement Analysis CLI](../user-guide/requirement-analysis-cli.md) — full reference
- [Architecture overview](../architecture/overview.md)
- [Golden baseline](../productization/golden-baseline.md)
