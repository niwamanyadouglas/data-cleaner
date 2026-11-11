from pathlib import Path

from cleaner.main import main

SAMPLE = Path(__file__).resolve().parent.parent / "sample_data" / "messy_sample.csv"

EXPECTED_OUTPUT = (
    "station_id,date,depth_m,temperature,operator\n"
    "ST01,2026-01-05,12.5,21.3,Amina\n"
    "ST02,2026-01-05,,19.8,Brian\n"
    "ST03,2026-01-07,15.0,,Chloe\n"
    "ST04,2026-01-07,18.2,22.1,\n"
)


def test_sample_file_produces_the_output_shown_in_the_readme(tmp_path):
    out = tmp_path / "cleaned.csv"
    assert main([str(SAMPLE), "-o", str(out)]) == 0
    assert out.read_text(encoding="utf-8") == EXPECTED_OUTPUT


def test_report_is_written_next_to_the_output(tmp_path):
    out = tmp_path / "cleaned.csv"
    main([str(SAMPLE), "-o", str(out)])
    report = (tmp_path / "cleaned.report.txt").read_text(encoding="utf-8")
    assert "Rows before: 5" in report
    assert "Rows after: 4" in report
    assert "Duplicate rows removed: 1" in report
    assert "Placeholder values replaced with missing: 1" in report


def test_missing_input_returns_nonzero_exit_code(tmp_path):
    assert main([str(tmp_path / "nope.csv"), "-o", str(tmp_path / "out.csv")]) == 1


def test_unsupported_input_returns_nonzero_exit_code(tmp_path):
    bad = tmp_path / "data.txt"
    bad.write_text("x")
    assert main([str(bad), "-o", str(tmp_path / "out.csv")]) == 1


def test_refuses_to_overwrite_the_input_file(tmp_path):
    src = tmp_path / "in.csv"
    src.write_text("a\n1\n")
    assert main([str(src), "-o", str(src)]) == 1
    assert src.read_text() == "a\n1\n"


def test_date_columns_and_month_first_flags(tmp_path):
    src = tmp_path / "in.csv"
    src.write_text("Start Date,Value\n05/01/2026,1\n")
    out = tmp_path / "out.csv"
    code = main([str(src), "-o", str(out), "--date-columns", "Start Date", "--month-first"])
    assert code == 0
    assert out.read_text().splitlines()[1] == "2026-05-01,1"
