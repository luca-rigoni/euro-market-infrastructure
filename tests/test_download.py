"""Tests for src/download.py that replace the ECB API with a fake response (no internet needed)."""

import pytest
import requests

import src.download as download
from src.download import COUNTRIES, SERIES, build_url, parse_csv

# A small extract with the same layout as the CSV returned by the ECB Data Portal,
# including one period without a value
SAMPLE_CSV = """KEY,FREQ,TIME_PERIOD,OBS_VALUE,TITLE
HICP.M.U2.N.000000.4D0.ANR,M,2024-01,2.8,HICP
HICP.M.U2.N.000000.4D0.ANR,M,2024-02,2.6,HICP
HICP.M.U2.N.000000.4D0.ANR,M,2024-03,,HICP
"""


class FakeResponse:
    """Stands in for the object returned by requests.get."""

    def __init__(self, text, status=200):
        self.text = text
        self.status = status

    def raise_for_status(self):
        if self.status >= 400:
            raise requests.HTTPError(f"HTTP {self.status}")


def test_fetch_series_calls_the_right_url_and_cleans_the_data(monkeypatch):
    calls = {}

    def fake_get(url, params=None, timeout=None):
        calls.update(url=url, params=params)
        return FakeResponse(SAMPLE_CSV)

    monkeypatch.setattr(download.requests, "get", fake_get)
    data = download.fetch_series("HICP", "M.U2.N.000000.4D0.ANR")

    assert calls["url"] == "https://data-api.ecb.europa.eu/service/data/HICP/M.U2.N.000000.4D0.ANR"
    assert calls["params"] == {"format": "csvdata"}
    assert list(data.columns) == ["period", "value"]
    assert data["period"].tolist() == ["2024-01", "2024-02"]  # the empty period is dropped
    assert data["value"].tolist() == [2.8, 2.6]


def test_fetch_series_raises_on_http_errors(monkeypatch):
    monkeypatch.setattr(download.requests, "get", lambda url, params=None, timeout=None: FakeResponse("", 404))
    with pytest.raises(requests.HTTPError):
        download.fetch_series("HICP", "WRONG.KEY")


def test_series_keys_start_with_their_frequency():
    for info in download.SERIES.values():
        assert info["frequency"] in {"M", "Q"}
        assert info["key"].startswith(info["frequency"] + ".")


def test_every_country_has_its_three_series():
    assert len(SERIES) == 3 * len(COUNTRIES)
    for country in COUNTRIES:
        assert {f"target_{country}", f"yield10y_{country}", f"gdp_{country}"} <= SERIES.keys()
