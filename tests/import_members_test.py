import sqlite3

import pytest
from openpyxl import Workbook

import src.helpers.import_members as im
import src.db as members

HEADER = ["0,Nyckelnr", "Namn", "Styrelsemedlem", "Senast aktivitet"]


def make_xlsx(tmp_path, rows, header=HEADER, name="members.xlsx"):
    wb = Workbook()
    ws = wb.active
    ws.append(header)
    for r in rows:
        ws.append(r)
    path = tmp_path / name
    wb.save(path)
    return path


def count(db_path):
    with sqlite3.connect(db_path) as other:
        return other.execute("SELECT COUNT(*) FROM members").fetchone()[0]


# ---------- parsing ----------

def test_reads_the_documented_format(tmp_path):
    path = make_xlsx(tmp_path, [["0012345", "John Doe", None]])
    result = im.read_rows(path)
    assert result.rows == [(2, "0012345", "John Doe", 0)]  # leading zeros kept
    assert result.errors == [] and result.warnings == []


def test_headers_any_order_any_case_and_extra_columns_reported(tmp_path):
    path = make_xlsx(tmp_path, [["A", "zzz", "1", "Styret"]],
                     header=["namn", "EXTRA", "0,NYCKELNR", "Styrelsemedlem"])
    result = im.read_rows(path)
    assert result.rows == [(2, "1", "A", 1)]
    assert result.ignored_columns == ["EXTRA"]


def test_missing_header_column_is_a_problem(tmp_path):
    path = make_xlsx(tmp_path, [], header=["0,Nyckelnr", "Namn"])
    with pytest.raises(im.ImportProblem):
        im.read_rows(path)


def test_oddly_prefixed_header_is_not_guessed(tmp_path):
    path = make_xlsx(tmp_path, [], header=["0,Nyckelnr", "Namn", "Styrelsemedlem"])
    with pytest.raises(im.ImportProblem) as e:
        im.read_rows(path)
    assert "0,Nyckelnr" in str(e.value)  # shows what it actually found


def test_numeric_card_cell_warns_that_zeros_are_lost(tmp_path):
    result = im.read_rows(make_xlsx(tmp_path, [[12345, "A", None]]))
    assert result.rows == [(2, "12345", "A", 0)]
    assert len(result.warnings) == 1


def test_whole_float_card_is_accepted(tmp_path):
    result = im.read_rows(make_xlsx(tmp_path, [[12345.0, "A", None]]))
    assert result.rows[0][1] == "12345"


@pytest.mark.parametrize("bad", ["0,0012345", 0.0012345, "12a45", "12 345",
                                 "-5", "١٢٣", True])
def test_bad_card_values_are_errors(tmp_path, bad):
    result = im.read_rows(make_xlsx(tmp_path, [[bad, "A", None]]))
    assert result.rows == []
    assert [row for row, _ in result.errors] == [2]


def test_missing_card_and_missing_name_are_errors(tmp_path):
    result = im.read_rows(make_xlsx(tmp_path, [[None, "A", None], ["1", None, None]]))
    assert [row for row, _ in result.errors] == [2, 3]


@pytest.mark.parametrize("cell,expected", [
    ("Styret", 1), ("styret", 1), ("  STYRET ", 1),
    (None, 0), ("", 0), ("   ", 0),
])
def test_board_member_values(tmp_path, cell, expected):
    result = im.read_rows(make_xlsx(tmp_path, [["1", "A", cell]]))
    assert result.errors == []
    assert result.rows[0][3] == expected


def test_capitalisation_of_the_marker_constant_does_not_matter(monkeypatch):
    # Someone editing BOARD_MARKER to match the sheet ("Styret") must not break it.
    monkeypatch.setattr(im, "BOARD_MARKER", "Styret")
    assert im.parse_board("styret") == 1
    assert im.parse_board("Styret") == 1
    assert im.parse_board("  STYRET ") == 1


@pytest.mark.parametrize("cell", ["Ja", "x", "1", 1, True, 0, "Nej",
                                  "Styrelse", "Styret!", "Styret, kassör"])
def test_anything_but_styret_or_blank_is_an_error_not_a_guess(tmp_path, cell):
    result = im.read_rows(make_xlsx(tmp_path, [["1", "A", cell]]))
    assert result.rows == []
    assert [row for row, _ in result.errors] == [2]
    assert "Styret" in result.errors[0][1]  # tells you what was expected


def test_blank_rows_are_skipped_and_counted(tmp_path):
    path = make_xlsx(tmp_path, [["1", "A", None], ["  ", None, ""], ["2", "B", None]])
    result = im.read_rows(path)
    assert [r[1] for r in result.rows] == ["1", "2"]
    assert result.blank_rows == 1


def test_error_row_numbers_match_excel_even_with_gaps(tmp_path):
    wb = Workbook()
    ws = wb.active
    for col, h in enumerate(HEADER, start=1):
        ws.cell(row=1, column=col, value=h)
    ws.cell(row=2, column=1, value="1"); ws.cell(row=2, column=2, value="A")
    # rows 3 and 4 never written at all
    ws.cell(row=5, column=1, value="bad!"); ws.cell(row=5, column=2, value="B")
    path = tmp_path / "gap.xlsx"
    wb.save(path)
    result = im.read_rows(path)
    assert [row for row, _ in result.errors] == [5]
    assert result.rows[0][0] == 2


