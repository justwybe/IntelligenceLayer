"""Tests for ResidentManager — CRUD and context building."""


class TestResidentManager:
    def test_create_and_get(self, residents):
        rid = residents.create(name="Martha", room="204", notes="Loves gardening")
        r = residents.get(rid)
        assert r is not None
        assert r["name"] == "Martha"
        assert r["room"] == "204"
        assert r["notes"] == "Loves gardening"

    def test_find_by_name(self, residents):
        residents.create(name="Hans", room="101")
        r = residents.find_by_name("Hans")
        assert r is not None
        assert r["room"] == "101"

    def test_find_by_name_case_insensitive(self, residents):
        residents.create(name="Martha")
        r = residents.find_by_name("martha")
        assert r is not None
        assert r["name"] == "Martha"

    def test_find_by_name_not_found(self, residents):
        assert residents.find_by_name("Nobody") is None

    def test_list_all(self, residents):
        residents.create(name="Alice")
        residents.create(name="Bob")
        residents.create(name="Charlie")
        all_r = residents.list_all()
        names = [r["name"] for r in all_r]
        assert "Alice" in names
        assert "Bob" in names
        assert "Charlie" in names

    def test_update(self, residents):
        rid = residents.create(name="Martha", room="204")
        residents.update(rid, room="301", notes="Moved rooms")
        r = residents.get(rid)
        assert r["room"] == "301"
        assert r["notes"] == "Moved rooms"

    def test_update_ignores_unknown_fields(self, residents):
        rid = residents.create(name="Martha")
        residents.update(rid, unknown_field="ignored")
        r = residents.get(rid)
        assert r["name"] == "Martha"

    def test_delete(self, residents, store):
        rid = residents.create(name="Martha", room="204")
        residents.delete(rid)
        assert residents.get(rid) is None

    def test_delete_cascades_preferences(self, residents, preferences):
        rid = residents.create(name="Martha")
        preferences.set(rid, "food", "tea", "chamomile")
        residents.delete(rid)
        assert residents.get(rid) is None
        prefs = preferences.list_for_resident(rid)
        assert len(prefs) == 0

    def test_build_context(self, residents, preferences, task_logger):
        rid = residents.create(name="Martha", room="204", notes="Loves gardening")
        preferences.set(rid, "drink", "tea", "chamomile", confidence=0.9)
        preferences.set(rid, "activity", "hobby", "gardening", confidence=0.95)
        task_logger.log_task("fetch", "Brought glasses from room", resident_id=rid)

        ctx = residents.build_context(rid)
        assert "Martha" in ctx
        assert "204" in ctx
        assert "chamomile" in ctx
        assert "gardening" in ctx
        assert "fetch" in ctx

    def test_build_context_empty_resident(self, residents):
        assert residents.build_context("nonexistent") == ""
