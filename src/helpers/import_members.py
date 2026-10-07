"""Import members from an Excel (.xlsx) file into the members database.

    python import_members.py members.xlsx            # dry run: report only, writes nothing
    python import_members.py members.xlsx --commit   # really insert

Expected header row (any order, any capitalisation): Nyckelnr, Namn, Styrelsemedlem.
Only the FIRST sheet is read. Any problem in the file aborts the whole import:
nothing is guessed, and nothing is half-imported.
"""
import argparse
import re
import sys
from tkinter.font import names
import zipfile
from dataclasses import dataclass, field

from openpyxl import load_workbook
from openpyxl.utils.exceptions import InvalidFileException

import src.db as members

REQUIRED = ("0,Nyckelnr", "Namn", "Styrelsemedlem", "Senast aktivitet")
BOARD_MARKER = "Styret"  # the only non-blank value expected in Styrelsemedlem


class ImportProblem(ValueError):
    """The file as a whole can't be read (e.g. a required header is missing)."""


@dataclass
class ParseResult:
    sheet: str = ""
    rows: list = field(default_factory=list)      # (excel_row, card, name, board)
    errors: list = field(default_factory=list)    # (excel_row, message)
    warnings: list = field(default_factory=list)  # (excel_row, message)
    blank_rows: int = 0
    ignored_columns: list = field(default_factory=list)
    other_sheets: list = field(default_factory=list)


# ---------- cell parsing ----------

def _is_blank(value):
    return value is None or (isinstance(value, str) and not value.strip())


def parse_card(value):
    """Return (card_text, warning_or_None). Raises ValueError if unusable."""
    DECIMAL_COMMA_KEY = re.compile(r"0,([0-9]+)")
    KEY_LEN = None  # expected key length, set to None to disable the check

    if _is_blank(value):
        raise ValueError("missing key number")
    warnings = []
    if isinstance(value, bool):
        raise ValueError(f"key number {value!r} is not a number")
    if isinstance(value, float):
        if value != int(value):
            raise ValueError(f"key number {value!r} is a non-whole float; "
                             "trailing zeros may already be lost, so it "
                             "can't be recovered reliably")
        value = int(value)
    if isinstance(value, int):
        text = str(value)
        warnings.append("stored as a number in Excel, so any leading zeros "
                        "are already lost")
    else:
        text = str(value).strip()
        m = DECIMAL_COMMA_KEY.fullmatch(text)
        if m:
            text = m.group(1)
            warnings.append("decimal-comma format '0,xxxxxxxx'; "
                            "used the digits after the comma")
    if not re.fullmatch(r"[0-9]+", text):  # ASCII digits only
        raise ValueError(f"key number {text!r} is not digits only")
    if KEY_LEN and len(text) != KEY_LEN:
        warnings.append(f"length {len(text)}, expected {KEY_LEN}")
    return text, "; ".join(warnings) or None


def parse_name(value):
    if _is_blank(value):
        raise ValueError("missing name")
    return str(value).strip()


def parse_board(value):
    """Blank -> 0 (not on the board), "Styret" -> 1, anything else is an error."""
    if _is_blank(value):
        return 0
    if isinstance(value, str) and value.strip().casefold() == BOARD_MARKER.casefold():
        return 1
    raise ValueError(f'cannot read {value!r} in the Styrelsemedlem column '
                     '(expected "Styret" or blank)')


# ---------- reading the file ----------

def _cell(row, i):
    return row[i] if i < len(row) else None


