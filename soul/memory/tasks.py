"""Task history — logging completed and in-progress tasks for context."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from soul.memory.store import SoulStore

logger = logging.getLogger(__name__)


class TaskLogger:
    """Logs task execution history for residents."""

    def __init__(self, store: SoulStore):
        self._store = store

    def log_task(
        self,
        task_type: str,
        description: str,
        resident_id: str | None = None,
        status: str = "completed",
        result: str | None = None,
    ) -> str:
        tid = self._store._new_id()
        with self._store._transaction():
            self._store._conn.execute(
                "INSERT INTO task_history "
                "(id, resident_id, task_type, description, status, result) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (tid, resident_id, task_type, description, status, result),
            )
        return tid

    def update_task(self, task_id: str, status: str, result: str | None = None) -> None:
        self._store._conn.execute(
            "UPDATE task_history SET status = ?, result = ?, "
            "completed_at = CURRENT_TIMESTAMP WHERE id = ?",
            (status, result, task_id),
        )
        self._store._conn.commit()

    def get_task(self, task_id: str) -> dict | None:
        row = self._store._conn.execute(
            "SELECT * FROM task_history WHERE id = ?", (task_id,)
        ).fetchone()
        return self._store._row_to_dict(row)

    def recent_tasks(
        self,
        resident_id: str | None = None,
        limit: int = 20,
        task_type: str | None = None,
    ) -> list[dict]:
        sql = "SELECT * FROM task_history WHERE 1=1"
        params: list = []
        if resident_id:
            sql += " AND resident_id = ?"
            params.append(resident_id)
        if task_type:
            sql += " AND task_type = ?"
            params.append(task_type)
        sql += " ORDER BY started_at DESC LIMIT ?"
        params.append(limit)
        rows = self._store._conn.execute(sql, params).fetchall()
        return self._store._rows_to_list(rows)

    # -- conversations ---------------------------------------------------------

    def start_conversation(self, resident_id: str | None = None) -> str:
        cid = self._store._new_id()
        with self._store._transaction():
            self._store._conn.execute(
                "INSERT INTO conversations (id, resident_id) VALUES (?, ?)",
                (cid, resident_id),
            )
        return cid

    def add_message(
        self, conversation_id: str, role: str, content: str
    ) -> None:
        self._store._conn.execute(
            "INSERT INTO conversation_messages (conversation_id, role, content) "
            "VALUES (?, ?, ?)",
            (conversation_id, role, content),
        )
        self._store._conn.commit()

    def end_conversation(
        self, conversation_id: str, summary: str | None = None
    ) -> None:
        self._store._conn.execute(
            "UPDATE conversations SET ended_at = CURRENT_TIMESTAMP, summary = ? "
            "WHERE id = ?",
            (summary, conversation_id),
        )
        self._store._conn.commit()

    def get_conversation_messages(
        self, conversation_id: str
    ) -> list[dict]:
        rows = self._store._conn.execute(
            "SELECT * FROM conversation_messages "
            "WHERE conversation_id = ? ORDER BY created_at ASC",
            (conversation_id,),
        ).fetchall()
        return self._store._rows_to_list(rows)

    def recent_conversations(
        self, resident_id: str | None = None, limit: int = 10
    ) -> list[dict]:
        if resident_id:
            rows = self._store._conn.execute(
                "SELECT * FROM conversations WHERE resident_id = ? "
                "ORDER BY started_at DESC LIMIT ?",
                (resident_id, limit),
            ).fetchall()
        else:
            rows = self._store._conn.execute(
                "SELECT * FROM conversations ORDER BY started_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return self._store._rows_to_list(rows)
