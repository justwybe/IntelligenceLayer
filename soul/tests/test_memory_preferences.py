"""Tests for PreferenceManager — confidence scoring and context building."""


class TestPreferenceManager:
    def test_set_new_preference(self, preferences, sample_resident):
        pid = preferences.set(sample_resident, "drink", "tea", "chamomile")
        pref = preferences.get(sample_resident, "drink", "tea")
        assert pref is not None
        assert pref["value"] == "chamomile"
        assert pref["confidence"] == 0.5

    def test_set_with_explicit_confidence(self, preferences, sample_resident):
        preferences.set(sample_resident, "food", "breakfast", "oatmeal", confidence=0.9)
        pref = preferences.get(sample_resident, "food", "breakfast")
        assert pref["confidence"] == 0.9

    def test_update_existing_boosts_confidence(self, preferences, sample_resident):
        preferences.set(sample_resident, "drink", "tea", "chamomile")
        preferences.set(sample_resident, "drink", "tea", "chamomile")  # repeat
        pref = preferences.get(sample_resident, "drink", "tea")
        assert pref["confidence"] == 0.65  # 0.5 + 0.15

    def test_confidence_caps_at_1(self, preferences, sample_resident):
        preferences.set(sample_resident, "drink", "tea", "chamomile", confidence=0.95)
        preferences.set(sample_resident, "drink", "tea", "chamomile")  # boost
        pref = preferences.get(sample_resident, "drink", "tea")
        assert pref["confidence"] == 1.0

    def test_update_changes_value(self, preferences, sample_resident):
        preferences.set(sample_resident, "drink", "tea", "chamomile")
        preferences.set(sample_resident, "drink", "tea", "earl grey")
        pref = preferences.get(sample_resident, "drink", "tea")
        assert pref["value"] == "earl grey"

    def test_list_for_resident(self, preferences, sample_resident):
        preferences.set(sample_resident, "drink", "tea", "chamomile")
        preferences.set(sample_resident, "food", "snack", "biscuits")
        preferences.set(sample_resident, "activity", "hobby", "gardening")
        prefs = preferences.list_for_resident(sample_resident)
        assert len(prefs) == 3

    def test_list_by_category(self, preferences, sample_resident):
        preferences.set(sample_resident, "food", "breakfast", "oatmeal")
        preferences.set(sample_resident, "food", "snack", "biscuits")
        preferences.set(sample_resident, "drink", "tea", "chamomile")
        prefs = preferences.list_for_resident(sample_resident, category="food")
        assert len(prefs) == 2

    def test_list_with_min_confidence(self, preferences, sample_resident):
        preferences.set(sample_resident, "food", "breakfast", "oatmeal", confidence=0.9)
        preferences.set(sample_resident, "food", "snack", "biscuits", confidence=0.2)
        prefs = preferences.list_for_resident(sample_resident, min_confidence=0.5)
        assert len(prefs) == 1
        assert prefs[0]["key"] == "breakfast"

    def test_reinforce(self, preferences, sample_resident):
        preferences.set(sample_resident, "drink", "tea", "chamomile")
        result = preferences.reinforce(sample_resident, "drink", "tea")
        assert result is True
        pref = preferences.get(sample_resident, "drink", "tea")
        assert pref["confidence"] == 0.65

    def test_reinforce_nonexistent(self, preferences, sample_resident):
        result = preferences.reinforce(sample_resident, "drink", "coffee")
        assert result is False

    def test_delete(self, preferences, sample_resident):
        pid = preferences.set(sample_resident, "drink", "tea", "chamomile")
        preferences.delete(pid)
        assert preferences.get(sample_resident, "drink", "tea") is None

    def test_build_preferences_context(self, preferences, sample_resident):
        preferences.set(sample_resident, "drink", "tea", "chamomile", confidence=0.9)
        preferences.set(sample_resident, "food", "snack", "biscuits", confidence=0.7)
        preferences.set(sample_resident, "activity", "hobby", "gardening", confidence=0.3)

        ctx = preferences.build_preferences_context(sample_resident, min_confidence=0.3)
        assert "Preferences:" in ctx
        assert "chamomile" in ctx
        assert "biscuits" in ctx
        assert "gardening" in ctx

    def test_build_preferences_context_empty(self, preferences, sample_resident):
        ctx = preferences.build_preferences_context(sample_resident)
        assert ctx == ""

    def test_source_tracking(self, preferences, sample_resident):
        preferences.set(sample_resident, "food", "allergy", "nuts", source="staff_reported")
        pref = preferences.get(sample_resident, "food", "allergy")
        assert pref["source"] == "staff_reported"
