from __future__ import annotations
import pytest
from pathlib import Path
from src.config.loader import load_config, ConfigError


def test_load_config_success(write_config: Path):
    cfg = load_config(write_config)
    assert cfg.source_directory == "./data"
    assert cfg.timezone == "UTC"
    assert "Customers" in cfg.sheet_mappings
    assert cfg.sequences.get("id") == "customers_id_seq"


def test_load_config_missing_file(temp_workdir: Path):
    missing = temp_workdir / "config" / "not_exists.yml"
    with pytest.raises(ConfigError):
        load_config(missing)


def test_load_config_missing_required(write_config: Path):
    # remove required key
    text = write_config.read_text(encoding="utf-8").replace("fk_propagations:\n  customer_id: id\n", "")
    write_config.write_text(text, encoding="utf-8")
    with pytest.raises(ConfigError) as e:
        load_config(write_config)
    assert "config validation failed" in str(e.value) and "required property" in str(e.value)


def test_load_config_invalid_sheet_mapping(write_config: Path):
    # create invalid sheet mapping (missing required 'table' key)
    text = write_config.read_text(encoding="utf-8").replace(
        "  Customers:\n    table: customers\n    sequence_columns: [id]",
        "  Customers:\n    sequence_columns: [id]"
    )
    write_config.write_text(text, encoding="utf-8")
    with pytest.raises(ConfigError) as e:
        load_config(write_config)
    assert "config validation failed" in str(e.value)


def test_load_config_extra_field(write_config: Path):
    # add extra field that should be rejected by additionalProperties: false
    text = write_config.read_text(encoding="utf-8") + "\nextra_field: not_allowed\n"
    write_config.write_text(text, encoding="utf-8")
    with pytest.raises(ConfigError) as e:
        load_config(write_config)
    assert "config validation failed" in str(e.value)
