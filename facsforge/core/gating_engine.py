import numpy as np
import pandas as pd
from pathlib import Path

import flowkit as fk
from flowkit._models.gates import *
# flowutils and fcsparser available for extensions later
from flowkit import Dimension

from facsforge.core.thresholds import compute_auto_thresholds
from facsforge.core.transforms import prepare_markers
from facsforge.utils.logging import log_info, log_warn, log_error

from .index import load_index_csv, merge_index_with_fcs, check_well_conflicts

import warnings

## for the plotting
import matplotlib.pyplot as plt
import re

def safe_filename(s: str) -> str:
    """
    Make string filesystem-safe:
    - Replace spaces with _
    - Remove or replace unsafe characters (*, /, \, :, ?, etc.)
    """
    s = s.strip()
    s = s.replace(" ", "_")
    # Keep only: letters, numbers, underscore, dash, dot
    s = re.sub(r"[^A-Za-z0-9._-]", "_", s)
    # Collapse multiple underscores
    s = re.sub(r"_+", "_", s)
    return s

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
        return sample.get_events(source="raw"), sample.channels

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

def _normalize_channel(ch):
    return ch.replace(" (SW-unmix)", "").strip()

def _strip_front_progressively(name):
    """
    Generates candidates by stripping leftmost tokens:
    'E.coli Lysosom Alexa Fluor 488-A' ->
      'Lysosom Alexa Fluor 488-A'
      'Alexa Fluor 488-A'
      'Fluor 488-A'
      '488-A'
    """
    parts = name.split()
    return [" ".join(parts[i:]) for i in range(1, len(parts))]

def _validate_channels(df, channels):
    """
    Validates channel existence and returns Vec<Dimension>.
    Rust-equivalent: fn validate_channels(...) -> Vec<Dimension>
    """
    dims = []

    for ch in channels:
        # 1) exact match
        if ch in df.columns:
            dims.append(Dimension(ch))
            continue

        # 2) strip '(SW-unmix)' and retry
        ch2 = _normalize_channel(ch)
        if ch2 in df.columns:
            print(f"[FACSForge] Channel normalized: '{ch}' -> '{ch2}'")
            dims.append(Dimension(ch2))
            continue
        # 3. Progressive strip from front
        for candidate in _strip_front_progressively(ch2):
            if candidate in df.columns:
                print(f"[FACSForge] Channel reduced: '{ch}' -> '{candidate}'")
                dims.append(Dimension(candidate))
                break
        else: #only runs if for did not break
            # 3) fail loudly and honestly
            raise RuntimeError(
                f"Missing FCS channel: {ch}\n"
                f"Available: {list(df.columns)}"
            )

    return dims

def _apply_gate(df, gate_def, gate_name):
    """
    Executes a gate definition (polygon, rectangle, threshold).
    """
    gtype = gate_def["type"]
    df.columns = [c[1] if isinstance(c, tuple) else c for c in df.columns]

    # ------------------------------------------------------------------
    # POLYGON GATE
    # ------------------------------------------------------------------
    if gtype == "polygon":
        channels = gate_def["channels"]
        dims = _validate_channels(df,channels)

        vertices = gate_def["vertices"]

        gate = PolygonGate(
            gate_name=gate_name,
            dimensions=dims,
            vertices=vertices
        )

        mask = gate.apply(df)
        return df[mask]

    # ------------------------------------------------------------------
    # RECTANGLE GATE
    # ------------------------------------------------------------------
    if gtype == "rectangle":
        channels = gate_def["channels"]
        dims = _validate_channels(df, channels)
        ch1, ch2 = channels

        vertices = gate_def["vertices"]

        g = RectangleGate(
            gate_name=gate_name,
            dimensions=dims,
            x_min=min(v[0] for v in vertices),
            x_max=max(v[0] for v in vertices),
            y_min=min(v[1] for v in vertices),
            y_max=max(v[1] for v in vertices),
        )

        mask = g.gate(df)
        return df[mask]

    # ------------------------------------------------------------------
    # THRESHOLD GATE
    # ------------------------------------------------------------------
    if gtype == "threshold":
        ch = gate_def["channel"]
        _validate_channels([ch])

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

def _apply_compensation(sample, experiment):
    try:
        return sample.get_events(), sample.channels
    except AttributeError:
        return sample.get_events(source="raw"), sample.channels

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

