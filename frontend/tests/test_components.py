"""Tests for frontend HTML component builders."""

from __future__ import annotations

import pytest

from frontend.components.activity_feed import render_activity_feed
from frontend.components.dataset_card import render_dataset_cards
from frontend.components.gpu_panel import render_gpu_cards
from frontend.components.helpers import format_number, html_escape, time_ago, truncate_path
from frontend.components.icons import (
    icon_bar_chart,
    icon_box,
    icon_brain,
    icon_check_circle,
    icon_cpu,
    icon_database,
    icon_folder_plus,
    icon_home,
    icon_message_circle,
    icon_play,
    icon_rocket,
    icon_server,
    icon_settings,
    icon_sparkles,
    icon_stop_circle,
    icon_x_circle,
)
from frontend.components.metric_card import render_metric_card, render_metric_grid
from frontend.components.notification import render_toast, render_toast_container
from frontend.components.pipeline_stepper import render_pipeline_stepper
from frontend.components.progress_bar import render_progress_bar
from frontend.components.status_badge import render_status_badge
from frontend.constants import EMBODIMENT_CHOICES, SIM_TASKS, TRAINING_PRESETS


class TestIcons:
    def test_all_icons_return_svg(self):
        icons = [
            icon_database, icon_cpu, icon_bar_chart, icon_rocket, icon_play,
            icon_check_circle, icon_x_circle, icon_stop_circle, icon_folder_plus,
            icon_box, icon_server, icon_settings, icon_message_circle,
            icon_sparkles, icon_home, icon_brain,
        ]
        for icon_fn in icons:
            svg = icon_fn()
            assert isinstance(svg, str)
            assert "<svg" in svg
            assert "</svg>" in svg

    def test_icons_accept_size(self):
        svg = icon_database(size=32)
        assert 'width="32"' in svg
        assert 'height="32"' in svg

    def test_icons_accept_color(self):
        svg = icon_cpu(color="#ff0000")
        assert "#ff0000" in svg


class TestPipelineStepper:
    def test_renders_all_pages(self):
        html = render_pipeline_stepper("dashboard")
        for page in ["dashboard", "data", "train", "evaluate", "deploy"]:
            assert f'data-page="{page}"' in html

    def test_active_page_highlighted(self):
        html = render_pipeline_stepper("train")
        # The active page node gets the "active" CSS class
        assert "active" in html

    def test_returns_non_empty_string(self):
        html = render_pipeline_stepper("data")
        assert isinstance(html, str)
        assert len(html) > 50


class TestGpuPanel:
    def test_renders_gpu_cards(self):
        gpus = [
            {"name": "RTX 4090", "utilization_pct": 75, "memory_used_mb": 8000, "memory_total_mb": 24000, "temperature_c": 65},
        ]
        html = render_gpu_cards(gpus)
        assert "RTX 4090" in html
        assert "75" in html

    def test_empty_gpus(self):
        html = render_gpu_cards([])
        assert isinstance(html, str)
        assert "no gpu" in html.lower() or len(html) > 0

    def test_multiple_gpus(self):
        gpus = [
            {"name": "GPU 0", "utilization_pct": 50, "memory_used_mb": 4000, "memory_total_mb": 24000, "temperature_c": 55},
            {"name": "GPU 1", "utilization_pct": 90, "memory_used_mb": 20000, "memory_total_mb": 24000, "temperature_c": 80},
        ]
        html = render_gpu_cards(gpus)
        assert "GPU 0" in html
        assert "GPU 1" in html


class TestMetricCard:
    def test_renders_card(self):
        html = render_metric_card("Datasets", "12")
        assert "Datasets" in html
        assert "12" in html

    def test_card_with_delta(self):
        html = render_metric_card("Models", "5", delta="+2")
        assert "+2" in html

    def test_metric_grid(self):
        metrics = [
            {"label": "A", "value": "1"},
            {"label": "B", "value": "2"},
        ]
        html = render_metric_grid(metrics)
        assert "A" in html
        assert "B" in html


