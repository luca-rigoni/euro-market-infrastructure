"""Build the country-month panel of TARGET balances, GDP and sovereign spreads.

For each country and month the panel contains:
    target      TARGET balance of the national central bank (EUR millions, end of month)
    gdp         nominal GDP over the last four quarters (EUR millions)
    target_gdp  TARGET balance in percent of GDP
    yield10y    10-year government bond yield (percent)
    spread      yield10y minus the German yield (percentage points)
"""

import pandas as pd

from src.database import load_series
from src.download import COUNTRIES

BENCHMARK = "DE"  # spreads are measured against German government bonds


def load_periods(connection, series_id, freq):
    """Load one series from the database as values indexed by period (monthly or quarterly)."""
    data = load_series(connection, series_id)
    index = pd.PeriodIndex(data["period"], freq=freq)
    return pd.Series(data["value"].to_numpy(), index=index, name=series_id)


def annual_sum(quarterly):
    """Sum of the last four quarters, so that GDP is measured over a full year."""
    return quarterly.rolling(4).sum().dropna()


def quarterly_to_monthly(quarterly):
    """Repeat the value of each quarter in its three months."""
    months = pd.period_range(
        quarterly.index[0].asfreq("M", how="start"),
        quarterly.index[-1].asfreq("M", how="end"),
        freq="M",
    )
    quarter_of_each_month = months.asfreq("Q")
    return pd.Series(quarterly.reindex(quarter_of_each_month).to_numpy(), index=months)


def country_panel(connection, country):
    """Build the monthly panel rows of one country (only months where every variable exists)."""
    target = load_periods(connection, f"target_{country}", "M")
    yield10y = load_periods(connection, f"yield10y_{country}", "M")
    benchmark = load_periods(connection, f"yield10y_{BENCHMARK}", "M")
    gdp = quarterly_to_monthly(annual_sum(load_periods(connection, f"gdp_{country}", "Q")))

    panel = pd.DataFrame({
        "target": target,
        "gdp": gdp,
        "yield10y": yield10y,
        "spread": yield10y - benchmark,
    }).dropna()
    panel["target_gdp"] = 100 * panel["target"] / panel["gdp"]

    panel.index.name = "month"
    panel = panel.reset_index()
    panel.insert(0, "country", country)
    return panel


def build_panel(connection, countries=COUNTRIES):
    """Stack the panels of all countries into one table (country, month, variables)."""
    return pd.concat([country_panel(connection, c) for c in countries], ignore_index=True)

def add_changes(panel, columns=("target_gdp", "spread")):
    """Add the monthly change of each column (d_target_gdp, d_spread), within each country.

    A change is left missing when the previous row is another country or not the
    previous month (a gap in the data), so that it never spans two countries or months.
    """
    panel = panel.sort_values(["country", "month"]).reset_index(drop=True)
    months = pd.Series(pd.PeriodIndex(panel["month"], freq="M").asi8, index=panel.index)
    consecutive = panel["country"].eq(panel["country"].shift()) & months.diff().eq(1)
    for column in columns:
        panel[f"d_{column}"] = panel[column].diff().where(consecutive)
    return panel