def _plot_population(sub_df, gate_def, name, outdir):
    """
    Create a plot for a gated population and save it as PNG.

    gate_def: dict with at least 'type' and either 'channels' or 'channel'.
    name: population name (string).
    outdir: pathlib.Path
    """
    gtype = gate_def.get("type")
    fig, ax = plt.subplots()

    if gtype in ("polygon", "rectangle"):
        ch1, ch2 = gate_def["channels"]
        if ch1 not in sub_df.columns or ch2 not in sub_df.columns:
            # Fallback: don't crash plotting if something is off
            plt.close(fig)
            return

        ax.scatter(sub_df[ch1], sub_df[ch2], s=2)
        ax.set_xlabel(ch1)
        ax.set_ylabel(ch2)
        ax.set_title(f"{name}: {gtype} gate on {ch1} vs {ch2}")

        fname = outdir / f"gated_{name}_{ch1}_vs_{ch2}.png"

    elif gtype == "threshold":
        ch = gate_def["channel"]
        if ch not in sub_df.columns:
            plt.close(fig)
            return

        ax.hist(sub_df[ch], bins=100)
        ax.set_xlabel(ch)
        ax.set_ylabel("Count")
        ax.set_title(f"{name}: threshold gate on {ch}")

        fname = outdir / f"gated_{name}_{ch}_hist.png"

    else:
        # Unknown gate type – optional fallback: FSC vs SSC if available
        if "FSC-A" in sub_df.columns and "SSC (Imaging)-A" in sub_df.columns:
            ax.scatter(sub_df["FSC-A"], sub_df["SSC (Imaging)-A"], s=2)
            ax.set_xlabel("FSC-A")
            ax.set_ylabel("SSC (Imaging)-A")
            ax.set_title(f"{name}: FSC vs SSC (fallback)")
            fname = outdir / f"gated_{name}_FSC_vs_SSC.png"
        else:
            plt.close(fig)
            return

    fig.tight_layout()
    fig.savefig(fname, dpi=150)
    plt.close(fig)

def _find_well_column(df):
    for k in ("Well", "well", "WELL", "RowCol", "rowcol"):
        if k in df.columns:
            return k
    return None

