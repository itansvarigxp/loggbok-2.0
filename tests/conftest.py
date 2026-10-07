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