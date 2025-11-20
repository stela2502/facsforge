import yaml
import json
from jsonschema import validate, Draft202012Validator
from pathlib import Path

class FACSForgeConfigError(Exception):
    """Raised when the experiment config is invalid."""
    pass


def _load_schema():
    """
    Loads the JSON schema from facsforge/config/schema.json.
    """
    schema_path = Path(__file__).resolve().parent.parent / "config" / "schema.json"
    if not schema_path.exists():
        raise FACSForgeConfigError(f"Schema file not found: {schema_path}")
    return json.loads(schema_path.read_text())


def _pretty_schema_error(error):
    """
    Turns raw jsonschema errors into human-readable diagnostics.
    """
    path = " → ".join(str(x) for x in error.absolute_path) or "<root>"
    return (
        f"❌ Schema validation error at '{path}':\n"
        f"   {error.message}\n"
        f"   Validator: {error.validator}\n"
        f"   Problematic value: {error.instance}"
    )


def _validate_schema(data, schema):
    """
    Performs JSON Schema validation using the Draft 2020-12 validator.
    Raises descriptive error messages.
    """
    validator = Draft202012Validator(schema)

    errors = sorted(validator.iter_errors(data), key=lambda e: e.path)
    if errors:
        msg = "\n\n".join(_pretty_schema_error(err) for err in errors)
        raise FACSForgeConfigError(f"Configuration does not match schema:\n\n{msg}")


def _validate_parents(data):
    """
    Ensures that all 'parent' references in celltypes exist.
    """
    celltypes = data.get("celltypes", {})
    valid_parents = set(celltypes.keys()) | {None}

    for ct_name, ct_def in celltypes.items():
        parent = ct_def.get("parent")
        if parent is None:
            continue
        if parent not in celltypes:
            raise FACSForgeConfigError(
                f"❌ Celltype '{ct_name}' specifies parent '{parent}', "
                f"but no such parent exists in 'celltypes'."
            )


def _validate_panel(data):
    """
    Ensures that panel channel names are unique.
    """
    panel = data.get("panel", {})
    if not isinstance(panel, dict):
        raise FACSForgeConfigError("❌ 'panel' must be a mapping of channel names → metadata.")

    seen = set()
    for channel in panel:
        if channel in seen:
            raise FACSForgeConfigError(f"❌ Duplicate panel channel found: {channel}")
        seen.add(channel)


def _validate_celltypes(data):
    """
    Ensures each celltype name is unique and sensible.
    """
    cts = data.get("celltypes", {})
    if not isinstance(cts, dict):
        raise FACSForgeConfigError("❌ 'celltypes' must be a mapping of cell type names → rules.")

    for name, body in cts.items():
        if not isinstance(body, dict):
            raise FACSForgeConfigError(
                f"❌ Celltype '{name}' must have a dictionary as its definition."
            )

def _validate_fluorochromes(data):
    """
    Ensures that each fluorochrome is used at most once.
    Biological constraint:
      Two antibodies using the same fluor are generally invalid.
    """
    panel = data.get("panel", {})
    used = {}

    for channel, cfg in panel.items():
        fluor = cfg.get("fluor")
        if fluor is None:
            continue
        if fluor in used:
            raise FACSForgeConfigError(
                f"❌ Duplicate fluorochrome detected: '{fluor}' is used by both "
                f"'{used[fluor]}' and '{channel}'."
            )
        used[fluor] = channel


def load_experiment(config_path):
    """
    Loads and fully validates an experiment YAML file.

    Performs:
      - YAML parsing
      - JSON schema validation
      - parent consistency checks
      - duplicate channel checks
      - duplicate celltype checks

    Returns:
        dict: validated configuration data
    """
    config_path = Path(config_path).resolve()

    if not config_path.exists():
        raise FACSForgeConfigError(f"Config file not found: {config_path}")

    # ----- Load YAML -----
    try:
        with open(config_path, "r") as f:
            data = yaml.safe_load(f)
    except Exception as e:
        raise FACSForgeConfigError(f"❌ Failed to parse YAML file:\n{e}")

    # ----- Load JSON Schema -----
    schema = _load_schema()

    # ----- Validate against schema -----
    _validate_schema(data, schema)

    # ----- Additional semantic validation -----
    _validate_panel(data)
    _validate_celltypes(data)
    _validate_parents(data)
    _validate_fluorochromes(data)

    return data

