"""SoulStore — SQLite-backed persistence for the Soul System.

Follows the WorkspaceStore pattern: thread-safe, WAL mode, migration versioning,
context-manager transactions. Stores resident profiles, preferences, facility
layout, task history, and conversation logs.
"""

from __future__ import annotations

from contextlib import contextmanager
import logging
import os
import sqlite3
import threading
import uuid

logger = logging.getLogger(__name__)

_SCHEMA_VERSION = 2


def _default_db_path() -> str:
    base = os.environ.get("WYBE_DATA_DIR", os.path.expanduser("~/.wybe_studio"))
    os.makedirs(base, exist_ok=True)
    return os.path.join(base, "soul.db")


class SoulStore:
    """Thread-safe SQLite wrapper for Soul System state."""

    def __init__(self, db_path: str | None = None):
        self._db_path = db_path or _default_db_path()
        self._local = threading.local()
        self._migrate()

    # -- connection handling ---------------------------------------------------

    @property
    def _conn(self) -> sqlite3.Connection:
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = sqlite3.connect(self._db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
            self._local.conn = conn
        return conn

    def close(self) -> None:
        conn = getattr(self._local, "conn", None)
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
            self._local.conn = None

    @contextmanager
    def _transaction(self):
        conn = self._conn
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    # -- schema migration ------------------------------------------------------

    def _migrate(self) -> None:
        c = self._conn

        c.execute(
            "CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL)"
        )
        row = c.execute("SELECT version FROM schema_version").fetchone()
        current_version = row[0] if row else 0

        if current_version < 1:
            c.executescript("""
                CREATE TABLE IF NOT EXISTS residents (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    room TEXT,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS preferences (
                    id TEXT PRIMARY KEY,
                    resident_id TEXT NOT NULL REFERENCES residents(id),
                    category TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    confidence REAL DEFAULT 0.5,
                    source TEXT DEFAULT 'observed',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(resident_id, category, key)
                );

                CREATE TABLE IF NOT EXISTS locations (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    location_type TEXT NOT NULL,
                    floor INTEGER DEFAULT 1,
                    description TEXT,
                    navigable INTEGER DEFAULT 1
                );

                CREATE TABLE IF NOT EXISTS objects (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    object_type TEXT,
                    location_id TEXT REFERENCES locations(id),
                    owner_resident_id TEXT REFERENCES residents(id),
                    description TEXT
                );

                CREATE TABLE IF NOT EXISTS task_history (
                    id TEXT PRIMARY KEY,
                    resident_id TEXT REFERENCES residents(id),
                    task_type TEXT NOT NULL,
                    description TEXT NOT NULL,
                    status TEXT DEFAULT 'completed',
                    result TEXT,
                    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    resident_id TEXT REFERENCES residents(id),
                    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    ended_at TIMESTAMP,
                    summary TEXT
                );

                CREATE TABLE IF NOT EXISTS conversation_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id TEXT NOT NULL REFERENCES conversations(id),
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                -- Indexes
                CREATE INDEX IF NOT EXISTS idx_preferences_resident
                    ON preferences(resident_id);
                CREATE INDEX IF NOT EXISTS idx_preferences_category
                    ON preferences(resident_id, category);
                CREATE INDEX IF NOT EXISTS idx_objects_location
                    ON objects(location_id);
                CREATE INDEX IF NOT EXISTS idx_objects_owner
                    ON objects(owner_resident_id);
                CREATE INDEX IF NOT EXISTS idx_task_history_resident
                    ON task_history(resident_id);
                CREATE INDEX IF NOT EXISTS idx_conversations_resident
                    ON conversations(resident_id);
                CREATE INDEX IF NOT EXISTS idx_conv_messages_conv
                    ON conversation_messages(conversation_id);
            """)

        if current_version < 2:
            c.executescript("""
                CREATE TABLE IF NOT EXISTS speaker_embeddings (
                    id TEXT PRIMARY KEY,
                    resident_id TEXT NOT NULL REFERENCES residents(id),
                    embedding BLOB NOT NULL,
                    audio_duration REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_speaker_emb_resident
                    ON speaker_embeddings(resident_id);
            """)

        if current_version == 0:
            c.execute(
                "INSERT INTO schema_version (version) VALUES (?)",
                (_SCHEMA_VERSION,),
            )
        elif current_version < _SCHEMA_VERSION:
            c.execute(
                "UPDATE schema_version SET version = ?", (_SCHEMA_VERSION,)
            )

        c.commit()

    # -- helpers ---------------------------------------------------------------

    @staticmethod
    def _new_id() -> str:
        return uuid.uuid4().hex[:12]

    def _row_to_dict(self, row: sqlite3.Row | None) -> dict | None:
        if row is None:
            return None
        return dict(row)

    def _rows_to_list(self, rows: list[sqlite3.Row]) -> list[dict]:
        return [dict(r) for r in rows]
