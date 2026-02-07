"""Keyword-based intent classifier — no API calls, microsecond execution.

Routes utterances to IntentCategory based on keyword matching and heuristics.
When in doubt, routes to complex_plan (Sonnet) so the heavier model can decide.
"""

from __future__ import annotations

import re
from soul.cognition.schemas import Intent, IntentCategory


# ---------------------------------------------------------------------------
# Keyword dictionaries — order matters: checked from highest to lowest priority
# ---------------------------------------------------------------------------

_EMERGENCY_KEYWORDS = {
    "help", "fall", "fallen", "fell", "pain", "emergency", "hurt", "hurts",
    "bleeding", "chest", "breathe", "breath", "can't breathe", "dizzy",
    "faint", "unconscious", "ambulance", "911", "stroke", "heart attack",
    "choking", "fire", "sos", "urgent", "call nurse", "nurse",
}

_GREETING_PATTERNS = [
    r"\b(hello|hi|hey|good\s+morning|good\s+afternoon|good\s+evening|howdy|hiya)\b",
    r"^(hi|hey|hello)[\!\.\,]?\s*$",
    r"\bhow\s+are\s+you\b",
    r"\bnice\s+to\s+(see|meet)\b",
]

_FAREWELL_PATTERNS = [
    r"\b(goodbye|bye|see\s+you|good\s+night|goodnight|take\s+care|farewell|later|so\s+long)\b",
    r"\bsee\s+you\s+(later|tomorrow|soon)\b",
    r"\bgood\s*night\b",
]

_NAVIGATE_KEYWORDS = {
    "go to", "take me", "bring me to", "walk me", "navigate", "escort",
    "where is", "how do i get to", "lead me", "show me the way",
    "walk to", "move to", "go back", "return to",
}

_ITEM_KEYWORDS = {
    "bring", "fetch", "get me", "could you get", "can you get",
    "i need my", "grab", "hand me", "pass me",
    "bring me", "get my", "find my", "where is my", "where are my",
    "give me", "could i have", "can i have", "may i have",
}

# "i need" and "i want" are only item requests when followed by a/my/the/some + noun,
# not "to + verb" (which indicates a complex plan).
_ITEM_PATTERNS = [
    r"\bi\s+(?:need|want)\s+(?:my|a|an|the|some)\s+\w+",
]

_HELP_KEYWORDS = {
    "help me", "assist", "i'm stuck", "i can't", "having trouble",
    "confused", "don't understand", "what should i", "how do i",
    "can you help", "need help", "need assistance",
}

_PREFERENCE_PATTERNS = [
    r"\bi\s+(like|love|prefer|enjoy|hate|dislike|don't\s+like|can't\s+stand)\b",
    r"\bmy\s+favorite\b",
    r"\bi\s+always\s+(want|have|take|drink|eat)\b",
    r"\bi\s+usually\b",
    r"\bdon't\s+give\s+me\b",
    r"\bi\s+never\s+(want|eat|drink|like)\b",
]

_INFORMATION_PATTERNS = [
    r"\bwhat\s+(time|day|date|year)\b",
    r"\bwhat('s|\s+is)\s+the\s+(weather|temperature|time|date|day)\b",
    r"\bwhat('s|\s+is)\s+for\s+(lunch|dinner|breakfast)\b",
    r"\btell\s+me\s+about\b",
    r"\bwhat\s+activities\b",
    r"\bwhen\s+is\b",
    r"\bwho\s+is\b",
    r"\bwhat('s|\s+is)\s+happening\b",
    r"\bschedule\b",
    r"\bmenu\b",
]

_SIMPLE_CHAT_PATTERNS = [
    r"\b(thank|thanks|thank\s+you)\b",
    r"\b(yes|no|yeah|nah|yep|nope|okay|ok|sure|alright)\b",
    r"\b(that's\s+nice|wonderful|lovely|great)\b",
    r"\btell\s+me\s+a\s+(joke|story)\b",
    r"\b(weather|beautiful\s+day)\b",
    r"\bhow('s|\s+is)\s+the\s+weather\b",
    r"\byou('re|\s+are)\s+(nice|kind|sweet|funny|wonderful)\b",
    r"\bi('m|\s+am)\s+(fine|good|well|okay|ok|great|tired|bored)\b",
]


# ---------------------------------------------------------------------------
# Entity extraction helpers
# ---------------------------------------------------------------------------

