import sqlite3
from storage.base import BaseStorage


class SQLiteStorage(BaseStorage):

    def __init__(self, db_path="data/db.sqlite"):
        self.conn = sqlite3.connect(db_path)
        self._init()

    def _init(self):
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS earthquakes (
            id TEXT PRIMARY KEY,
            magnitude REAL,
            timestamp INTEGER
        )
        """)

    def save(self, records, path=None):
        for r in records:
            self.conn.execute(
                "INSERT OR REPLACE INTO earthquakes VALUES (?, ?, ?)",
                (r["id"], r["mag"], r["time"])
            )
        self.conn.commit()
