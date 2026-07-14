"""
Lightweight SQLite persistence for the watchlist and portfolio features.
Uses the standard library sqlite3 module — no ORM, no extra dependency.

All rows are scoped by session_id so each browser visitor gets their own
watchlist and portfolio (via the httponly session cookie).
"""
import sqlite3
from contextlib import contextmanager
from config import DB_FILE


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def _needs_session_migration(conn) -> bool:
    """True when an older schema (no session_id) is present."""
    tables = {
        r[0]
        for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    for table in ("watchlist", "portfolio"):
        if table not in tables:
            continue
        cols = {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}
        if "session_id" not in cols:
            return True
    return False


def init_db():
    with get_conn() as conn:
        if _needs_session_migration(conn):
            conn.execute("DROP TABLE IF EXISTS watchlist")
            conn.execute("DROP TABLE IF EXISTS portfolio")

        conn.execute("""
            CREATE TABLE IF NOT EXISTS watchlist (
                session_id TEXT NOT NULL,
                ticker TEXT NOT NULL,
                added_at TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (session_id, ticker)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS portfolio (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                ticker TEXT NOT NULL,
                quantity REAL NOT NULL,
                buy_price REAL NOT NULL,
                buy_date TEXT NOT NULL
            )
        """)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_portfolio_session ON portfolio(session_id)"
        )


# ---------------- Watchlist ----------------
def add_to_watchlist(session_id: str, ticker: str):
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO watchlist (session_id, ticker) VALUES (?, ?)",
            (session_id, ticker.upper()),
        )


def remove_from_watchlist(session_id: str, ticker: str):
    with get_conn() as conn:
        conn.execute(
            "DELETE FROM watchlist WHERE session_id = ? AND ticker = ?",
            (session_id, ticker.upper()),
        )


def get_watchlist(session_id: str):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT ticker, added_at FROM watchlist WHERE session_id = ? ORDER BY added_at DESC",
            (session_id,),
        ).fetchall()
        return [dict(r) for r in rows]


# ---------------- Portfolio ----------------
def clear_portfolio(session_id: str):
    with get_conn() as conn:
        conn.execute("DELETE FROM portfolio WHERE session_id = ?", (session_id,))


def add_holding(session_id: str, ticker: str, quantity: float, buy_price: float, buy_date: str):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO portfolio (session_id, ticker, quantity, buy_price, buy_date) "
            "VALUES (?, ?, ?, ?, ?)",
            (session_id, ticker.upper(), quantity, buy_price, buy_date),
        )


def get_holdings(session_id: str):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM portfolio WHERE session_id = ?", (session_id,)
        ).fetchall()
        return [dict(r) for r in rows]
