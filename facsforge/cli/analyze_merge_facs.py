# analyze_merge_facs.py

from facsforge.core.loader import load_experiment
from facsforge.core.gating_engine import run_gating_pipeline_merged
import os


def cmd_analyze_merge_facs(fcs_files, config_file, index_csv, outdir):
    """
    Merge FCS files first, then analyze as one experiment.
    """
    os.makedirs(outdir, exist_ok=True)

    experiment = load_experiment(config_file)

    print("[FACSForge] Merge-first mode enabled.")
    print(f"[FACSForge] Input files ({len(fcs_files)}):")
    for f in fcs_files:
        print("   ", f)

    run_gating_pipeline_merged(fcs_files, index_csv, experiment, outdir)

    print(f"[FACSForge] Merge analysis complete. Output at: {outdir}")