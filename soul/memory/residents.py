"""Resident profile management — CRUD + context building for LLM prompts."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from soul.memory.store import SoulStore

logger = logging.getLogger(__name__)


class ResidentManager:
    """Manages resident profiles and builds context strings for LLM injection."""

    def __init__(self, store: SoulStore):
        self._store = store

    def create(
        self,
        name: str,
        room: str | None = None,
        notes: str | None = None,
    ) -> str:
        rid = self._store._new_id()
        with self._store._transaction():
            self._store._conn.execute(
                "INSERT INTO residents (id, name, room, notes) VALUES (?, ?, ?, ?)",
                (rid, name, room, notes),
            )
        logger.info("Created resident %s: %s", rid, name)
        return rid

    def get(self, resident_id: str) -> dict | None:
        row = self._store._conn.execute(
            "SELECT * FROM residents WHERE id = ?", (resident_id,)
        ).fetchone()
        return self._store._row_to_dict(row)

    def find_by_name(self, name: str) -> dict | None:
        row = self._store._conn.execute(
            "SELECT * FROM residents WHERE LOWER(name) = LOWER(?)", (name,)
        ).fetchone()
        return self._store._row_to_dict(row)

    def list_all(self) -> list[dict]:
        rows = self._store._conn.execute(
            "SELECT * FROM residents ORDER BY name"
        ).fetchall()
        return self._store._rows_to_list(rows)

    def update(self, resident_id: str, **kwargs) -> None:
        allowed = {"name", "room", "notes"}
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return
        updates["updated_at"] = "CURRENT_TIMESTAMP"
        set_parts = []
        values = []
        for k, v in updates.items():
            if v == "CURRENT_TIMESTAMP":
                set_parts.append(f"{k} = CURRENT_TIMESTAMP")
            else:
                set_parts.append(f"{k} = ?")
                values.append(v)
        values.append(resident_id)
        self._store._conn.execute(
            f"UPDATE residents SET {', '.join(set_parts)} WHERE id = ?",
            values,
        )
        self._store._conn.commit()

    def delete(self, resident_id: str) -> None:
        with self._store._transaction():
            self._store._conn.execute(
                "DELETE FROM conversation_messages WHERE conversation_id IN "
                "(SELECT id FROM conversations WHERE resident_id = ?)",
                (resident_id,),
            )
            self._store._conn.execute(
                "DELETE FROM conversations WHERE resident_id = ?",
                (resident_id,),
            )
            self._store._conn.execute(
                "DELETE FROM task_history WHERE resident_id = ?",
                (resident_id,),
            )
            self._store._conn.execute(
                "DELETE FROM preferences WHERE resident_id = ?",
                (resident_id,),
            )
            self._store._conn.execute(
                "UPDATE objects SET owner_resident_id = NULL WHERE owner_resident_id = ?",
                (resident_id,),
            )
            self._store._conn.execute(
                "DELETE FROM residents WHERE id = ?", (resident_id,)
            )

    def build_context(self, resident_id: str) -> str:
        """Build a context string about a resident for LLM prompt injection.

        Includes name, room, notes, preferences, and recent task history.
        """
        resident = self.get(resident_id)
        if not resident:
            return ""

        parts = [f"Resident: {resident['name']}"]
        if resident.get("room"):
            parts.append(f"Room: {resident['room']}")
        if resident.get("notes"):
            parts.append(f"Notes: {resident['notes']}")

        # Preferences
        prefs = self._store._conn.execute(
            "SELECT category, key, value, confidence FROM preferences "
            "WHERE resident_id = ? ORDER BY category, confidence DESC",
            (resident_id,),
        ).fetchall()
        if prefs:
            parts.append("Known preferences:")
            for p in prefs:
                conf = f" (confidence: {p['confidence']:.0%})" if p["confidence"] < 0.9 else ""
                parts.append(f"  - {p['category']}/{p['key']}: {p['value']}{conf}")

        # Recent tasks
        tasks = self._store._conn.execute(
            "SELECT task_type, description, status, started_at FROM task_history "
            "WHERE resident_id = ? ORDER BY started_at DESC LIMIT 5",
            (resident_id,),
        ).fetchall()
        if tasks:
            parts.append("Recent interactions:")
            for t in tasks:
                parts.append(f"  - [{t['started_at']}] {t['task_type']}: {t['description']} ({t['status']})")

        return "\n".join(parts)
