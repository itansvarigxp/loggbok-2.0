import sqlite3

import pytest

import src.db as members


@pytest.fixture
def db_path(tmp_path, monkeypatch):
    """Point the module at a throwaway file DB instead of the real members.db.

    A file (not :memory:) is used so tests can open a *second* connection and
    check that data was actually committed.
    """
    path = tmp_path / "test_members.db"
    conn = sqlite3.connect(path)
    monkeypatch.setattr(members, "db", conn)
    members.init_db()
    yield path
    conn.close()


# ---------- init_db ----------

def test_init_db_creates_members_table(db_path):
    with sqlite3.connect(db_path) as other:
        tables = [r[0] for r in other.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")]
    assert "members" in tables


def test_init_db_is_idempotent_and_keeps_data(db_path):
    members.add_member("123", "Alice", 0, None)
    members.init_db()  # second call must not raise or wipe the table
    assert members.get_member("123") is not None


# ---------- add_member / get_member ----------

def test_add_then_get_returns_the_member(db_path):
    members.add_member("123", "Alice", 1, "treasurer")
    row = members.get_member("123")
    # SELECT * order follows the schema: id, name, card_number, boardmember, comment
    assert row[1:] == ("Alice", "123", 1, "treasurer")


def test_get_unknown_card_returns_none(db_path):
    assert members.get_member("does-not-exist") is None


def test_add_assigns_an_id(db_path):
    members.add_member("123", "Alice", 0, None)
    assert isinstance(members.get_member("123")[0], int)


def test_optional_fields_can_be_none(db_path):
    members.add_member("123", "Alice", None, None)
    row = members.get_member("123")
    assert row[3] is None and row[4] is None


def test_duplicate_card_number_is_rejected(db_path):
    members.add_member("123", "Alice", 0, None)
    with pytest.raises(sqlite3.IntegrityError):
        members.add_member("123", "Bob", 0, None)
    assert members.get_member("123")[1] == "Alice"  # original untouched


def test_name_is_required(db_path):
    with pytest.raises(sqlite3.IntegrityError):
        members.add_member("123", None, 0, None)


def test_card_number_is_required(db_path):
    with pytest.raises(sqlite3.IntegrityError):
        members.add_member(None, "Alice", 0, None)


def test_leading_zeros_are_significant(db_path):
    members.add_member("00123", "Alice", 0, None)
    members.add_member("123", "Bob", 0, None)
    assert members.get_member("00123")[1] == "Alice"
    assert members.get_member("123")[1] == "Bob"


def test_sql_metacharacters_are_treated_as_data(db_path):
    nasty = "'; DROP TABLE members; --"
    members.add_member(nasty, "Mallory", 0, "x'y")
    assert members.get_member(nasty)[1] == "Mallory"
    assert members.get_member("anything-else") is None  # table still exists


def test_add_is_committed_to_disk(db_path):
    members.add_member("123", "Alice", 0, None)
    with sqlite3.connect(db_path) as other:  # separate connection
        count = other.execute("SELECT COUNT(*) FROM members").fetchone()[0]
    assert count == 1


# ---------- remove_member ----------

def test_remove_existing_member(db_path):
    members.add_member("123", "Alice", 0, None)
    members.remove_member("123")
    assert members.get_member("123") is None


def test_remove_only_affects_the_given_member(db_path):
    members.add_member("123", "Alice", 0, None)
    members.add_member("456", "Bob", 0, None)
    members.remove_member("123")
    assert members.get_member("456") is not None


def test_remove_unknown_card_does_not_raise(db_path):
    members.remove_member("nope")


def test_card_number_can_be_reused_after_removal(db_path):
    members.add_member("123", "Alice", 0, None)
    members.remove_member("123")
    members.add_member("123", "Bob", 0, None)
    assert members.get_member("123")[1] == "Bob"


def test_remove_is_committed_to_disk(db_path):
    members.add_member("123", "Alice", 0, None)
    members.remove_member("123")
    with sqlite3.connect(db_path) as other:
        count = other.execute("SELECT COUNT(*) FROM members").fetchone()[0]
    assert count == 0

# ---------- update_member ----------
 
@pytest.fixture
def alice(db_path):
    members.add_member("123", "Alice", 1, "treasurer")
 
 
def test_update_name_only_leaves_other_fields(alice):
    assert members.update_member("123", name="Alicia") is True
    assert members.get_member("123")[1:] == ("Alicia", "123", 1, "treasurer")
 
 
def test_update_comment_only(alice):
    members.update_member("123", comment="new note")
    assert members.get_member("123")[1:] == ("Alice", "123", 1, "new note")
 
 
def test_update_multiple_fields_at_once(alice):
    members.update_member("123", name="Alicia", boardmember=0, comment="left board")
    assert members.get_member("123")[1:] == ("Alicia", "123", 0, "left board")
 
 
def test_falsy_values_are_applied_not_skipped(alice):
    # Guards against `if value:` checks: 0 and "" must be written.
    members.update_member("123", boardmember=0, comment="")
    row = members.get_member("123")
    assert row[3] == 0 and row[4] == ""
 
 
def test_can_clear_comment_and_boardmember_to_none(alice):
    members.update_member("123", boardmember=None, comment=None)
    row = members.get_member("123")
    assert row[3] is None and row[4] is None
    assert row[1] == "Alice"  # untouched
 
 
def test_update_unknown_member_returns_false_and_creates_nothing(db_path):
    assert members.update_member("nope", name="X") is False
    assert members.get_member("nope") is None
 
 
def test_update_to_identical_values_still_returns_true(alice):
    assert members.update_member("123", name="Alice") is True
 
 
def test_update_only_affects_target_member(alice):
    members.add_member("456", "Bob", 0, None)
    members.update_member("123", name="Alicia")
    assert members.get_member("456")[1:] == ("Bob", "456", 0, None)
 
 
def test_change_card_number_keeps_id_and_data(alice):
    old_id = members.get_member("123")[0]
    assert members.update_member("123", new_card_number="999") is True
    assert members.get_member("123") is None
    row = members.get_member("999")
    assert row[0] == old_id
    assert row[1:] == ("Alice", "999", 1, "treasurer")
 
 
def test_new_card_number_already_taken_is_rejected_and_nothing_changes(alice):
    members.add_member("456", "Bob", 0, None)
    with pytest.raises(sqlite3.IntegrityError):
        members.update_member("123", name="Changed", new_card_number="456")
    assert members.get_member("123")[1] == "Alice"  # name not half-applied
    assert members.get_member("456")[1] == "Bob"
 
 
def test_name_cannot_be_set_to_none(alice):
    with pytest.raises(sqlite3.IntegrityError):
        members.update_member("123", name=None)
    assert members.get_member("123")[1] == "Alice"
 
 
def test_update_with_nothing_to_change_raises(alice):
    with pytest.raises(ValueError):
        members.update_member("123")
 
 
def test_fields_must_be_passed_by_keyword(alice):
    # add_member takes (card, name, boardmember, comment) positionally; a
    # positional update_member would make argument-order mix-ups silent.
    with pytest.raises(TypeError):
        members.update_member("123", "Alicia")
 
 
def test_sql_metacharacters_in_values_are_data(alice):
    nasty = "x'; DROP TABLE members; --"
    members.update_member("123", name=nasty, comment=nasty)
    assert members.get_member("123")[1] == nasty
    assert members.get_member("123")[4] == nasty
 
 
def test_update_is_committed_to_disk(alice):
    members.update_member("123", name="Alicia")
    with sqlite3.connect(db_path_of(members.db)) as other:
        name = other.execute(
            "SELECT name FROM members WHERE card_number='123'").fetchone()[0]
    assert name == "Alicia"
 
 
def db_path_of(conn):
    """Filesystem path of a sqlite3 connection's main database."""
    return conn.execute("PRAGMA database_list").fetchone()[2]