import pandas as pd
import pytest

from cleaner.loader import load_file


def test_load_csv_keeps_placeholders_as_text(tmp_path):
    path = tmp_path / "a.csv"
    path.write_text("a,b\n1,N/A\n", encoding="utf-8")
    df = load_file(path)
    assert df["b"].iloc[0] == "N/A"


def test_load_csv_falls_back_to_latin1(tmp_path):
    path = tmp_path / "a.csv"
    path.write_bytes("name\nJosé\n".encode("latin-1"))
    assert load_file(path)["name"].iloc[0] == "José"


def test_load_csv_strips_byte_order_mark(tmp_path):
    path = tmp_path / "a.csv"
    path.write_bytes("﻿a\n1\n".encode("utf-8"))
    assert list(load_file(path).columns) == ["a"]


def test_load_xlsx(tmp_path):
    path = tmp_path / "a.xlsx"
    pd.DataFrame({"a": [1, 2]}).to_excel(path, index=False)
    assert load_file(path)["a"].tolist() == [1, 2]


def test_load_missing_file_raises_file_not_found(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_file(tmp_path / "nope.csv")


def test_load_unsupported_type_raises_value_error(tmp_path):
    path = tmp_path / "a.txt"
    path.write_text("hello")
    with pytest.raises(ValueError, match="Unsupported"):
        load_file(path)


def test_load_empty_csv_raises_value_error_with_cause(tmp_path):
    path = tmp_path / "empty.csv"
    path.write_text("")
    with pytest.raises(ValueError, match="Error reading") as excinfo:
        load_file(path)
    assert excinfo.value.__cause__ is not None
