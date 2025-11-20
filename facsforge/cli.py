import argparse
from facsforge.core.loader import load_experiment
from facsforge.core.gating_engine import run_gating_pipeline

def main():
    parser = argparse.ArgumentParser(description="FACSForge: automated flow cytometry analysis")
    parser.add_argument("fcs_files", nargs="+", help="Input FCS file(s)")
    parser.add_argument("--config", required=True, help="Experiment YAML definition")
    parser.add_argument("--outdir", default="facsforge_output", help="Output directory")
    args = parser.parse_args()

    experiment = load_experiment(args.config)
    run_gating_pipeline(args.fcs_file, experiment, args.outdir)
    print(f"Finished. Results saved to {args.outdir}")
