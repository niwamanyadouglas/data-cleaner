"""Load CSV and Excel files into DataFrames."""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

SUPPORTED_SUFFIXES = (".csv", ".xlsx", ".xls")


def load_file(path: str | Path, encoding: str = "utf-8-sig") -> pd.DataFrame:
    """Load a CSV or Excel file into a DataFrame.

    Values like "N/A" are deliberately kept as text (``keep_default_na=False``)
    so the cleaning step can replace them and report how many it found.
    The default ``utf-8-sig`` encoding also handles the byte-order mark that
    Excel adds to CSV exports.
    """
    file_path = Path(path)
    if not file_path.is_file():
        raise FileNotFoundError(f"File not found: {file_path}")

    suffix = file_path.suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        raise ValueError(
            f"Unsupported file type: {suffix or '(none)'}. "
            f"Supported types: {', '.join(SUPPORTED_SUFFIXES)}"
        )

    logger.info("Loading file: %s", file_path)

    try:
        if suffix == ".csv":
            try:
                return pd.read_csv(file_path, encoding=encoding, keep_default_na=False)
            except UnicodeDecodeError:
                # Common for messy data exported from older tools.
                logger.warning("%s decoding failed for %s, trying latin-1...", encoding, file_path)
                return pd.read_csv(file_path, encoding="latin-1", keep_default_na=False)
        return pd.read_excel(file_path, keep_default_na=False)
    except Exception as e:
        raise ValueError(f"Error reading file {file_path}: {e}") from e
