"""Tests for src/target.py on a small database with invented values."""

import pandas as pd
import pytest

from src.database import connect, save_observations, save_series
from src.target import annual_sum, build_panel, quarterly_to_monthly, add_changes


def periods(start, values, freq):
    index = pd.period_range(start, periods=len(values), freq=freq)
    return pd.Series(values, index=index, dtype=float)


def as_table(series):
    return pd.DataFrame({"period": series.index.astype(str), "value": series.to_numpy()})


def test_annual_sum_adds_the_last_four_quarters():
    gdp = periods("2020Q1", [1, 2, 3, 4, 5], "Q")
    result = annual_sum(gdp)
    assert result.index.astype(str).tolist() == ["2020Q4", "2021Q1"]
    assert result.tolist() == [10, 14]


def test_each_quarter_is_repeated_in_its_three_months():
    result = quarterly_to_monthly(periods("2020Q1", [10, 20], "Q"))
    assert result.index.astype(str).tolist() == [
        "2020-01", "2020-02", "2020-03", "2020-04", "2020-05", "2020-06"]
    assert result.tolist() == [10, 10, 10, 20, 20, 20]


@pytest.fixture
def connection(tmp_path):
    """A database with three months of invented data for Italy and Germany."""
    connection = connect(tmp_path / "test.db")
    for country, target, yld in [("IT", -100.0, 4.0), ("DE", 300.0, 2.5)]:
        series = {
            f"target_{country}": (periods("2021-01", [target] * 3, "M"), "M"),
            f"yield10y_{country}": (periods("2021-01", [yld] * 3, "M"), "M"),
            f"gdp_{country}": (periods("2020Q2", [250.0] * 4, "Q"), "Q"),
        }
        for series_id, (values, freq) in series.items():
            info = {"flow": "TEST", "key": "key", "description": "", "frequency": freq, "unit": ""}
            save_series(connection, series_id, info)
            save_observations(connection, series_id, as_table(values))
    yield connection
    connection.close()


def test_panel_computes_spread_and_ratio_to_gdp(connection):
    panel = build_panel(connection, countries=["IT", "DE"])
    italy = panel[panel["country"] == "IT"]
    assert italy["month"].astype(str).tolist() == ["2021-01", "2021-02", "2021-03"]
    assert italy["spread"].tolist() == pytest.approx([1.5] * 3)          # 4.0 - 2.5
    assert italy["target_gdp"].tolist() == pytest.approx([-10.0] * 3)    # -100 / 1000 * 100
    assert (panel.loc[panel["country"] == "DE", "spread"] == 0).all()

def test_changes_never_span_two_countries_or_a_gap():
    panel = pd.DataFrame({
        "country": ["IT", "IT", "IT", "ES", "ES"],
        "month": ["2021-01", "2021-02", "2021-04", "2021-01", "2021-02"],  # IT misses March
        "target_gdp": [1.0, 3.0, 4.0, 10.0, 7.0],
        "spread": [1.0, 1.5, 2.0, 1.0, 1.0],
    })
    result = add_changes(panel)
    italy = result[result["country"] == "IT"]["d_target_gdp"].tolist()
    spain = result[result["country"] == "ES"]["d_target_gdp"].tolist()
    assert pd.isna(italy[0]) and italy[1] == 2.0 and pd.isna(italy[2])
    assert pd.isna(spain[0]) and spain[1] == -3.0
