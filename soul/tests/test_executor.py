"""Tests for the executor layer — Speaker, Navigator, Manipulator, Dispatcher."""

import sys
from unittest.mock import MagicMock, patch

import pytest

from soul.cognition.schemas import Action, ActionPlan, ActionType
from soul.config import SoulConfig
from soul.executor.dispatcher import ActionResult, Dispatcher
from soul.executor.manipulate import Manipulator
from soul.executor.navigate import Navigator
from soul.executor.speak import Speaker


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def elevenlabs_config():
    """Config that requests ElevenLabs TTS."""
    return SoulConfig(
        tts_provider="elevenlabs",
        elevenlabs_api_key="test-el-key",
        elevenlabs_voice_id="test-voice",
        tts_rate=150,
        groot_enabled=False,
    )


@pytest.fixture
def pyttsx3_config():
    """Config that requests pyttsx3 TTS."""
    return SoulConfig(
        tts_provider="pyttsx3",
        tts_rate=160,
        groot_enabled=False,
    )


@pytest.fixture
def groot_config():
    """Config with GR00T enabled."""
    return SoulConfig(
        tts_provider="pyttsx3",
        groot_enabled=True,
        groot_host="localhost",
        groot_port=5555,
    )


@pytest.fixture
def mock_speaker():
    speaker = MagicMock(spec=Speaker)
    return speaker


@pytest.fixture
def mock_navigator():
    nav = MagicMock(spec=Navigator)
    nav.navigate.return_value = True
    return nav


@pytest.fixture
def mock_manipulator():
    manip = MagicMock(spec=Manipulator)
    manip.execute.return_value = True
    return manip


@pytest.fixture
def dispatcher(mock_speaker, mock_navigator, mock_manipulator, preferences, sample_resident):
    return Dispatcher(
        speaker=mock_speaker,
        navigator=mock_navigator,
        manipulator=mock_manipulator,
        preferences=preferences,
        resident_id=sample_resident,
    )


# ===========================================================================
# Speaker tests
# ===========================================================================


class TestSpeaker:
    """Test Speaker with mocked TTS backends."""

    def test_speak_with_mocked_pyttsx3(self, pyttsx3_config):
        """Speaker uses pyttsx3 when configured."""
        mock_engine = MagicMock()
        mock_pyttsx3_mod = MagicMock()
        mock_pyttsx3_mod.init.return_value = mock_engine

        # Inject the mock module into sys.modules so `import pyttsx3` finds it
        with patch.dict(sys.modules, {"pyttsx3": mock_pyttsx3_mod}):
            speaker = Speaker.__new__(Speaker)
            speaker._config = pyttsx3_config
            speaker._elevenlabs_client = None
            speaker._pyttsx3_engine = None
            speaker._init_pyttsx3()

            assert speaker._pyttsx3_engine is mock_engine
            mock_engine.setProperty.assert_called_with("rate", 160)

            speaker.speak("Hello, Martha!")
            mock_engine.say.assert_called_once_with("Hello, Martha!")
            mock_engine.runAndWait.assert_called_once()

    def test_speak_with_mocked_elevenlabs(self, elevenlabs_config):
        """Speaker uses ElevenLabs when configured and available."""
        mock_client = MagicMock()
        mock_client.text_to_speech.convert.return_value = iter([b"audio-chunk"])

        speaker = Speaker.__new__(Speaker)
        speaker._config = elevenlabs_config
        speaker._elevenlabs_client = mock_client
        speaker._pyttsx3_engine = None

        speaker.speak("Good morning!")

        mock_client.text_to_speech.convert.assert_called_once_with(
            text="Good morning!",
            voice_id="test-voice",
            model_id="eleven_turbo_v2_5",
            optimize_streaming_latency=3,
            output_format="mp3_22050_32",
            language_code="nb",
        )

    def test_fallback_when_elevenlabs_fails(self, elevenlabs_config):
        """When ElevenLabs raises, Speaker falls back to pyttsx3."""
        mock_el_client = MagicMock()
        mock_el_client.text_to_speech.convert.side_effect = RuntimeError("API down")

        mock_engine = MagicMock()

        speaker = Speaker.__new__(Speaker)
        speaker._config = elevenlabs_config
        speaker._elevenlabs_client = mock_el_client
        speaker._pyttsx3_engine = mock_engine

        speaker.speak("Fallback test")

        # ElevenLabs was attempted
        mock_el_client.text_to_speech.convert.assert_called_once()
        # pyttsx3 was used as fallback
        mock_engine.say.assert_called_once_with("Fallback test")
        mock_engine.runAndWait.assert_called_once()

    def test_speak_empty_text_is_noop(self, pyttsx3_config):
        """Speaking empty text does nothing."""
        mock_engine = MagicMock()

        speaker = Speaker.__new__(Speaker)
        speaker._config = pyttsx3_config
        speaker._elevenlabs_client = None
        speaker._pyttsx3_engine = mock_engine

        speaker.speak("")

        mock_engine.say.assert_not_called()

    def test_no_tts_available_does_not_raise(self, pyttsx3_config):
        """If no TTS engine is available, speak() logs but does not crash."""
        speaker = Speaker.__new__(Speaker)
        speaker._config = pyttsx3_config
        speaker._elevenlabs_client = None
        speaker._pyttsx3_engine = None

        # Should not raise
        speaker.speak("Nobody is listening")


