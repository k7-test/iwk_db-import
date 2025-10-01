from __future__ import annotations

import json
import pathlib

import pytest
import yaml

try:
    import jsonschema  # type: ignore
    from jsonschema.exceptions import ValidationError  # type: ignore
except ImportError:  # pragma: no cover
    jsonschema = None  # type: ignore
    ValidationError = Exception  # type: ignore

"""Config schema contract test (FR-026, FR-027)."""

SCHEMA_PATH = pathlib.Path("specs/001-excel-postgressql-excel/contracts/config_schema.json")


@pytest.mark.skipif(jsonschema is None, reason="jsonschema library not installed")
def test_config_schema_valid_example():
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    config = {
        "source_directory": "./data",
        "sheet_mappings": {
            "Customers": {
                "table": "customers",
                "sequence_columns": ["id"]
            },
            "Orders": {
                "table": "orders",
                "sequence_columns": ["id"],
                "fk_propagation_columns": ["customer_id"]
            }
        },
        "sequences": {
            "id": "customers_id_seq"
        },
        "fk_propagations": {
            "customer_id": "id"
        },
        "timezone": "UTC",
        "database": {
            "host": "localhost",
            "port": 5432,
            "user": "appuser",
            "password": "secret",
            "database": "appdb"
        }
    }
    jsonschema.validate(config, schema)  # type: ignore


@pytest.mark.skipif(jsonschema is None, reason="jsonschema library not installed")
def test_config_schema_missing_required_key():
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    # Missing required key 'database'
    config = {
        "source_directory": "./data",
        "sheet_mappings": {
            "Customers": {
                "table": "customers"
            }
        },
        "sequences": {},
        "fk_propagations": {}
    }
    with pytest.raises(ValidationError):
        jsonschema.validate(config, schema)  # type: ignore


@pytest.mark.skipif(jsonschema is None, reason="jsonschema library not installed")
def test_config_schema_invalid_sheet_mapping():
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    # Sheet mapping missing required 'table' key
    config = {
        "source_directory": "./data",
        "sheet_mappings": {
            "Customers": {
                "sequence_columns": ["id"]  # Missing 'table'
            }
        },
        "sequences": {},
        "fk_propagations": {},
        "database": {}
    }
    with pytest.raises(ValidationError):
        jsonschema.validate(config, schema)  # type: ignore


@pytest.mark.skipif(jsonschema is None, reason="jsonschema library not installed")
def test_config_schema_rejects_extra_key():
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    config = {
        "source_directory": "./data",
        "sheet_mappings": {
            "Customers": {
                "table": "customers"
            }
        },
        "sequences": {},
        "fk_propagations": {},
        "database": {},
        "extra_field": "not allowed"  # Extra field should be rejected
    }
    with pytest.raises(ValidationError):
        jsonschema.validate(config, schema)  # type: ignore


@pytest.mark.skipif(jsonschema is None, reason="jsonschema library not installed")
def test_config_schema_validates_from_sample_yaml(sample_config_yaml: str):
    """Test that the sample config from conftest.py validates against schema."""
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    config = yaml.safe_load(sample_config_yaml)
    jsonschema.validate(config, schema)  # type: ignore


@pytest.mark.skipif(jsonschema is None, reason="jsonschema library not installed")
def test_config_schema_minimal_valid_config():
    """Test minimal valid config with only required fields."""
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    config = {
        "source_directory": "./data",
        "sheet_mappings": {
            "Sheet1": {
                "table": "table1"
            }
        },
        "sequences": {},
        "fk_propagations": {},
        "database": {}
    }
    jsonschema.validate(config, schema)  # type: ignore