import logging

import pandas as pd

from cleaner.cleaning import (
    CleaningLog,
    clean_column_names,
    clean_pipeline,
    convert_numeric_columns,
    normalise_column_name,
    remove_duplicates,
    replace_placeholders,
    standardise_dates,
    strip_text_values,
)


# --- column names -----------------------------------------------------------

def test_normalise_column_name():
    assert normalise_column_name("  Depth (m) ") == "depth_m"


def test_clean_column_names_snake_case():
    df = pd.DataFrame(columns=[" Station ID ", "Depth (m)", "Temperature (°C)"])
    out = clean_column_names(df)
    assert list(out.columns) == ["station_id", "depth_m", "temperature_c"]


def test_clean_column_names_logs_only_changed_names():
    df = pd.DataFrame(columns=["date", "Depth (m)"])
    log = CleaningLog()
    clean_column_names(df, log)
    assert log.renamed_columns == {"Depth (m)": "depth_m"}


def test_clean_column_names_keeps_colliding_names_unique(caplog):
    df = pd.DataFrame([[1, 2]], columns=["Depth (m)", "Depth m"])
    with caplog.at_level(logging.WARNING):
        out = clean_column_names(df)
    assert list(out.columns) == ["depth_m", "depth_m_2"]
    assert "collides" in caplog.text


# --- text values ------------------------------------------------------------

def test_strip_text_values_trims_and_turns_blanks_into_missing():
    df = pd.DataFrame({"name": ["  Brian", "Amina ", "   ", ""]})
    out = strip_text_values(df)
    assert out["name"].iloc[0] == "Brian"
    assert out["name"].iloc[1] == "Amina"
    assert out["name"].isna().tolist() == [False, False, True, True]


def test_strip_text_values_handles_pandas_string_dtype():
    df = pd.DataFrame({"name": pd.array(["  x "], dtype="string")})
    assert strip_text_values(df)["name"].iloc[0] == "x"


def test_replace_placeholders_matches_exactly_and_counts():
    df = pd.DataFrame({"v": ["N/A", "-", "N/A tower", "ok"]})
    log = CleaningLog()
    out = replace_placeholders(df, log=log)
    assert out["v"].isna().tolist() == [True, True, False, False]
    assert log.placeholders_replaced == 2


def test_replace_placeholders_custom_list():
    df = pd.DataFrame({"v": ["missing", "N/A"]})
    out = replace_placeholders(df, placeholders=("missing",))
    assert out["v"].isna().tolist() == [True, False]


# --- duplicates -------------------------------------------------------------

def test_remove_duplicates_counts_removed_rows():
    df = pd.DataFrame({"a": [1, 1, 2]})
    log = CleaningLog()
    out = remove_duplicates(df, log)
    assert len(out) == 2
    assert log.duplicates_removed == 1


# --- dates ------------------------------------------------------------------

def test_standardise_dates_mixed_formats_day_first():
    df = pd.DataFrame({"date": ["2026-01-05", "05/01/2026", "07-Jan-2026"]})
    out = standardise_dates(df, ["date"])
    assert out["date"].tolist() == [
        pd.Timestamp("2026-01-05"),
        pd.Timestamp("2026-01-05"),
        pd.Timestamp("2026-01-07"),
    ]


def test_standardise_dates_iso_values_ignore_day_first_setting():
    df = pd.DataFrame({"date": ["2026-01-05"]})
    assert standardise_dates(df, ["date"], dayfirst=True)["date"].iloc[0] == pd.Timestamp("2026-01-05")
    assert standardise_dates(df, ["date"], dayfirst=False)["date"].iloc[0] == pd.Timestamp("2026-01-05")


def test_standardise_dates_keeps_existing_datetime_columns():
    df = pd.DataFrame({"date": pd.to_datetime(["2026-01-05", None])})
    out = standardise_dates(df, ["date"])
    assert out["date"].iloc[0] == pd.Timestamp("2026-01-05")
    assert out["date"].isna().tolist() == [False, True]


def test_standardise_dates_month_first():
    df = pd.DataFrame({"date": ["05/01/2026"]})
    out = standardise_dates(df, ["date"], dayfirst=False)
    assert out["date"].iloc[0] == pd.Timestamp("2026-05-01")


def test_standardise_dates_counts_unparseable_values():
    df = pd.DataFrame({"date": ["not a date", "2026-01-05", None]})
    log = CleaningLog()
    out = standardise_dates(df, ["date"], log=log)
    assert log.dates_unparsed == {"date": 1}
    assert out["date"].isna().tolist() == [True, False, True]


def test_standardise_dates_warns_about_missing_column(caplog):
    df = pd.DataFrame({"a": [1]})
    with caplog.at_level(logging.WARNING):
        standardise_dates(df, ["date"])
    assert "not found" in caplog.text


# --- numeric conversion -----------------------------------------------------

def test_convert_numeric_columns_converts_fully_numeric_text():
    df = pd.DataFrame({"depth": pd.array(["12.5", None, "15"], dtype="string")})
    log = CleaningLog()
    out = convert_numeric_columns(df, log)
    assert pd.api.types.is_numeric_dtype(out["depth"])
    assert log.numeric_columns == ["depth"]


def test_convert_numeric_columns_leaves_mixed_text_alone():
    df = pd.DataFrame({"v": ["1", "two", "3"]})
    out = convert_numeric_columns(df)
    assert not pd.api.types.is_numeric_dtype(out["v"])


def test_convert_numeric_columns_keeps_leading_zero_identifiers():
    df = pd.DataFrame({"zip": ["00123", "00456"]})
    out = convert_numeric_columns(df)
    assert out["zip"].tolist() == ["00123", "00456"]


def test_convert_numeric_columns_skips_all_missing_columns():
    df = pd.DataFrame({"v": pd.array([None, None], dtype="string")})
    out = convert_numeric_columns(df)
    assert not pd.api.types.is_numeric_dtype(out["v"])


# --- pipeline ---------------------------------------------------------------

def test_pipeline_matches_date_column_given_in_original_case():
    df = pd.DataFrame({"Date": ["05/01/2026"], "Value": ["1"]})
    out = clean_pipeline(df, date_columns=["Date"])
    assert pd.api.types.is_datetime64_any_dtype(out["date"])


def test_pipeline_catches_duplicates_that_differ_only_in_date_format():
    df = pd.DataFrame({"id": ["A", "A"], "date": ["2026-01-05", "05/01/2026"]})
    log = CleaningLog()
    out = clean_pipeline(df, log=log)
    assert len(out) == 1
    assert log.duplicates_removed == 1


def test_pipeline_can_skip_numeric_conversion():
    df = pd.DataFrame({"value": ["1", "2"]})
    out = clean_pipeline(df, date_columns=[], convert_numeric=False)
    assert not pd.api.types.is_numeric_dtype(out["value"])
