"""Plot the TARGET balances of the national central banks in percent of GDP.

Run from the project root after build_target_panel:  python -m scripts.plot_target
"""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

PANEL = Path("data/processed/target_panel.csv")
FIGURE = Path("figures/target_balances.png")
HIGHLIGHT = ["DE", "IT", "ES", "GR", "IE", "PT"]  # the other countries are drawn in grey


def main():
    panel = pd.read_csv(PANEL)
    panel["month"] = pd.PeriodIndex(panel["month"], freq="M").to_timestamp()
    wide = panel.pivot(index="month", columns="country", values="target_gdp")

    fig, ax = plt.subplots(figsize=(10, 5))
    for country in wide.columns:
        if country in HIGHLIGHT:
            ax.plot(wide.index, wide[country], label=country, linewidth=1.6)
        else:
            ax.plot(wide.index, wide[country], color="lightgrey", linewidth=1)
    ax.axhline(0, color="black", linewidth=0.8)
    ax.axvline(pd.Timestamp("2015-03-01"), color="grey", linestyle="--", linewidth=0.8)
    ax.text(pd.Timestamp("2015-05-01"), ax.get_ylim()[1] * 0.9, "Asset purchases (APP)", fontsize=9)
    ax.set_ylabel("TARGET balance, % of annual GDP")
    ax.set_title("TARGET balances of euro area national central banks")
    ax.legend(ncol=6, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.08))

    FIGURE.parent.mkdir(exist_ok=True)
    fig.savefig(FIGURE, dpi=150, bbox_inches="tight")
    print(f"Saved {FIGURE}")


if __name__ == "__main__":
    main()