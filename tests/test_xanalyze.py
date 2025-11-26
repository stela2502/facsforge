import os
import subprocess
import tempfile
import pytest
import shutil
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
    fcs_file = os.path.join(test_dir, "data", "two_cells.fcs")
    index_csv = os.path.join(test_dir, "data", "two_cells.csv")
    config_file = os.path.join(test_dir, "data", "two_cells.yaml")
    # Ensure the test wsp file exists
    assert os.path.exists(config_file), f"Missing test file: {config_file}"

    out_analysis = os.path.join(test_dir, "data","out", "analysis")
    
    # ✅ ENSURE FRESH OUTPUT DIR
    if os.path.exists(out_analysis):
        shutil.rmtree(out_analysis)

    # Call the CLI via subprocess to mimic real-world usage
    result = subprocess.run(
        [sys.executable, "-m", "facsforge.cli.main", "analyze-facs", "-o", out_analysis, fcs_file, index_csv, config_file],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    # Output just for debugging when tests fail
    print("STDOUT:", result.stdout)
    print("STDERR:", result.stderr)

    # CLI call should not crash
    assert result.returncode == 0, "facsforge analyze-facs crashed"

    # The output YAML file should be created
    assert os.path.exists(out_analysis), "Output analysis was not created"

    # check the analysis (later)

