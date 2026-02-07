"""Shared fixtures for Soul System tests."""

import pytest

from soul.config import SoulConfig
from soul.memory.store import SoulStore
from soul.memory.residents import ResidentManager
from soul.memory.facility import FacilityManager
from soul.memory.preferences import PreferenceManager
from soul.memory.tasks import TaskLogger


@pytest.fixture
def db_path(tmp_path):
    return str(tmp_path / "test_soul.db")


@pytest.fixture
def store(db_path):
    s = SoulStore(db_path=db_path)
    yield s
    s.close()


@pytest.fixture
def residents(store):
    return ResidentManager(store)


@pytest.fixture
def facility(store):
    return FacilityManager(store)


@pytest.fixture
def preferences(store):
    return PreferenceManager(store)


@pytest.fixture
def task_logger(store):
    return TaskLogger(store)


@pytest.fixture
def config():
    return SoulConfig(
        anthropic_api_key="test-key",
        tts_provider="pyttsx3",
        groot_enabled=False,
        stt_enabled=False,
    )


@pytest.fixture
def sample_resident(residents):
    """Create a sample resident and return their ID."""
    return residents.create(name="Martha", room="204", notes="Loves gardening")


@pytest.fixture
def sample_facility(facility):
    """Seed the facility with common locations."""
    ids = {}
    ids["dining"] = facility.add_location("Dining Hall", "common_area", floor=1, description="Main dining area")
    ids["garden"] = facility.add_location("Garden", "outdoor", floor=1, description="Accessible garden with raised beds")
    ids["room_204"] = facility.add_location("Room 204", "resident_room", floor=2)
    ids["kitchen"] = facility.add_location("Kitchen", "staff_area", floor=1, navigable=False)
    ids["lobby"] = facility.add_location("Lobby", "common_area", floor=1, description="Main entrance")
    return ids
