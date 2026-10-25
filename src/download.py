"""Download euro area series from the ECB Data Portal API."""

import io
import pandas as pd
import requests

BASE_URL = "https://data-api.ecb.europa.eu/service/data"

# Euro area countries with data since 2008 (Luxembourg excluded as a financial-centre outlier)
COUNTRIES = ["AT", "BE", "DE", "ES", "FI", "FR", "GR", "IE", "IT", "NL", "PT"]


def country_series(country):
    """Return the three series used for one country."""
    return {
        f"target_{country}": {
            "flow": "TGB",
            "key": f"M.{country}.N.A094T.U2.EUR.E",
            "description": f"TARGET balance of the {country} central bank, end of month",
            "frequency": "M",
            "unit": "EUR millions",
        },
        f"yield10y_{country}": {
            "flow": "IRS",
            "key": f"M.{country}.L.L40.CI.0000.EUR.N.Z",
            "description": f"10-year government bond yield of {country} (convergence criterion)",
            "frequency": "M",
            "unit": "percent per annum",
        },
        f"gdp_{country}": {
            "flow": "MNA",
            "key": f"Q.Y.{country}.W2.S1.S1.B.B1GQ._Z._Z._Z.EUR.V.N",
            "description": f"Nominal GDP of {country}, seasonally and calendar adjusted",
            "frequency": "Q",
            "unit": "EUR millions, current prices",
        },
    }


SERIES = {}
for country in COUNTRIES:
    SERIES.update(country_series(country))

def build_url(flow, key):
    """Return the API address of one series."""
    return f"{BASE_URL}/{flow}/{key}"


def parse_csv(text):
    """Turn the CSV returned by the API into a table with columns period and value."""

    # 1. Read the CSV text received from the API
    df = pd.read_csv(io.StringIO(text))

    # 2. Keep and rename the two columns we need; drop periods without a value
    df = df[["TIME_PERIOD", "OBS_VALUE"]].rename(
        columns={"TIME_PERIOD": "period", "OBS_VALUE": "value"}
    )
    df = df.dropna(subset=["value"])

    # 3. Put the periods in time order
    return df.sort_values("period").reset_index(drop=True)


def fetch_series(flow, key):
    """Download one series and return a table with columns period and value."""

    # 1. HTTP request with parameters and timeout
    response = requests.get(build_url(flow, key), params={"format": "csvdata"}, timeout=30)

    # 2. Raise an exception if the status code is 4xx or 5xx (e.g. a wrong key)
    response.raise_for_status()

    # 3. Convert the CSV into a table
    return parse_csv(response.text)


if __name__ == "__main__":
    for series_id, info in SERIES.items():
        data = fetch_series(info["flow"], info["key"])

        num_obs = len(data)
        first_period = data["period"].iloc[0]
        last_period = data["period"].iloc[-1]
        last_value = data["value"].iloc[-1]

        print(
            f"{series_id} | Observations: {num_obs} | "
            f"Period: {first_period} -> {last_period} | "
            f"Last value: {last_value}"
        )