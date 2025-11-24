#gernerate_config.py
import yaml
import pandas as pd
from flowkit import Sample
from facsforge.core.loader import flatten_columns

def normalize_channel_name(ch):
    if isinstance(ch, tuple):
        return ch[0]
    return str(ch)

def cmd_generate_config(fcs_file, output):
    sample = Sample(fcs_file)
    df = sample.as_dataframe(source="raw")
    columns = flatten_columns(df)

    # Basic skeleton
    config = {
        "metadata": {
            "experiment_name": fcs_file,
            "operator": None,
            "date": None,
            "notes": ""
        },
        "panel": {},
        "ignore_markers": [],
        "compensation": {"source": "none"},
        "celltypes": {},
        "celltypes_of_interest": [],
        "umap": {"enabled": False}
    }

    # Add all channels as ignore
    for ch in columns:
        key = normalize_channel_name(ch)
        config["panel"][key] = {
            "fluor": None,
            "role": None,
            "ignore": True
        }

    with open(output, "w") as f:
        yaml.dump(config, f)

    print(f"Wrote config to {output}")
    