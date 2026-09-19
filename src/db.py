import sqlite3

db = sqlite3.connect('members.db')

def init_db():
    cursor = db.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS members (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        card_number TEXT NOT NULL UNIQUE,
        boardmember INTEGER,
        comment TEXT
    )
""")
    db.commit()

def get_member(card_number):
    cursor = db.cursor()
    cursor.execute("SELECT * FROM members WHERE card_number=?", (card_number,))
    return cursor.fetchone()

def add_member(card_number, name, boardmember, comment):
    cursor = db.cursor()
    cursor.execute("INSERT INTO members (card_number, name, boardmember, comment) VALUES (?, ?, ?, ?)",
                   (card_number, name, boardmember, comment))
    db.commit()

def remove_member(card_number):
    cursor = db.cursor()
    cursor.execute("DELETE FROM members WHERE card_number=?", (card_number,))
    db.commit()

# Sentinel meaning "caller did not pass this argument". Needed because None is a
# legitimate value (e.g. clearing a comment), so it can't also mean "leave alone".
_UNSET = object()
 
def update_member(card_number, *, name=_UNSET, boardmember=_UNSET,
                  comment=_UNSET, new_card_number=_UNSET):
    """Update the fields you pass for the member with `card_number`.
 
    Only the arguments you provide are changed. Pass new_card_number to
    re-issue a lost/replaced card. Returns True if a member was found (and
    updated), False if no member has that card number.
 
    Raises ValueError if nothing to update was given, and sqlite3.IntegrityError
    if the change violates a constraint (name=None, or a new_card_number that
    already belongs to someone else).
    """
    # Column names are hard-coded here, never taken from caller input, so
    # building the SET clause below is safe; all *values* stay parameterised.
    candidates = {
        "name": name,
        "boardmember": boardmember,
        "comment": comment,
        "card_number": new_card_number,
    }
    changes = {col: val for col, val in candidates.items() if val is not _UNSET}
    if not changes:
        raise ValueError("update_member called with nothing to update")
 
    assignments = ", ".join(f"{col}=?" for col in changes)
    cursor = db.cursor()
    cursor.execute(
        f"UPDATE members SET {assignments} WHERE card_number=?",
        (*changes.values(), card_number),
    )
    db.commit()
    return cursor.rowcount > 0