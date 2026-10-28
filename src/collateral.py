"""Read and clean the Eurosystem list of eligible marketable assets.

Each snapshot lists every asset accepted as collateral in Eurosystem credit
operations on one day. The files are tab-separated text encoded in UTF-16 and
come in three containers over time:
    ea_all_YYMMDD.tgz      2010-2013  (a tar archive with a .txt file inside)
    ea_all_YYMMDD.txt.gz   2014-2015
    ea_csv_YYMMDD.csv.gz   from 2016
"""

import io
import re
import tarfile
from datetime import date
from pathlib import Path

import pandas as pd

READ_OPTIONS = {
    "sep": "\t",
    "encoding": "utf-16",      # the files start with the UTF-16 byte order mark
    "dtype": str,              # keep every code as text (ISINs, categories, dates)
    "keep_default_na": False,  # "NA" is Namibia's country code, not a missing value
    "quoting": 3,              # csv.QUOTE_NONE: issuer names may contain quote marks
}


def snapshot_day(path):
    """Return the date of a snapshot from its file name (ea_csv_250131.csv.gz -> 2025-01-31)."""
    code = Path(path).name.split("_")[2][:6]
    return date(2000 + int(code[:2]), int(code[2:4]), int(code[4:6]))


def read_snapshot(path):
    """Read one snapshot, whatever its container, as a table of text columns."""
    path = Path(path)
    if path.name.endswith(".tgz"):
        with tarfile.open(path) as archive:
            member = next(m for m in archive.getmembers() if m.name.endswith(".txt"))
            raw = archive.extractfile(member).read()
        return pd.read_csv(io.BytesIO(raw), **READ_OPTIONS)
    return pd.read_csv(path, compression="gzip", **READ_OPTIONS)


# Columns kept, with their name in the files from 2016 and, if different, in the older files
COLUMNS = {
    "isin": ["ISIN_CODE"],
    "haircut_category": ["HAIRCUT_CATEGORY", "LIQUIDITY_CLASS"],
    "asset_type": ["TYPE"],
    "currency": ["DENOMINATION"],
    "issuer_residence": ["ISSUER_RESIDENCE"],
    "issuer_group": ["ISSUER_GROUP"],
    "guarantor_group": ["GUARANTOR_GROUP"],
    "settlement": ["ISSUER_CSD", "COUNTRY_OF_LOCATION"],
    "coupon_definition": ["COUPON_DEFINITION"],
    "maturity_date": ["MATURITY_DATE"],
    "haircut": ["HAIRCUT", "VALUATION_HAIRCUT"],
}


def valid_isin(code):
    """Check the format and the check digit of an ISIN (Luhn algorithm on the digits)."""
    if not re.fullmatch(r"[A-Z]{2}[A-Z0-9]{9}[0-9]", code):
        return False
    digits = "".join(str(int(char, 36)) for char in code[:-1])  # A -> 10, ..., Z -> 35
    total = 0
    for position, digit in enumerate(reversed(digits)):
        value = int(digit) * (2 if position % 2 == 0 else 1)
        total += value // 10 + value % 10
    return (10 - total % 10) % 10 == int(code[-1])


def country_code(values, prefix):
    """Extract the two-letter country from codes such as IRFR (issuer residence) or CLFR01 (CSD)."""
    
    # (?=[A-Z]{2}) = "only if two letters follow": IRFR -> FR, CLFR01 -> FR, a plain DE stays DE
    return values.str.replace(rf"^{prefix}(?=[A-Z]{{2}})", "", regex=True).str[:2]


def harmonise(raw, day):
    """Turn one raw snapshot (old or new format) into the common table stored in the database."""
    table = pd.DataFrame({"snapshot_date": day.isoformat()}, index=raw.index)
    for name, candidates in COLUMNS.items():
        source = next((column for column in candidates if column in raw.columns), None)
        table[name] = raw[source].str.strip() if source else ""

    table["issuer_country"] = country_code(table.pop("issuer_residence"), "IR")
    table["settlement_country"] = country_code(table.pop("settlement"), "CL")
    table["maturity_date"] = pd.to_datetime(
        table["maturity_date"], format="%d/%m/%Y %H:%M:%S", errors="coerce"
    ).dt.strftime("%Y-%m-%d")
    table["haircut"] = pd.to_numeric(table["haircut"], errors="coerce")

    table = table[table["isin"].map(valid_isin)]
    return table.drop_duplicates("isin").reset_index(drop=True)


SCHEMA = """
CREATE TABLE IF NOT EXISTS eligible_assets (
    snapshot_date      TEXT NOT NULL,
    isin               TEXT NOT NULL,
    haircut_category   TEXT,
    asset_type         TEXT,
    currency           TEXT,
    issuer_group       TEXT,
    guarantor_group    TEXT,
    coupon_definition  TEXT,
    maturity_date      TEXT,
    haircut            REAL,
    issuer_country     TEXT,
    settlement_country TEXT,
    PRIMARY KEY (snapshot_date, isin)
);
"""


def save_snapshot(connection, table):
    """Insert one harmonised snapshot; loading the same snapshot again replaces its rows."""
    connection.executescript(SCHEMA)
    columns = list(table.columns)

    # SQLite does not understand pandas' NaN: missing values become None (NULL in the database)
    rows = table.astype(object).where(table.notna(), None).itertuples(index=False, name=None)
    
    connection.executemany(
        f"INSERT OR REPLACE INTO eligible_assets ({', '.join(columns)}) "
        f"VALUES ({', '.join('?' * len(columns))})",
        rows,
    )
    return len(table)
