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

    # --------------------------
    # EXPECTED OUTPUT FILES
    # --------------------------

    expected_csv = {
        "gated_Cells.csv": 3306,
        "gated_Erythrocytes.csv": 15,
        "gated_Leukocytes.csv": 1,
        "gated_Leukocytes2.csv": 1,
        "gated_Leukocytes3.csv": 8,
        "gated_Particles.csv": 1,
        "gated_Phagocytosis 1.csv": 218,
        "gated_Phagocytosis 2.csv": 33,
        "gated_Single Cells (FSC).csv": 2477,
        "gated_Single Cells (Imaging).csv": 2179,
        "gated_Single Cells (SSC).csv": 2717,
        "gated_no uptake.csv": 1549,
    }

    expected_png = [
        "Particles_FSC-A_Total_Intensity_SSC_Imaging_.png",
        "Leukocytes2_FSC-A_Total_Intensity_SSC_Imaging_.png",
        "Single_Cells_SSC_SSC_Violet_-H_SSC_Violet_-A.png",
        "Cells_FSC-A_SSC_Violet_-A.png",
        "Leukocytes3_FSC-A_Total_Intensity_SSC_Imaging_.png",
        "Single_Cells_FSC_FSC-A_FSC-H.png",
        "Single_Cells_Imaging_Eccentricity_FSC_Radial_Moment_FSC_.png",
        "Erythrocytes_FSC-A_Total_Intensity_SSC_Imaging_.png",
        "Phagocytosis_1_Alexa_Fluor_488-A_eF780-right_-A.png",
        "Phagocytosis_2_Alexa_Fluor_488-A_eF780-right_-A.png",
        "Leukocytes_FSC-A_Total_Intensity_SSC_Imaging_.png",
        "no_uptake_Alexa_Fluor_488-A_eF780-right_-A.png",
    ]

    # --------------------------
    # CSV FILE VALIDATION
    # --------------------------
    import pandas as pd

    for fname, expected_rows in expected_csv.items():
        csv_path = os.path.join(out_analysis, fname)
        assert os.path.exists(csv_path), f"Missing CSV output: {fname}"

        df = pd.read_csv(csv_path)
        assert len(df) == expected_rows, (
            f"{fname}: expected {expected_rows} rows, got {len(df)}"
        )

    # --------------------------
    # PNG FILE VALIDATION
    # --------------------------

    for fname in expected_png:
        p = os.path.join(out_analysis, fname)
        assert os.path.exists(p), f"Missing PNG output: {fname}"
        assert os.path.getsize(p) > 1000, f"{fname} is suspiciously small (broken image)"