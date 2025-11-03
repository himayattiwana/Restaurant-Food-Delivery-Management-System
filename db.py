# db.py
import os
import sqlite3
import pymysql
import urllib.parse as up

MYSQL_URL = os.getenv("MYSQL_URL")  # e.g., mysql://user:pass@host:3306/dbname

def _convert_percent_s_to_qmark(query: str) -> str:
    return query.replace("%s", "?")

def _row_to_dict(row):
    if row is None:
        return None
    if isinstance(row, sqlite3.Row):
        return {k: row[k] for k in row.keys()}
    return row

class _SQLiteCompatCursor:
    def __init__(self, inner):
        self._cur = inner
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc, tb):
        try:
            self._cur.close()
        except Exception:
            pass
    def execute(self, query, params=None):
        q = _convert_percent_s_to_qmark(query)
        if params is None:
            return self._cur.execute(q)
        if isinstance(params, dict):
            # naive: convert dict to tuple by sorted keys
            params = tuple(params[k] for k in sorted(params.keys()))
        elif not isinstance(params, (list, tuple)):
            params = (params,)
        return self._cur.execute(q, params)
    def executemany(self, query, seq_of_params):
        q = _convert_percent_s_to_qmark(query)
        seq = []
        for p in seq_of_params:
            if isinstance(p, dict):
                p = tuple(p[k] for k in sorted(p.keys()))
            elif not isinstance(p, (list, tuple)):
                p = (p,)
            seq.append(p)
        return self._cur.executemany(q, seq)
    def fetchone(self):
        return _row_to_dict(self._cur.fetchone())
    def fetchall(self):
        return [_row_to_dict(r) for r in self._cur.fetchall()]
    def fetchmany(self, size=None):
        rows = self._cur.fetchmany(size) if size else self._cur.fetchmany()
        return [_row_to_dict(r) for r in rows]
    def close(self):
        return self._cur.close()
    @property
    def lastrowid(self):
        return getattr(self._cur, "lastrowid", None)

class _SQLiteConnProxy:
    def __init__(self, conn):
        self._conn = conn
    def __getattr__(self, name):
        # delegate most attributes/methods (commit, rollback, etc.)
        return getattr(self._conn, name)
    def __enter__(self):
        self._conn.__enter__()
        return self
    def __exit__(self, exc_type, exc, tb):
        return self._conn.__exit__(exc_type, exc, tb)
    def cursor(self):
        return _SQLiteCompatCursor(self._conn.cursor())
    def close(self):
        try:
            self._conn.close()
        except Exception:
            pass

def get_conn():
    if MYSQL_URL:
        u = up.urlparse(MYSQL_URL)
        return pymysql.connect(
            host=u.hostname,
            user=u.username,
            password=u.password,
            port=u.port or 3306,
            database=u.path.lstrip('/'),
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=True,
        )
    else:
        # SQLite fallback for demo; write under /tmp for Render
        path = os.getenv("SQLITE_PATH", "/tmp/demo.db")
        conn = sqlite3.connect(path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return _SQLiteConnProxy(conn)
