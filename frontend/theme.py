"""Wybe Studio dark-mode theme and CSS design system.

Provides WybeTheme (a gr.themes.Base subclass) and WYBE_CSS (a ~400-line
CSS string) used by the top-level gr.Blocks.
"""

from __future__ import annotations

import gradio as gr
from gradio.themes import Color
from gradio.themes.utils.fonts import GoogleFont


# ── Colour palette ─────────────────────────────────────────────────────
SLATE_50 = "#f8fafc"
SLATE_100 = "#f1f5f9"
SLATE_200 = "#e2e8f0"
SLATE_300 = "#cbd5e1"
SLATE_400 = "#94a3b8"
SLATE_500 = "#64748b"
SLATE_600 = "#475569"
SLATE_700 = "#334155"
SLATE_800 = "#1e293b"
SLATE_900 = "#0f172a"
SLATE_950 = "#020617"

BLUE_400 = "#60a5fa"
BLUE_500 = "#3b82f6"
BLUE_600 = "#2563eb"
BLUE_700 = "#1d4ed8"

GREEN_400 = "#4ade80"
GREEN_500 = "#22c55e"

YELLOW_400 = "#facc15"
YELLOW_500 = "#eab308"

RED_400 = "#f87171"
RED_500 = "#ef4444"

PURPLE_500 = "#a855f7"
CYAN_500 = "#06b6d4"


class WybeTheme(gr.themes.Base):
    """Dark-mode theme for Wybe Studio."""

    def __init__(self):
        slate = Color(
            SLATE_50, SLATE_100, SLATE_200, SLATE_300, SLATE_400,
            SLATE_500, SLATE_600, SLATE_700, SLATE_800, SLATE_900,
            SLATE_950, name="slate",
        )
        blue = Color(
            "#eff6ff", "#dbeafe", "#bfdbfe", "#93c5fd", BLUE_400,
            BLUE_500, BLUE_600, BLUE_700, "#1e40af", "#1e3a8a",
            "#172554", name="blue",
        )

        super().__init__(
            primary_hue=blue,
            secondary_hue=slate,
            neutral_hue=slate,
            font=[GoogleFont("Inter"), "ui-sans-serif", "system-ui", "sans-serif"],
            font_mono=[GoogleFont("JetBrains Mono"), "ui-monospace", "monospace"],
        )

        # Background layers
        self.body_background_fill = SLATE_900
        self.body_background_fill_dark = SLATE_950
        self.background_fill_primary = SLATE_800
        self.background_fill_primary_dark = SLATE_900
        self.background_fill_secondary = SLATE_700
        self.background_fill_secondary_dark = SLATE_800

        # Text
        self.body_text_color = SLATE_200
        self.body_text_color_dark = SLATE_200
        self.body_text_color_subdued = SLATE_500
        self.body_text_color_subdued_dark = SLATE_500

        # Block styling
        self.block_background_fill = SLATE_800
        self.block_background_fill_dark = SLATE_800
        self.block_border_color = SLATE_700
        self.block_border_color_dark = SLATE_700
        self.block_border_width = "1px"
        self.block_label_text_color = SLATE_400
        self.block_label_text_color_dark = SLATE_400
        self.block_radius = "12px"
        self.block_padding = "16px"
        self.block_shadow = "0 1px 3px 0 rgba(0,0,0,0.3)"

        # Inputs
        self.input_background_fill = SLATE_900
        self.input_background_fill_dark = SLATE_900
        self.input_border_color = SLATE_600
        self.input_border_color_dark = SLATE_600
        self.input_border_color_focus = BLUE_500
        self.input_border_color_focus_dark = BLUE_500

        # Buttons
        self.button_primary_background_fill = BLUE_600
        self.button_primary_background_fill_dark = BLUE_600
        self.button_primary_background_fill_hover = BLUE_500
        self.button_primary_background_fill_hover_dark = BLUE_500
        self.button_primary_text_color = "#ffffff"
        self.button_primary_text_color_dark = "#ffffff"
        self.button_secondary_background_fill = SLATE_700
        self.button_secondary_background_fill_dark = SLATE_700
        self.button_secondary_text_color = SLATE_200
        self.button_secondary_text_color_dark = SLATE_200

        # Borders
        self.border_color_primary = SLATE_600
        self.border_color_primary_dark = SLATE_600

        # Shadows
        self.shadow_spread = "1px"


