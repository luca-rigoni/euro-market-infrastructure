"""Build the country-month panel and save it as a CSV for the estimation (Python and Stata).

Run from the project root after build_database:  python -m scripts.build_target_panel
"""

from pathlib import Path

from src.database import DB_PATH, connect
from src.target import build_panel

OUTPUT = Path("data/processed/target_panel.csv")


def main():
    connection = connect(DB_PATH)
    panel = build_panel(connection)
    connection.close()

    panel["month"] = panel["month"].astype(str)  # e.g. 2012-07, readable by Stata and Tableau
    panel.to_csv(OUTPUT, index=False)

    print(f"{len(panel)} rows, {panel['country'].nunique()} countries, "
          f"{panel['month'].min()} to {panel['month'].max()}")
    summary = panel.groupby("country")[["target_gdp", "spread"]].agg(["min", "max"]).round(1)
    print(summary)


if __name__ == "__main__":
    main()
