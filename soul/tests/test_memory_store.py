"""Tests for SoulStore — SQLite schema, migrations, thread safety."""

import threading

from soul.memory.store import SoulStore


class TestSoulStore:
    def test_creates_tables(self, store):
        tables = store._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        table_names = {t["name"] for t in tables}
        assert "residents" in table_names
        assert "preferences" in table_names
        assert "locations" in table_names
        assert "objects" in table_names
        assert "task_history" in table_names
        assert "conversations" in table_names
        assert "conversation_messages" in table_names
        assert "schema_version" in table_names

    def test_schema_version(self, store):
        row = store._conn.execute("SELECT version FROM schema_version").fetchone()
        assert row["version"] == 1

    def test_idempotent_migration(self, db_path):
        """Running migration twice doesn't error."""
        s1 = SoulStore(db_path=db_path)
        s1.close()
        s2 = SoulStore(db_path=db_path)
        row = s2._conn.execute("SELECT version FROM schema_version").fetchone()
        assert row["version"] == 1
        s2.close()

    def test_wal_mode(self, store):
        mode = store._conn.execute("PRAGMA journal_mode").fetchone()
        assert mode[0] == "wal"

    def test_foreign_keys_enabled(self, store):
        fk = store._conn.execute("PRAGMA foreign_keys").fetchone()
        assert fk[0] == 1

    def test_new_id_format(self, store):
        id1 = store._new_id()
        id2 = store._new_id()
        assert len(id1) == 12
        assert id1 != id2
        assert id1.isalnum()

    def test_transaction_commit(self, store):
        with store._transaction():
            store._conn.execute(
                "INSERT INTO residents (id, name) VALUES (?, ?)",
                ("test1", "Alice"),
            )
        row = store._conn.execute("SELECT * FROM residents WHERE id = 'test1'").fetchone()
        assert row is not None
        assert row["name"] == "Alice"

    def test_transaction_rollback(self, store):
        try:
            with store._transaction():
                store._conn.execute(
                    "INSERT INTO residents (id, name) VALUES (?, ?)",
                    ("test2", "Bob"),
                )
                raise ValueError("oops")
        except ValueError:
            pass
        row = store._conn.execute("SELECT * FROM residents WHERE id = 'test2'").fetchone()
        assert row is None

    def test_thread_safety(self, db_path):
        """Each thread gets its own connection."""
        store = SoulStore(db_path=db_path)
        results = []

        def worker(name):
            rid = store._new_id()
            with store._transaction():
                store._conn.execute(
                    "INSERT INTO residents (id, name) VALUES (?, ?)",
                    (rid, name),
                )
            results.append(rid)

        threads = [threading.Thread(target=worker, args=(f"T{i}",)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(results) == 5
        rows = store._conn.execute("SELECT COUNT(*) as cnt FROM residents").fetchone()
        assert rows["cnt"] == 5
        store.close()

    def test_close(self, db_path):
        store = SoulStore(db_path=db_path)
        store.close()
        # Closing again should not raise
        store.close()
