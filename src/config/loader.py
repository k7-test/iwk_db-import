from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

"""Config loader skeleton (Phase 1) - Failing tests will drive implementation.

Responsibilities:
- Load YAML config/import.yml
- Validate required keys (per contracts/config_schema.yaml)
- Apply defaults (timezone=UTC if missing)
- DO NOT implement full logic yet.
"""

if TYPE_CHECKING:
    import jsonschema
    from jsonschema.exceptions import ValidationError
else:
    try:
        import jsonschema
        from jsonschema.exceptions import ValidationError
    except ImportError:  # pragma: no cover
        jsonschema = None  # type: ignore[assignment]
        ValidationError = Exception  # type: ignore[misc,assignment]


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
    fk_propagations: Any  # dict[str,str] 旧形式 or list[{parent,child}] 新形式
    timezone: str
    database: DatabaseConfig


def _validate_config_schema(data: dict[str, Any]) -> None:
    """Validate config data against JSON schema.

    Args:
        data: Configuration data to validate

    Raises:
        ConfigError: If any of the following occurs:
            - The jsonschema library is not available.
            - The schema file does not exist.
            - The schema file is not valid JSON.
            - The config data fails schema validation (e.g., missing required keys, 
              wrong types, or other schema violations).
    """
    if jsonschema is None:
        raise ConfigError("jsonschema library is required for config validation")
    
    if not SCHEMA_PATH.exists():
        raise ConfigError(f"config schema not found: {SCHEMA_PATH}")
    
    try:
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        jsonschema.validate(data, schema)
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
        fk_propagations=data["fk_propagations"],  # 形式は後段サービスで解釈
        timezone=tz,
        database=db,
    )
