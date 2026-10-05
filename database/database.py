import sqlite3
from pathlib import Path
from config import DB_PATH

def connect():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    with connect() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS matches (
            id TEXT PRIMARY KEY,
            competition TEXT NOT NULL,
            kickoff TEXT NOT NULL,
            home TEXT NOT NULL,
            away TEXT NOT NULL,
            source TEXT NOT NULL,
            raw_json TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            match_id TEXT NOT NULL,
            probabilities_json TEXT NOT NULL,
            confidence INTEGER NOT NULL,
            report TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        """)
