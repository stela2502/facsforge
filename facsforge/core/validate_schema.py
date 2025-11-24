import json
import jsonschema
import os

def load_schema():
    here = os.path.dirname(__file__)
    schema_path = os.path.join(here, "..", "config", "schema.json")
    with open(schema_path, "r") as f:
        return json.load(f)

# Absolute, explicit, direct load of facsforge/config/schema.json
SCHEMA_PATH = os.path.join(
    os.path.dirname(__file__),   # facsforge/core/
    "..",
    "config",
    "schema.json"
)

SCHEMA_PATH = os.path.abspath(SCHEMA_PATH)

if not os.path.exists(SCHEMA_PATH):
    raise RuntimeError(
        f"FATAL ERROR: Could not find FACSForge schema at:\n  {SCHEMA_PATH}"
    )

with open(SCHEMA_PATH, "r") as f:
    SCHEMA = json.load(f)

def validate_config(cfg):
    try:
        jsonschema.validate(cfg, SCHEMA)
    except jsonschema.ValidationError as e:
        raise RuntimeError(f"FACSForge YAML does not match schema:\n{e}")
