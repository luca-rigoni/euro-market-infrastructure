"""Tests for src/collateral.py: the old and the new file formats must give the same table."""

from datetime import date

import pandas as pd

from src.collateral import country_code, harmonise, valid_isin

# One asset as it appears in a 2010-2014 file and in a file from 2016
OLD = pd.DataFrame({
    "ISIN_CODE": ["FR001400BHC8", "FR001400BHC9"],   # the second has a wrong check digit
    "LIQUIDITY_CLASS": ["L1D", "L1D"],
    "TYPE": ["AT01", "AT01"],
    "DENOMINATION": ["USD", "USD"],
    "ISSUER_RESIDENCE": ["IRFR", "IRFR"],
    "ISSUER_GROUP": ["IG4", "IG4"],
    "GUARANTOR_GROUP": ["", ""],
    "COUNTRY_OF_LOCATION": ["FR", "FR"],
    "COUPON_DEFINITION": ["CD2", "CD2"],
    "MATURITY_DATE": ["08/07/2027 00:00:00", "08/07/2027 00:00:00"],
    "VALUATION_HAIRCUT": ["22.3", "22.3"],
})
NEW = OLD.rename(columns={"LIQUIDITY_CLASS": "HAIRCUT_CATEGORY", "VALUATION_HAIRCUT": "HAIRCUT"})
NEW = NEW.drop(columns="COUNTRY_OF_LOCATION").assign(ISSUER_CSD=["CLFR01", "CLFR01"])


def test_isin_check_digit():
    assert valid_isin("US0378331005")        # Apple
    assert not valid_isin("US0378331006")    # same code, wrong check digit
    assert not valid_isin("IT0001")          # too short


def test_country_is_extracted_from_both_kinds_of_code():
    codes = pd.Series(["IRFR", "CLFR01", "DE", ""])
    assert country_code(codes, "IR").tolist() == ["FR", "CL", "DE", ""]
    assert country_code(codes, "CL").tolist() == ["IR", "FR", "DE", ""]


def test_old_and_new_formats_give_the_same_table():
    old = harmonise(OLD, date(2014, 1, 31)).drop(columns="snapshot_date")
    new = harmonise(NEW, date(2026, 1, 30)).drop(columns="snapshot_date")
    pd.testing.assert_frame_equal(old, new)
    row = new.iloc[0]
    assert len(new) == 1                     # the invalid ISIN is dropped
    assert row["issuer_country"] == "FR" and row["settlement_country"] == "FR"
    assert row["maturity_date"] == "2027-07-08" and row["haircut"] == 22.3