def test_duplicate_card_in_file_is_an_error(tmp_path):
    path = make_xlsx(tmp_path, [["1", "A", None], ["2", "B", None], ["1", "C", None]])
    result = im.read_rows(path)
    assert result.errors == [(4, "duplicate key number 1 (also on row 2)")]
    assert [r[1] for r in result.rows] == ["1", "2"]


def test_cards_differing_only_by_leading_zeros_warn(tmp_path):
    result = im.read_rows(make_xlsx(tmp_path, [["0012345", "A", None], ["12345", "B", None]]))
    assert result.errors == []
    assert any("leading zeros" in msg for _, msg in result.warnings)


def test_only_first_sheet_is_read_and_others_are_reported(tmp_path):
    wb = Workbook()
    ws = wb.active
    ws.append(HEADER); ws.append(["1", "A", None])
    ws2 = wb.create_sheet("Old")
    ws2.append(HEADER); ws2.append(["2", "B", None])
    path = tmp_path / "two.xlsx"
    wb.save(path)
    result = im.read_rows(path)
    assert [r[1] for r in result.rows] == ["1"]
    assert result.other_sheets == ["Old"]


def test_names_are_trimmed_and_unicode_preserved(tmp_path):
    result = im.read_rows(make_xlsx(tmp_path, [["1", "  Åsa Öberg  ", None]]))
    assert result.rows[0][2] == "Åsa Öberg"


# ---------- run() / CLI ----------

def test_dry_run_writes_nothing(db_path, tmp_path, capsys):
    path = make_xlsx(tmp_path, [["1", "A", None], ["2", "B", "Styret"]])
    assert im.run(path) == 0
    out = capsys.readouterr().out
    assert "Dry run" in out and "To insert: 2" in out
    assert count(db_path) == 0


def test_commit_inserts_rows(db_path, tmp_path):
    path = make_xlsx(tmp_path, [["0012345", "John Doe", None], ["2", "Åsa", "Styret"]])
    assert im.run(path, commit=True) == 0
    assert count(db_path) == 2
    assert members.get_member("0012345")[1:] == ("John Doe", "0012345", 0, None)
    assert members.get_member("2")[1:] == ("Åsa", "2", 1, None)


def test_any_error_aborts_everything_even_with_commit(db_path, tmp_path, capsys):
    path = make_xlsx(tmp_path, [["1", "Good", None], ["bad,1", "Bad", None]])
    assert im.run(path, commit=True) == 1
    assert count(db_path) == 0
    out = capsys.readouterr().out
    assert "row 3" in out and "Nothing was written" in out


def test_existing_members_are_skipped_never_overwritten(db_path, tmp_path, capsys):
    members.add_member("1", "Old name", 1, "keep me")
    path = make_xlsx(tmp_path, [["1", "New name", None], ["2", "Two", None]])
    assert im.run(path, commit=True) == 0
    assert members.get_member("1")[1:] == ("Old name", "1", 1, "keep me")
    assert members.get_member("2") is not None
    assert "skipped" in capsys.readouterr().out


def test_rerunning_the_same_import_is_harmless(db_path, tmp_path):
    path = make_xlsx(tmp_path, [["1", "A", None], ["2", "B", None]])
    assert im.run(path, commit=True) == 0
    assert im.run(path, commit=True) == 0
    assert count(db_path) == 2


def test_dry_run_does_not_create_the_table(tmp_path, monkeypatch):
    conn = sqlite3.connect(tmp_path / "fresh.db")
    monkeypatch.setattr(members, "db", conn)
    path = make_xlsx(tmp_path, [["1", "A", None]])
    assert im.run(path) == 0
    assert conn.execute("SELECT COUNT(*) FROM sqlite_master").fetchone()[0] == 0
    conn.close()


def test_commit_on_a_fresh_database_creates_the_table(tmp_path, monkeypatch):
    conn = sqlite3.connect(tmp_path / "fresh.db")
    monkeypatch.setattr(members, "db", conn)
    path = make_xlsx(tmp_path, [["1", "A", None]])
    assert im.run(path, commit=True) == 0
    assert members.get_member("1") is not None
    conn.close()


def test_report_shows_which_database_is_used(db_path, tmp_path, capsys):
    im.run(make_xlsx(tmp_path, [["1", "A", None]]))
    out = capsys.readouterr().out
    assert "Database:" in out
    assert db_path.name in out  # the real file path, not just the label


def test_missing_file_returns_2(db_path, tmp_path, capsys):
    assert im.run(tmp_path / "nope.xlsx") == 2


def test_file_that_is_not_xlsx_returns_2(db_path, tmp_path):
    fake = tmp_path / "fake.xlsx"
    fake.write_text("hello")
    assert im.run(fake) == 2


def test_main_defaults_to_dry_run_and_commit_flag_inserts(db_path, tmp_path):
    path = make_xlsx(tmp_path, [["1", "A", None]])
    assert im.main([str(path)]) == 0
    assert count(db_path) == 0
    assert im.main([str(path), "--commit"]) == 0
    assert count(db_path) == 1