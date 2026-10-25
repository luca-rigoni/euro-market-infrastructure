"""Store the downloaded series in a local SQLite database."""

import sqlite3
import pandas as pd
from pathlib import Path

DB_PATH = Path("data/processed/ea_macro.db")

SCHEMA = """
    CREATE TABLE IF NOT EXISTS series (
        series_id   TEXT PRIMARY KEY,
        source      TEXT NOT NULL,
        key         TEXT NOT NULL,
        description TEXT,
        frequency   TEXT NOT NULL,
        unit        TEXT
    );
    CREATE TABLE IF NOT EXISTS observations (
        series_id   TEXT NOT NULL,
        period      TEXT NOT NULL,
        value       REAL NOT NULL,
        PRIMARY KEY (series_id, period),
        FOREIGN KEY (series_id) REFERENCES series(series_id)
    );
"""

def connect(path):
    """Connect to the SQLite database at the given path and create tables if they don't exist."""
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    return conn


def save_series(connection, series_id, info):
    """Insert the metadata of a series, or update it if it already exists."""
    connection.execute(
        """
        INSERT INTO series (series_id, source, key, description, frequency, unit)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT (series_id) DO UPDATE SET
            source = excluded.source,
            key = excluded.key,
            description = excluded.description,
            frequency = excluded.frequency,
            unit = excluded.unit
        """,
        (
            series_id, 
            "ECB",
            f"{info['flow']}.{info['key']}",
            info["description"],
            info["frequency"],
            info["unit"],
        ),
    )


def save_observations(connection, series_id, data):
    """Insert the observations of a series; existing periods are overwritten."""

    rows = [
        (series_id, period, value)
        for period, value in zip(data["period"], data["value"])
    ]
    connection.executemany(
        """
        INSERT INTO observations (series_id, period, value)
        VALUES (?, ?, ?)
        ON CONFLICT (series_id, period) DO UPDATE SET
            value = excluded.value
        """,
        rows,
    )
    return len(rows)

def load_series(connection, series_id):
    """Load the observations of a series from the database."""
    query = """
        SELECT period, value
        FROM observations
        WHERE series_id = ?
        ORDER BY period
    """
    df = pd.read_sql_query(query, connection, params=(series_id,))
    return df


if __name__ == "__main__":
    from src.download import SERIES, fetch_series

    connection = connect("data/processed/test.db")

    # Data download.py, obtains the latest data for the HICP series
    hicp_info = SERIES["hicp"]
    hicp_data = fetch_series(hicp_info["flow"], hicp_info["key"])

    # Saves the series metadata and observations into the database
    save_series(connection, "hicp", hicp_info)
    save_observations(connection, "hicp", hicp_data)

    # confirms that the data has been saved
    connection.commit()

    # prints the number of observations saved for the HICP series
    print("DB observations count:")
    print(
        connection.execute("SELECT COUNT(*) FROM observations").fetchone()
    )

    print ("\nLast 5 months read from DB:")
    print(load_series(connection, "hicp").tail())

    # closes the database connection
    connection.close()