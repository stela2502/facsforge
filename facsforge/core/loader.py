import yaml
import json
from jsonschema import validate, Draft202012Validator
from pathlib import Path

class FACSForgeConfigError(Exception):
    """Raised when the experiment config is invalid."""
    pass


def flatten_columns(columns):
    """
    A stub that does nothing - just return the columns.
    """
    return columns

def validate_panel_channels(panel_dict, df_columns):
    """
    Ensure that every YAML panel entry matches an existing FCS/CSV channel.
    If not, raise a human-friendly error showing EXACT string matches.
    """
    df_cols = set(df_columns)
    yaml_cols = set(panel_dict.keys())

    missing = yaml_cols - df_cols

    if missing:
        # Build a readable error message
        error_lines = [
            "The following channels defined in your YAML panel are not present",
            "in the FCS/CSV data:",
            ""
        ]

        for c in sorted(missing):
            error_lines.append(f"  - '{c}'")

        error_lines.append("")
        error_lines.append("Available channels are:")
        for c in sorted(df_cols):
            error_lines.append(f"  - '{c}'")

        error_lines.append("")
        error_lines.append("Please copy one of the above exact strings into your YAML.")

        raise ValueError("\n".join(error_lines))

def enrich_panel_with_missing_channels(panel_dict, df_columns):
    """
    Add missing channels to panel_dict with ignore: true.
    Returns a modified panel_dict.
    """
    panel = dict(panel_dict)  # shallow copy

    yaml_cols = set(panel.keys())
    df_cols = set(df_columns)

    missing_cols = sorted(df_cols - yaml_cols)

    for col in missing_cols:
        panel[col] = {
            "fluor": None,
            "role": None,
            "ignore": True
        }

    return panel

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

    for name, cell in data["celltypes"].items():
        g = cell.get("gate", {})
        if isinstance(g.get("min"), list) or isinstance(g.get("max"), list):
            print("🚨 BAD GATE:", name, g)

    # ----- Validate against schema -----
    _validate_schema(data, schema)

    # ----- Additional semantic validation -----
    _validate_panel(data)
    _validate_celltypes(data)
    _validate_parents(data)
    _validate_fluorochromes(data)

    return data

