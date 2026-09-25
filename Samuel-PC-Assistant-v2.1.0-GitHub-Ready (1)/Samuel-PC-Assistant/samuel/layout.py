from __future__ import annotations


def fitted_geometry(screen_width: int, screen_height: int, preferred_width: int,
                    preferred_height: int, margin: int = 72) -> tuple[str, int, int]:
    """Return centered geometry plus safe minimum dimensions for the current display."""
    usable_width = max(320, screen_width - margin)
    usable_height = max(360, screen_height - margin)
    width = min(preferred_width, usable_width)
    height = min(preferred_height, usable_height)
    x = max(0, (screen_width - width) // 2)
    y = max(0, (screen_height - height) // 2)
    return f"{width}x{height}+{x}+{y}", min(width, 560), min(height, 520)
