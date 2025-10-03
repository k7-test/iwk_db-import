from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from src.config.loader import ConfigError, _validate_config_schema

"""Unit tests for config validation error cases (T034)."""


def test_validate_config_schema_missing_jsonschema():
    """Test that ConfigError is raised when jsonschema library is not available."""
    with patch("src.config.loader.jsonschema", None):
        with pytest.raises(ConfigError) as e:
            _validate_config_schema({})
        assert "jsonschema library is required for config validation" in str(e.value)


def test_validate_config_schema_missing_schema_file():
    """Test that ConfigError is raised when schema file does not exist."""
    with patch("src.config.loader.SCHEMA_PATH", Path("/nonexistent/schema.json")):
        with pytest.raises(ConfigError) as e:
            _validate_config_schema({})
        assert "config schema not found" in str(e.value)


def test_validate_config_schema_invalid_json_schema():
    """Test that ConfigError is raised when schema file contains invalid JSON."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write("{ invalid json }")
        f.flush()
        temp_path = Path(f.name)
    
    try:
        with patch("src.config.loader.SCHEMA_PATH", temp_path):
            with pytest.raises(ConfigError) as e:
                _validate_config_schema({})
            assert "invalid schema file" in str(e.value)
    finally:
        temp_path.unlink()


def test_validate_config_schema_missing_required_keys():
    """Test that ConfigError is raised when required keys are missing."""
    # Empty config missing all required keys
    with pytest.raises(ConfigError) as e:
        _validate_config_schema({})
    assert "config validation failed" in str(e.value)
    assert "required property" in str(e.value)


def test_validate_config_schema_wrong_type():
    """Test that ConfigError is raised when value has wrong type."""
    invalid_config = {
        "source_directory": 123,  # should be string
        "sheet_mappings": {},
        "sequences": {},
        "fk_propagations": {},
        "database": {}
    }
    with pytest.raises(ConfigError) as e:
        _validate_config_schema(invalid_config)
    assert "config validation failed" in str(e.value)


def test_validate_config_schema_additional_properties():
    """Test that ConfigError is raised when additional properties are present."""
    invalid_config = {
        "source_directory": "./data",
        "sheet_mappings": {},
        "sequences": {},
        "fk_propagations": {},
        "database": {},
        "extra_field": "not allowed"  # additional property
    }
    with pytest.raises(ConfigError) as e:
        _validate_config_schema(invalid_config)
    assert "config validation failed" in str(e.value)


def test_validate_config_schema_invalid_sheet_mapping():
    """Test that ConfigError is raised when sheet mapping is invalid."""
    invalid_config = {
        "source_directory": "./data",
        "sheet_mappings": {
            "Sheet1": {
                # missing required 'table' field
                "sequence_columns": ["id"]
            }
        },
        "sequences": {},
        "fk_propagations": {},
        "database": {}
    }
    with pytest.raises(ConfigError) as e:
        _validate_config_schema(invalid_config)
    assert "config validation failed" in str(e.value)


def test_validate_config_schema_invalid_database_config():
    """Test that ConfigError is raised when database config has wrong types."""
    invalid_config = {
        "source_directory": "./data",
        "sheet_mappings": {},
        "sequences": {},
        "fk_propagations": {},
        "database": {
            "port": "not_an_integer"  # should be integer
        }
    }
    with pytest.raises(ConfigError) as e:
        _validate_config_schema(invalid_config)
    assert "config validation failed" in str(e.value)


def test_validate_config_schema_database_additional_properties():
    """Test that ConfigError is raised when database has additional properties."""
    invalid_config = {
        "source_directory": "./data",
        "sheet_mappings": {},
        "sequences": {},
        "fk_propagations": {},
        "database": {
            "host": "localhost",
            "extra_db_field": "not allowed"  # additional property
        }
    }
    with pytest.raises(ConfigError) as e:
        _validate_config_schema(invalid_config)
    assert "config validation failed" in str(e.value)


def test_validate_config_schema_valid_config():
    """Test that no error is raised for valid config."""
    valid_config = {
        "source_directory": "./data",
        "sheet_mappings": {
            "Customers": {
                "table": "customers",
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
        "database": {
            "host": "localhost",
            "port": 5432,
            "user": "appuser",
            "password": "secret",
            "database": "appdb"
        },
        "timezone": "UTC"
    }
    # Should not raise any exception
    _validate_config_schema(valid_config)


def test_validate_config_schema_minimal_valid_config():
    """Test that minimal valid config passes validation."""
    minimal_config = {
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
    # Should not raise any exception
    _validate_config_schema(minimal_config)