"""Cleaning steps for messy tabular data.

Each step takes a DataFrame and returns a new one. Steps that change data can
record what they did in a ``CleaningLog`` so the final report is accurate.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

import pandas as pd

logger = logging.getLogger(__name__)

DEFAULT_PLACEHOLDERS: tuple[str, ...] = (
    "N/A",
    "n/a",
    "NA",
    "#N/A",
    "null",
    "NULL",
    "Null",
    "-",
    "--",
    "None",
    "none",
    "NaN",
    "nan",
)

# Values such as "007" or "00123" are identifiers, not numbers.
_LEADING_ZERO = re.compile(r"^[+-]?0\d")


@dataclass
class CleaningLog:
    """Everything the pipeline changed, used to build the report."""

    renamed_columns: dict[str, str] = field(default_factory=dict)
    placeholders_replaced: int = 0
    duplicates_removed: int = 0
    dates_unparsed: dict[str, int] = field(default_factory=dict)
    numeric_columns: list[str] = field(default_factory=list)


def _text_columns(df: pd.DataFrame) -> list:
    """Columns holding text, for both the object dtype and pandas string dtypes.

    ``select_dtypes(include="object")`` misses the dedicated string dtype that
    pandas 3 uses by default, so check both explicitly.
    """
    return [
        col
        for col in df.columns
        if df[col].dtype == object or pd.api.types.is_string_dtype(df[col].dtype)
    ]


def normalise_column_name(name) -> str:
    """Turn a raw column name into snake_case."""
    text = str(name).strip().lower()
    text = re.sub(r"\s+", "_", text)  # spaces -> underscore
    text = re.sub(r"[^a-z0-9_]", "", text)  # drop anything else
    text = re.sub(r"_+", "_", text)  # collapse repeated underscores
    return text.strip("_")


def clean_column_names(df: pd.DataFrame, log: CleaningLog | None = None) -> pd.DataFrame:
    """Standardise column names to snake_case, keeping them unique."""
    df = df.copy()
    used: set[str] = set()
    new_names: list[str] = []

    for old in df.columns:
        base = normalise_column_name(old) or "column"
        candidate = base
        suffix = 2
        while candidate in used:
            candidate = f"{base}_{suffix}"
            suffix += 1
        if candidate != base:
            logger.warning(
                "Column %r collides with an earlier column after cleaning; renamed to %r.",
                old,
                candidate,
            )
        used.add(candidate)
        new_names.append(candidate)
        if log is not None and str(old) != candidate:
            log.renamed_columns[str(old)] = candidate

    df.columns = new_names
    return df


def strip_text_values(df: pd.DataFrame) -> pd.DataFrame:
    """Trim whitespace in all text columns and convert empty strings to missing."""
    df = df.copy()
    for col in _text_columns(df):
        stripped = df[col].astype("string").str.strip()
        is_blank = stripped.eq("").fillna(False).astype(bool)
        df[col] = stripped.mask(is_blank)
    return df


def replace_placeholders(
    df: pd.DataFrame,
    placeholders: tuple[str, ...] = DEFAULT_PLACEHOLDERS,
    log: CleaningLog | None = None,
) -> pd.DataFrame:
    """Replace placeholder strings (exact matches only) with missing values."""
    df = df.copy()
    placeholder_set = set(placeholders)
    total = 0
    for col in _text_columns(df):
        hits = df[col].isin(placeholder_set)
        count = int(hits.sum())
        if count:
            df[col] = df[col].mask(hits)
            total += count
    if total:
        logger.info("Replaced %d placeholder values with missing.", total)
    if log is not None:
        log.placeholders_replaced += total
    return df


def remove_duplicates(df: pd.DataFrame, log: CleaningLog | None = None) -> pd.DataFrame:
    """Drop exact duplicate rows."""
    initial_len = len(df)
    df = df.drop_duplicates().reset_index(drop=True)
    removed = initial_len - len(df)
    if removed:
        logger.info("Removed %d duplicate rows.", removed)
    if log is not None:
        log.duplicates_removed += removed
    return df


def _parse_dates(series: pd.Series, dayfirst: bool) -> pd.Series:
    """Parse mixed-format dates.

    ISO values (2026-01-05) are unambiguous, so they are parsed first and
    always read year-first. Passing ``dayfirst=True`` straight to pandas can
    swap the month and day of ISO strings. Only the values that are not ISO
    go through the day-first / month-first rule.
    """
    iso = pd.to_datetime(series, format="ISO8601", errors="coerce")
    remaining = iso.isna() & series.notna()
    if remaining.any():
        other = pd.to_datetime(series[remaining], format="mixed", dayfirst=dayfirst, errors="coerce")
        iso = iso.copy()
        iso[remaining] = other
    return iso


def standardise_dates(
    df: pd.DataFrame,
    date_columns: list[str],
    dayfirst: bool = True,
    log: CleaningLog | None = None,
) -> pd.DataFrame:
    """Parse date columns into datetimes, handling mixed formats.

    ``dayfirst`` decides how ambiguous values such as 05/01/2026 are read:
    True means 5 January, False means 1 May. Values that cannot be parsed
    become missing and are counted in the log.
    """
    df = df.copy()
    for col in date_columns:
        if col not in df.columns:
            logger.warning("Date column '%s' not found in DataFrame.", col)
            continue

        logger.info("Standardising dates in column: %s", col)
        before = int(df[col].notna().sum())
        df[col] = _parse_dates(df[col], dayfirst)
        unparsed = before - int(df[col].notna().sum())

        if unparsed:
            logger.warning(
                "%d value(s) in column '%s' could not be parsed as dates and were set to missing.",
                unparsed,
                col,
            )
        if log is not None and unparsed:
            log.dates_unparsed[col] = unparsed
    return df


def convert_numeric_columns(df: pd.DataFrame, log: CleaningLog | None = None) -> pd.DataFrame:
    """Convert text columns to numbers when every non-missing value is numeric.

    Columns with any non-numeric value are left alone, as are columns whose
    values have leading zeros (likely identifiers such as zip codes).
    """
    df = df.copy()
    for col in _text_columns(df):
        values = df[col]
        non_missing = values.dropna()
        if non_missing.empty:
            continue
        if non_missing.astype("string").str.match(_LEADING_ZERO).any():
            continue
        converted = pd.to_numeric(values, errors="coerce")
        if int(converted.notna().sum()) == len(non_missing):
            df[col] = converted
            if log is not None:
                log.numeric_columns.append(col)
    return df


def clean_pipeline(
    df: pd.DataFrame,
    date_columns: list[str] | None = None,
    dayfirst: bool = True,
    convert_numeric: bool = True,
    log: CleaningLog | None = None,
) -> pd.DataFrame:
    """Run all cleaning steps in order.

    ``date_columns`` may use the original column names; they are normalised
    the same way as the data's columns so ``Date`` matches ``date``.
    Duplicates are removed last, so rows that only differed in text padding,
    placeholders or date format are caught too.
    """
    if date_columns is None:
        date_columns = ["date"]
    if log is None:
        log = CleaningLog()

    date_columns = [normalise_column_name(col) for col in date_columns]

    df = clean_column_names(df, log)
    df = strip_text_values(df)
    df = replace_placeholders(df, log=log)
    df = standardise_dates(df, date_columns, dayfirst=dayfirst, log=log)
    if convert_numeric:
        df = convert_numeric_columns(df, log)
    df = remove_duplicates(df, log)
    return df