def _extract_item(text: str) -> str | None:
    """Try to extract an item name from a request."""
    patterns = [
        r"(?:bring|fetch|get|grab|hand|pass|give)\s+(?:me\s+)?(?:my\s+)?(?:a\s+)?(?:the\s+)?(.+?)(?:\s+please|\s*[\.!\?]?\s*$)",
        r"(?:i\s+need|i\s+want|could\s+i\s+have|can\s+i\s+have|may\s+i\s+have)\s+(?:my\s+)?(?:a\s+)?(?:the\s+)?(.+?)(?:\s+please|\s*[\.!\?]?\s*$)",
        r"(?:find|where\s+is|where\s+are)\s+(?:my\s+)?(?:the\s+)?(.+?)(?:\s*[\.!\?]?\s*$)",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            item = m.group(1).strip().rstrip(".,!?")
            if item and len(item) < 60:
                return item
    return None


def _extract_location(text: str) -> str | None:
    """Try to extract a location/destination from a request."""
    patterns = [
        r"(?:go\s+to|take\s+me\s+to|bring\s+me\s+to|walk\s+me\s+to|navigate\s+to|escort\s+me\s+to|lead\s+me\s+to)\s+(?:the\s+)?(.+?)(?:\s+please|\s*[\.!\?]?\s*$)",
        r"(?:where\s+is|how\s+do\s+i\s+get\s+to)\s+(?:the\s+)?(.+?)(?:\s*[\.!\?]?\s*$)",
        r"(?:return\s+to|go\s+back\s+to|walk\s+to|move\s+to)\s+(?:the\s+)?(.+?)(?:\s+please|\s*[\.!\?]?\s*$)",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            loc = m.group(1).strip().rstrip(".,!?")
            if loc and len(loc) < 60:
                return loc
    return None


def _extract_person(text: str) -> str | None:
    """Try to extract a person name from a request."""
    patterns = [
        r"(?:tell|ask|call|find|see|visit|talk\s+to)\s+(\w+)",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            name = m.group(1).strip()
            # Filter out common non-names
            if name.lower() not in {"me", "us", "them", "her", "him", "it", "the", "a", "an", "my"}:
                return name
    return None


# ---------------------------------------------------------------------------
# Main classification
# ---------------------------------------------------------------------------

def classify(text: str) -> Intent:
    """Classify an utterance into an Intent (category + entities + confidence).

    Priority order:
    1. Emergency (always first — safety critical)
    2. Greeting / Farewell (social niceties)
    3. Navigation requests
    4. Item requests
    5. Preferences (learning about the resident)
    6. Information requests
    7. Help requests
    8. Simple chat
    9. Default → complex_plan (let Sonnet figure it out)
    """
    lower = text.lower().strip()
    entities: dict[str, str] = {}

    # ---- 1. Emergency (highest priority) ----
    for kw in _EMERGENCY_KEYWORDS:
        if kw in lower:
            return Intent(
                category=IntentCategory.EMERGENCY,
                confidence=0.95,
                entities={"trigger": kw},
                raw_text=text,
            )

    # ---- 2. Greeting ----
    for pat in _GREETING_PATTERNS:
        if re.search(pat, lower):
            return Intent(
                category=IntentCategory.GREETING,
                confidence=0.9,
                entities={},
                raw_text=text,
            )

    # ---- 3. Farewell ----
    for pat in _FAREWELL_PATTERNS:
        if re.search(pat, lower):
            return Intent(
                category=IntentCategory.FAREWELL,
                confidence=0.9,
                entities={},
                raw_text=text,
            )

    # ---- 4. Navigation requests ----
    for kw in _NAVIGATE_KEYWORDS:
        if kw in lower:
            loc = _extract_location(text)
            if loc:
                entities["location"] = loc
            return Intent(
                category=IntentCategory.REQUEST_NAVIGATE,
                confidence=0.85,
                entities=entities,
                raw_text=text,
            )

    # ---- 5. Item requests ----
    item_match = False
    for kw in _ITEM_KEYWORDS:
        if kw in lower:
            item_match = True
            break
    if not item_match:
        for pat in _ITEM_PATTERNS:
            if re.search(pat, lower):
                item_match = True
                break
    if item_match:
        item = _extract_item(text)
        if item:
            entities["item"] = item
        return Intent(
            category=IntentCategory.REQUEST_ITEM,
            confidence=0.85,
            entities=entities,
            raw_text=text,
        )

    # ---- 6. Preferences ----
    for pat in _PREFERENCE_PATTERNS:
        if re.search(pat, lower):
            return Intent(
                category=IntentCategory.PREFERENCE,
                confidence=0.8,
                entities={},
                raw_text=text,
            )

    # ---- 7. Information requests ----
    for pat in _INFORMATION_PATTERNS:
        if re.search(pat, lower):
            return Intent(
                category=IntentCategory.INFORMATION,
                confidence=0.8,
                entities={},
                raw_text=text,
            )

    # ---- 8. Help requests ----
    for kw in _HELP_KEYWORDS:
        if kw in lower:
            return Intent(
                category=IntentCategory.REQUEST_HELP,
                confidence=0.75,
                entities={},
                raw_text=text,
            )

    # ---- 9. Simple chat ----
    for pat in _SIMPLE_CHAT_PATTERNS:
        if re.search(pat, lower):
            return Intent(
                category=IntentCategory.SIMPLE_CHAT,
                confidence=0.7,
                entities={},
                raw_text=text,
            )

    # ---- 10. Default: complex_plan (let Sonnet decide) ----
    person = _extract_person(text)
    if person:
        entities["person"] = person

    return Intent(
        category=IntentCategory.COMPLEX_PLAN,
        confidence=0.5,
        entities=entities,
        raw_text=text,
    )
