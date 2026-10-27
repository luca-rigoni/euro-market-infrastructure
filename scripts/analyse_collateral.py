"""Describe how the Eurosystem collateral list changed over time, from the database.

Outputs (CSV files are also the data sources of the Tableau dashboard):
    output/collateral_composition.csv   eligible assets by month and haircut category
    output/collateral_turnover.csv      assets added and removed each month
    output/collateral_settlement.csv    share of assets settled outside the issuer's country
    figures/collateral_composition.png  and  figures/collateral_turnover.png

Run from the project root after build_collateral_db:  python -m scripts.analyse_collateral
"""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from src.database import DB_PATH, connect

OUTPUT = Path("output")
FIGURES = Path("figures")
CATEGORIES = {"L1A": "I", "L1B": "II", "L1C": "III", "L1D": "IV", "L1E": "V"}


def composition(connection):
    """Number of eligible assets in each haircut category, month by month."""
    query = """
        SELECT snapshot_date, haircut_category, COUNT(*) AS assets
        FROM eligible_assets
        GROUP BY snapshot_date, haircut_category
        ORDER BY snapshot_date, haircut_category
    """
    table = pd.read_sql_query(query, connection)
    table["category"] = table["haircut_category"].map(CATEGORIES).fillna("other")
    return table


def turnover(connection):
    """Assets added to and removed from the list between consecutive month-end snapshots.

    Removals are split between assets that matured and assets removed while still
    outstanding (for example after a downgrade or a change in the eligibility rules).
    """
    dates = [d for (d,) in connection.execute(
        "SELECT DISTINCT snapshot_date FROM eligible_assets ORDER BY snapshot_date")]
    rows = []
    for previous, current in zip(dates, dates[1:]):
        if (pd.Timestamp(current) - pd.Timestamp(previous)).days > 35:
            continue  # not consecutive months (the 2026 archive is missing)
        added = connection.execute("""
            SELECT COUNT(*) FROM eligible_assets AS now
            WHERE now.snapshot_date = ? AND NOT EXISTS (
                SELECT 1 FROM eligible_assets AS before
                WHERE before.snapshot_date = ? AND before.isin = now.isin)
        """, (current, previous)).fetchone()[0]
        removed, removed_before_maturity = connection.execute("""
            SELECT COUNT(*), SUM(before.maturity_date IS NULL OR before.maturity_date > ?)
            FROM eligible_assets AS before
            WHERE before.snapshot_date = ? AND NOT EXISTS (
                SELECT 1 FROM eligible_assets AS now
                WHERE now.snapshot_date = ? AND now.isin = before.isin)
        """, (current, previous, current)).fetchone()
        rows.append({"snapshot_date": current, "added": added, "removed": removed,
                     "removed_before_maturity": removed_before_maturity or 0})
    return pd.DataFrame(rows)


def settlement(connection):
    """Share of assets settled in a CSD located outside the issuer's country of residence."""
    query = """
        SELECT snapshot_date,
               COUNT(*) AS assets,
               AVG(settlement_country <> issuer_country) AS cross_border_share
        FROM eligible_assets
        WHERE settlement_country <> '' AND issuer_country <> ''
        GROUP BY snapshot_date
        ORDER BY snapshot_date
    """
    return pd.read_sql_query(query, connection)


def plot_composition(table):
    wide = table.pivot_table(index="snapshot_date", columns="category", values="assets",
                             aggfunc="sum").fillna(0)
    wide.index = pd.to_datetime(wide.index)
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.stackplot(wide.index, wide.T.to_numpy(), labels=[f"Category {c}" for c in wide.columns])
    ax.set_ylabel("Number of eligible marketable assets")
    ax.set_title("Eurosystem eligible marketable assets by haircut category (month-end)")
    ax.legend(ncol=5, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.08))
    fig.savefig(FIGURES / "collateral_composition.png", dpi=150, bbox_inches="tight")


def plot_turnover(table):
    data = table.assign(date=pd.to_datetime(table["snapshot_date"]))
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.bar(data["date"], data["added"], width=20, label="Added")
    ax.bar(data["date"], -data["removed_before_maturity"], width=20,
           label="Removed before maturity")
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_ylabel("Assets per month")
    ax.set_title("Monthly changes in the list of eligible assets")
    ax.legend(frameon=False)
    fig.savefig(FIGURES / "collateral_turnover.png", dpi=150, bbox_inches="tight")


def main():
    OUTPUT.mkdir(exist_ok=True)
    FIGURES.mkdir(exist_ok=True)
    connection = connect(DB_PATH)
    tables = {
        "composition": composition(connection),
        "turnover": turnover(connection),
        "settlement": settlement(connection),
    }
    connection.close()
    for name, table in tables.items():
        table.to_csv(OUTPUT / f"collateral_{name}.csv", index=False)
    plot_composition(tables["composition"])
    plot_turnover(tables["turnover"])

    totals = tables["composition"].groupby("snapshot_date")["assets"].sum()
    print(f"Snapshots: {len(totals)}, from {totals.index[0]} to {totals.index[-1]}")
    print(f"Eligible assets: {totals.iloc[0]:,} at the start, {totals.iloc[-1]:,} at the end, "
          f"{totals.sum():,} asset-month rows in total")
    by_category = tables["composition"].pivot_table(
        index="snapshot_date", columns="category", values="assets", aggfunc="sum")
    print("\nAssets by category, first and last snapshot:")
    print(by_category.iloc[[0, -1]].to_string())
    print("\nMonths with the most removals before maturity:")
    print(tables["turnover"].nlargest(5, "removed_before_maturity").to_string(index=False))
    print("\nMonths with the most additions:")
    print(tables["turnover"].nlargest(5, "added").to_string(index=False))
    share = tables["settlement"].set_index("snapshot_date")["cross_border_share"]
    print("\nShare settled outside the issuer's country, by year (December or last snapshot):")
    print(share.groupby(share.index.str[:4]).last().round(3).to_string())


if __name__ == "__main__":
    main()
