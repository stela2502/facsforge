import os
import yaml

def merge_configs(base, new):
    """
    Merge two FACSForge YAML dictionaries.
    Values from 'new' override or fill missing entries in 'base'.
    """
    result = dict(base)

    for key, value in new.items():

        # Skip panel here — handled separately
        if key == "panel":
            continue

        # Nested dict: merge recursively
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_configs(result[key], value)
            continue

        # Arrays: extend only if new array is non-empty
        if isinstance(value, list):
            if value:
                result[key] = value
            continue

        # scalars: override if new value is not None
        if value is not None:
            result[key] = value
    
    result["panel"] = merge_panels(
        result.get("panel", {}),
        new.get("panel", {})
    )
    return result

def load_existing_yaml(path):
    if os.path.exists(path):
        with open(path, "r") as f:
            return yaml.safe_load(f) or {}
    return {}

def merge_panels(base_panel, new_panel):
    """
    Merge panel dictionaries.
    - Keep all existing (FlowJo) panel entries.
    - Add new channels from FCS with ignore=True.
    - Do NOT overwrite existing keys.
    """
    merged = dict(base_panel)

    for ch, values in new_panel.items():
        if ch not in merged:
            merged[ch] = values

    return merged