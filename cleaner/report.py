"""Build the plain-text cleaning report."""

from __future__ import annotations

import pandas as pd

from .cleaning import CleaningLog


def build_report(
    original: pd.DataFrame,
    cleaned: pd.DataFrame,
    log: CleaningLog | None = None,
) -> str:
    """Generate a plain-text report of what the cleaner changed."""
    log = log or CleaningLog()

    rows_before = len(original)
    rows_after = len(cleaned)

    unparsed_total = sum(log.dates_unparsed.values())
    unparsed_detail = ""
    if unparsed_total:
        detail = ", ".join(f"{col}: {n}" for col, n in log.dates_unparsed.items())
        unparsed_detail = f" ({detail})"
    numeric = ", ".join(log.numeric_columns) if log.numeric_columns else "none"

    lines = [
        "DATA CLEANING REPORT",
        "========================================",
        f"Rows before: {rows_before}",
        f"Rows after: {rows_after}",
        f"Rows removed: {rows_before - rows_after}",
        "",
        "Changes made:",
        f"  - Columns renamed: {len(log.renamed_columns)}",
        f"  - Placeholder values replaced with missing: {log.placeholders_replaced}",
        f"  - Duplicate rows removed: {log.duplicates_removed}",
        f"  - Dates that could not be parsed: {unparsed_total}{unparsed_detail}",
        f"  - Columns converted to numbers: {numeric}",
    ]

    if log.renamed_columns:
        lines += ["", "Column renames:"]
        for old, new in log.renamed_columns.items():
            lines.append(f"  - {old!r} -> {new}")

    lines += ["", "Missing values after cleaning:"]
    for col, count in cleaned.isna().sum().items():
        lines.append(f"  - {col}: {count}")

    return "\n".join(lines)
