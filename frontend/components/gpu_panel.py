"""GPU status panel with visual utilisation/VRAM/temperature bars."""

from __future__ import annotations


def _bar_color(pct: float) -> str:
    if pct >= 90:
        return "var(--wybe-danger)"
    if pct >= 70:
        return "var(--wybe-warning)"
    return "var(--wybe-success)"


def render_gpu_cards(gpus: list[dict]) -> str:
    """Render visual GPU status cards.

    Each dict should have: name, utilization_pct, memory_used_mb,
    memory_total_mb, temperature_c, power_w.
    """
    if not gpus:
        return (
            '<div class="gpu-card">'
            '<div class="gpu-name" style="color:var(--wybe-text-muted)">'
            "No GPUs detected</div></div>"
        )

    parts = []
    for i, g in enumerate(gpus):
        util = g.get("utilization_pct", 0)
        mem_used = g.get("memory_used_mb", 0)
        mem_total = g.get("memory_total_mb", 1)
        mem_pct = (mem_used / mem_total * 100) if mem_total > 0 else 0
        temp = g.get("temperature_c", 0)

        parts.append(f'<div class="gpu-card">')
        parts.append(f'<div class="gpu-name">GPU {i}: {g.get("name", "Unknown")}</div>')

        # Utilisation bar
        parts.append(
            f'<div class="gpu-bar-row">'
            f'<span class="gpu-bar-label">Util</span>'
            f'<div class="gpu-bar-track">'
            f'<div class="gpu-bar-fill" style="width:{util:.0f}%;background:{_bar_color(util)}"></div>'
            f"</div>"
            f'<span class="gpu-bar-value">{util:.0f}%</span>'
            f"</div>"
        )

        # VRAM bar
        parts.append(
            f'<div class="gpu-bar-row">'
            f'<span class="gpu-bar-label">VRAM</span>'
            f'<div class="gpu-bar-track">'
            f'<div class="gpu-bar-fill" style="width:{mem_pct:.0f}%;background:{_bar_color(mem_pct)}"></div>'
            f"</div>"
            f'<span class="gpu-bar-value">{mem_used:.0f}/{mem_total:.0f}</span>'
            f"</div>"
        )

        # Temperature bar
        temp_pct = min(temp / 100 * 100, 100)
        parts.append(
            f'<div class="gpu-bar-row">'
            f'<span class="gpu-bar-label">Temp</span>'
            f'<div class="gpu-bar-track">'
            f'<div class="gpu-bar-fill" style="width:{temp_pct:.0f}%;background:{_bar_color(temp_pct)}"></div>'
            f"</div>"
            f'<span class="gpu-bar-value">{temp:.0f}°C</span>'
            f"</div>"
        )

        parts.append("</div>")

    return "\n".join(parts)
