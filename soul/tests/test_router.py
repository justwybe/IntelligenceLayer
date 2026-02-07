"""Tests for the keyword-based intent router.

Covers 30+ utterances across all IntentCategory values, plus entity
extraction and confidence scoring.
"""

import pytest

from soul.cognition.router import classify, _extract_item, _extract_location
from soul.cognition.schemas import IntentCategory


# =========================================================================
# Emergency detection — highest priority, safety-critical
# =========================================================================

class TestEmergency:
    """Emergency keywords must always be detected, regardless of context."""

    @pytest.mark.parametrize("utterance", [
        "Help!",
        "I've fallen and I can't get up",
        "I'm in pain",
        "This is an emergency",
        "I think I'm having a heart attack",
        "I hurt my arm",
        "Call the nurse please",
        "I feel dizzy",
        "I can't breathe",
        "Someone call 911",
    ])
    def test_emergency_detected(self, utterance):
        intent = classify(utterance)
        assert intent.category == IntentCategory.EMERGENCY
        assert intent.confidence >= 0.9
        assert "trigger" in intent.entities

    def test_emergency_has_raw_text(self):
        intent = classify("Help me I fell!")
        assert intent.raw_text == "Help me I fell!"


# =========================================================================
# Greetings
# =========================================================================

class TestGreeting:

    @pytest.mark.parametrize("utterance", [
        "Hello!",
        "Hi there",
        "Good morning",
        "Good afternoon, how are you?",
        "Hey Wybe",
        "Nice to see you",
    ])
    def test_greeting_detected(self, utterance):
        intent = classify(utterance)
        assert intent.category == IntentCategory.GREETING
        assert intent.confidence >= 0.8


# =========================================================================
# Farewells
# =========================================================================

class TestFarewell:

    @pytest.mark.parametrize("utterance", [
        "Goodbye",
        "Bye bye",
        "See you later",
        "Good night",
        "Take care",
    ])
    def test_farewell_detected(self, utterance):
        intent = classify(utterance)
        assert intent.category == IntentCategory.FAREWELL
        assert intent.confidence >= 0.8


# =========================================================================
# Navigation requests
# =========================================================================

class TestNavigate:

    @pytest.mark.parametrize("utterance,expected_location", [
        ("Take me to the dining hall", "dining hall"),
        ("Can you go to the garden?", "garden"),
        ("Where is the lobby?", "lobby"),
        ("Navigate to room 204", "room 204"),
    ])
    def test_navigate_detected(self, utterance, expected_location):
        intent = classify(utterance)
        assert intent.category == IntentCategory.REQUEST_NAVIGATE
        assert intent.confidence >= 0.8
        if expected_location:
            assert "location" in intent.entities
            assert expected_location.lower() in intent.entities["location"].lower()


# =========================================================================
# Item requests
# =========================================================================

class TestRequestItem:

    @pytest.mark.parametrize("utterance,expected_item", [
        ("Bring me my glasses", "glasses"),
        ("Can you get me a glass of water?", "glass of water"),
        ("I need my medication", "medication"),
        ("Fetch my book please", "book"),
    ])
    def test_item_request_detected(self, utterance, expected_item):
        intent = classify(utterance)
        assert intent.category == IntentCategory.REQUEST_ITEM
        assert intent.confidence >= 0.8
        if expected_item:
            assert "item" in intent.entities
            assert expected_item.lower() in intent.entities["item"].lower()


# =========================================================================
# Preferences
# =========================================================================

class TestPreference:

    @pytest.mark.parametrize("utterance", [
        "I like chamomile tea",
        "I love watching the birds",
        "I prefer the window seat",
        "My favorite show is Jeopardy",
        "I always have coffee in the morning",
        "I don't like loud music",
    ])
    def test_preference_detected(self, utterance):
        intent = classify(utterance)
        assert intent.category == IntentCategory.PREFERENCE
        assert intent.confidence >= 0.7


# =========================================================================
# Information requests
# =========================================================================

class TestInformation:

    @pytest.mark.parametrize("utterance", [
        "What time is it?",
        "What's for lunch today?",
        "What activities are planned?",
        "When is bingo?",
        "What day is it?",
    ])
    def test_information_detected(self, utterance):
        intent = classify(utterance)
        assert intent.category == IntentCategory.INFORMATION
        assert intent.confidence >= 0.7


# =========================================================================
# Simple chat
# =========================================================================

class TestSimpleChat:

    @pytest.mark.parametrize("utterance", [
        "Thank you so much",
        "Yes please",
        "That's lovely",
        "Tell me a joke",
    ])
    def test_simple_chat_detected(self, utterance):
        intent = classify(utterance)
        assert intent.category == IntentCategory.SIMPLE_CHAT
        assert intent.confidence >= 0.6


# =========================================================================
# Complex plan (default / ambiguous)
# =========================================================================

class TestComplexPlan:

    @pytest.mark.parametrize("utterance", [
        "I'd like to organize a birthday party for next Tuesday",
        "Can you plan a movie night for the residents on floor 2?",
        "I want to rearrange the furniture in the lounge",
    ])
    def test_complex_falls_through(self, utterance):
        """Ambiguous utterances that don't match simpler patterns should
        fall through to complex_plan for Sonnet to handle."""
        intent = classify(utterance)
        assert intent.category == IntentCategory.COMPLEX_PLAN
        assert intent.confidence <= 0.6


# =========================================================================
# Entity extraction unit tests
# =========================================================================

class TestEntityExtraction:

    def test_extract_item_basic(self):
        assert _extract_item("bring me my glasses") == "glasses"

    def test_extract_item_with_article(self):
        assert _extract_item("get me a blanket") == "blanket"

    def test_extract_item_with_please(self):
        assert _extract_item("fetch my book please") == "book"

    def test_extract_item_none(self):
        assert _extract_item("hello there") is None

    def test_extract_location_basic(self):
        assert _extract_location("take me to the garden") == "garden"

    def test_extract_location_room(self):
        assert _extract_location("navigate to room 204") == "room 204"

    def test_extract_location_none(self):
        assert _extract_location("hello there") is None


# =========================================================================
# Priority ordering: emergency always wins
# =========================================================================

class TestPriority:

    def test_emergency_over_greeting(self):
        """'Help' should be emergency even if it contains a greeting-like word."""
        intent = classify("Hi, I need help, I fell!")
        assert intent.category == IntentCategory.EMERGENCY

    def test_emergency_over_item(self):
        intent = classify("Get me help, I'm in pain!")
        assert intent.category == IntentCategory.EMERGENCY

    def test_emergency_over_navigate(self):
        intent = classify("Take me to the nurse, I hurt myself")
        assert intent.category == IntentCategory.EMERGENCY


# =========================================================================
# Edge cases
# =========================================================================

class TestEdgeCases:

    def test_empty_string(self):
        intent = classify("")
        assert intent.category == IntentCategory.COMPLEX_PLAN
        assert intent.confidence == 0.5

    def test_whitespace_only(self):
        intent = classify("   ")
        assert intent.category == IntentCategory.COMPLEX_PLAN

    def test_raw_text_preserved(self):
        intent = classify("Hello there!")
        assert intent.raw_text == "Hello there!"

    def test_case_insensitive(self):
        intent = classify("HELLO")
        assert intent.category == IntentCategory.GREETING

    def test_case_insensitive_emergency(self):
        intent = classify("HELP ME!")
        assert intent.category == IntentCategory.EMERGENCY