def read_rows(path):
    wb = load_workbook(path, read_only=True, data_only=True)
    try:
        ws = wb.worksheets[0]
        ws.reset_dimensions()

        result = ParseResult(
            sheet=ws.title,
            other_sheets=[s.title for s in wb.worksheets[1:]]
        )

        row_iter = ws.iter_rows(values_only=True)
        header = next(row_iter, None)

        if header is None:
            raise ImportProblem("the first sheet is empty")

        print("EXPECTED:", [repr(x) for x in REQUIRED])
        print("FOUND:   ", [repr(x) for x in header])

        names = ["" if h is None else str(h).strip().lower() for h in header]

        required = [h.strip().lower() for h in REQUIRED]
        missing = [h for h in required if h not in names]
        if missing:
            found = [str(h) for h in header if h is not None]
            raise ImportProblem(f"missing header column(s) {missing}; found {found}")
        idx = {h: names.index(h.strip().lower()) for h in REQUIRED}
        result.ignored_columns = [str(h) for h in header
                                  if h is not None and str(h).strip().lower() not in REQUIRED]

        seen = {}       # card -> excel row
        seen_nozero = {}  # card without leading zeros -> (card, excel row)
        for excel_row, row in enumerate(row_iter, start=2):
            if all(_is_blank(v) for v in row):
                result.blank_rows += 1
                continue
            try:
                card, warning = parse_card(_cell(row, idx["0,Nyckelnr"]))
                name = parse_name(_cell(row, idx["Namn"]))
                board = parse_board(_cell(row, idx["Styrelsemedlem"]))
            except ValueError as e:
                result.errors.append((excel_row, str(e)))
                continue

            if card in seen:
                result.errors.append(
                    (excel_row, f"duplicate key number {card} (also on row {seen[card]})"))
                continue
            seen[card] = excel_row

            key = card.lstrip("0") or "0"
            if key in seen_nozero and seen_nozero[key][0] != card:
                other_card, other_row = seen_nozero[key]
                result.warnings.append(
                    (excel_row, f"{card} differs from {other_card} (row {other_row}) "
                                "only by leading zeros"))
            seen_nozero.setdefault(key, (card, excel_row))

            if warning:
                result.warnings.append((excel_row, warning))
            result.rows.append((excel_row, card, name, board))
        return result
    finally:
        wb.close()


# ---------- database side ----------

def _database_path():
    return members.db.execute("PRAGMA database_list").fetchone()[2]


def _existing_cards():
    """Cards already in the DB. Reads only: never creates the table."""
    has_table = members.db.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='members'").fetchone()
    if not has_table:
        return set()
    return {r[0] for r in members.db.execute("SELECT card_number FROM members")}


def _show(items, label, limit=10):
    for excel_row, message in items[:limit]:
        print(f"  row {excel_row}: {message}")
    if len(items) > limit:
        print(f"  ... and {len(items) - limit} more {label}")


def run(path, commit=False):
    """Returns 0 = ok, 1 = problems in the data (nothing written), 2 = unreadable file."""
    print(f"Database: {_database_path()}")
    try:
        result = read_rows(path)
    except ImportProblem as e:
        print(f"Cannot import {path}: {e}")
        return 2
    except (FileNotFoundError, zipfile.BadZipFile, InvalidFileException) as e:
        print(f"Cannot open {path} as an .xlsx file: {e}")
        return 2

    print(f"Sheet: {result.sheet!r}"
          + (f"  (other sheets NOT read: {result.other_sheets})" if result.other_sheets else ""))
    if result.ignored_columns:
        print(f"Columns ignored: {result.ignored_columns}")
    print(f"Rows: {len(result.rows)} usable, {len(result.errors)} with errors, "
          f"{result.blank_rows} blank skipped")

    if result.warnings:
        print(f"\nWarnings ({len(result.warnings)}):")
        _show(result.warnings, "warnings")

    if result.errors:
        print(f"\nERRORS ({len(result.errors)}) - fix the spreadsheet and run again:")
        _show(result.errors, "errors")
        print("\nNothing was written.")
        return 1

    existing = _existing_cards()
    to_add = [r for r in result.rows if r[1] not in existing]
    skipped = [r for r in result.rows if r[1] in existing]
    if skipped:
        print(f"\nAlready in the database, skipped (NOT overwritten): {len(skipped)}")
        _show([(r[0], f"key number {r[1]} ({r[2]})") for r in skipped], "already present")

    print(f"\nTo insert: {len(to_add)} member(s)")
    if not commit:
        print("Dry run: nothing was written. Re-run with --commit to import.")
        return 0

    members.init_db()
    for _, card, name, board in to_add:
        members.add_member(card, name, board)
    print(f"Inserted {len(to_add)} member(s).")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="Import members from an .xlsx file.")
    parser.add_argument("xlsx", help="path to the spreadsheet")
    parser.add_argument("--commit", action="store_true",
                        help="actually insert (default is a dry run)")
    args = parser.parse_args(argv)
    return run(args.xlsx, commit=args.commit)


if __name__ == "__main__":
    sys.exit(main())