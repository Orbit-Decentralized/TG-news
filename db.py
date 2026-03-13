"""
Use SQLite for persistent storage
Avoid losing sent records when the container restarts
"""
import os
import sqlite3
from datetime import datetime, timedelta, timezone

DB_PATH = os.environ.get(
    "SQLITE_DB_PATH",
    os.path.join(os.path.dirname(__file__), "sent_news.db"),
)


def _get_conn():
    return sqlite3.connect(DB_PATH)


async def init_db():
    """Initialize tables and clean records older than 7 days"""
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    cutoff_iso = cutoff.isoformat()
    with _get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sent_news (
                news_id TEXT PRIMARY KEY,
                source TEXT,
                title TEXT,
                url TEXT,
                sent_at TEXT
            )
            """
        )
        conn.execute(
            "DELETE FROM sent_news WHERE sent_at < ?",
            (cutoff_iso,),
        )


async def is_sent(news_id: str) -> bool:
    with _get_conn() as conn:
        cur = conn.execute(
            "SELECT 1 FROM sent_news WHERE news_id = ? LIMIT 1",
            (news_id,),
        )
        return cur.fetchone() is not None


async def mark_sent(news_id: str, source: str, title: str, url: str):
    sent_at = datetime.now(timezone.utc).isoformat()
    with _get_conn() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO sent_news (news_id, source, title, url, sent_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (news_id, source, title, url, sent_at),
        )


async def get_recent_titles(hours: int = 48) -> list[str]:
    """Get titles sent within the last N hours for dedup"""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    cutoff_iso = cutoff.isoformat()
    with _get_conn() as conn:
        cur = conn.execute(
            "SELECT title FROM sent_news WHERE sent_at > ?",
            (cutoff_iso,),
        )
        return [row[0] or "" for row in cur.fetchall()]
