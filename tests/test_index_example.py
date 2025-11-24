import os
import pandas as pd
from flowkit import Sample
from facsforge.core.index import load_index_csv

def test_index_example_data():

    TEST_DIR = os.path.dirname(__file__)
    DATA_DIR = os.path.join(TEST_DIR, "data")

    FCS_PATH = os.path.join(DATA_DIR, "two_cells.fcs")
    CSV_PATH = os.path.join(DATA_DIR, "two_cells.csv")

    assert os.path.exists(FCS_PATH)
    assert os.path.exists(CSV_PATH)

    # Load bulk
    sample = Sample(FCS_PATH)
    df_bulk = sample.as_dataframe(source="raw")
    if isinstance(df_bulk.columns, pd.MultiIndex):
        df_bulk.columns = df_bulk.columns.get_level_values(0)

    # Sanity
    assert df_bulk.shape[0] > 100
    assert "FSC-A" in df_bulk.columns
    assert "SSC (Violet)-A" in df_bulk.columns

    # Load index cells
    df_index = load_index_csv(CSV_PATH)

    # Should contain exactly 2 (true for your example)
    assert len(df_index) == 2

    # Must include EventID
    assert "EventID" in df_index.columns

    # Shared channels should overlap
    common = [c for c in df_index.columns if c in df_bulk.columns]
    assert len(common) > 0