# ===========================================================================
# Navigator tests
# ===========================================================================


class TestNavigator:
    """Test Navigator in simulation mode."""

    def test_simulation_mode(self, config):
        """With groot_enabled=False, navigate returns True (simulation)."""
        nav = Navigator(config)
        assert nav.navigate("Dining Hall") is True

    def test_simulation_mode_logs(self, config, caplog):
        """Simulation mode logs the destination."""
        nav = Navigator(config)
        with caplog.at_level("INFO"):
            nav.navigate("Garden")
        assert "Garden" in caplog.text
        assert "SIM" in caplog.text

    def test_groot_enabled_without_package(self, groot_config):
        """When GR00T is enabled but server is unreachable, falls back to simulation."""
        # Mock the gr00t import to raise ImportError, ensuring consistent
        # behavior whether or not the gr00t package is installed.
        with patch.dict(sys.modules, {"gr00t": None, "gr00t.policy": None, "gr00t.policy.server_client": None}):
            nav = Navigator(groot_config)
            result = nav.navigate("Room 204")
            assert result is True

    def test_with_injected_client(self, groot_config):
        """When a client is injected, it is used for navigation."""
        mock_client = MagicMock()
        mock_client.call_endpoint.return_value = {"status": "ok"}

        nav = Navigator(groot_config, client=mock_client)
        result = nav.navigate("Lobby")

        assert result is True
        mock_client.call_endpoint.assert_called_once()

    def test_client_error_returns_false(self, groot_config):
        """When the client raises, navigate returns False."""
        mock_client = MagicMock()
        mock_client.call_endpoint.side_effect = RuntimeError("connection lost")

        nav = Navigator(groot_config, client=mock_client)
        result = nav.navigate("Kitchen")

        assert result is False


# ===========================================================================
# Manipulator tests
# ===========================================================================


