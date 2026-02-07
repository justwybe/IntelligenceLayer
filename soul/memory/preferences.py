"""Learned preferences with confidence scoring.

Preferences are learned observations about residents. Confidence grows
with repeated observations and decays without reinforcement. Categories
include: food, drink, activity, schedule, social, comfort, health.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from soul.memory.store import SoulStore

logger = logging.getLogger(__name__)

# How much confidence increases per observation (capped at 1.0)
_CONFIDENCE_INCREMENT = 0.15
# Starting confidence for a new observation
_DEFAULT_CONFIDENCE = 0.5


class PreferenceManager:
    """Manages learned preferences with confidence scoring."""

    def __init__(self, store: SoulStore):
        self._store = store

    def set(
        self,
        resident_id: str,
        category: str,
        key: str,
        value: str,
        source: str = "observed",
        confidence: float | None = None,
    ) -> str:
        """Set or update a preference. If it exists, update value and boost confidence."""
        existing = self._store._conn.execute(
            "SELECT id, confidence FROM preferences "
            "WHERE resident_id = ? AND category = ? AND key = ?",
            (resident_id, category, key),
        ).fetchone()

        if existing:
            new_confidence = min(1.0, existing["confidence"] + _CONFIDENCE_INCREMENT)
            if confidence is not None:
                new_confidence = confidence
            self._store._conn.execute(
                "UPDATE preferences SET value = ?, confidence = ?, source = ?, "
                "updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (value, new_confidence, source, existing["id"]),
            )
            self._store._conn.commit()
            return existing["id"]
        else:
            pid = self._store._new_id()
            conf = confidence if confidence is not None else _DEFAULT_CONFIDENCE
            with self._store._transaction():
                self._store._conn.execute(
                    "INSERT INTO preferences "
                    "(id, resident_id, category, key, value, confidence, source) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (pid, resident_id, category, key, value, conf, source),
                )
            return pid

    def get(self, resident_id: str, category: str, key: str) -> dict | None:
        row = self._store._conn.execute(
            "SELECT * FROM preferences "
            "WHERE resident_id = ? AND category = ? AND key = ?",
            (resident_id, category, key),
        ).fetchone()
        return self._store._row_to_dict(row)

    def list_for_resident(
        self,
        resident_id: str,
        category: str | None = None,
        min_confidence: float = 0.0,
    ) -> list[dict]:
        sql = "SELECT * FROM preferences WHERE resident_id = ?"
        params: list = [resident_id]
        if category:
            sql += " AND category = ?"
            params.append(category)
        if min_confidence > 0:
            sql += " AND confidence >= ?"
            params.append(min_confidence)
        sql += " ORDER BY category, confidence DESC"
        rows = self._store._conn.execute(sql, params).fetchall()
        return self._store._rows_to_list(rows)

    def reinforce(self, resident_id: str, category: str, key: str) -> bool:
        """Boost confidence for an existing preference. Returns True if found."""
        existing = self._store._conn.execute(
            "SELECT id, confidence FROM preferences "
            "WHERE resident_id = ? AND category = ? AND key = ?",
            (resident_id, category, key),
        ).fetchone()
        if not existing:
            return False
        new_confidence = min(1.0, existing["confidence"] + _CONFIDENCE_INCREMENT)
        self._store._conn.execute(
            "UPDATE preferences SET confidence = ?, updated_at = CURRENT_TIMESTAMP "
            "WHERE id = ?",
            (new_confidence, existing["id"]),
        )
        self._store._conn.commit()
        return True

    def delete(self, preference_id: str) -> None:
        self._store._conn.execute(
            "DELETE FROM preferences WHERE id = ?", (preference_id,)
        )
        self._store._conn.commit()

    def build_preferences_context(
        self, resident_id: str, min_confidence: float = 0.3
    ) -> str:
        """Build a preferences summary for LLM context injection."""
        prefs = self.list_for_resident(
            resident_id, min_confidence=min_confidence
        )
        if not prefs:
            return ""

        by_category: dict[str, list[dict]] = {}
        for p in prefs:
            by_category.setdefault(p["category"], []).append(p)

        parts = []
        for cat, items in sorted(by_category.items()):
            entries = []
            for p in items:
                conf = f" ({p['confidence']:.0%})" if p["confidence"] < 0.9 else ""
                entries.append(f"{p['key']}: {p['value']}{conf}")
            parts.append(f"  {cat}: {', '.join(entries)}")

        return "Preferences:\n" + "\n".join(parts)
