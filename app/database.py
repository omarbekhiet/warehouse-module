import sqlite3
import os
from contextlib import contextmanager
from app.config import Config


class Database:
    def __init__(self):
        self.db_path = Config.DATABASE_PATH

    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA foreign_keys = ON')
        try:
            yield conn
        finally:
            conn.close()

    @contextmanager
    def transaction(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA foreign_keys = ON')
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def query(self, sql, params=None, one=False):
        with self.get_connection() as conn:
            cur = conn.execute(sql, params or ())
            rows = [dict(r) for r in cur.fetchall()]
            if one:
                return rows[0] if rows else None
            return rows

    def execute(self, sql, params=None):
        with self.transaction() as conn:
            cur = conn.execute(sql, params or ())
            return cur.lastrowid


db = Database()
