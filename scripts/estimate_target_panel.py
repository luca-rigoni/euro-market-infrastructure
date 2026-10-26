"""Estimate how TARGET balances respond to sovereign spreads in a country-month panel.

Model, for country i and month t (Germany excluded, its spread is zero by construction):

    change in TARGET balance (% of GDP)_it = beta * change in spread_it + a_i + g_t + e_it

a_i and g_t are country and month fixed effects: g_t absorbs everything common to all
countries in a month (ECB policy, global shocks), so beta compares countries in the same month.
Standard errors are clustered by country and, as a check, Driscoll-Kraay (robust to
correlation across countries and over time), because 10 clusters are few.

Run from the project root after build_target_panel:  python -m scripts.estimate_target_panel
"""

from pathlib import Path

import pandas as pd
from linearmodels.panel import PanelOLS

from src.target import BENCHMARK, add_changes

PANEL = Path("data/processed/target_panel.csv")
OUTPUT = Path("output/target_panel_results.csv")

SAMPLES = {
    "Full sample": ("2008-06", "2026-06"),
    "Crisis years": ("2008-06", "2014-12"),
    "Asset purchase years": ("2015-01", "2026-06"),
}


def estimate(data):
    """Fit the fixed-effects regression and return the coefficient with both standard errors."""
    data = data.assign(time=pd.PeriodIndex(data["month"], freq="M").to_timestamp())
    data = data.set_index(["country", "time"])
    model = PanelOLS.from_formula("d_target_gdp ~ d_spread + EntityEffects + TimeEffects", data=data)
    clustered = model.fit(cov_type="clustered", cluster_entity=True)
    driscoll_kraay = model.fit(cov_type="kernel")
    return {
        "beta": clustered.params["d_spread"],
        "se_clustered": clustered.std_errors["d_spread"],
        "se_driscoll_kraay": driscoll_kraay.std_errors["d_spread"],
        "observations": int(clustered.nobs),
    }


def main():
    panel = pd.read_csv(PANEL)
    panel = add_changes(panel[panel["country"] != BENCHMARK]).dropna()

    rows = []
    for name, (start, end) in SAMPLES.items():
        sample = panel[(panel["month"] >= start) & (panel["month"] <= end)]
        rows.append({"sample": name, "period": f"{start} to {end}", **estimate(sample)})

    results = pd.DataFrame(rows)
    OUTPUT.parent.mkdir(exist_ok=True)
    results.to_csv(OUTPUT, index=False)
    print(results.round(3).to_string(index=False))


if __name__ == "__main__":
    main()