_SCATTER_RE = re.compile(
    r"""
    (
        FSC |
        SSC |
        TIME
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)


def scale_info(name: str):
    if _SCATTER_RE.search(name) is not None:
        return False, name         # scatter → linear
    else:
        return True, f"{name} (scaled)"  # fluorescence → logicle


def _plot_nice_population(
    parent_df,
    sub_df,
    index_df,
    gate_def,
    name,
    outdir,
    density=False,
    logicle=True,
):
    """
    Matplotlib + logicle (biexponential) cytometry plotting.
    Produces FlowJo-like scaling with parent background + gated + index overlays.
    """
    # Global flags / handles
    _HAS_LOGICLE = False
    _logicle = None

    # ----------------------------------
    # Lazy import for logicle
    # ----------------------------------
    try:
        from flowutils import logicle_c as _logicle      
        # Figure out the callable inside the module (works across flowutils versions)
        if hasattr(_logicle, "logicle"):
            _logicle = _logicle.logicle
        elif hasattr(_logicle, "logicle_transform"):
            _logicle = _logicle.logicle_transform
        elif hasattr(_logicle, "logicle_scale"):
            _logicle = _logicle.logicle_scale
        else:
            raise ImportError("flowutils.logicle_c has no callable logicle function")
        _HAS_LOGICLE = True
    except Exception as e:
        _HAS_LOGICLE = False
        _logicle = None
        print(f"[FACSForge] flowutils.logicle_c not available — falling back to linear axes: {e}")


    # ----------------------------------
    # Transform helper
    # ----------------------------------
    def _xform(x, cn):
        x = np.asarray(x, dtype=float)
        if (_logicle is not None and _HAS_LOGICLE) and scale_info(cn)[0] :
            # Auto-parameters give robust behavior without manual tuning
            # FlowJo-like defaults (safe starting values)
            T = 262144.0   # top of scale (~18-bit)
            W = 0.5        # linear width around zero
            M = 4.5        # decades
            A = 0.0        # linearization

            return _logicle(T, W, M, A, x)
            #return _logicle(x)
        return x

    # ----------------------------------
    # Channels from gate
    # ----------------------------------
    gate = gate_def.get("gate", {})
    channels = gate.get("channels")

    if not channels or len(channels) != 2:
        print(f"[FACSForge] Skipping plot for {name} — not a 2D gate.")
        return

    ch1, ch2 = _validate_channels(parent_df, channels)
    ch1 = ch1.id
    ch2 = ch2.id

    try:
        ch_idx_1, ch_idx_2 = _validate_channels(index_df, channels)
        ch_idx_1 = ch_idx_1.id
        ch_idx_2 = ch_idx_2.id
        index = index_df.dropna()
        well_col = _find_well_column(index)
        if well_col:
            wells = index[well_col].astype(str).values
        else:
            wells = None
            print("[FACSForge] Index overlay has no well column")
    except RuntimeError as e:
        print(f"[FACSForge] WARNING: {e}")
        ch_idx_1 = ch_idx_2 = None
        index = None


    print(f"Plotting subset {name} and columns {ch1} + {ch2} ")

    # ----------------------------------
    # Output path
    # ----------------------------------
    out_file = outdir / safe_filename(f"{name}_{ch1}_{ch2}.png")

    # ----------------------------------
    # Prepare data (drop invalid rows)
    # ----------------------------------
    parent = parent_df[[ch1, ch2]].dropna()
    gated = sub_df[[ch1, ch2]].dropna()
    
    # ----------------------------------
    # Apply transform
    # ----------------------------------
    Xp = _xform(parent[ch1].values, ch1)
    Yp = _xform(parent[ch2].values, ch2)

    Xg = _xform(gated[ch1].values, ch1)
    Yg = _xform(gated[ch2].values, ch2)

    # --------------------------
    # APPLY TRANSFORM TO INDEX
    # --------------------------
    if (
        index is not None
        and not index.empty
        and ch_idx_1 in index.columns
        and ch_idx_2 in index.columns
    ):
        Xi = _xform(index[ch_idx_1].values, ch_idx_1)
        Yi = _xform(index[ch_idx_2].values, ch_idx_2)
    else:
        if index is not None:
            missing = [c for c in (ch1, ch2) if c not in index.columns]
            if missing:
                print(f"[FACSForge] Index overlay skipped for {name} — missing columns: {missing}")
        Xi = Yi = None

    # ----------------------------------
    # Create plot
    # ----------------------------------
    fig, ax = plt.subplots(figsize=(6, 5))

    # Background (parent)
    ax.scatter(
        Xp, Yp,
        s=3,
        c="#1f1f1f",
        alpha=0.30,
        linewidths=0,
        label="Parent",
        zorder=1,
    )

    # Gated
    ax.scatter(
        Xg, Yg,
        s=6,
        c="dodgerblue",
        alpha=0.95,
        linewidths=0,
        label="Gated",
        zorder=3,
    )

    # Index overlay
    if Xi is not None:
        ax.scatter(
            Xi, Yi,
            s=5,
            c="crimson",
            edgecolors="black",
            linewidths=0.7,
            label="Index",
            zorder=4,
        )
    # ----------------------------------
    # Annotate wells at index positions
    # ----------------------------------
    if wells is not None:
        for x, y, w in zip(Xi, Yi, wells):
            ax.text(
                x, y,
                w,
                fontsize=9,
                weight="bold",
                color="black",
                ha="left",
                va="bottom",
                zorder=5,
                bbox=dict(
                    boxstyle="round,pad=0.2",
                    facecolor="white",
                    alpha=0.75,
                    edgecolor="none"
                )
            )

    # ----------------------------------
    # Cosmetics
    # ----------------------------------
    ax.set_title( name )
    ax.set_xlabel( scale_info(ch1)[1] )
    ax.set_ylabel( scale_info(ch2)[1] )

    # Optional density look (cheap KDE via rasterization)
    if density:
        ax.set_rasterized(True)

    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(out_file, dpi=200)
    plt.close(fig)

    print(f"[FACSForge] Wrote plot → {out_file}")

def run_gating_pipeline(fcs_path, index_csv, experiment, outdir):
    """
    Main entry point for the FACSForge gating engine.
    Produces:
      - gated populations (CSV)
      - thresholds.json (future)
    """

    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    

    # -------------------------------------------------------
    # 1. Load files (FCS + index)
    # -------------------------------------------------------
    log_info(f"Loading FCS file: {fcs_path}")
    sample = fk.Sample(str(fcs_path))
    overlay = load_index_csv( index_csv )

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
    # 5. Export gated subsets + plots
    # -------------------------------------------------------
    for name, sub in populations.items():
        dest = outdir / f"gated_{name}.csv"
        sub.to_csv(dest, index=False)
        log_info(f"Wrote {len(sub)} events → {dest}")

        # Look up gate definition
        gate_def = experiment.get("celltypes", {}).get(name)
        if gate_def is None:
            continue

        # Identify parent population (if any)
        parent_name = gate_def.get("parent")
        parent_df = populations.get(parent_name, df)

        # Call overlay plotter
        _plot_nice_population(
            parent_df=parent_df,
            sub_df=sub,
            index_df=overlay,
            gate_def=gate_def,
            name=name,
            outdir=outdir
        )

        log_info(f"Wrote overlay plot for {name} → {outdir}")


    return populations

def merge_fcs_files(fcs_paths):
    """
    Load and merge multiple FCS files into one DataFrame.
    Adds sample_id column.
    """
    all_dfs = []

    for fcs in fcs_paths:
        name = Path(fcs).stem
        sample = fk.Sample(fcs)

        df = pd.DataFrame(
            sample.get_events(),
            columns=sample.channels
        )

        df["sample_id"] = name
        df["__fcs_file"] = str(fcs)   # optional safety metadata

        all_dfs.append(df)

    merged = pd.concat(all_dfs, axis=0, ignore_index=True)

    return merged

def run_gating_pipeline_multi(fcs_paths, index_csvs, experiment, outdir):
    """
    Runs gating on multiple FCS files and merges populations.
    """  

    warnings.warn(
        "run_gating_pipeline_multi(): This function ANALYZES FIRST and MERGES LATER.\n"
        "For MERGE FIRST → ANALYZE LATER behavior, use run_gating_pipeline_merged().",
        UserWarning,
        stacklevel=2
    )

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

def run_gating_pipeline_merged(fcs_paths, index_csvs, experiment, outdir):
    """
    Merge all FCS first, then run gating once.
    """
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    print("[FACSForge] Merging FCS files…")
    merged_df = merge_fcs_files(fcs_paths)

    print("[FACSForge] Running gating on merged data…")
    pops = run_gating_pipeline_dataframe(merged_df, experiment, outdir)

    return pops