"""Parse nvidia-smi output for GPU status information."""

import subprocess


def get_gpu_info() -> list[dict]:
    """Query nvidia-smi and return a list of GPU info dicts.

    Each dict contains: name, utilization_pct, memory_used_mb,
    memory_total_mb, temperature_c, power_w.
    Returns an empty list if nvidia-smi is unavailable.
    """
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,utilization.gpu,memory.used,memory.total,temperature.gpu,power.draw",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return []
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []

    gpus = []
    for line in result.stdout.strip().splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 6:
            continue
        try:
            gpus.append(
                {
                    "name": parts[0],
                    "utilization_pct": float(parts[1]),
                    "memory_used_mb": float(parts[2]),
                    "memory_total_mb": float(parts[3]),
                    "temperature_c": float(parts[4]),
                    "power_w": float(parts[5]) if parts[5] not in ("[N/A]", "N/A") else 0.0,
                }
            )
        except (ValueError, IndexError):
            continue
    return gpus


def format_gpu_markdown(gpus: list[dict]) -> str:
    """Format GPU info as a readable markdown table."""
    if not gpus:
        return "No GPUs detected (nvidia-smi unavailable)"

    lines = ["| GPU | Name | Util% | VRAM | Temp | Power |", "| --- | ---- | ----- | ---- | ---- | ----- |"]
    for i, g in enumerate(gpus):
        vram = f"{g['memory_used_mb']:.0f} / {g['memory_total_mb']:.0f} MB"
        lines.append(
            f"| {i} | {g['name']} | {g['utilization_pct']:.0f}% | {vram} | {g['temperature_c']:.0f}°C | {g['power_w']:.0f}W |"
        )
    return "\n".join(lines)