class TestManipulator:
    """Test Manipulator in simulation mode."""

    def test_simulation_mode(self, config):
        """With groot_enabled=False, execute returns True (simulation)."""
        manip = Manipulator(config)
        assert manip.execute({"action": "pick_up", "target": "cup"}) is True

    def test_simulation_mode_logs(self, config, caplog):
        """Simulation mode logs the action and target."""
        manip = Manipulator(config)
        with caplog.at_level("INFO"):
            manip.execute({"action": "hand_over", "target": "book"})
        assert "hand_over" in caplog.text
        assert "book" in caplog.text

    def test_with_injected_client(self, groot_config):
        """When a client is injected, it is used for manipulation."""
        mock_client = MagicMock()
        mock_client.call_endpoint.return_value = {"status": "ok"}

        manip = Manipulator(groot_config, client=mock_client)
        result = manip.execute({"action": "put_down", "target": "tray"})

        assert result is True
        mock_client.call_endpoint.assert_called_once()

    def test_client_error_returns_false(self, groot_config):
        """When the client raises, execute returns False."""
        mock_client = MagicMock()
        mock_client.call_endpoint.side_effect = RuntimeError("servo error")

        manip = Manipulator(groot_config, client=mock_client)
        result = manip.execute({"action": "pick_up", "target": "glass"})

        assert result is False


# ===========================================================================
# Dispatcher tests
# ===========================================================================


