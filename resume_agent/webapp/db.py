"""SQLite-backed users + per-user resume metadata, plus on-disk resume folders."""

from __future__ import annotations

import os
import secrets
import shutil
import sqlite3
import time
from pathlib import Path

from resume_agent.library import _slugify


def home() -> Path:
    return Path(os.environ.get("RESUME_AGENT_HOME", "~/.resume-agent")).expanduser()


def web_dir() -> Path:
    d = home() / "web"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _db_path() -> Path:
    return web_dir() / "app.db"


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    with get_conn() as c:
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                email         TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created       REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS resumes (
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                name    TEXT NOT NULL,
                slug    TEXT NOT NULL,
                status  TEXT NOT NULL DEFAULT 'new',
                created REAL NOT NULL,
                updated REAL NOT NULL
            );
            """
        )
    # Any resume left 'building' from a previous (crashed) run is stale.
    with get_conn() as c:
        c.execute("UPDATE resumes SET status='error' WHERE status='building'")


def secret_key() -> str:
    p = web_dir() / "secret_key"
    if not p.exists():
        p.write_text(secrets.token_hex(32), encoding="utf-8")
    return p.read_text(encoding="utf-8").strip()


# -- users -------------------------------------------------------------------


def create_user(email: str, password_hash: str) -> int:
    now = time.time()
    with get_conn() as c:
        cur = c.execute(
            "INSERT INTO users (email, password_hash, created) VALUES (?, ?, ?)",
            (email.strip().lower(), password_hash, now),
        )
        return int(cur.lastrowid)


def get_user_by_email(email: str) -> sqlite3.Row | None:
    with get_conn() as c:
        return c.execute(
            "SELECT * FROM users WHERE email = ?", (email.strip().lower(),)
        ).fetchone()


def get_user(user_id: int) -> sqlite3.Row | None:
    with get_conn() as c:
        return c.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


# -- resumes -----------------------------------------------------------------


def create_resume(user_id: int, name: str) -> int:
    now = time.time()
    with get_conn() as c:
        cur = c.execute(
            "INSERT INTO resumes (user_id, name, slug, status, created, updated) "
            "VALUES (?, ?, ?, 'new', ?, ?)",
            (user_id, name.strip(), _slugify(name), now, now),
        )
        return int(cur.lastrowid)


def list_resumes(user_id: int) -> list[sqlite3.Row]:
    with get_conn() as c:
        return c.execute(
            "SELECT * FROM resumes WHERE user_id = ? ORDER BY updated DESC", (user_id,)
        ).fetchall()


def get_resume(resume_id: int) -> sqlite3.Row | None:
    with get_conn() as c:
        return c.execute("SELECT * FROM resumes WHERE id = ?", (resume_id,)).fetchone()


def set_status(resume_id: int, status: str) -> None:
    with get_conn() as c:
        c.execute(
            "UPDATE resumes SET status = ?, updated = ? WHERE id = ?",
            (status, time.time(), resume_id),
        )


def rename_resume(resume_id: int, name: str) -> None:
    with get_conn() as c:
        c.execute(
            "UPDATE resumes SET name = ?, slug = ?, updated = ? WHERE id = ?",
            (name.strip(), _slugify(name), time.time(), resume_id),
        )


def delete_resume(resume_id: int) -> None:
    r = get_resume(resume_id)
    if r is not None:
        shutil.rmtree(resume_dir(r["user_id"], resume_id), ignore_errors=True)
    with get_conn() as c:
        c.execute("DELETE FROM resumes WHERE id = ?", (resume_id,))


def resume_dir(user_id: int, resume_id: int) -> Path:
    d = web_dir() / "users" / str(user_id) / str(resume_id)
    d.mkdir(parents=True, exist_ok=True)
    return d


def resume_pdf(user_id: int, resume_id: int) -> Path | None:
    pdf = resume_dir(user_id, resume_id) / "main.pdf"
    return pdf if pdf.exists() else None
