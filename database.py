import sqlite3
import os
from datetime import date

import config

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "comments.db")


def _get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            video_id TEXT NOT NULL,
            video_title TEXT,
            profile_index INTEGER NOT NULL,
            comment TEXT NOT NULL,
            success INTEGER NOT NULL DEFAULT 0,
            error TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
        )
    """)
    conn.commit()
    return conn


def can_post(video_id: str) -> tuple[bool, str]:
    conn = _get_conn()
    row = conn.execute(
        "SELECT id FROM comments WHERE video_id = ? AND success = 1", (video_id,)
    ).fetchone()
    conn.close()
    if row:
        return False, "이 영상에는 이미 댓글을 달았습니다. (영상당 1개)"
    return True, ""


def get_posted_video_ids() -> set[str]:
    conn = _get_conn()
    rows = conn.execute(
        "SELECT DISTINCT video_id FROM comments WHERE success = 1"
    ).fetchall()
    conn.close()
    return {r["video_id"] for r in rows}


def today_count() -> int:
    conn = _get_conn()
    row = conn.execute(
        "SELECT COUNT(*) as cnt FROM comments WHERE success = 1 AND date(created_at) = ?",
        (date.today().isoformat(),),
    ).fetchone()
    conn.close()
    return row["cnt"]


def log_comment(video_id, video_title, profile_index, comment, success, error=None):
    config.log_event("comment_post", f"success={bool(success)} videoId={video_id} account={profile_index} "
                                     f"title={video_title} error={error} | {comment}")
    conn = _get_conn()
    conn.execute(
        "INSERT INTO comments (video_id, video_title, profile_index, comment, success, error) VALUES (?, ?, ?, ?, ?, ?)",
        (video_id, video_title, profile_index, comment, 1 if success else 0, error),
    )
    conn.commit()
    conn.close()


def get_history(limit=100):
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM comments ORDER BY created_at DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_history_by_date(target_date=None, limit=100):
    conn = _get_conn()
    if target_date:
        rows = conn.execute(
            "SELECT * FROM comments WHERE date(created_at) = ? ORDER BY created_at DESC LIMIT ?",
            (target_date.isoformat(), limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM comments ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
