import os
import subprocess
import tempfile
import pytest
from facsforge.core.loader import load_experiment
import sys

def test_flowjo2own_cli_runs():
    """
    This test verifies that the CLI command:

        facsforge flowjo2own <file.wsp>

    - accepts the WSP path
    - does not fail with argument parsing errors
    - produces an output YAML file
    """

    # Path to sample wsp test file inside the test directory
    test_dir = os.path.dirname(__file__)
    wsp_path = os.path.join(test_dir, "data", "AnalysisForE2-E3-Bioinformatics.wsp")

    # Ensure the test wsp file exists
    assert os.path.exists(wsp_path), f"Missing test file: {wsp_path}"

    out_yaml = os.path.join(test_dir, "data","out", "two_cells.yaml")

    # Call the CLI via subprocess to mimic real-world usage
    result = subprocess.run(
        [sys.executable, "-m", "facsforge.cli.main",
    "flowjo9_to_facsforge", "--wsp", wsp_path, "--out", out_yaml],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    # -----------------------------------------
    # CLI must work
    # -----------------------------------------
    assert result.returncode == 0, "CLI invocation failed"

    # -----------------------------------------
    # Output must exist
    # -----------------------------------------
    assert os.path.exists(out_yaml), "YAML output file was not created"

    # -----------------------------------------
    # YAML must not be empty
    # -----------------------------------------
    with open(out_yaml) as f:
        content = f.read().strip()

    assert content, "Generated YAML file is empty"

    # -----------------------------------------
    # YAML must be SEMANTICALLY VALID
    # -----------------------------------------
    load_experiment(out_yaml)