# ── CSS Design System ──────────────────────────────────────────────────

WYBE_CSS = """
/* ── CSS Variables ─────────────────────────────────────────── */
:root {
    --wybe-bg-primary: #0f172a;
    --wybe-bg-secondary: #1e293b;
    --wybe-bg-tertiary: #334155;
    --wybe-bg-hover: #3b4d6b;
    --wybe-accent: #3b82f6;
    --wybe-accent-hover: #60a5fa;
    --wybe-accent-dim: #1d4ed8;
    --wybe-text: #e2e8f0;
    --wybe-text-muted: #64748b;
    --wybe-text-bright: #f8fafc;
    --wybe-success: #22c55e;
    --wybe-success-dim: #166534;
    --wybe-warning: #eab308;
    --wybe-warning-dim: #854d0e;
    --wybe-danger: #ef4444;
    --wybe-danger-dim: #991b1b;
    --wybe-purple: #a855f7;
    --wybe-cyan: #06b6d4;
    --wybe-border: #334155;
    --wybe-radius: 12px;
    --wybe-radius-sm: 8px;
    --wybe-radius-xs: 4px;
    --wybe-shadow: 0 1px 3px 0 rgba(0,0,0,0.3);
    --wybe-shadow-lg: 0 4px 12px 0 rgba(0,0,0,0.4);
    --wybe-font: 'Inter', ui-sans-serif, system-ui, sans-serif;
    --wybe-font-mono: 'JetBrains Mono', ui-monospace, monospace;
    --wybe-transition: 150ms ease;
}

/* ── Global overrides ──────────────────────────────────────── */
.gradio-container {
    max-width: 100% !important;
    padding: 0 !important;
    background: var(--wybe-bg-primary) !important;
}
footer { display: none !important; }

/* ── Shell bar ─────────────────────────────────────────────── */
.shell-bar {
    background: var(--wybe-bg-secondary);
    border-bottom: 1px solid var(--wybe-border);
    padding: 8px 20px;
    display: flex;
    align-items: center;
    gap: 12px;
    min-height: 56px;
    position: sticky;
    top: 0;
    z-index: 100;
    flex-wrap: nowrap !important;
}
/* Shell bar children: Logo | Project Dropdown | Dashboard Toggle */
.shell-bar > div:nth-child(1) { flex: 0 0 auto !important; min-width: 0 !important; max-width: fit-content !important; }
.shell-bar > div:nth-child(2) { flex: 0 0 200px !important; min-width: 0 !important; }
.shell-bar > div:nth-child(3) { flex: 0 0 auto !important; min-width: 0 !important; max-width: fit-content !important; }
.shell-logo {
    font-size: 18px;
    font-weight: 700;
    color: var(--wybe-accent);
    letter-spacing: -0.5px;
    white-space: nowrap;
    font-family: var(--wybe-font);
}
.shell-logo span { color: var(--wybe-text-bright); }

/* ── Navigation Tabs ───────────────────────────────────────── */
.nav-tabs .tab-nav {
    background: var(--wybe-bg-secondary) !important;
    border-bottom: 1px solid var(--wybe-border) !important;
    padding: 0 8px !important;
}
.nav-tabs .tab-nav button {
    color: var(--wybe-text-muted) !important;
    background: transparent !important;
    border: none !important;
    border-bottom: 2px solid transparent !important;
    font-family: var(--wybe-font) !important;
    font-size: 14px !important;
    font-weight: 500 !important;
    padding: 10px 20px !important;
    cursor: pointer !important;
    transition: all var(--wybe-transition) !important;
}
.nav-tabs .tab-nav button:hover {
    color: var(--wybe-text) !important;
}
.nav-tabs .tab-nav button.selected {
    color: var(--wybe-accent) !important;
    border-bottom: 2px solid var(--wybe-accent) !important;
}

/* ── Status Badges ─────────────────────────────────────────── */
.status-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 3px 10px;
    border-radius: 12px;
    font-size: 12px;
    font-weight: 500;
    font-family: var(--wybe-font);
}
.status-badge .badge-dot {
    width: 6px; height: 6px;
    border-radius: 50%;
    flex-shrink: 0;
}
.badge-running { background: rgba(59,130,246,0.15); color: #60a5fa; }
.badge-running .badge-dot { background: #3b82f6; animation: pulse 1.5s ease-in-out infinite; }
.badge-completed { background: rgba(34,197,94,0.15); color: #4ade80; }
.badge-completed .badge-dot { background: #22c55e; }
.badge-failed { background: rgba(239,68,68,0.15); color: #f87171; }
.badge-failed .badge-dot { background: #ef4444; }
.badge-pending { background: rgba(100,116,139,0.15); color: #94a3b8; }
.badge-pending .badge-dot { background: #64748b; }
.badge-stopped { background: rgba(234,179,8,0.15); color: #facc15; }
.badge-stopped .badge-dot { background: #eab308; }

/* ── Metric Cards ──────────────────────────────────────────── */
.metric-card {
    background: var(--wybe-bg-secondary);
    border: 1px solid var(--wybe-border);
    border-radius: var(--wybe-radius);
    padding: 20px;
    transition: border-color var(--wybe-transition);
}
.metric-card:hover { border-color: var(--wybe-accent); }
.metric-card .mc-label {
    font-size: 12px;
    color: var(--wybe-text-muted);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 8px;
    font-family: var(--wybe-font);
}
.metric-card .mc-value {
    font-size: 28px;
    font-weight: 700;
    color: var(--wybe-text-bright);
    font-family: var(--wybe-font);
}
.metric-card .mc-delta {
    font-size: 12px;
    margin-top: 4px;
    font-family: var(--wybe-font);
}
.mc-delta.positive { color: var(--wybe-success); }
.mc-delta.negative { color: var(--wybe-danger); }

/* ── Dataset Cards ─────────────────────────────────────────── */
.dataset-card {
    background: var(--wybe-bg-secondary);
    border: 1px solid var(--wybe-border);
    border-radius: var(--wybe-radius);
    padding: 16px;
    transition: all var(--wybe-transition);
    cursor: default;
}
.dataset-card:hover {
    border-color: var(--wybe-accent);
    box-shadow: 0 0 0 1px var(--wybe-accent), var(--wybe-shadow-lg);
}
.dataset-card .dc-name {
    font-size: 15px;
    font-weight: 600;
    color: var(--wybe-text-bright);
    margin-bottom: 8px;
    font-family: var(--wybe-font);
}
.dataset-card .dc-meta {
    font-size: 12px;
    color: var(--wybe-text-muted);
    display: flex;
    gap: 12px;
    margin-bottom: 10px;
    font-family: var(--wybe-font);
}

/* ── GPU Bars ──────────────────────────────────────────────── */
.gpu-card {
    background: var(--wybe-bg-secondary);
    border: 1px solid var(--wybe-border);
    border-radius: var(--wybe-radius-sm);
    padding: 12px 16px;
    margin-bottom: 8px;
}
.gpu-card .gpu-name {
    font-size: 13px;
    font-weight: 600;
    color: var(--wybe-text);
    margin-bottom: 8px;
    font-family: var(--wybe-font);
}
.gpu-bar-row {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 6px;
}
.gpu-bar-label {
    font-size: 11px;
    color: var(--wybe-text-muted);
    width: 50px;
    flex-shrink: 0;
    font-family: var(--wybe-font);
}
.gpu-bar-track {
    flex: 1;
    height: 8px;
    background: var(--wybe-bg-primary);
    border-radius: 4px;
    overflow: hidden;
}
.gpu-bar-fill {
    height: 100%;
    border-radius: 4px;
    transition: width 0.5s ease;
}
.gpu-bar-value {
    font-size: 11px;
    color: var(--wybe-text-muted);
    width: 45px;
    text-align: right;
    font-family: var(--wybe-font-mono);
}

/* ── Progress Bars ─────────────────────────────────────────── */
.progress-bar-container {
    width: 100%;
    margin: 4px 0;
}
.progress-bar-track {
    height: 10px;
    background: var(--wybe-bg-primary);
    border-radius: 5px;
    overflow: hidden;
}
.progress-bar-fill {
    height: 100%;
    border-radius: 5px;
    background: linear-gradient(90deg, var(--wybe-accent-dim), var(--wybe-accent));
    transition: width 0.5s ease;
}
.progress-bar-label {
    display: flex;
    justify-content: space-between;
    font-size: 11px;
    color: var(--wybe-text-muted);
    margin-top: 4px;
    font-family: var(--wybe-font);
}

/* ── Activity Feed ─────────────────────────────────────────── */
.activity-feed { padding: 4px 0; }
.activity-item {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    padding: 8px 0;
    border-bottom: 1px solid rgba(51,65,85,0.5);
}
.activity-item:last-child { border-bottom: none; }
.activity-icon {
    width: 28px; height: 28px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    font-size: 12px;
}
.activity-content {
    flex: 1;
    min-width: 0;
}
.activity-message {
    font-size: 13px;
    color: var(--wybe-text);
    font-family: var(--wybe-font);
}
.activity-time {
    font-size: 11px;
    color: var(--wybe-text-muted);
    font-family: var(--wybe-font);
}

/* ── Toast Notifications ───────────────────────────────────── */
.toast-container {
    position: fixed;
    top: 70px;
    right: 20px;
    z-index: 1000;
    display: flex;
    flex-direction: column;
    gap: 8px;
}
.toast {
    padding: 12px 16px;
    border-radius: var(--wybe-radius-sm);
    font-size: 13px;
    font-family: var(--wybe-font);
    color: var(--wybe-text-bright);
    box-shadow: var(--wybe-shadow-lg);
    animation: toast-in 0.3s ease;
    max-width: 360px;
}
.toast-success { background: var(--wybe-success-dim); border: 1px solid var(--wybe-success); }
.toast-error { background: var(--wybe-danger-dim); border: 1px solid var(--wybe-danger); }
.toast-info { background: var(--wybe-accent-dim); border: 1px solid var(--wybe-accent); }

/* ── Page layout ───────────────────────────────────────────── */
.page-container {
    padding: 24px;
    min-height: calc(100vh - 60px);
}
.page-title {
    font-size: 22px;
    font-weight: 700;
    color: var(--wybe-text-bright);
    margin-bottom: 20px;
    font-family: var(--wybe-font);
}
.section-title {
    font-size: 16px;
    font-weight: 600;
    color: var(--wybe-text);
    margin-bottom: 12px;
    font-family: var(--wybe-font);
}

/* ── Card grid ─────────────────────────────────────────────── */
.card-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 16px;
}
.metric-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 12px;
}

/* ── Quick action buttons ──────────────────────────────────── */
.quick-action {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 10px 16px;
    background: var(--wybe-bg-secondary);
    border: 1px solid var(--wybe-border);
    border-radius: var(--wybe-radius-sm);
    color: var(--wybe-text);
    cursor: pointer;
    transition: all var(--wybe-transition);
    font-size: 13px;
    font-family: var(--wybe-font);
    text-decoration: none;
}
.quick-action:hover {
    border-color: var(--wybe-accent);
    background: var(--wybe-bg-tertiary);
}

/* ── Assistant panel ───────────────────────────────────────── */
.assistant-panel {
    border-left: 1px solid var(--wybe-border);
    background: var(--wybe-bg-secondary);
    height: calc(100vh - 56px);
    display: flex;
    flex-direction: column;
}
.assistant-header {
    padding: 12px 16px;
    border-bottom: 1px solid var(--wybe-border);
    font-size: 14px;
    font-weight: 600;
    color: var(--wybe-text);
    font-family: var(--wybe-font);
    display: flex;
    align-items: center;
    gap: 8px;
}
.assistant-header .ai-dot {
    width: 8px; height: 8px;
    border-radius: 50%;
    background: var(--wybe-success);
    animation: pulse 2s ease-in-out infinite;
}

/* ── Chatbot overrides ─────────────────────────────────────── */
.assistant-panel .chatbot {
    flex: 1;
    overflow-y: auto;
}

/* ── Welcome overlay ───────────────────────────────────────── */
.welcome-overlay {
    text-align: center;
    padding: 60px 40px;
    max-width: 600px;
    margin: 0 auto;
}
.welcome-overlay h2 {
    font-size: 26px;
    font-weight: 700;
    color: var(--wybe-text-bright);
    margin-bottom: 12px;
    font-family: var(--wybe-font);
}
.welcome-overlay p {
    font-size: 14px;
    color: var(--wybe-text-muted);
    line-height: 1.6;
    margin-bottom: 24px;
    font-family: var(--wybe-font);
}

/* ── Optimization pipeline visual ──────────────────────────── */
.opt-pipeline {
    display: flex;
    align-items: center;
    gap: 0;
    padding: 16px 0;
}
.opt-stage {
    padding: 10px 20px;
    border-radius: var(--wybe-radius-sm);
    font-size: 13px;
    font-weight: 500;
    font-family: var(--wybe-font);
    text-align: center;
    min-width: 100px;
    border: 1px solid var(--wybe-border);
    background: var(--wybe-bg-secondary);
    color: var(--wybe-text-muted);
}
.opt-stage.active { border-color: var(--wybe-accent); color: var(--wybe-accent); }
.opt-stage.done { border-color: var(--wybe-success); color: var(--wybe-success); }
.opt-arrow {
    font-size: 18px;
    color: var(--wybe-text-muted);
    padding: 0 4px;
}

/* ── Server health dot ─────────────────────────────────────── */
.health-dot {
    width: 10px; height: 10px;
    border-radius: 50%;
    display: inline-block;
}
.health-dot.alive { background: var(--wybe-success); animation: pulse 2s ease-in-out infinite; }
.health-dot.dead { background: var(--wybe-danger); }
.health-dot.starting { background: var(--wybe-warning); animation: pulse 1s ease-in-out infinite; }

/* ── Animations ────────────────────────────────────────────── */
@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.4; }
}
@keyframes toast-in {
    from { transform: translateX(100px); opacity: 0; }
    to { transform: translateX(0); opacity: 1; }
}

/* ── Gradio component overrides ────────────────────────────── */
.gradio-container .gr-button { border-radius: var(--wybe-radius-sm) !important; }
.gradio-container .gr-input, .gradio-container .gr-text-input {
    border-radius: var(--wybe-radius-sm) !important;
}
.gradio-container .gr-accordion {
    border-radius: var(--wybe-radius) !important;
    border-color: var(--wybe-border) !important;
}

/* ── New Project bar ───────────────────────────────────────── */
.new-project-bar {
    background: transparent !important;
    border: 1px dashed var(--wybe-border) !important;
    border-radius: var(--wybe-radius-sm) !important;
    margin-bottom: 12px;
}
.new-project-bar .label-wrap {
    color: var(--wybe-text-muted) !important;
    font-size: 13px !important;
}
.new-project-bar .label-wrap:hover {
    color: var(--wybe-text) !important;
}

/* ── Sidebar overlay ───────────────────────────────────────── */
.sidebar-overlay {
    position: fixed;
    right: 0;
    top: 56px;
    width: 320px;
    height: calc(100vh - 56px);
    background: var(--wybe-bg-secondary);
    border-left: 1px solid var(--wybe-border);
    z-index: 90;
    overflow-y: auto;
    padding: 16px;
    box-shadow: -4px 0 12px rgba(0,0,0,0.3);
}
.sidebar-toggle-btn {
    background: var(--wybe-bg-tertiary);
    border: 1px solid var(--wybe-border);
    border-radius: var(--wybe-radius-sm);
    color: var(--wybe-text-muted);
    cursor: pointer;
    padding: 6px 10px;
    font-size: 13px;
    font-family: var(--wybe-font);
    transition: all var(--wybe-transition);
    white-space: nowrap;
}
.sidebar-toggle-btn:hover {
    border-color: var(--wybe-accent);
    color: var(--wybe-text);
}

/* ── Responsive ────────────────────────────────────────────── */
@media (max-width: 1200px) {
    .metric-grid { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 768px) {
    .metric-grid { grid-template-columns: 1fr; }
    .card-grid { grid-template-columns: 1fr; }
    .pipeline-stepper { display: none; }
}
"""
