import argparse
import logging
from pathlib import Path
from cleaner.loader import load_file
from cleaner.cleaning import clean_pipeline, CleaningLog
from cleaner.report import build_report

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description="Clean a messy CSV or Excel file.")
    parser.add_argument("input", help="Path to the input file")
    parser.add_argument("-o", "--output", default="cleaned.csv", help="Output CSV path")
    parser.add_argument("--date-columns", nargs="+", default=["date"], help="Columns to parse as dates")
    args = parser.parse_args()

    try:
        logger.info("Starting cleaning process for %s", args.input)
        original = load_file(args.input)
        
        # Create the log and pass it to the pipeline
        log = CleaningLog()
        cleaned = clean_pipeline(original, date_columns=args.date_columns, log=log)
        
        cleaned.to_csv(args.output, index=False)
        
        # Pass the log to the report builder
        report_path = Path(args.output).with_suffix(".report.txt")
        report_content = build_report(original, cleaned, log=log)
        report_path.write_text(report_content, encoding="utf-8")
        
        logger.info("Cleaned data saved to %s", args.output)
        logger.info("Report saved to %s", report_path)
        
    except Exception as e:
        logger.error("Failed: %s", e)

if __name__ == "__main__":
    main()