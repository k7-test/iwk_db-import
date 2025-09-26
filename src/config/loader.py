from __future__ import annotations
"""Config loader skeleton (Phase 1) - Failing tests will drive implementation.

Responsibilities:
- Load YAML config/import.yml
- Validate required keys (per contracts/config_schema.yaml)
- Apply defaults (timezone=UTC if missing)
- DO NOT implement full logic yet.
"""
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import yaml

REQUIRED_ROOT_KEYS = {"source_directory", "sheet_mappings", "sequences", "fk_propagations", "database"}

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


def load_config(path: Path) -> ImportConfig:
    if not path.exists():  # FR-015
        raise ConfigError(f"config file not found: {path}")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as e:
        raise ConfigError(f"invalid yaml: {e}") from e

    missing = REQUIRED_ROOT_KEYS - data.keys()
    if missing:  # FR-026
        raise ConfigError(f"missing required keys: {sorted(missing)}")

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
