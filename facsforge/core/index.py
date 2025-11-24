#index.py

import pandas as pd
import numpy as np
import re

def detect_event_column(df):
    candidates = [c for c in df.columns if re.match(r"event|event[_ ]?id|index", c.lower())]
    if not candidates:
        raise ValueError("❌ No EventID column found in index CSV")
    return candidates[0]


def load_index_csv(path):
    """
    Load a BD S8 index CSV.
    The file contains metadata followed by the real CSV table.
    We detect the header ("Well,...") and parse from there.
    """

    # Detect header line
    header_line = None
    with open(path, "r") as f:
        for i, line in enumerate(f):
            if line.startswith("Well,"):
                header_line = i
                break

    if header_line is None:
        raise ValueError(f"Could not find BD S8 header ('Well,') in {path}")

    # Read CSV starting from the header line
    df = pd.read_csv(path, skiprows=header_line)

    # Normalize column names: remove spaces
    df.columns = [c.strip().replace(" ", "") for c in df.columns]

    # Detect Event or EventIndex column
    event_col = None
    for c in df.columns:
        if re.fullmatch(r"Event|EventID|EventIndex", c, flags=re.IGNORECASE):
            event_col = c
            break

    if event_col is None:
        raise ValueError(f"No EventID or Event column found in {path}")

    # Rename to EventID
    df = df.rename(columns={event_col: "EventID"})

    # Convert EventID to int
    df["EventID"] = pd.to_numeric(df["EventID"], errors="coerce").astype("Int64")

    # Remove empty rows (BD S8 writes zeros for missed wells)
    numeric = df.select_dtypes(include=[np.number]).columns
    zero_mask = (df[numeric].fillna(0) == 0).all(axis=1)
    removed = zero_mask.sum()
    df = df.loc[~zero_mask].copy()

    print(f"Loaded index CSV {path}: {len(df)} rows, removed {removed} zero rows.")

    return df


def merge_index_with_fcs(fcs_df, index_df):
    merged = fcs_df.merge(index_df, on="EventID", how="inner")
    return merged


def check_well_conflicts(index_df):
    conflicts = index_df["Well"].value_counts()
    conflicts = conflicts[conflicts > 1]
    return conflicts