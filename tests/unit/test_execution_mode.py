"""Unit tests for the canonical execution-mode selection (CAP-074A).

Proves the three properties the platform depends on: exactly one environment
variable selects the mode, the default is FILE, and the resolved mode reaches
every connector through the registry loader — so no connector, and nothing
downstream of it, ever decides the mode for itself.
"""

from __future__ import annotations

import pytest

from requirement_intelligence.registry.execution_mode import (
    API_MODE,
    DEFAULT_EXECUTION_MODE,
    EXECUTION_MODE_ENV_VAR,
    FILE_MODE,
    resolve_execution_mode,
)
from requirement_intelligence.registry.registry_exceptions import RegistryValidationError
from requirement_intelligence.registry.registry_loader import RegistryLoader


# =========================================================================== #
# resolve_execution_mode
# =========================================================================== #
@pytest.mark.unit
def test_default_is_file_when_unset() -> None:
    assert resolve_execution_mode({}) == FILE_MODE
    assert DEFAULT_EXECUTION_MODE == FILE_MODE


@pytest.mark.unit
@pytest.mark.parametrize("blank", ["", "   ", "\t"])
def test_blank_falls_back_to_default(blank: str) -> None:
    assert resolve_execution_mode({EXECUTION_MODE_ENV_VAR: blank}) == FILE_MODE


@pytest.mark.unit
@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("FILE", FILE_MODE),
        ("API", API_MODE),
        ("api", API_MODE),
        ("  file  ", FILE_MODE),
        ("Api", API_MODE),
    ],
)
def test_case_and_whitespace_insensitive(raw: str, expected: str) -> None:
    assert resolve_execution_mode({EXECUTION_MODE_ENV_VAR: raw}) == expected


@pytest.mark.unit
@pytest.mark.parametrize("bad", ["api-mode", "LIVE", "file mode", "0"])
def test_unsupported_mode_raises_actionable_error(bad: str) -> None:
    with pytest.raises(RegistryValidationError) as exc:
        resolve_execution_mode({EXECUTION_MODE_ENV_VAR: bad})
    message = str(exc.value)
    assert EXECUTION_MODE_ENV_VAR in message
    assert "FILE, API" in message


@pytest.mark.unit
def test_reads_process_environment_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(EXECUTION_MODE_ENV_VAR, "API")
    assert resolve_execution_mode() == API_MODE
    monkeypatch.delenv(EXECUTION_MODE_ENV_VAR)
    assert resolve_execution_mode() == FILE_MODE


# =========================================================================== #
# RegistryLoader — the single application point
# =========================================================================== #
@pytest.mark.unit
@pytest.mark.parametrize("mode", [FILE_MODE, API_MODE])
def test_loader_stamps_mode_onto_every_enabled_source(mode: str) -> None:
    sources = RegistryLoader(execution_mode=mode).get_enabled_sources()
    assert sources, "expected at least one enabled source"
    assert {s["inputMode"] for s in sources} == {mode}


@pytest.mark.unit
def test_loader_resolves_mode_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(EXECUTION_MODE_ENV_VAR, "API")
    assert RegistryLoader().execution_mode == API_MODE
    assert all(s["inputMode"] == API_MODE for s in RegistryLoader().get_enabled_sources())


@pytest.mark.unit
def test_explicit_mode_overrides_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(EXECUTION_MODE_ENV_VAR, "API")
    loader = RegistryLoader(execution_mode=FILE_MODE)
    assert loader.execution_mode == FILE_MODE
    assert all(s["inputMode"] == FILE_MODE for s in loader.get_enabled_sources())


@pytest.mark.unit
def test_mode_overrides_any_per_source_declaration(tmp_path: object) -> None:
    """A stale per-source ``inputMode`` never wins over the global selection."""
    import json
    from pathlib import Path

    registry = {
        "defaults": {"inputMode": "FILE", "enabled": False},
        "sources": [
            {
                "sourceId": "jira",
                "enabled": True,
                "inputMode": "FILE",  # deliberately contradicts the global mode
                "connectorClass": "a.B",
                "mapperClass": "c.D",
            }
        ],
    }
    path = Path(str(tmp_path)) / "source-registry.json"
    path.write_text(json.dumps(registry), encoding="utf-8")

    loader = RegistryLoader(path, execution_mode=API_MODE)
    assert loader.get_enabled_sources()[0]["inputMode"] == API_MODE


@pytest.mark.unit
def test_loader_rejects_invalid_environment_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(EXECUTION_MODE_ENV_VAR, "nonsense")
    with pytest.raises(RegistryValidationError):
        RegistryLoader()
