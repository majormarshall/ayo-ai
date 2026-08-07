"""
AYO AI — SQLite Memory Store
==============================
Persists conversation history, user preferences, enrolled voice
profiles metadata, and action logs.
"""

import sqlite3
import json
import logging
from pathlib import Path
from datetime import datetime

log = logging.getLogger("ayo.memory")
DB_PATH = Path(__file__).parents[2] / "data" / "db" / "ayo.db"


class MemoryStore:
    def __init__(self):
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        self._create_tables()
        log.info(f"💾 Memory store ready at {DB_PATH}")

    def _create_tables(self):
        c = self.conn.cursor()
        c.executescript("""
            CREATE TABLE IF NOT EXISTS conversations (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp   TEXT NOT NULL,
                speaker     TEXT NOT NULL,
                role        TEXT NOT NULL,
                content     TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS voice_profiles (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT UNIQUE NOT NULL,
                created_at  TEXT NOT NULL,
                sample_count INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS action_log (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp   TEXT NOT NULL,
                speaker     TEXT NOT NULL,
                action      TEXT NOT NULL,
                params      TEXT,
                result      TEXT
            );

            CREATE TABLE IF NOT EXISTS settings (
                key   TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
        """)
        self.conn.commit()

    # ── Conversations ─────────────────────────────────────────────────────────

    def add_message(self, speaker: str, role: str, content: str):
        c = self.conn.cursor()
        c.execute(
            "INSERT INTO conversations (timestamp, speaker, role, content) VALUES (?, ?, ?, ?)",
            (datetime.now().isoformat(), speaker, role, content)
        )
        self.conn.commit()

    def get_history(self, speaker: str = None, limit: int = 20) -> list[dict]:
        c = self.conn.cursor()
        if speaker:
            rows = c.execute(
                "SELECT role, content FROM conversations WHERE speaker=? "
                "ORDER BY id DESC LIMIT ?", (speaker, limit)
            ).fetchall()
        else:
            rows = c.execute(
                "SELECT role, content FROM conversations ORDER BY id DESC LIMIT ?",
                (limit,)
            ).fetchall()
        return [{"role": r, "content": c} for r, c in reversed(rows)]

    def clear_history(self, speaker: str = None):
        c = self.conn.cursor()
        if speaker:
            c.execute("DELETE FROM conversations WHERE speaker=?", (speaker,))
        else:
            c.execute("DELETE FROM conversations")
        self.conn.commit()

    # ── Voice Profiles ────────────────────────────────────────────────────────

    def register_voice_profile(self, name: str, sample_count: int = 0):
        c = self.conn.cursor()
        c.execute(
            "INSERT OR REPLACE INTO voice_profiles (name, created_at, sample_count) "
            "VALUES (?, ?, ?)",
            (name, datetime.now().isoformat(), sample_count)
        )
        self.conn.commit()

    def delete_voice_profile(self, name: str):
        c = self.conn.cursor()
        c.execute("DELETE FROM voice_profiles WHERE name=?", (name,))
        self.conn.commit()

    def list_voice_profiles(self) -> list[dict]:
        c = self.conn.cursor()
        rows = c.execute(
            "SELECT name, created_at, sample_count FROM voice_profiles ORDER BY created_at"
        ).fetchall()
        return [{"name": n, "created_at": ca, "samples": sc} for n, ca, sc in rows]

    # ── Action Log ────────────────────────────────────────────────────────────

    def log_action(self, speaker: str, action: str, params: dict, result: str):
        c = self.conn.cursor()
        c.execute(
            "INSERT INTO action_log (timestamp, speaker, action, params, result) "
            "VALUES (?, ?, ?, ?, ?)",
            (datetime.now().isoformat(), speaker, action, json.dumps(params), result)
        )
        self.conn.commit()

    # ── Settings ──────────────────────────────────────────────────────────────

    def get_setting(self, key: str, default=None):
        c = self.conn.cursor()
        row = c.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return row[0] if row else default

    def set_setting(self, key: str, value: str):
        c = self.conn.cursor()
        c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                  (key, str(value)))
        self.conn.commit()
