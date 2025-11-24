import numpy as np
import pandas as pd
from pathlib import Path

import flowkit as fk
from flowkit._models.gates import *
# flowutils and fcsparser available for extensions later

from facsforge.core.thresholds import compute_auto_thresholds
from facsforge.core.transforms import prepare_markers
from facsforge.utils.logging import log_info, log_warn, log_error

from .index import load_index_csv, merge_index_with_fcs, check_well_conflicts


def merge_with_index_data(df_raw, index_paths):
    index_list = []
    for path in index_paths:
        idx = load_index_csv(path)
        index_list.append(idx)
    index_all = pd.concat(index_list, ignore_index=True)

    # Flag conflicts
    conflicts = check_well_conflicts(index_all)
    if len(conflicts) > 0:
        print("⚠️ Well conflicts detected:")
        print(conflicts)

    return index_all
    

def _apply_compensation(sample, experiment):
    """
    Applies compensation based on config.
    """
    comp_cfg = experiment.get("compensation", {"source": "fcs"})

    source = comp_cfg.get("source", "fcs")

    if source == "none":
        log_info("No compensation applied (source: none).")
        return sample.get_events(), sample.channels

    if source == "fcs":
        if not sample.has_comp_matrix:
            log_warn("FCS file does NOT contain a compensation matrix.")
            return sample.get_events(), sample.channels

        log_info("Applying compensation from FCS matrix.")
        comp = sample.apply_compensation()
        return comp, sample.channels

    if source == "file":
        path = comp_cfg.get("path")
        if not path:
            raise ValueError("Compensation source 'file' requires 'path'.")
        log_info(f"Loading compensation matrix from {path}")

        df_mat = pd.read_csv(path, index_col=0)
        comp = sample.apply_compensation(matrix=df_mat.to_numpy())
        return comp, df_mat.columns.to_list()

    raise ValueError(f"Invalid compensation source: {source}")


def _apply_gate(df, gate_def, gate_name):
    """
    Executes a gate definition (polygon, rectangle, threshold).
    """
    gtype = gate_def["type"]

    if gtype == "polygon":
        channels = gate_def["channels"]
        vertices = gate_def["vertices"]

        gate = PolygonGate(
            gate_name=gate_name,
            channels=channels,
            vertices=vertices
        )
        mask = gate.gate(df[channels].to_numpy())
        return df[mask]

    if gtype == "rectangle":
        ch1, ch2 = gate_def["channels"]
        g = RectangleGate(
            gate_name=gate_name,
            channels=[ch1, ch2],
            x_min=min(v[0] for v in gate_def["vertices"]),
            x_max=max(v[0] for v in gate_def["vertices"]),
            y_min=min(v[1] for v in gate_def["vertices"]),
            y_max=max(v[1] for v in gate_def["vertices"])
        )
        mask = g.gate(df[[ch1, ch2]].to_numpy())
        return df[mask]

    if gtype == "threshold":
        ch = gate_def["channel"]
        mn = gate_def.get("min", -np.inf)
        mx = gate_def.get("max", np.inf)
        mask = (df[ch] >= mn) & (df[ch] <= mx)
        return df[mask]

    raise ValueError(f"Unknown gate type: {gtype}")


def _apply_marker_rules(df, rules, thresholds):
    """
    Apply positive/negative marker rules on a DataFrame slice.
    """
    subset = df

    # positives = marker > threshold
    for m in rules.get("positive", []):
        if m not in thresholds:
            log_warn(f" Marker '{m}' has no auto-threshold; skipping.")
            continue
        subset = subset[subset[m] > thresholds[m]]

    # negatives = marker <= threshold
    for m in rules.get("negative", []):
        if m not in thresholds:
            log_warn(f" Marker '{m}' has no auto-threshold; skipping.")
            continue
        subset = subset[subset[m] <= thresholds[m]]

    return subset


def _run_gating_tree(df_raw, experiment):
    """
    Execute hierarchical gating as defined in the YAML.

    Returns:
      dict(celltype_name → gated_df)
    """
    celltypes = experiment["celltypes"]

    # First compute thresholds for all markers
    thresholds = compute_auto_thresholds(df_raw, experiment)
    log_info(f"Computed thresholds for {len(thresholds)} markers.")

    # Store gated subsets
    gated = {}

    # We loop until all nodes are processed
    pending = set(celltypes.keys())
    max_iters = len(pending) + 4

    for _ in range(max_iters):
        if not pending:
            break

        for ct in list(pending):
            cfg = celltypes[ct]
            parent = cfg.get("parent")

            # determine parent dataframe
            if parent is None:
                df_parent = df_raw
            else:
                if parent not in gated:
                    continue  # parent not ready yet
                df_parent = gated[parent]

            # apply geometric gate (if exists)
            if "gate" in cfg:
                gate_def = cfg["gate"]
                df_stage = _apply_gate(df_parent, gate_def, ct)
            else:
                df_stage = df_parent

            # apply positive/negative rules
            df_stage = _apply_marker_rules(df_stage, cfg, thresholds)

            gated[ct] = df_stage
            pending.remove(ct)

    if pending:
        raise RuntimeError(f"Could not resolve gating tree; unresolved: {pending}")

    return gated


def run_gating_pipeline(fcs_path, experiment, outdir):
    """
    Main entry point for the FACSForge gating engine.
    Produces:
      - gated populations (CSV)
      - thresholds.json (future)
    """

    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    # -------------------------------------------------------
    # 1. Load FCS
    # -------------------------------------------------------
    log_info(f"Loading FCS file: {fcs_path}")
    sample = fk.Sample(str(fcs_path))

    # -------------------------------------------------------
    # 2. Compensation
    # -------------------------------------------------------
    events, channels = _apply_compensation(sample, experiment)
    df = pd.DataFrame(events, columns=channels)

    # -------------------------------------------------------
    # 3. Drop ignored markers
    # -------------------------------------------------------
    df = prepare_markers(df, experiment)

    # -------------------------------------------------------
    # 4. Run hierarchical gating
    # -------------------------------------------------------
    populations = _run_gating_tree(df, experiment)

    # -------------------------------------------------------
    # 5. Export gated subsets
    # -------------------------------------------------------
    for name, sub in populations.items():
        dest = outdir / f"gated_{name}.csv"
        sub.to_csv(dest, index=False)
        log_info(f"Wrote {len(sub)} events → {dest}")

    return populations


def run_gating_pipeline_multi(fcs_paths, experiment, outdir):
    """
    Runs gating on multiple FCS files and merges populations.
    """
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    merged_pops = {}

    for fcs in fcs_paths:
        name = Path(fcs).stem
        pops = run_gating_pipeline(fcs, experiment, outdir / name)

        for ct, df in pops.items():
            df = df.copy()
            df["sample_id"] = name

            if ct not in merged_pops:
                merged_pops[ct] = df
            else:
                merged_pops[ct] = pd.concat([merged_pops[ct], df], axis=0)

    return merged_pops
