"""Test of the monthly turnover of the eligible assets list on a tiny invented database."""

import pandas as pd

from scripts.analyse_collateral import turnover
from src.collateral import save_snapshot
from src.database import connect


def snapshot(day, isins, maturities):
    return pd.DataFrame({"snapshot_date": day, "isin": isins, "maturity_date": maturities})


def test_removals_are_split_between_matured_and_still_outstanding(tmp_path):
    connection = connect(tmp_path / "test.db")
    # January: A matures in 2030, B in mid-February, C in 2030
    save_snapshot(connection, snapshot("2025-01-31", ["A", "B", "C"],
                                       ["2030-01-01", "2025-02-15", "2030-01-01"]))
    # February: A is still there, B has matured, C was removed early, D is new
    save_snapshot(connection, snapshot("2025-02-28", ["A", "D"], ["2030-01-01", "2031-01-01"]))
    result = turnover(connection).iloc[0]
    assert result["added"] == 1                    # D
    assert result["removed"] == 2                  # B and C
    assert result["removed_before_maturity"] == 1  # only C