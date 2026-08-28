"""
Palette-aware utilities bridging the theme system and chart creation.

Translates theme color definitions into matplotlib rcParams, provides
highlight and categorical palette accessors, generates palettes for
arbitrary n, and enforces WCAG contrast requirements.

Usage:
    from ai_analyst.helpers.chart_palette import (
        apply_theme_colors, highlight_palette, categorical_colors,
        ensure_contrast, palette_for_n, format_hex,
    )
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def apply_theme_colors(theme: Dict) -> None:
    """Update matplotlib rcParams with colors from the theme.

    Args:
        theme: Parsed theme dict (from load_theme()).
    """
    import matplotlib as mpl
    import matplotlib.pyplot as plt

    colors = theme["colors"]
    mpl.rcParams["axes.prop_cycle"] = plt.cycler(color=colors["categorical"])
    mpl.rcParams["axes.facecolor"] = colors["background"]
    mpl.rcParams["figure.facecolor"] = colors["background"]
    mpl.rcParams["text.color"] = colors["text"]
    mpl.rcParams["axes.labelcolor"] = colors["text"]
    mpl.rcParams["xtick.color"] = colors["text_light"]
    mpl.rcParams["ytick.color"] = colors["text_light"]


def highlight_palette(theme: Dict) -> Dict[str, str]:
    """Return highlight colors for SWD charts.

    Args:
        theme: Parsed theme dict.

    Returns:
        Dict with keys: focus, comparison, alert.
    """
    hl = theme["colors"]["highlight"]
    return {"focus": hl["focus"], "comparison": hl["comparison"], "alert": hl["alert"]}


def categorical_colors(theme: Dict, n: Optional[int] = None) -> List[str]:
    """Return first n colors from the categorical palette.

    Args:
        theme: Parsed theme dict.
        n: Number of colors. None returns all.

    Returns:
        List of hex color strings.
    """
    palette = list(theme["colors"]["categorical"])
    if n is None:
        return palette
    return palette[:max(0, min(n, len(palette)))]


def ensure_contrast(hex_color: str, background: str = "#F7F6F2",
                    min_ratio: float = 4.5) -> str:
    """Adjust hex_color to meet WCAG contrast against background.

    Args:
        hex_color: Foreground color in hex.
        background: Background color in hex.
        min_ratio: Minimum WCAG contrast ratio (default 4.5 for AA).

    Returns:
        Hex color meeting contrast requirement.
    """
    fg = _hex_to_rgb(format_hex(hex_color))
    bg = _hex_to_rgb(format_hex(background))
    fg_lum = _relative_luminance(*fg)
    bg_lum = _relative_luminance(*bg)

    if _contrast_ratio(fg_lum, bg_lum) >= min_ratio:
        return format_hex(hex_color)

    bg_is_light = bg_lum > 0.5
    r, g, b = float(fg[0]), float(fg[1]), float(fg[2])

    for _ in range(200):
        step = -255 * 0.02 if bg_is_light else 255 * 0.02
        r = max(0, min(255, r + step))
        g = max(0, min(255, g + step))
        b = max(0, min(255, b + step))
        new_lum = _relative_luminance(r, g, b)
        if _contrast_ratio(new_lum, bg_lum) >= min_ratio:
            break

    return _rgb_to_hex(int(round(r)), int(round(g)), int(round(b)))


def palette_for_n(theme: Dict, n: int) -> List[str]:
    """Return exactly n colors using the best strategy.

    - n <= 8: categorical colors (distinct, colorblind-safe).
    - n > 8: evenly-spaced samples from the sequential colormap.

    Args:
        theme: Parsed theme dict.
        n: Number of colors needed.

    Returns:
        List of n hex color strings.
    """
    if n <= 0:
        return []

    cat = theme["colors"]["categorical"]
    if n <= len(cat):
        return list(cat[:n])

    import matplotlib.colors as mcolors
    import numpy as np

    seq = theme["colors"]["sequential"]
    cmap = mcolors.LinearSegmentedColormap.from_list(
        "theme_seq", [seq["low"], seq["mid"], seq["high"]], N=256)
    positions = np.linspace(0.0, 1.0, n)
    return [
        _rgb_to_hex(int(round(cmap(p)[0]*255)),
                     int(round(cmap(p)[1]*255)),
                     int(round(cmap(p)[2]*255)))
        for p in positions
    ]


def format_hex(color: str) -> str:
    """Normalize hex color to uppercase 6-digit format.

    Args:
        color: Hex color string.

    Returns:
        Uppercase 6-digit hex string.
    """
    color = color.strip()
    if not color.startswith("#"):
        color = "#" + color
    raw = color[1:]
    if len(raw) == 3:
        raw = raw[0]*2 + raw[1]*2 + raw[2]*2
    return "#" + raw.upper()[:6]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """Parse 6-digit hex string to (R, G, B) integers."""
    h = hex_color.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _rgb_to_hex(r: int, g: int, b: int) -> str:
    """Convert (R, G, B) to uppercase hex string."""
    r = max(0, min(255, r))
    g = max(0, min(255, g))
    b = max(0, min(255, b))
    return f"#{r:02X}{g:02X}{b:02X}"


def _linearize(channel_8bit: float) -> float:
    """Convert sRGB channel (0-255) to linear RGB (0-1)."""
    s = channel_8bit / 255.0
    return s / 12.92 if s <= 0.04045 else ((s + 0.055) / 1.055) ** 2.4


def _relative_luminance(r: float, g: float, b: float) -> float:
    """WCAG 2.1 relative luminance from (R, G, B) in 0-255 range."""
    return 0.2126 * _linearize(r) + 0.7152 * _linearize(g) + 0.0722 * _linearize(b)


def _contrast_ratio(lum1: float, lum2: float) -> float:
    """WCAG contrast ratio between two luminance values."""
    lighter = max(lum1, lum2)
    darker = min(lum1, lum2)
    return (lighter + 0.05) / (darker + 0.05)
