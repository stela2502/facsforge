import pytest
from facsforge.core.loader import load_experiment, FACSForgeConfigError
from pathlib import Path

# -----------------------------
# Test: Valid configuration loads
# -----------------------------
def test_valid_config_loads(data_dir):
    cfg = data_dir / "valid_basic.yaml"
    data = load_experiment(cfg)
    assert "panel" in data
    assert "celltypes" in data
    assert data["celltypes"]["Singlets"]["parent"] is None


# -----------------------------
# Test: Missing required fields
# -----------------------------
def test_missing_panel_fails(data_dir):
    cfg = data_dir / "invalid_missing_panel.yaml"
    with pytest.raises(FACSForgeConfigError):
        load_experiment(cfg)


# -----------------------------
# Test: Schema violation
# -----------------------------
def test_invalid_schema_fails(data_dir):
    cfg = data_dir / "invalid_schema.yaml"
    with pytest.raises(FACSForgeConfigError) as exc:
        load_experiment(cfg)

    # confirm helpful error
    assert "ignore" in str(exc.value)


# -----------------------------
# Test: Parent relationship validation
# -----------------------------
def test_invalid_parent_reference(data_dir):
    cfg = data_dir / "invalid_parent.yaml"
    with pytest.raises(FACSForgeConfigError) as exc:
        load_experiment(cfg)

    assert "parent" in str(exc.value)
    msg = str(exc.value)
    assert "no such parent" in msg.lower()

def test_duplicate_panel_channels_fail(data_dir):
    cfg = data_dir / "invalid_duplicate_panel.yaml"
    with pytest.raises(FACSForgeConfigError):
        load_experiment(cfg)
