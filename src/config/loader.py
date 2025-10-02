from __future__ import annotations

"""Config loader skeleton (Phase 1) - Failing tests will drive implementation.

Responsibilities:
- Load YAML config/import.yml
- Validate required keys (per contracts/config_schema.yaml)
- Apply defaults (timezone=UTC if missing)
- DO NOT implement full logic yet.
"""
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

try:
    import jsonschema  # type: ignore
    from jsonschema.exceptions import ValidationError  # type: ignore
except ImportError:  # pragma: no cover
    jsonschema = None  # type: ignore
    ValidationError = Exception  # type: ignore


# Get schema path relative to the repository root
_current_file = Path(__file__)
# src/config/loader.py -> src/config -> src -> repo_root
_repo_root = _current_file.parent.parent.parent
SCHEMA_PATH = (
    _repo_root / "specs" / "001-excel-postgressql-excel" / "contracts" / "config_schema.json"
)

class ConfigError(Exception):
    pass

@dataclass(frozen=True)
class DatabaseConfig:
    host: str | None
    port: int | None
    user: str | None
    password: str | None
    database: str | None
    dsn: str | None

@dataclass(frozen=True)
class ImportConfig:
    source_directory: str
    sheet_mappings: dict[str, Any]
    sequences: dict[str, str]
    fk_propagations: dict[str, str]
    timezone: str
    database: DatabaseConfig


def _validate_config_schema(data: dict[str, Any]) -> None:
    """Validate config data against JSON schema.
    
    Args:
        data: Configuration data to validate
        
    Raises:
        ConfigError: If jsonschema is not available or validation fails
    """
    if jsonschema is None:
        raise ConfigError("jsonschema library is required for config validation")
    
    if not SCHEMA_PATH.exists():
        raise ConfigError(f"config schema not found: {SCHEMA_PATH}")
    
    try:
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        jsonschema.validate(data, schema)  # type: ignore
    except json.JSONDecodeError as e:
        raise ConfigError(f"invalid schema file: {e}") from e
    except ValidationError as e:
        raise ConfigError(f"config validation failed: {e.message}") from e


def load_config(path: Path) -> ImportConfig:
    if not path.exists():  # FR-015
        raise ConfigError(f"config file not found: {path}")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as e:
        raise ConfigError(f"invalid yaml: {e}") from e

    # Validate against JSON schema
    _validate_config_schema(data)

    tz = data.get("timezone", "UTC")  # FR-023 default
    db_raw = data.get("database", {})
    db = DatabaseConfig(
        host=db_raw.get("host"),
        port=db_raw.get("port"),
        user=db_raw.get("user"),
        password=db_raw.get("password"),
        database=db_raw.get("database"),
        dsn=db_raw.get("dsn"),
    )
    return ImportConfig(
        source_directory=data["source_directory"],
        sheet_mappings=data["sheet_mappings"],
        sequences=data["sequences"],
        fk_propagations=data["fk_propagations"],
        timezone=tz,
        database=db,
    )
