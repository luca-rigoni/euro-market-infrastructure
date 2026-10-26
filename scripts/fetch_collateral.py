"""Download the yearly archives of the Eurosystem list of eligible marketable assets
and keep one snapshot per month (the last working day of each month).

Each yearly ZIP contains one file per working day (ea_all_YYMMDD.tgz in the early
years, ea_csv_YYMMDD.csv.gz later). Keeping the month-end snapshots gives a monthly
panel of eligible assets and saves disk space: each archive is deleted once read.

Run from the project root:  python -m scripts.fetch_collateral
"""

import re
import zipfile
from pathlib import Path

import requests

ARCHIVE_URL = "https://www.ecb.europa.eu/paym/coll/assets/shared/data/archive/{year}.zip"
RAW_DIR = Path("data/raw")
SNAPSHOT_DIR = RAW_DIR / "collateral"
YEARS = range(2010, 2026)

DATE_IN_NAME = re.compile(r"_(\d{6})\.")  # ea_csv_250131.csv.gz -> 250131 (YYMMDD)


def snapshot_date(name):
    """Return the date code YYMMDD contained in a snapshot file name, or None."""
    match = DATE_IN_NAME.search(name)
    return match.group(1) if match else None


def month_end_files(names):
    """Among the daily file names of an archive, keep the last one of each month."""
    last = {}
    for name in names:
        code = snapshot_date(name)
        if code is None:
            continue  # folders and other files
        month = code[:4]  # YYMM
        if month not in last or code > snapshot_date(last[month]):
            last[month] = name
    return [last[month] for month in sorted(last)]


def download(url, path):
    """Download a large file in chunks of 1 MB, without holding it all in memory."""
    with requests.get(url, stream=True, timeout=120) as response:
        response.raise_for_status()
        with open(path, "wb") as file:
            for chunk in response.iter_content(chunk_size=1 << 20):
                file.write(chunk)


def main():
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    for year in YEARS:
        archive = RAW_DIR / f"{year}.zip"
        if not archive.exists():
            print(f"{year}: downloading the yearly archive...")
            download(ARCHIVE_URL.format(year=year), archive)
        with zipfile.ZipFile(archive) as zf:
            selected = month_end_files(zf.namelist())
            for name in selected:
                (SNAPSHOT_DIR / Path(name).name).write_bytes(zf.read(name))
        archive.unlink()  # the daily files of the other days are not needed
        print(f"{year}: {len(selected)} month-end snapshots kept")


if __name__ == "__main__":
    main()