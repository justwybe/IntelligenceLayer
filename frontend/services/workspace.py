"""WorkspaceStore — SQLite-backed persistence for Wybe Studio.

Stores metadata for projects, datasets, runs, models, evaluations, and
activity logs.  All heavy data (checkpoints, datasets, videos) stays on
the filesystem; the DB only records paths and metadata.
"""

from __future__ import annotations

from contextlib import contextmanager
import json
import logging
import os
import sqlite3
import threading
from typing import Any
import uuid


logger = logging.getLogger(__name__)

# Schema version — bump when adding/changing tables
_SCHEMA_VERSION = 2


def _default_db_path() -> str:
    base = os.environ.get("WYBE_DATA_DIR", os.path.expanduser("~/.wybe_studio"))
    os.makedirs(base, exist_ok=True)
    return os.path.join(base, "studio.db")


class WorkspaceStore:
    """Thread-safe SQLite wrapper for Wybe Studio state."""

    def __init__(self, db_path: str | None = None):
        self._db_path = db_path or _default_db_path()
        self._local = threading.local()
        self._migrate()

    # -- connection handling (one per thread) ----------------------------------

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
        """Close the connection for the current thread."""
        conn = getattr(self._local, "conn", None)
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
            self._local.conn = None

    @contextmanager
    def _transaction(self):
        """Context manager for atomic transactions.

        Commits on success, rolls back on exception.
        """
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

        # Create version tracking table
        c.execute(
            "CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL)"
        )
        row = c.execute("SELECT version FROM schema_version").fetchone()
        current_version = row[0] if row else 0

        if current_version < 1:
            c.executescript(
                """
                CREATE TABLE IF NOT EXISTS projects (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    embodiment_tag TEXT NOT NULL,
                    base_model TEXT DEFAULT 'nvidia/GR00T-N1.6-3B',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    notes TEXT
                );

                CREATE TABLE IF NOT EXISTS datasets (
                    id TEXT PRIMARY KEY,
                    project_id TEXT REFERENCES projects(id),
                    name TEXT NOT NULL,
                    path TEXT NOT NULL,
                    source TEXT,
                    parent_dataset_id TEXT,
                    episode_count INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT
                );

                CREATE TABLE IF NOT EXISTS models (
                    id TEXT PRIMARY KEY,
                    project_id TEXT REFERENCES projects(id),
                    name TEXT NOT NULL,
                    path TEXT NOT NULL,
                    source_run_id TEXT REFERENCES runs(id),
                    base_model TEXT,
                    embodiment_tag TEXT,
                    step INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    notes TEXT
                );

                CREATE TABLE IF NOT EXISTS runs (
                    id TEXT PRIMARY KEY,
                    project_id TEXT REFERENCES projects(id),
                    run_type TEXT NOT NULL,
                    dataset_id TEXT REFERENCES datasets(id),
                    model_id TEXT REFERENCES models(id),
                    config TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    log_path TEXT,
                    metrics TEXT,
                    pid INTEGER
                );

                CREATE TABLE IF NOT EXISTS evaluations (
                    id TEXT PRIMARY KEY,
                    run_id TEXT REFERENCES runs(id),
                    model_id TEXT REFERENCES models(id),
                    eval_type TEXT,
                    metrics TEXT,
                    artifacts TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS activity_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id TEXT REFERENCES projects(id),
                    event_type TEXT NOT NULL,
                    entity_type TEXT,
                    entity_id TEXT,
                    message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """
            )

        if current_version < 2:
            # Add indexes for common query patterns
            c.executescript(
                """
                CREATE INDEX IF NOT EXISTS idx_datasets_project ON datasets(project_id);
                CREATE INDEX IF NOT EXISTS idx_runs_project ON runs(project_id);
                CREATE INDEX IF NOT EXISTS idx_runs_status ON runs(status);
                CREATE INDEX IF NOT EXISTS idx_models_project ON models(project_id);
                CREATE INDEX IF NOT EXISTS idx_evaluations_run ON evaluations(run_id);
                CREATE INDEX IF NOT EXISTS idx_evaluations_model ON evaluations(model_id);
                CREATE INDEX IF NOT EXISTS idx_activity_project ON activity_log(project_id);
                """
            )

        # Update version tracker
        if current_version == 0:
            c.execute("INSERT INTO schema_version (version) VALUES (?)", (_SCHEMA_VERSION,))
        elif current_version < _SCHEMA_VERSION:
            c.execute("UPDATE schema_version SET version = ?", (_SCHEMA_VERSION,))

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

    # -- projects --------------------------------------------------------------

    def create_project(
        self,
        name: str,
        embodiment_tag: str,
        base_model: str = "nvidia/GR00T-N1.6-3B",
        notes: str = "",
    ) -> str:
        pid = self._new_id()
        with self._transaction():
            self._conn.execute(
                "INSERT INTO projects (id, name, embodiment_tag, base_model, notes) VALUES (?, ?, ?, ?, ?)",
                (pid, name, embodiment_tag, base_model, notes),
            )
            self._conn.execute(
                """INSERT INTO activity_log
                   (project_id, event_type, entity_type, entity_id, message)
                   VALUES (?, ?, ?, ?, ?)""",
                (pid, "project_created", "project", pid, f"Project '{name}' created"),
            )
        return pid

    def list_projects(self) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM projects ORDER BY created_at DESC"
        ).fetchall()
        return self._rows_to_list(rows)

    def get_project(self, project_id: str) -> dict | None:
        row = self._conn.execute(
            "SELECT * FROM projects WHERE id = ?", (project_id,)
        ).fetchone()
        return self._row_to_dict(row)

    def delete_project(self, project_id: str) -> None:
        with self._transaction():
            self._conn.execute("DELETE FROM activity_log WHERE project_id = ?", (project_id,))
            self._conn.execute("DELETE FROM evaluations WHERE run_id IN (SELECT id FROM runs WHERE project_id = ?)", (project_id,))
            self._conn.execute("DELETE FROM runs WHERE project_id = ?", (project_id,))
            self._conn.execute("DELETE FROM models WHERE project_id = ?", (project_id,))
            self._conn.execute("DELETE FROM datasets WHERE project_id = ?", (project_id,))
            self._conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))

    # -- datasets --------------------------------------------------------------

    def register_dataset(
        self,
        project_id: str,
        name: str,
        path: str,
        source: str = "imported",
        parent_dataset_id: str | None = None,
        episode_count: int | None = None,
        metadata: dict | None = None,
    ) -> str:
        did = self._new_id()
        with self._transaction():
            self._conn.execute(
                """INSERT INTO datasets
                   (id, project_id, name, path, source, parent_dataset_id, episode_count, metadata)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    did,
                    project_id,
                    name,
                    path,
                    source,
                    parent_dataset_id,
                    episode_count,
                    json.dumps(metadata) if metadata else None,
                ),
            )
            self._conn.execute(
                """INSERT INTO activity_log
                   (project_id, event_type, entity_type, entity_id, message)
                   VALUES (?, ?, ?, ?, ?)""",
                (project_id, "dataset_registered", "dataset", did, f"Dataset '{name}' registered"),
            )
        return did

    def list_datasets(self, project_id: str | None = None) -> list[dict]:
        if project_id:
            rows = self._conn.execute(
                "SELECT * FROM datasets WHERE project_id = ? ORDER BY created_at DESC",
                (project_id,),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM datasets ORDER BY created_at DESC"
            ).fetchall()
        return self._rows_to_list(rows)

    def get_dataset(self, dataset_id: str) -> dict | None:
        row = self._conn.execute(
            "SELECT * FROM datasets WHERE id = ?", (dataset_id,)
        ).fetchone()
        return self._row_to_dict(row)

    def delete_dataset(self, dataset_id: str) -> None:
        with self._transaction():
            self._conn.execute("DELETE FROM datasets WHERE id = ?", (dataset_id,))

    # -- runs ------------------------------------------------------------------

    def create_run(
        self,
        project_id: str,
        run_type: str,
        config: dict,
        dataset_id: str | None = None,
        model_id: str | None = None,
    ) -> str:
        rid = self._new_id()
        with self._transaction():
            self._conn.execute(
                """INSERT INTO runs
                   (id, project_id, run_type, dataset_id, model_id, config, status)
                   VALUES (?, ?, ?, ?, ?, ?, 'pending')""",
                (rid, project_id, run_type, dataset_id, model_id, json.dumps(config)),
            )
            self._conn.execute(
                """INSERT INTO activity_log
                   (project_id, event_type, entity_type, entity_id, message)
                   VALUES (?, ?, ?, ?, ?)""",
                (project_id, "run_created", "run", rid, f"{run_type} run created"),
            )
        return rid

    def update_run(self, run_id: str, **kwargs: Any) -> None:
        allowed = {"status", "started_at", "completed_at", "log_path", "metrics", "pid"}
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return
        if "metrics" in updates and isinstance(updates["metrics"], dict):
            updates["metrics"] = json.dumps(updates["metrics"])
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [run_id]
        self._conn.execute(
            f"UPDATE runs SET {set_clause} WHERE id = ?", values  # noqa: S608
        )
        self._conn.commit()

    def get_run(self, run_id: str) -> dict | None:
        row = self._conn.execute(
            "SELECT * FROM runs WHERE id = ?", (run_id,)
        ).fetchone()
        return self._row_to_dict(row)

    def list_runs(
        self,
        project_id: str | None = None,
        run_type: str | None = None,
    ) -> list[dict]:
        sql = "SELECT * FROM runs WHERE 1=1"
        params: list = []
        if project_id:
            sql += " AND project_id = ?"
            params.append(project_id)
        if run_type:
            sql += " AND run_type = ?"
            params.append(run_type)
        sql += " ORDER BY started_at DESC NULLS LAST"
        rows = self._conn.execute(sql, params).fetchall()
        return self._rows_to_list(rows)

    def get_active_runs(self) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM runs WHERE status IN ('pending', 'running') ORDER BY started_at DESC"
        ).fetchall()
        return self._rows_to_list(rows)

    # -- models ----------------------------------------------------------------

    def register_model(
        self,
        project_id: str,
        name: str,
        path: str,
        source_run_id: str | None = None,
        base_model: str | None = None,
        embodiment_tag: str | None = None,
        step: int | None = None,
        notes: str = "",
    ) -> str:
        mid = self._new_id()
        with self._transaction():
            self._conn.execute(
                """INSERT INTO models
                   (id, project_id, name, path, source_run_id, base_model, embodiment_tag, step, notes)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (mid, project_id, name, path, source_run_id, base_model, embodiment_tag, step, notes),
            )
            self._conn.execute(
                """INSERT INTO activity_log
                   (project_id, event_type, entity_type, entity_id, message)
                   VALUES (?, ?, ?, ?, ?)""",
                (project_id, "model_registered", "model", mid, f"Model '{name}' registered"),
            )
        return mid

    def list_models(self, project_id: str | None = None) -> list[dict]:
        if project_id:
            rows = self._conn.execute(
                "SELECT * FROM models WHERE project_id = ? ORDER BY created_at DESC",
                (project_id,),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM models ORDER BY created_at DESC"
            ).fetchall()
        return self._rows_to_list(rows)

    def get_model(self, model_id: str) -> dict | None:
        row = self._conn.execute(
            "SELECT * FROM models WHERE id = ?", (model_id,)
        ).fetchone()
        return self._row_to_dict(row)

    # -- evaluations -----------------------------------------------------------

    def save_evaluation(
        self,
        run_id: str,
        model_id: str,
        eval_type: str,
        metrics: dict,
        artifacts: dict | None = None,
    ) -> str:
        eid = self._new_id()
        self._conn.execute(
            """INSERT INTO evaluations
               (id, run_id, model_id, eval_type, metrics, artifacts)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                eid,
                run_id,
                model_id or None,  # Store NULL instead of empty string for FK safety
                eval_type,
                json.dumps(metrics),
                json.dumps(artifacts) if artifacts else None,
            ),
        )
        self._conn.commit()
        return eid

    def list_evaluations(self, model_id: str | None = None, run_id: str | None = None) -> list[dict]:
        sql = "SELECT * FROM evaluations WHERE 1=1"
        params: list = []
        if model_id:
            sql += " AND model_id = ?"
            params.append(model_id)
        if run_id:
            sql += " AND run_id = ?"
            params.append(run_id)
        sql += " ORDER BY created_at DESC"
        rows = self._conn.execute(sql, params).fetchall()
        return self._rows_to_list(rows)

    # -- activity log ----------------------------------------------------------

    def log_activity(
        self,
        project_id: str | None,
        event_type: str,
        entity_type: str | None = None,
        entity_id: str | None = None,
        message: str = "",
    ) -> None:
        self._conn.execute(
            """INSERT INTO activity_log
               (project_id, event_type, entity_type, entity_id, message)
               VALUES (?, ?, ?, ?, ?)""",
            (project_id, event_type, entity_type, entity_id, message),
        )
        self._conn.commit()

    def recent_activity(
        self,
        project_id: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        if project_id:
            rows = self._conn.execute(
                "SELECT * FROM activity_log WHERE project_id = ? ORDER BY created_at DESC LIMIT ?",
                (project_id, limit),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM activity_log ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return self._rows_to_list(rows)
