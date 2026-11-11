# Data Cleaner: Automated Cleaning for Messy CSV and Excel Files

![Tests](https://github.com/YOUR-USERNAME/data-cleaner/actions/workflows/tests.yml/badge.svg)

A command-line tool that takes a messy CSV or Excel file and produces a clean, analysis-ready dataset along with a plain-language report of what it changed.

## The Problem

Field, lab and operational data often arrives in spreadsheets with inconsistent column names, padded text, duplicate rows, mixed date formats and placeholder values such as "N/A". Cleaning these files by hand is slow and error-prone. This tool automates the common fixes and documents them, so the cleaned data can be trusted before analysis begins.

## Features

- Loads CSV and Excel files (.csv, .xlsx, .xls), including Latin-1 CSVs and Excel's byte-order mark
- Standardises column names to snake_case and keeps them unique
- Trims whitespace and converts empty text to missing values
- Replaces common placeholders (N/A, NA, null, -) with missing values
- Parses mixed date formats into a consistent date type, and counts values it cannot parse
- Converts columns that contain only numbers into numeric columns
- Removes duplicate rows, after the other fixes so near-duplicates are caught
- Produces a report of rows removed, every change made and missing values per column
- Exits with a non-zero code on failure, so it works in scripts and CI

## Before and After

**Input (`sample_data/messy_sample.csv`)**

```csv
 Station ID ,Date,Depth (m),Temperature,Operator
ST01,2026-01-05,12.5,21.3,Amina
ST02,05/01/2026,,19.8,  Brian
ST02,05/01/2026,,19.8,  Brian
ST03,2026-01-07,15.0,N/A,Chloe
ST04,07-Jan-2026,18.2,22.1,
```

**Output (`cleaned.csv`)**

```csv
station_id,date,depth_m,temperature,operator
ST01,2026-01-05,12.5,21.3,Amina
ST02,2026-01-05,,19.8,Brian
ST03,2026-01-07,15.0,,Chloe
ST04,2026-01-07,18.2,22.1,
```

The duplicate row was removed, column names were standardised, dates were converted to a single format and placeholder values became empty cells.

## Installation

Clone the repository and create a virtual environment:

```bash
git clone https://github.com/YOUR-USERNAME/data-cleaner.git
cd data-cleaner
python -m venv venv
source venv/bin/activate        # On Windows: venv\Scripts\activate
pip install -e .
```

To also install the test tools, use `pip install -e ".[dev]"`.

## Usage

Run the cleaner on any supported file:

```bash
data-cleaner sample_data/messy_sample.csv -o cleaned.csv
```

You can also run it as a module: `python -m cleaner sample_data/messy_sample.csv`.

This creates two outputs:

- `cleaned.csv`: the cleaned dataset
- `cleaned.report.txt`: a report of the changes made and the missing values per column

### Options

| Option | What it does |
| --- | --- |
| `-o`, `--output` | Output CSV path (default `cleaned.csv`). The tool refuses to overwrite the input file. |
| `--date-columns COLUMN [COLUMN ...]` | Columns to parse as dates, using their original names, for example `--date-columns "Start Date" "End Date"`. Default is `date`. |
| `--month-first` | Read ambiguous dates such as `05/01/2026` as month/day. By default they are read as day/month (5 January). Dates like `2026-01-05` are always read year-first. |
| `--no-numeric` | Keep numeric-looking columns as text. Columns with leading zeros (such as `00123`) are always kept as text. |

Example report:

```
DATA CLEANING REPORT
========================================
Rows before: 5
Rows after: 4
Rows removed: 1

Changes made:
  - Columns renamed: 5
  - Placeholder values replaced with missing: 1
  - Duplicate rows removed: 1
  - Dates that could not be parsed: 0
  - Columns converted to numbers: depth_m, temperature

Column renames:
  - ' Station ID ' -> station_id
  - 'Date' -> date
  - 'Depth (m)' -> depth_m
  - 'Temperature' -> temperature
  - 'Operator' -> operator

Missing values after cleaning:
  - station_id: 0
  - date: 0
  - depth_m: 1
  - temperature: 1
  - operator: 1
```

Dates that cannot be parsed become empty cells. The report and the log both say how many, so check that line before trusting a date column.

## Project Structure

```
data-cleaner/
├── .github/
│   └── workflows/
│       └── tests.yml
├── cleaner/
│   ├── __init__.py
│   ├── __main__.py
│   ├── cleaning.py
│   ├── loader.py
│   ├── main.py
│   └── report.py
├── sample_data/
│   └── messy_sample.csv
├── tests/
│   ├── test_cleaning.py
│   ├── test_cli.py
│   └── test_loader.py
├── .gitignore
├── LICENSE
├── pyproject.toml
├── requirements.txt
└── README.md
```

## Running the Tests

```bash
pip install -e ".[dev]"
pytest
```

The tests cover column names, text trimming, placeholders, duplicates, date parsing, numeric conversion, file loading and the command line, including an end-to-end check that the sample file produces the output shown above. They run on Python 3.10 to 3.13 in GitHub Actions.

## Customisation

- **Placeholders:** change `DEFAULT_PLACEHOLDERS` in `cleaner/cleaning.py`, or pass your own tuple as the `placeholders` argument of `replace_placeholders`. Matching is exact and case-sensitive.
- **Date columns:** use the `--date-columns` option, or pass `date_columns` to `clean_pipeline` when using the package from Python.
- **Using it from Python:**

```python
from cleaner.cleaning import CleaningLog, clean_pipeline
from cleaner.loader import load_file
from cleaner.report import build_report

original = load_file("sample_data/messy_sample.csv")
log = CleaningLog()
cleaned = clean_pipeline(original, date_columns=["Date"], log=log)
print(build_report(original, cleaned, log))
```

## Requirements

- Python 3.10 or newer
- pandas 2.0 or newer
- openpyxl 3.1 or newer (`.xlsx`)
- xlrd 2.0.1 or newer (`.xls`)
- pytest 7.0 or newer (development only)

## Author

Niwamanya Douglas, geophysicist and data analyst. Available for freelance data cleaning and analysis projects.

## Licence

MIT
