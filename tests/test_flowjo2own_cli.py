import os
import subprocess
import tempfile
import pytest

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
    wsp_path = os.path.join(test_dir, "data", "01-Jun-2021.wsp")

    # Ensure the test wsp file exists
    assert os.path.exists(wsp_path), f"Missing test file: {wsp_path}"

    # Temporary output file
    with tempfile.TemporaryDirectory() as tmp:
        out_yaml = os.path.join(tmp, "out.yaml")

        # Call the CLI via subprocess to mimic real-world usage
        result = subprocess.run(
            ["facsforge", "flowjo2own ", wsp_path, "-o", out_yaml],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # Output just for debugging when tests fail
        print("STDOUT:", result.stdout)
        print("STDERR:", result.stderr)

        # CLI call should not crash
        assert result.returncode == 0, "facsforge flowjo2own crashed"

        # The output YAML file should be created
        assert os.path.exists(out_yaml), "Output YAML was not created"

        # YAML should not be empty
        with open(out_yaml) as f:
            content = f.read().strip()
            assert len(content) > 0, "Output YAML is empty"
