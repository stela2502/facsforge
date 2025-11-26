#analyze_facs.py
from facsforge.core.loader import load_experiment
from facsforge.core.gating_engine import run_gating_pipeline
import os

def cmd_analyze_facs(fcs_file, config_file, index_csv, outdir):
    os.makedirs(outdir, exist_ok=True)
    experiment = load_experiment(config_file)
    run_gating_pipeline(fcs_file, index_csv, experiment,  outdir)
    print(f"Analysis complete. Output at: {outdir}")