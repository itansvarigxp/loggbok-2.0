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