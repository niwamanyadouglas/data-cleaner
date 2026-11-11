"""Command-line interface for the data cleaner."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from .cleaning import CleaningLog, clean_pipeline
from .loader import load_file
from .report import build_report

logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="data-cleaner",
        description="Clean a messy CSV or Excel file.",
    )
    parser.add_argument("input", help="Path to the input file (.csv, .xlsx or .xls)")
    parser.add_argument("-o", "--output", default="cleaned.csv", help="Output CSV path")
    parser.add_argument(
        "--date-columns",
        nargs="+",
        default=["date"],
        metavar="COLUMN",
        help="Columns to parse as dates, using their original names (default: date)",
    )
    parser.add_argument(
        "--month-first",
        action="store_true",
        help="Read ambiguous dates like 05/01/2026 as month/day (default is day/month)",
    )
    parser.add_argument(
        "--no-numeric",
        action="store_true",
        help="Do not convert fully numeric text columns to numbers",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the cleaner. Returns 0 on success and 1 on failure."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    args = build_parser().parse_args(argv)

    input_path = Path(args.input)
    output_path = Path(args.output)

    try:
        if input_path.resolve() == output_path.resolve():
            raise ValueError("Output path is the same as the input file; refusing to overwrite it.")

        logger.info("Starting cleaning process for %s", input_path)
        original = load_file(input_path)

        log = CleaningLog()
        cleaned = clean_pipeline(
            original,
            date_columns=args.date_columns,
            dayfirst=not args.month_first,
            convert_numeric=not args.no_numeric,
            log=log,
        )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        cleaned.to_csv(output_path, index=False)

        report_path = output_path.with_suffix(".report.txt")
        report_path.write_text(build_report(original, cleaned, log), encoding="utf-8")

        logger.info("Cleaned data saved to %s", output_path)
        logger.info("Report saved to %s", report_path)
    except (FileNotFoundError, ValueError) as e:
        logger.error(e)
        return 1
    except Exception:
        logger.exception("An unexpected error occurred")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())