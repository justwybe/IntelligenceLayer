"""Facility map — locations, objects, and spatial context for navigation."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from soul.memory.store import SoulStore

logger = logging.getLogger(__name__)


class FacilityManager:
    """Manages facility locations and objects for navigation and fetch tasks."""

    def __init__(self, store: SoulStore):
        self._store = store

    # -- locations -------------------------------------------------------------

    def add_location(
        self,
        name: str,
        location_type: str,
        floor: int = 1,
        description: str | None = None,
        navigable: bool = True,
    ) -> str:
        lid = self._store._new_id()
        with self._store._transaction():
            self._store._conn.execute(
                "INSERT INTO locations (id, name, location_type, floor, description, navigable) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (lid, name, location_type, floor, description, int(navigable)),
            )
        return lid

    def get_location(self, location_id: str) -> dict | None:
        row = self._store._conn.execute(
            "SELECT * FROM locations WHERE id = ?", (location_id,)
        ).fetchone()
        return self._store._row_to_dict(row)

    def find_location(self, name: str) -> dict | None:
        row = self._store._conn.execute(
            "SELECT * FROM locations WHERE LOWER(name) = LOWER(?)", (name,)
        ).fetchone()
        return self._store._row_to_dict(row)

    def list_locations(self, location_type: str | None = None) -> list[dict]:
        if location_type:
            rows = self._store._conn.execute(
                "SELECT * FROM locations WHERE location_type = ? ORDER BY name",
                (location_type,),
            ).fetchall()
        else:
            rows = self._store._conn.execute(
                "SELECT * FROM locations ORDER BY name"
            ).fetchall()
        return self._store._rows_to_list(rows)

    def update_location(self, location_id: str, **kwargs) -> None:
        allowed = {"name", "location_type", "floor", "description", "navigable"}
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return
        if "navigable" in updates:
            updates["navigable"] = int(updates["navigable"])
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [location_id]
        self._store._conn.execute(
            f"UPDATE locations SET {set_clause} WHERE id = ?", values
        )
        self._store._conn.commit()

    def delete_location(self, location_id: str) -> None:
        with self._store._transaction():
            self._store._conn.execute(
                "UPDATE objects SET location_id = NULL WHERE location_id = ?",
                (location_id,),
            )
            self._store._conn.execute(
                "DELETE FROM locations WHERE id = ?", (location_id,)
            )

    # -- objects ----------------------------------------------------------------

    def add_object(
        self,
        name: str,
        object_type: str | None = None,
        location_id: str | None = None,
        owner_resident_id: str | None = None,
        description: str | None = None,
    ) -> str:
        oid = self._store._new_id()
        with self._store._transaction():
            self._store._conn.execute(
                "INSERT INTO objects (id, name, object_type, location_id, owner_resident_id, description) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (oid, name, object_type, location_id, owner_resident_id, description),
            )
        return oid

    def get_object(self, object_id: str) -> dict | None:
        row = self._store._conn.execute(
            "SELECT * FROM objects WHERE id = ?", (object_id,)
        ).fetchone()
        return self._store._row_to_dict(row)

    def find_objects(self, name: str) -> list[dict]:
        rows = self._store._conn.execute(
            "SELECT * FROM objects WHERE LOWER(name) LIKE LOWER(?)",
            (f"%{name}%",),
        ).fetchall()
        return self._store._rows_to_list(rows)

    def list_objects(
        self,
        location_id: str | None = None,
        owner_resident_id: str | None = None,
    ) -> list[dict]:
        sql = "SELECT * FROM objects WHERE 1=1"
        params: list = []
        if location_id:
            sql += " AND location_id = ?"
            params.append(location_id)
        if owner_resident_id:
            sql += " AND owner_resident_id = ?"
            params.append(owner_resident_id)
        sql += " ORDER BY name"
        rows = self._store._conn.execute(sql, params).fetchall()
        return self._store._rows_to_list(rows)

    def update_object(self, object_id: str, **kwargs) -> None:
        allowed = {"name", "object_type", "location_id", "owner_resident_id", "description"}
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [object_id]
        self._store._conn.execute(
            f"UPDATE objects SET {set_clause} WHERE id = ?", values
        )
        self._store._conn.commit()

    def delete_object(self, object_id: str) -> None:
        self._store._conn.execute(
            "DELETE FROM objects WHERE id = ?", (object_id,)
        )
        self._store._conn.commit()

    def build_facility_context(self) -> str:
        """Build a context string of the facility layout for LLM injection."""
        locations = self.list_locations()
        if not locations:
            return "No facility map configured."

        parts = ["Facility layout:"]
        for loc in locations:
            nav = "" if loc["navigable"] else " [not navigable]"
            desc = f" — {loc['description']}" if loc.get("description") else ""
            parts.append(f"  - {loc['name']} ({loc['location_type']}, floor {loc['floor']}){desc}{nav}")

            objects = self.list_objects(location_id=loc["id"])
            for obj in objects:
                owner = ""
                if obj.get("owner_resident_id"):
                    owner_row = self._store._conn.execute(
                        "SELECT name FROM residents WHERE id = ?",
                        (obj["owner_resident_id"],),
                    ).fetchone()
                    if owner_row:
                        owner = f" [belongs to {owner_row['name']}]"
                parts.append(f"      * {obj['name']}{owner}")

        return "\n".join(parts)
