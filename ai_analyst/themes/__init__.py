"""Theme system for AI Analyst — load, merge, and cache brand themes."""

from ai_analyst.themes.theme_loader import (
    ThemeNotFoundError,
    clear_cache,
    get_categorical_palette,
    get_color,
    get_diverging_colormap,
    get_sequential_colormap,
    list_themes,
    load_theme,
)

__all__: list[str] = [
    "ThemeNotFoundError",
    "clear_cache",
    "get_categorical_palette",
    "get_color",
    "get_diverging_colormap",
    "get_sequential_colormap",
    "list_themes",
    "load_theme",
]
