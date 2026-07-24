# Development Environment

| Attribute        | Value                                                                 |
| ---------------- | --------------------------------------------------------------------- |
| Document type    | Developer Engineering Guide                                           |
| Status           | Active                                                                 |
| Applies to       | Anyone running `make check` (or any individual `make lint`/`make typecheck`/`make test`/`make cov`) locally |
| Supplements      | `Makefile`, `requirements.txt`, `requirements-dev.txt`                |
| Audience         | Engineers setting up or debugging this repository's local dev environment |

> This is an operational guide, not an architecture document. It says how to get
> `make check` to run reliably on a workstation. It does not define what any
> check gates on — that is the Makefile and the requirements files themselves.

---

## 1. The venv is mandatory, and the Makefile now enforces it

This project's dev tools (`ruff`, `mypy`, `pytest`) are **not** meant to be run
as bare shell commands. Every `Makefile` target invokes them through the
project's own interpreter — `PY := .venv/bin/python`, then `$(PY) -m ruff`,
`$(PY) -m mypy`, `$(PY) -m pytest`, etc. — never a bare `ruff`/`mypy`/`pytest`
resolved off `$PATH`.

This means:

- `make lint`, `make typecheck`, `make test`, `make cov`, and `make check` work
  correctly **whether or not you have activated the venv in your shell**, as
  long as `.venv/` exists at the repo root and is populated (§2).
- You do **not** need `source .venv/bin/activate` before running `make`
  targets. It doesn't hurt, but the Makefile no longer depends on it.

## 2. The Python-3.9-on-PATH trap

On at least one development machine this repository has been worked on, a
**second, unrelated** `pytest` exists on `$PATH`, installed under a Python 3.9
user-site install (`~/Library/Python/3.9/bin/pytest`) — nothing to do with
this project. Before this Makefile was fixed, a bare `pytest` invocation with
an unactivated shell could silently run *that* interpreter's pytest instead of
this project's, against a completely different (and likely incompatible)
Python version.

**This is exactly the failure mode `PY := .venv/bin/python` (§1) makes
structurally impossible** — every `make` target now names the interpreter by
path, so there is no `$PATH` lookup left to shadow. If you ever run these
tools directly (not through `make`), always invoke them the same way:

```bash
.venv/bin/python -m pytest
.venv/bin/python -m ruff check .
.venv/bin/python -m mypy .
```

Never `pytest ...`, `ruff ...`, or `mypy ...` bare — even in an activated
shell, since activation order and `$PATH` precedence across different tools
(`pyenv`, Homebrew, a user-site install) are not something to rely on.

## 3. Setting up (or repairing) `.venv`

```bash
python3.11 -m venv .venv          # this project targets Python 3.11+
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt -r requirements-dev.txt
```

`make dev` does the second step for you (plus `pre-commit install`), but still
requires `.venv/` to already exist — `make dev` does not create the venv
itself.

If `make check` ever fails in a way that looks environmental rather than
code-related (missing module, unexpected tool version), the fastest diagnosis
is usually:

```bash
.venv/bin/python --version
.venv/bin/python -m pip list
```

and comparing against `requirements.txt` / `requirements-dev.txt`. A `.venv`
that was populated by ad hoc, piecemeal `pip install`s (rather than the two
requirements files together) is the most likely cause of drift — see §4.

## 4. The `pytest` pin: resolved in favor of the declared range

`requirements-dev.txt` pins `pytest>=8.2,<9.0`. At one point, this project's
`.venv` had `pytest==9.1.1` installed instead — outside that range, alongside
several other undeclared or out-of-range packages (`pytest-cov` past its
`<6.0` ceiling, `tenacity` past its `<9.0` ceiling, and a `vulture` install not
declared in either requirements file at all). No lockfile, constraints file,
or CI configuration exists anywhere in this repository to explain how that
happened — the most plausible explanation is a series of manual,
piecemeal `pip install`s over time that drifted away from
`requirements-dev.txt`, not a deliberate decision to run newer versions. That
is inference, not a confirmed cause.

**Resolution:** the declared range is correct, not the drifted install. The
full test suite (4642 tests) was run under both `pytest==8.4.2` (the newest
version satisfying the declared `<9.0` pin) and the drifted `pytest==9.1.1`,
in isolated environments, using the same Python 3.11 interpreter this
project's `.venv` uses. **Both passed the identical 4642 tests** — nothing in
this codebase requires 9.x. `.venv` was rebuilt from scratch and reinstalled
strictly from `requirements.txt` + `requirements-dev.txt`, which restored
`pytest` to `8.4.2` and removed the undeclared `vulture` package along with
the other out-of-range drift.

If a future `pip install -U` (or similar) drifts the venv again, re-run:

```bash
rm -rf .venv
python3.11 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt -r requirements-dev.txt
```

rather than upgrading individual packages in place.

## 5. `mypy` — installed, and measured, not yet gated as clean

`mypy` was declared in `requirements-dev.txt` (`mypy>=1.10,<2.0`) but was not
actually installed in this project's `.venv` until this environment repair.
It is now installed (`mypy==1.20.2` at time of writing) and `make typecheck`
runs it.

Running it once, as a measurement, found **434 errors across 129 files**
(673 source files checked) — mostly in `tests/` (342), with the remainder in
`requirement_intelligence/` (91) and one in `infrastructure/`. No type error
was fixed as part of installing the tool; this is a baseline count for future
work to burn down, not a claim that the codebase currently type-checks
cleanly. See the environment-repair task's report (or `git log`) for the
top error-category breakdown at the time this was measured.

**Until that backlog is triaged and burned down, `make check`'s `typecheck`
target will fail on a clean checkout.** Whether `check` should gate on
`typecheck` during any given piece of work (e.g. a pure rename refactor,
where introducing zero new type errors is achievable and worth enforcing) is
a per-task decision, not something this document fixes — see the calling
task's own report for that recommendation. This guide only ensures `mypy`
is installed and invocable.
