"""Load every month-end snapshot of eligible assets into the SQLite database.

Run from the project root after fetch_collateral:  python -m scripts.build_collateral_db
"""

from scripts.fetch_collateral import SNAPSHOT_DIR
from src.collateral import harmonise, read_snapshot, save_snapshot, snapshot_day
from src.database import DB_PATH, connect


def main():
    connection = connect(DB_PATH)
    total = 0
    for path in sorted(SNAPSHOT_DIR.glob("ea_*")):
        raw = read_snapshot(path)
        table = harmonise(raw, snapshot_day(path))
        total += save_snapshot(connection, table)
        connection.commit()
        print(f"{path.name:<24} {len(raw):>6} rows read  {len(table):>6} kept")
    connection.close()
    print(f"{total:,} asset-month rows stored in eligible_assets")


if __name__ == "__main__":
    main()
