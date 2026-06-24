"""Unit tests for the Connector Registry component.

Covers configuration loading, schema/structure validation, sorting by priority,
dynamic loading of connector/mapper classes, metadata validation at startup,
and pipeline execution (single source and all sources) using the actual
configurations from source-registry.json.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
import pytest

from requirement_intelligence.models.source_artifact import SourceArtifact
from requirement_intelligence.registry.connector_registry import ConnectorRegistry
from requirement_intelligence.registry.registry_exceptions import RegistryValidationError
from requirement_intelligence.registry.registry_loader import RegistryLoader

# Bundled sample exports shipped for FILE-mode ingestion.
_INPUT_DIR = Path(__file__).resolve().parents[2] / "input"
JIRA_SAMPLE_ISSUES = _INPUT_DIR / "jira" / "jira-issues.json"
ZAP_SAMPLE_ALERTS = _INPUT_DIR / "zap" / "zap-alerts.json"
SONAR_SAMPLE_ISSUES = _INPUT_DIR / "sonar" / "sonar-issues.json"


# --- Helpers for building temporary registry configurations ---
def _write_temp_registry(tmp_path: Path, data: dict[str, Any]) -> Path:
    registry_file = tmp_path / "source-registry.json"
    registry_file.write_text(json.dumps(data), encoding="utf-8")
    return registry_file


def _get_absolute_sources_data() -> dict[str, Any]:
    """Loads actual source-registry.json and overrides input paths to be absolute."""
    loader = RegistryLoader()
    registry_data = loader.load_registry()
    for source in registry_data.get("sources", []):
        source_id = source.get("sourceId")
        if source_id == "jira":
            source["inputPath"] = str(JIRA_SAMPLE_ISSUES)
        elif source_id == "owasp_zap":
            source["inputPath"] = str(ZAP_SAMPLE_ALERTS)
        elif source_id == "sonarqube":
            source["inputPath"] = str(SONAR_SAMPLE_ISSUES)
    return registry_data


# --- Registry Loader Tests ---
@pytest.mark.unit
def test_registry_loader_loads_valid() -> None:
    loader = RegistryLoader()
    registry = loader.load_registry()
    assert registry["registryVersion"] == "1.0.0"
    assert len(registry["sources"]) >= 3


@pytest.mark.unit
def test_registry_loader_missing_file() -> None:
    loader = RegistryLoader(Path("non_existent_file.json"))
    with pytest.raises(RegistryValidationError, match="Registry file not found"):
        loader.load_registry()


@pytest.mark.unit
def test_registry_loader_invalid_json(tmp_path: Path) -> None:
    path = tmp_path / "source-registry.json"
    path.write_text("{invalid json", encoding="utf-8")
    loader = RegistryLoader(path)
    with pytest.raises(RegistryValidationError, match="Failed to read or parse registry file"):
        loader.load_registry()


@pytest.mark.unit
def test_registry_loader_not_object(tmp_path: Path) -> None:
    path = _write_temp_registry(tmp_path, [1, 2, 3])  # type: ignore[arg-type]
    loader = RegistryLoader(path)
    with pytest.raises(RegistryValidationError, match="Registry must be a JSON object"):
        loader.load_registry()


@pytest.mark.unit
def test_registry_loader_missing_sources(tmp_path: Path) -> None:
    path = _write_temp_registry(tmp_path, {"registryVersion": "1.0.0"})
    loader = RegistryLoader(path)
    with pytest.raises(RegistryValidationError, match="missing the 'sources' list"):
        loader.load_registry()


@pytest.mark.unit
def test_registry_loader_sources_not_list(tmp_path: Path) -> None:
    path = _write_temp_registry(tmp_path, {"sources": "not-a-list"})
    loader = RegistryLoader(path)
    with pytest.raises(RegistryValidationError, match="'sources' key in registry must be a list"):
        loader.load_registry()


@pytest.mark.unit
def test_registry_loader_defaults_not_object(tmp_path: Path) -> None:
    path = _write_temp_registry(tmp_path, {"sources": [], "defaults": "not-an-object"})
    loader = RegistryLoader(path)
    with pytest.raises(RegistryValidationError, match="'defaults' key in registry must be a JSON object"):
        loader.load_registry()


@pytest.mark.unit
@pytest.mark.parametrize(
    "missing_field",
    ["sourceId", "connectorClass", "mapperClass"]
)
def test_registry_loader_missing_required_fields(tmp_path: Path, missing_field: str) -> None:
    # Load actual data and delete required field from the first source
    loader = RegistryLoader()
    data = loader.load_registry()
    data["sources"][0].pop(missing_field)
    
    path = _write_temp_registry(tmp_path, data)
    loader = RegistryLoader(path)
    with pytest.raises(RegistryValidationError, match="missing required string field"):
        loader.load_registry()


@pytest.mark.unit
def test_registry_loader_non_integer_priority(tmp_path: Path) -> None:
    loader = RegistryLoader()
    data = loader.load_registry()
    data["sources"][0]["priority"] = "not-an-int"
    
    path = _write_temp_registry(tmp_path, data)
    loader = RegistryLoader(path)
    with pytest.raises(RegistryValidationError, match="has non-integer priority"):
        loader.load_registry()


@pytest.mark.unit
def test_registry_loader_filtering_and_sorting(tmp_path: Path) -> None:
    # Test filtering and sorting using clean dummy entries with importable classes
    data = {
        "defaults": {
            "enabled": False,
            "priority": 5,
        },
        "sources": [
            {
                "sourceId": "source_2",
                "connectorClass": "requirement_intelligence.connectors.sonarqube.connector.SonarQubeConnector",
                "mapperClass": "requirement_intelligence.mappers.sonar_mapper.SonarMapper",
                "enabled": True,
                "priority": 2,
            },
            {
                "sourceId": "source_1",
                "connectorClass": "requirement_intelligence.connectors.sonarqube.connector.SonarQubeConnector",
                "mapperClass": "requirement_intelligence.mappers.sonar_mapper.SonarMapper",
                "enabled": True,
                "priority": 1,
            },
            {
                "sourceId": "source_3",
                "connectorClass": "requirement_intelligence.connectors.sonarqube.connector.SonarQubeConnector",
                "mapperClass": "requirement_intelligence.mappers.sonar_mapper.SonarMapper",
                # Enabled defaults to False from defaults block
            },
            {
                "sourceId": "source_4",
                "connectorClass": "requirement_intelligence.connectors.sonarqube.connector.SonarQubeConnector",
                "mapperClass": "requirement_intelligence.mappers.sonar_mapper.SonarMapper",
                "enabled": True,
                # Priority defaults to 5 from defaults block
            },
        ]
    }
    path = _write_temp_registry(tmp_path, data)
    loader = RegistryLoader(path)
    enabled = loader.get_enabled_sources()

    # source_3 is disabled by default, so we expect 3 sources
    assert len(enabled) == 3
    # Check ordering by priority: source_1 (1) -> source_2 (2) -> source_4 (5)
    assert enabled[0]["sourceId"] == "source_1"
    assert enabled[1]["sourceId"] == "source_2"
    assert enabled[2]["sourceId"] == "source_4"


# --- Connector Registry Tests ---
@pytest.mark.unit
def test_connector_registry_startup_metadata_validation() -> None:
    # Validate that actual registry file loads and startup validation passes
    loader = RegistryLoader()
    registry = ConnectorRegistry(loader)
    assert registry is not None


@pytest.mark.unit
def test_connector_registry_startup_metadata_validation_raises(tmp_path: Path) -> None:
    # Load actual sources configuration (maintaining enabled state from config file)
    data = _get_absolute_sources_data()
    loader = RegistryLoader()
    enabled_sources = loader.get_enabled_sources()
    
    if not enabled_sources:
        pytest.skip("No sources are enabled in source-registry.json, skipping validation test")
        
    # Modify the sourceId of the first enabled source to cause a mismatch
    target_source_id = enabled_sources[0]["sourceId"]
    for source in data["sources"]:
        if source["sourceId"] == target_source_id:
            source["sourceId"] = target_source_id + "_mismatched"
            
    path = _write_temp_registry(tmp_path, data)
    temp_loader = RegistryLoader(path)
    
    with pytest.raises(RegistryValidationError, match="Metadata validation failed"):
        ConnectorRegistry(temp_loader)


@pytest.mark.unit
def test_connector_registry_dynamic_load_errors(tmp_path: Path) -> None:
    # Load actual sources configuration
    data = _get_absolute_sources_data()
    loader = RegistryLoader()
    enabled_sources = loader.get_enabled_sources()
    
    if not enabled_sources:
        pytest.skip("No sources are enabled in source-registry.json, skipping dynamic load test")
        
    # Modify the connectorClass of the first enabled source to trigger a load error
    target_source_id = enabled_sources[0]["sourceId"]
    for source in data["sources"]:
        if source["sourceId"] == target_source_id:
            source["connectorClass"] = "nonexistent_module.NonexistentClass"
            
    path = _write_temp_registry(tmp_path, data)
    temp_loader = RegistryLoader(path)
    
    with pytest.raises(RegistryValidationError, match="Failed to dynamically load class"):
        ConnectorRegistry(temp_loader)


@pytest.mark.unit
@pytest.mark.parametrize("source_id", ["jira", "owasp_zap", "sonarqube"])
def test_connector_registry_execute_source(source_id: str) -> None:
    # 1. Load raw registry data
    loader = RegistryLoader()
    data = loader.load_registry()

    # 2. Extract the configuration for the current parameterized source
    source_config = next(s for s in data["sources"] if s["sourceId"] == source_id)

    # 3. Apply defaults to check its actual operational 'enabled' state
    defaults = data.get("defaults", {})
    final_config = {**defaults, **source_config}

    # 4. CRITICAL: Skip the test dynamically if it isn't enabled in the file!
    if not final_config.get("enabled", False):
        pytest.skip(f"Source '{source_id}' is disabled in source-registry.json. Skipping forced execution check.")

    # 5. Otherwise, override inputPath to absolute path and execute normally
    if source_id == "jira":
        source_config["inputPath"] = str(JIRA_SAMPLE_ISSUES)
    elif source_id == "owasp_zap":
        source_config["inputPath"] = str(ZAP_SAMPLE_ALERTS)
    elif source_id == "sonarqube":
        source_config["inputPath"] = str(SONAR_SAMPLE_ISSUES)

    registry = ConnectorRegistry()
    artifacts = registry.execute_source(source_config)

    assert isinstance(artifacts, list)
    assert len(artifacts) > 0
    assert all(isinstance(a, SourceArtifact) for a in artifacts)


@pytest.mark.unit
def test_connector_registry_execute_all(tmp_path: Path) -> None:
    # Load actual registry data (no overriding of enabled states)
    data = _get_absolute_sources_data()
    
    path = _write_temp_registry(tmp_path, data)
    loader = RegistryLoader(path)
    registry = ConnectorRegistry(loader)
    
    # Fetch which systems are enabled in source-registry.json
    enabled_sources = loader.get_enabled_sources()
    enabled_ids = [s["sourceId"] for s in enabled_sources]
    
    artifacts = registry.execute_all()
    
    # Verify results align with only the enabled sources
    systems = {a.source_system for a in artifacts}
    
    for source in data["sources"]:
        source_id = source["sourceId"]
        system_name = "owasp_zap" if source_id == "owasp_zap" else source_id
        if source_id in enabled_ids:
            assert system_name in systems
        else:
            assert system_name not in systems


@pytest.mark.unit
def test_actual_registry_file_loads_and_validates_successfully() -> None:
    loader = RegistryLoader()
    registry_data = loader.load_registry()
    assert len(registry_data.get("sources", [])) >= 3  # JIRA, OWASP ZAP, SonarQube exist in the file

    enabled = loader.get_enabled_sources()
    assert isinstance(enabled, list)

    registry = ConnectorRegistry(loader)
    assert registry is not None
