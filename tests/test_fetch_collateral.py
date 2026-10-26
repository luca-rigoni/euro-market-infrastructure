"""Tests for the selection of month-end snapshots (no download needed)."""

from scripts.fetch_collateral import month_end_files, snapshot_date


def test_date_code_is_read_from_both_file_formats():
    assert snapshot_date("2010/ea_all_100408.tgz") == "100408"
    assert snapshot_date("2025/ea_csv_250131.csv.gz") == "250131"
    assert snapshot_date("2025/") is None


def test_only_the_last_file_of_each_month_is_kept():
    names = ["2025/", "2025/ea_csv_250102.csv.gz", "2025/ea_csv_250131.csv.gz",
             "2025/ea_csv_250130.csv.gz", "2025/ea_csv_250203.csv.gz", "2025/ea_csv_250228.csv.gz"]
    assert month_end_files(names) == ["2025/ea_csv_250131.csv.gz", "2025/ea_csv_250228.csv.gz"]