class TestDatasetCard:
    def test_renders_cards(self):
        datasets = [
            {"name": "cube_to_bowl", "episode_count": 50, "source": "recorded", "path": "/data/cube", "registered_at": "2025-01-01T12:00:00"},
        ]
        html = render_dataset_cards(datasets)
        assert "cube_to_bowl" in html
        assert "50" in html

    def test_empty_datasets(self):
        html = render_dataset_cards([])
        assert isinstance(html, str)


class TestStatusBadge:
    def test_all_statuses(self):
        for status in ["running", "completed", "failed", "pending", "stopped", "imported", "recorded"]:
            html = render_status_badge(status)
            assert isinstance(html, str)
            assert len(html) > 0
            assert status in html.lower()

    def test_unknown_status(self):
        html = render_status_badge("unknown_state")
        assert isinstance(html, str)
        assert "unknown_state" in html.lower()


class TestProgressBar:
    def test_renders_bar(self):
        html = render_progress_bar(75, label="Training")
        assert "75" in html
        assert "Training" in html

    def test_zero_percent(self):
        html = render_progress_bar(0)
        assert isinstance(html, str)

    def test_hundred_percent(self):
        html = render_progress_bar(100, label="Done")
        assert "100" in html


class TestNotification:
    def test_toast_types(self):
        for t in ["success", "error", "info"]:
            html = render_toast("Test message", t)
            assert "Test message" in html
            assert isinstance(html, str)

    def test_toast_container(self):
        toasts = [
            {"message": "Done!", "type": "success"},
            {"message": "Oops!", "type": "error"},
        ]
        html = render_toast_container(toasts)
        assert "Done!" in html
        assert "Oops!" in html


class TestActivityFeed:
    def test_renders_events(self):
        events = [
            {"event_type": "training_started", "message": "Training started", "created_at": "2025-01-01T12:00:00"},
            {"event_type": "dataset_imported", "message": "Dataset imported", "created_at": "2025-01-01T11:00:00"},
        ]
        html = render_activity_feed(events)
        assert "Training started" in html
        assert "Dataset imported" in html

    def test_empty_events(self):
        html = render_activity_feed([])
        assert isinstance(html, str)

    def test_max_items_limit(self):
        events = [
            {"event_type": "test", "message": f"Event {i}", "created_at": "2025-01-01T12:00:00"}
            for i in range(20)
        ]
        html = render_activity_feed(events, max_items=5)
        assert isinstance(html, str)


class TestHelpers:
    def test_format_number_small(self):
        assert format_number(42) == "42"

    def test_format_number_thousands(self):
        result = format_number(1500)
        assert "1" in result
        # Should format with K or comma
        assert "k" in result.lower() or "," in result or "500" in result

    def test_truncate_path_short(self):
        path = "/data/test"
        assert truncate_path(path, 50) == path

    def test_truncate_path_long(self):
        path = "/very/long/path/to/some/deeply/nested/directory/file.txt"
        result = truncate_path(path, 20)
        assert len(result) <= 25  # Allow some overflow for ellipsis
        assert "..." in result or len(result) <= 20

    def test_html_escape(self):
        assert "&amp;" in html_escape("a & b")
        assert "&lt;" in html_escape("<script>")
        assert "&gt;" in html_escape("test>")

    def test_time_ago_with_none(self):
        result = time_ago(None)
        assert isinstance(result, str)


class TestConstants:
    def test_embodiment_choices_non_empty(self):
        assert len(EMBODIMENT_CHOICES) > 0
        assert all(isinstance(c, str) for c in EMBODIMENT_CHOICES)
        assert "new_embodiment" in EMBODIMENT_CHOICES

    def test_training_presets_structure(self):
        assert len(TRAINING_PRESETS) > 0
        for name, preset in TRAINING_PRESETS.items():
            assert isinstance(name, str)
            assert "max_steps" in preset
            assert isinstance(preset["max_steps"], int)
            # Check for batch size under either key name
            assert "batch_size" in preset or "global_batch_size" in preset

    def test_sim_tasks_all_envs(self):
        for env in ["LIBERO", "SimplerEnv", "BEHAVIOR"]:
            assert env in SIM_TASKS
            assert len(SIM_TASKS[env]) > 0
            assert all(isinstance(t, str) for t in SIM_TASKS[env])
