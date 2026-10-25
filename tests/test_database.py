"""Tests for src/database.py, run on a temporary database that pytest deletes afterwards."""

import sqlite3

import pandas as pd
import pytest

from src.database import connect, load_series, save_observations, save_series

HICP_INFO = {
    "flow": "HICP",
    "key": "M.U2.N.000000.4D0.ANR",
    "description": "HICP inflation, annual rate of change",
    "frequency": "M",
    "unit": "percent",
}


@pytest.fixture
def connection(tmp_path):
    """A fresh database in a temporary folder, with the metadata of one series."""
    connection = connect(tmp_path / "test.db")
    save_series(connection, "hicp", HICP_INFO)
    yield connection
    connection.close()


def monthly(periods, values):
    """A small table with the same columns returned by fetch_series."""
    return pd.DataFrame({"period": periods, "value": values})


def test_both_tables_are_created(connection):
    rows = connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
    assert {"series", "observations"} <= {name for (name,) in rows}


def test_series_metadata_is_stored(connection):
    source, key, frequency = connection.execute(
        "SELECT source, key, frequency FROM series WHERE series_id = 'hicp'"
    ).fetchone()
    assert (source, key, frequency) == ("ECB", "HICP.M.U2.N.000000.4D0.ANR", "M")


def test_observations_are_loaded_in_time_order(connection):
    saved = save_observations(
        connection, "hicp", monthly(["2024-03", "2024-01", "2024-02"], [2.4, 2.8, 2.6])
    )
    data = load_series(connection, "hicp")
    assert saved == 3
    assert data["period"].tolist() == ["2024-01", "2024-02", "2024-03"]
    assert data["value"].tolist() == [2.8, 2.6, 2.4]


def test_revised_values_replace_old_ones(connection):
    save_observations(connection, "hicp", monthly(["2024-01", "2024-02"], [2.8, 2.6]))
    save_observations(connection, "hicp", monthly(["2024-02"], [2.9]))  # a data revision
    data = load_series(connection, "hicp")
    assert data["value"].tolist() == [2.8, 2.9]  # updated, not duplicated


def test_observations_of_an_unknown_series_are_rejected(connection):
    # The foreign key forbids observations for a series that is not in the series table
    with pytest.raises(sqlite3.IntegrityError):
        save_observations(connection, "gdp", monthly(["2024-01"], [1.0]))
