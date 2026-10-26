"""Download every series of the project and store it in the SQLite database.

Run from the project root:  python -m scripts.build_database
"""

from src.database import DB_PATH, connect, save_observations, save_series
from src.download import SERIES, fetch_series


def main():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = connect(DB_PATH)
    for series_id, info in SERIES.items():
        data = fetch_series(info["flow"], info["key"])
        save_series(connection, series_id, info)
        saved = save_observations(connection, series_id, data)
        print(f"{series_id:<14} {saved:>4} observations saved")
    connection.commit()  # write everything to disk at the end
    connection.close()


if __name__ == "__main__":
    main()