class TestDispatcher:
    """Test the Dispatcher with mocked executors."""

    def test_speak_action(self, dispatcher, mock_speaker):
        """SPEAK action calls speaker.speak."""
        plan = ActionPlan.speak_only("Hello!")
        results = dispatcher.execute(plan)

        assert len(results) == 1
        assert results[0].success is True
        assert results[0].result_text == "Hello!"
        mock_speaker.speak.assert_called_once_with("Hello!")

    def test_navigate_action(self, dispatcher, mock_navigator):
        """NAVIGATE action calls navigator.navigate."""
        plan = ActionPlan(actions=[
            Action(ActionType.NAVIGATE, {"destination": "Garden"}),
        ])
        results = dispatcher.execute(plan)

        assert results[0].success is True
        mock_navigator.navigate.assert_called_once_with("Garden")

    def test_manipulate_action(self, dispatcher, mock_manipulator):
        """MANIPULATE action calls manipulator.execute."""
        params = {"action": "pick_up", "target": "cup"}
        plan = ActionPlan(actions=[
            Action(ActionType.MANIPULATE, params),
        ])
        results = dispatcher.execute(plan)

        assert results[0].success is True
        mock_manipulator.execute.assert_called_once_with(params)

    def test_wait_action(self, dispatcher):
        """WAIT action sleeps for the specified duration."""
        plan = ActionPlan(actions=[
            Action(ActionType.WAIT, {"duration": 0.01}),
        ])
        results = dispatcher.execute(plan)

        assert results[0].success is True
        assert "0.01" in results[0].result_text

    def test_alert_staff_action(self, dispatcher, mock_speaker):
        """ALERT_STAFF logs warning and speaks the alert."""
        plan = ActionPlan(actions=[
            Action(ActionType.ALERT_STAFF, {"message": "Resident fell"}),
        ])
        results = dispatcher.execute(plan)

        assert results[0].success is True
        assert results[0].result_text == "Resident fell"
        mock_speaker.speak.assert_called_once_with("Alert: Resident fell")

    def test_remember_action(self, dispatcher, preferences, sample_resident):
        """REMEMBER action stores a preference via PreferenceManager."""
        plan = ActionPlan(actions=[
            Action(ActionType.REMEMBER, {
                "category": "drink",
                "key": "favorite_tea",
                "value": "chamomile",
            }),
        ])
        results = dispatcher.execute(plan)

        assert results[0].success is True
        assert "chamomile" in results[0].result_text

        # Verify the preference was actually stored
        pref = preferences.get(sample_resident, "drink", "favorite_tea")
        assert pref is not None
        assert pref["value"] == "chamomile"

    def test_remember_without_key_fails(self, dispatcher):
        """REMEMBER without a key returns failure."""
        plan = ActionPlan(actions=[
            Action(ActionType.REMEMBER, {"category": "drink", "value": "water"}),
        ])
        results = dispatcher.execute(plan)

        assert results[0].success is False
        assert "key" in results[0].error

    def test_dependency_ordering(self, dispatcher, mock_speaker, mock_navigator):
        """Actions execute in dependency order: speak first, then navigate."""
        plan = ActionPlan(actions=[
            Action(ActionType.SPEAK, {"text": "On my way!"}, priority=1),
            Action(ActionType.NAVIGATE, {"destination": "Room 204"}, depends_on=[0]),
        ])
        results = dispatcher.execute(plan)

        assert len(results) == 2
        assert results[0].success is True
        assert results[1].success is True

        # Speak was called before navigate
        mock_speaker.speak.assert_called_once_with("On my way!")
        mock_navigator.navigate.assert_called_once_with("Room 204")

    def test_dependency_failure_skips_dependent(
        self, dispatcher, mock_speaker, mock_navigator
    ):
        """When a dependency fails, dependent actions are skipped."""
        mock_navigator.navigate.return_value = False

        plan = ActionPlan(actions=[
            Action(ActionType.NAVIGATE, {"destination": "Kitchen"}),
            Action(ActionType.MANIPULATE, {"action": "pick_up", "target": "cup"}, depends_on=[0]),
            Action(ActionType.SPEAK, {"text": "Here you go!"}, depends_on=[1]),
        ])
        results = dispatcher.execute(plan)

        assert len(results) == 3
        # Navigate failed
        assert results[0].success is False
        # Manipulate skipped due to dependency
        assert results[1].success is False
        assert "dependency" in results[1].error.lower()
        # Speak skipped due to transitive dependency
        assert results[2].success is False
        assert "dependency" in results[2].error.lower()

    def test_empty_plan(self, dispatcher):
        """Empty plan returns empty results."""
        plan = ActionPlan(actions=[])
        results = dispatcher.execute(plan)
        assert results == []

    def test_multi_action_plan(
        self, dispatcher, mock_speaker, mock_navigator, mock_manipulator
    ):
        """Complex plan with multiple action types."""
        plan = ActionPlan(
            actions=[
                Action(ActionType.SPEAK, {"text": "I'll get that for you!"}),
                Action(ActionType.NAVIGATE, {"destination": "Kitchen"}, depends_on=[0]),
                Action(ActionType.MANIPULATE, {"action": "pick_up", "target": "cup"}, depends_on=[1]),
                Action(ActionType.NAVIGATE, {"destination": "Room 204"}, depends_on=[2]),
                Action(ActionType.SPEAK, {"text": "Here is your cup!"}, depends_on=[3]),
            ],
            reasoning="Resident asked for a cup from the kitchen",
        )
        results = dispatcher.execute(plan)

        assert len(results) == 5
        assert all(r.success for r in results)

    def test_query_memory_action(self, dispatcher, preferences, sample_resident):
        """QUERY_MEMORY retrieves stored preferences."""
        # First store a preference
        preferences.set(sample_resident, "food", "breakfast", "oatmeal")

        plan = ActionPlan(actions=[
            Action(ActionType.QUERY_MEMORY, {
                "category": "food",
                "key": "breakfast",
            }),
        ])
        results = dispatcher.execute(plan)

        assert results[0].success is True
        assert "oatmeal" in results[0].result_text

    def test_independent_actions_order(self, dispatcher, mock_speaker, mock_navigator):
        """Actions without dependencies execute in original list order."""
        plan = ActionPlan(actions=[
            Action(ActionType.SPEAK, {"text": "First"}),
            Action(ActionType.NAVIGATE, {"destination": "Lobby"}),
            Action(ActionType.SPEAK, {"text": "Third"}),
        ])
        results = dispatcher.execute(plan)

        assert len(results) == 3
        assert results[0].action_index == 0
        assert results[1].action_index == 1
        assert results[2].action_index == 2


# ===========================================================================
# ActionResult tests
# ===========================================================================


class TestActionResult:
    def test_defaults(self):
        r = ActionResult(action_index=0, success=True)
        assert r.result_text == ""
        assert r.error is None

    def test_with_error(self):
        r = ActionResult(action_index=1, success=False, error="Connection lost")
        assert r.success is False
        assert r.error == "Connection lost"
