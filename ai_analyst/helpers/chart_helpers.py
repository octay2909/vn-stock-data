"""
Chart Helpers — Storytelling with Data (SWD) chart builders.

15+ reusable chart functions. Each accepts data + config, returns a
matplotlib Figure. Applies SWD 6 principles: declutter, highlight,
direct labels, action titles, minimal chrome, conclusion-first.

Usage:
    from ai_analyst.helpers.chart_helpers import (
        swd_style, highlight_bar, highlight_line, waterfall,
        heatmap, funnel, scatter, box, stacked_bar, slope,
        diverging_bar, donut, area, grouped_bar, bullet, gauge,
        action_title, annotate_point, save_chart, CHART_FIGSIZE,
    )
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import matplotlib.patches as mpatches
import numpy as np

# ---------------------------------------------------------------------------
# Default color palette (SWD-inspired)
# ---------------------------------------------------------------------------

COLORS: Dict[str, str] = {
    "primary":   "#4878CF",
    "secondary": "#6ACC65",
    "accent":    "#D65F5F",
    "neutral":   "#B0B0B0",
    "good":      "#6ACC65",
    "bad":       "#D65F5F",
    "highlight": "#4878CF",
    "muted":     "#B0B0B0",
    "bg":        "#F7F6F2",
    "text":      "#333333",
    "text_light":"#666666",
    "gray100":   "#F3F4F6",
    "gray200":   "#E5E7EB",
    "gray400":   "#9CA3AF",
    "gray600":   "#6B7280",
    "gray900":   "#1F2937",
    "white":     "#FFFFFF",
}

CHART_FIGSIZE: Tuple[int, int] = (10, 6)

# ---------------------------------------------------------------------------
# Style loader
# ---------------------------------------------------------------------------


def swd_style(theme: Optional[Dict] = None) -> Dict[str, str]:
    """Apply SWD matplotlib style and return the color palette.

    Args:
        theme: Optional theme dict. When provided, overrides background
            and text colors from the theme.

    Returns:
        Color palette dict.
    """
    plt.rcParams.update({
        "figure.figsize": CHART_FIGSIZE,
        "figure.dpi": 150,
        "figure.facecolor": COLORS["bg"],
        "axes.facecolor": COLORS["bg"],
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": False,
        "font.family": "sans-serif",
        "font.size": 10,
        "axes.titlesize": 14,
        "axes.titleweight": "bold",
        "text.color": COLORS["text"],
        "axes.labelcolor": COLORS["text"],
    })
    if theme is not None:
        colors = theme.get("colors", {})
        bg = colors.get("background", COLORS["bg"])
        text = colors.get("text", COLORS["text"])
        plt.rcParams["figure.facecolor"] = bg
        plt.rcParams["axes.facecolor"] = bg
        plt.rcParams["text.color"] = text
        plt.rcParams["axes.labelcolor"] = text
    return dict(COLORS)


def load_theme_colors(theme_name: Optional[str] = None) -> Dict:
    """Load theme colors and update the module-level COLORS dict.

    Args:
        theme_name: Theme to load. None loads the base theme.

    Returns:
        Full theme dict.
    """
    from ai_analyst.helpers.themes.theme_loader import load_theme
    from ai_analyst.helpers.chart_palette import apply_theme_colors

    theme = load_theme(theme_name)
    colors = theme["colors"]
    COLORS.update({
        "primary": colors["primary"],
        "secondary": colors.get("secondary", colors["primary"]),
        "accent": colors["accent"],
        "neutral": colors["neutral"],
        "bg": colors["background"],
        "text": colors["text"],
    })
    apply_theme_colors(theme)
    return theme


# ---------------------------------------------------------------------------
# Title & annotation helpers
# ---------------------------------------------------------------------------


def action_title(ax: plt.Axes, title: str, subtitle: Optional[str] = None) -> None:
    """Add a bold action title and optional subtitle.

    Args:
        ax: Matplotlib Axes.
        title: Takeaway statement.
        subtitle: Context line.
    """
    if subtitle:
        ax.text(0, 1.12, title, transform=ax.transAxes,
                fontsize=17, fontweight="bold", color=COLORS["gray900"],
                va="bottom", ha="left")
        ax.text(0, 1.06, subtitle, transform=ax.transAxes,
                fontsize=12, color=COLORS["gray600"], va="bottom", ha="left")
        ax.set_title("")
    else:
        ax.set_title(title, fontsize=17, fontweight="bold",
                     color=COLORS["gray900"], loc="left", pad=16)


def annotate_point(ax: plt.Axes, x: Any, y: float, text: str,
                   arrow_color: Optional[str] = None,
                   offset: Tuple[int, int] = (20, 20)) -> None:
    """Add a clean annotation with arrow to a data point.

    Args:
        ax: Matplotlib Axes.
        x: X-coordinate.
        y: Y-coordinate.
        text: Annotation text.
        arrow_color: Arrow/text color.
        offset: Label offset in points.
    """
    arrow_color = arrow_color or COLORS["gray600"]
    ax.annotate(text, xy=(x, y), xytext=offset, textcoords="offset points",
                fontsize=9, color=arrow_color,
                arrowprops=dict(arrowstyle="->", color=arrow_color, lw=1.0))


def save_chart(fig: plt.Figure, path: Union[str, Path],
               dpi: int = 150, close: bool = True) -> None:
    """Save chart with tight layout.

    Args:
        fig: Matplotlib Figure.
        path: Output file path.
        dpi: Resolution.
        close: Close figure after saving.
    """
    fig.tight_layout()
    fig.savefig(path, dpi=dpi, bbox_inches="tight",
                facecolor=COLORS["bg"], edgecolor="none")
    if close:
        plt.close(fig)


# ---------------------------------------------------------------------------
# 1. highlight_bar
# ---------------------------------------------------------------------------


def highlight_bar(ax: plt.Axes, categories: Sequence[str],
                  values: Sequence[float],
                  highlight: Optional[Union[str, List[str]]] = None,
                  highlight_color: Optional[str] = None,
                  base_color: Optional[str] = None,
                  horizontal: bool = True, sort: bool = True,
                  fmt: Optional[str] = None,
                  label_offset: float = 0.02) -> None:
    """Bar chart with one bar highlighted, the rest gray.

    Args:
        ax: Matplotlib Axes.
        categories: Category labels.
        values: Numeric values.
        highlight: Category to highlight (or list).
        highlight_color: Color for highlighted bar(s).
        base_color: Color for non-highlighted bars.
        horizontal: Draw horizontal bars if True.
        sort: Sort bars by value if True.
        fmt: Format string for value labels.
        label_offset: Fraction of max value for label offset.
    """
    highlight_color = highlight_color or COLORS["primary"]
    base_color = base_color or COLORS["gray200"]

    cats = list(categories)
    vals = list(values)

    if sort:
        paired = sorted(zip(vals, cats), reverse=False)
        vals, cats = zip(*paired)
        vals, cats = list(vals), list(cats)

    if isinstance(highlight, str):
        highlight = [highlight]
    highlight_set = set(highlight) if highlight else set()

    bar_colors = [highlight_color if c in highlight_set else base_color for c in cats]

    if horizontal:
        bars = ax.barh(cats, vals, color=bar_colors)
        ax.set_xlim(0, max(vals) * 1.15)
        ax.xaxis.set_visible(False)
        ax.spines["bottom"].set_visible(False)
        max_val = max(vals)
        for bar, v in zip(bars, vals):
            label = fmt.format(v) if fmt else f"{v:,.0f}"
            ax.text(v + max_val * label_offset,
                    bar.get_y() + bar.get_height() / 2,
                    label, va="center", fontsize=9, color=COLORS["gray900"])
    else:
        bars = ax.bar(cats, vals, color=bar_colors)
        ax.set_ylim(0, max(vals) * 1.15)
        ax.yaxis.set_visible(False)
        ax.spines["left"].set_visible(False)
        max_val = max(vals)
        for bar, v in zip(bars, vals):
            label = fmt.format(v) if fmt else f"{v:,.0f}"
            ax.text(bar.get_x() + bar.get_width() / 2,
                    v + max_val * label_offset,
                    label, ha="center", fontsize=9, color=COLORS["gray900"])
    ax.grid(False)


# ---------------------------------------------------------------------------
# 2. highlight_line
# ---------------------------------------------------------------------------


def highlight_line(ax: plt.Axes, x: Sequence, y_dict: Dict[str, Sequence[float]],
                   highlight: Optional[Union[str, List[str]]] = None,
                   highlight_color: Optional[str] = None,
                   base_color: Optional[str] = None,
                   linewidth_highlight: float = 2.5,
                   linewidth_base: float = 1.2) -> None:
    """Line chart with one line colored, the rest gray.

    Args:
        ax: Matplotlib Axes.
        x: Shared x-axis values.
        y_dict: Dict mapping series_name -> y-values.
        highlight: Series name(s) to highlight.
        highlight_color: Color for highlighted lines.
        base_color: Color for background lines.
        linewidth_highlight: Width of highlighted lines.
        linewidth_base: Width of background lines.
    """
    highlight_color = highlight_color or COLORS["primary"]
    base_color = base_color or COLORS["gray200"]

    if isinstance(highlight, str):
        highlight = [highlight]
    highlight_set = set(highlight) if highlight else set()

    for name, y in y_dict.items():
        if name not in highlight_set:
            ax.plot(x, y, color=base_color, linewidth=linewidth_base, zorder=1)
            ax.text(x[-1], y[-1], f"  {name}", va="center",
                    fontsize=8, color=COLORS["gray400"])

    for name, y in y_dict.items():
        if name in highlight_set:
            ax.plot(x, y, color=highlight_color, linewidth=linewidth_highlight, zorder=2)
            ax.text(x[-1], y[-1], f"  {name}", va="center",
                    fontsize=9, fontweight="bold", color=highlight_color)

    ax.yaxis.grid(True, color=COLORS["gray200"], linewidth=0.5)
    ax.set_axisbelow(True)


# ---------------------------------------------------------------------------
# 3. waterfall
# ---------------------------------------------------------------------------


def waterfall(ax: plt.Axes, labels: Sequence[str], values: Sequence[float],
              start_label: str = "Start", end_label: str = "End",
              positive_color: Optional[str] = None,
              negative_color: Optional[str] = None,
              total_color: Optional[str] = None,
              fmt: Optional[str] = None,
              show_connectors: bool = True) -> plt.Figure:
    """Waterfall chart showing incremental contributions.

    Args:
        ax: Matplotlib Axes.
        labels: Step labels (excluding start/end totals).
        values: Change values for each step (positive or negative).
        start_label: Label for the starting total bar.
        end_label: Label for the ending total bar.
        positive_color: Color for positive increments.
        negative_color: Color for negative increments.
        total_color: Color for total bars.
        fmt: Format string for labels.
        show_connectors: Draw connector lines between bars.

    Returns:
        Parent Figure.
    """
    positive_color = positive_color or COLORS["good"]
    negative_color = negative_color or COLORS["bad"]
    total_color = total_color or COLORS["primary"]
    fmt = fmt or "{:,.0f}"

    vals = list(values)
    all_labels = [start_label] + list(labels) + [end_label]
    n = len(all_labels)

    start_total = sum(v for v in vals if v > 0)
    running = start_total
    bottoms = [0.0]
    heights = [start_total]
    bar_colors = [total_color]

    for v in vals:
        if v >= 0:
            bottoms.append(running)
            heights.append(v)
            bar_colors.append(positive_color)
            running += v
        else:
            running += v
            bottoms.append(running)
            heights.append(abs(v))
            bar_colors.append(negative_color)

    bottoms.append(0)
    heights.append(running)
    bar_colors.append(total_color)

    x = np.arange(n)
    bars = ax.bar(x, heights, bottom=bottoms, color=bar_colors, width=0.6, zorder=2)

    if show_connectors:
        for i in range(n - 1):
            top_i = bottoms[i] + heights[i]
            ax.plot([x[i] + 0.3, x[i + 1] - 0.3], [top_i, top_i],
                    color=COLORS["gray400"], linewidth=0.8, linestyle="--", zorder=1)

    for bar, b, h, lbl in zip(bars, bottoms, heights, all_labels):
        value_text = fmt.format(h if lbl in (start_label, end_label) else
                                (h if bar.get_facecolor()[:3] != tuple(int(negative_color.lstrip('#')[i:i+2], 16)/255 for i in (0,2,4)) else -h))
        y_pos = b + h + max(heights) * 0.02
        ax.text(bar.get_x() + bar.get_width() / 2, y_pos, value_text,
                ha="center", va="bottom", fontsize=9, color=COLORS["gray900"])

    ax.set_xticks(x)
    ax.set_xticklabels(all_labels, fontsize=9)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.yaxis.grid(True, color=COLORS["gray100"], linewidth=0.5)
    ax.set_axisbelow(True)
    return ax.figure


# ---------------------------------------------------------------------------
# 4. heatmap
# ---------------------------------------------------------------------------


def heatmap(ax: plt.Axes, row_labels: Sequence[str],
            col_labels: Sequence[str], matrix: Any,
            fmt: str = "{:.0%}", cmap: Optional[str] = None,
            cmap_high: Optional[str] = None,
            cmap_low: Optional[str] = None) -> Tuple[plt.Figure, plt.Axes]:
    """Color-coded heatmap (e.g., retention triangle, correlation).

    Args:
        ax: Matplotlib Axes.
        row_labels: Y-axis labels.
        col_labels: X-axis labels.
        matrix: 2D numeric array. NaN cells render as light gray.
        fmt: Format string for cell labels.
        cmap: Matplotlib colormap name (overrides cmap_high/cmap_low).
        cmap_high: Hex color for high values.
        cmap_low: Hex color for low values.

    Returns:
        (fig, ax) tuple.
    """
    cmap_high = cmap_high or COLORS["good"]
    cmap_low = cmap_low or COLORS["bad"]
    data = np.array(matrix, dtype=float)
    n_rows, n_cols = data.shape

    if cmap is not None:
        from matplotlib.cm import get_cmap
        colormap = get_cmap(cmap)
    else:
        colormap = None

    def _hex_to_rgb(h: str) -> Tuple[int, int, int]:
        h = h.lstrip("#")
        return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

    def _interp(val: float, low: str, high: str) -> str:
        r1, g1, b1 = _hex_to_rgb(low)
        r2, g2, b2 = _hex_to_rgb(high)
        t = max(0.0, min(1.0, val))
        return "#{:02x}{:02x}{:02x}".format(
            int(r1 + (r2 - r1) * t), int(g1 + (g2 - g1) * t), int(b1 + (b2 - b1) * t))

    ax.set_xlim(-0.5, n_cols - 0.5)
    ax.set_ylim(n_rows - 0.5, -0.5)

    for i in range(n_rows):
        for j in range(n_cols):
            val = data[i, j]
            if np.isnan(val):
                rect = mpatches.Rectangle((j - 0.5, i - 0.5), 1, 1,
                                          facecolor=COLORS["gray100"],
                                          edgecolor=COLORS["white"], linewidth=1)
                ax.add_patch(rect)
            else:
                if colormap is not None:
                    rgba = colormap(max(0.0, min(1.0, val)))
                    color = "#{:02x}{:02x}{:02x}".format(
                        int(rgba[0]*255), int(rgba[1]*255), int(rgba[2]*255))
                    lum = 0.299*rgba[0] + 0.587*rgba[1] + 0.114*rgba[2]
                    is_dark = lum < 0.5
                else:
                    color = _interp(val, cmap_low, cmap_high)
                    is_dark = val >= 0.5

                rect = mpatches.Rectangle((j - 0.5, i - 0.5), 1, 1,
                                          facecolor=color,
                                          edgecolor=COLORS["white"], linewidth=1)
                ax.add_patch(rect)
                text_color = COLORS["white"] if is_dark else COLORS["gray900"]
                ax.text(j, i, fmt.format(val), ha="center", va="center",
                        fontsize=9, color=text_color, fontweight="bold")

    ax.set_xticks(range(n_cols))
    ax.set_xticklabels(col_labels, fontsize=10, color=COLORS["gray600"])
    ax.xaxis.set_ticks_position("top")
    ax.set_yticks(range(n_rows))
    ax.set_yticklabels(row_labels, fontsize=10, color=COLORS["gray600"])
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(axis="both", length=0)
    return ax.figure, ax


# ---------------------------------------------------------------------------
# 5. funnel
# ---------------------------------------------------------------------------


def funnel(ax: plt.Axes, steps: Sequence[str], counts: Sequence[float],
           highlight_step: Optional[int] = None,
           bar_color: Optional[str] = None,
           highlight_color: Optional[str] = None,
           fmt: Optional[str] = None) -> None:
    """Funnel chart showing drop-off at each step.

    Args:
        ax: Matplotlib Axes.
        steps: Step labels.
        counts: Counts at each step (monotonically decreasing).
        highlight_step: Index of step to highlight.
        bar_color: Non-highlighted bar color.
        highlight_color: Highlighted bar color.
        fmt: Format string for count labels.
    """
    bar_color = bar_color or COLORS["gray200"]
    highlight_color = highlight_color or COLORS["accent"]
    fmt = fmt or "{:,.0f}"

    n = len(steps)
    counts_list = list(counts)

    if highlight_step is None and n > 1:
        drops = [counts_list[i] - counts_list[i + 1] for i in range(n - 1)]
        highlight_step = drops.index(max(drops)) + 1

    y_positions = list(range(n - 1, -1, -1))
    colors = [highlight_color if i == highlight_step else bar_color for i in range(n)]

    bars = ax.barh(y_positions, counts_list, color=colors, height=0.6)
    ax.set_yticks(y_positions)
    ax.set_yticklabels(steps)
    ax.tick_params(axis="y", length=0)

    max_val = max(counts_list)
    for bar, count in zip(bars, counts_list):
        ax.text(count + max_val * 0.02, bar.get_y() + bar.get_height() / 2,
                fmt.format(count), va="center", fontsize=9, color=COLORS["gray900"])

    for i in range(n - 1):
        if counts_list[i] > 0:
            conv_rate = counts_list[i + 1] / counts_list[i]
            y_mid = (y_positions[i] + y_positions[i + 1]) / 2
            x_pos = max(counts_list[i], counts_list[i + 1]) + max_val * 0.12
            label_color = highlight_color if (i + 1) == highlight_step else COLORS["gray600"]
            ax.text(x_pos, y_mid, f"{conv_rate:.0%} pass",
                    va="center", ha="center", fontsize=8, color=label_color)

    ax.set_xlim(0, max_val * 1.35)
    ax.xaxis.set_visible(False)
    ax.spines["bottom"].set_visible(False)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(False)


# ---------------------------------------------------------------------------
# 6. scatter
# ---------------------------------------------------------------------------


def scatter(ax: plt.Axes, x: Sequence[float], y: Sequence[float],
            labels: Optional[Sequence[str]] = None,
            highlight: Optional[Union[str, List[str]]] = None,
            highlight_color: Optional[str] = None,
            base_color: Optional[str] = None,
            size: float = 40, alpha: float = 0.7,
            show_trendline: bool = False) -> None:
    """Scatter plot with optional highlight and trendline.

    Args:
        ax: Matplotlib Axes.
        x: X-values.
        y: Y-values.
        labels: Optional point labels (same length as x).
        highlight: Labels to highlight.
        highlight_color: Highlighted point color.
        base_color: Non-highlighted point color.
        size: Marker size.
        alpha: Marker opacity.
        show_trendline: Overlay linear trendline.
    """
    highlight_color = highlight_color or COLORS["primary"]
    base_color = base_color or COLORS["neutral"]

    if isinstance(highlight, str):
        highlight = [highlight]
    highlight_set = set(highlight) if highlight else set()

    x_arr = np.asarray(x, dtype=float)
    y_arr = np.asarray(y, dtype=float)

    if labels is not None:
        colors = [highlight_color if l in highlight_set else base_color for l in labels]
    else:
        colors = [base_color] * len(x_arr)

    ax.scatter(x_arr, y_arr, c=colors, s=size, alpha=alpha, zorder=2, edgecolors="none")

    if labels is not None:
        for xi, yi, lbl in zip(x_arr, y_arr, labels):
            if lbl in highlight_set:
                ax.annotate(lbl, (xi, yi), fontsize=8, fontweight="bold",
                            color=highlight_color, xytext=(5, 5),
                            textcoords="offset points")

    if show_trendline:
        z = np.polyfit(x_arr, y_arr, 1)
        trend = np.polyval(z, x_arr)
        order = np.argsort(x_arr)
        ax.plot(x_arr[order], trend[order], color=COLORS["gray400"],
                linewidth=1, linestyle="--", zorder=1)

    ax.yaxis.grid(True, color=COLORS["gray200"], linewidth=0.5)
    ax.set_axisbelow(True)


# ---------------------------------------------------------------------------
# 7. box
# ---------------------------------------------------------------------------


def box(ax: plt.Axes, data_dict: Dict[str, Sequence[float]],
        highlight: Optional[str] = None,
        highlight_color: Optional[str] = None,
        base_color: Optional[str] = None,
        show_means: bool = True) -> None:
    """Box plot comparing distributions across groups.

    Args:
        ax: Matplotlib Axes.
        data_dict: Dict mapping group names to value sequences.
        highlight: Group name to highlight.
        base_color: Non-highlighted box color.
        highlight_color: Highlighted box color.
        show_means: Show mean markers.
    """
    highlight_color = highlight_color or COLORS["primary"]
    base_color = base_color or COLORS["gray200"]

    names = list(data_dict.keys())
    data_list = [list(data_dict[n]) for n in names]
    positions = list(range(1, len(names) + 1))

    bp = ax.boxplot(data_list, positions=positions, widths=0.5,
                    patch_artist=True, showfliers=True,
                    flierprops=dict(marker="o", markersize=3,
                                    markerfacecolor=COLORS["gray400"]))

    for i, (patch, name) in enumerate(zip(bp["boxes"], names)):
        color = highlight_color if name == highlight else base_color
        patch.set_facecolor(color)
        patch.set_edgecolor(COLORS["gray600"])

    for element in ["whiskers", "caps"]:
        for line in bp[element]:
            line.set_color(COLORS["gray600"])
    for median in bp["medians"]:
        median.set_color(COLORS["gray900"])
        median.set_linewidth(2)

    if show_means:
        means = [np.mean(d) for d in data_list]
        ax.scatter(positions, means, marker="D", color=COLORS["accent"],
                   s=30, zorder=5, label="Mean")

    ax.set_xticks(positions)
    ax.set_xticklabels(names, fontsize=10)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.yaxis.grid(True, color=COLORS["gray100"], linewidth=0.5)
    ax.set_axisbelow(True)


# ---------------------------------------------------------------------------
# 8. stacked_bar
# ---------------------------------------------------------------------------


def stacked_bar(ax: plt.Axes, categories: Sequence[str],
                layers: Dict[str, Sequence[float]],
                colors_map: Optional[Dict[str, str]] = None,
                highlight_layer: Optional[str] = None,
                show_totals: bool = True,
                fmt: Optional[str] = None,
                normalize: bool = False) -> None:
    """Stacked bar chart with optional layer highlighting.

    Args:
        ax: Matplotlib Axes.
        categories: Category labels (x-axis).
        layers: Dict mapping layer_name -> values.
        colors_map: Optional dict of layer_name -> hex color.
        highlight_layer: Layer to highlight.
        show_totals: Show total above each stack.
        fmt: Format string.
        normalize: Normalize to 100%.
    """
    cats = list(categories)
    bottom = np.zeros(len(cats))
    fmt = fmt or ("{:.0%}" if normalize else "{:,.0f}")

    if normalize:
        totals = sum(np.array(v, dtype=float) for v in layers.values())
    else:
        totals = None

    _cycle = [COLORS["primary"], COLORS["secondary"], COLORS["accent"],
              COLORS["neutral"], COLORS["gray400"]]

    for idx, (name, values) in enumerate(layers.items()):
        vals = np.array(values, dtype=float)
        if normalize:
            vals = vals / totals

        if colors_map and name in colors_map:
            color = colors_map[name]
        elif name == highlight_layer:
            color = COLORS["accent"]
        else:
            color = _cycle[idx % len(_cycle)] if not highlight_layer else COLORS["gray200"]

        ax.bar(cats, vals, bottom=bottom, color=color, width=0.7, label=name)
        bottom += vals

    if normalize:
        ax.yaxis.set_major_formatter(mticker.PercentFormatter(1.0))

    if show_totals:
        for i, total in enumerate(bottom):
            label = fmt.format(total) if not normalize else "{:,.0f}".format(totals[i])
            ax.text(i, total + max(bottom) * 0.02, label,
                    ha="center", fontsize=9, color=COLORS["gray600"])

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.yaxis.grid(True, color=COLORS["gray100"], linewidth=0.5)
    ax.set_axisbelow(True)
    ax.legend(fontsize=9, frameon=False, loc="upper center",
              bbox_to_anchor=(0.5, -0.08), ncol=min(len(layers), 5))


# ---------------------------------------------------------------------------
# 9. slope
# ---------------------------------------------------------------------------


def slope(ax: plt.Axes, labels: Sequence[str],
          start_values: Sequence[float], end_values: Sequence[float],
          start_label: str = "Before", end_label: str = "After",
          highlight_labels: Optional[List[str]] = None,
          title: Optional[str] = None) -> Tuple[plt.Figure, plt.Axes]:
    """Slope chart showing change between two points.

    Args:
        ax: Matplotlib Axes.
        labels: Item labels.
        start_values: Starting values.
        end_values: Ending values.
        start_label: Left axis label.
        end_label: Right axis label.
        highlight_labels: Items to highlight.
        title: Chart title.

    Returns:
        (fig, ax) tuple.
    """
    if isinstance(highlight_labels, str):
        highlight_labels = [highlight_labels]
    highlight_set = set(highlight_labels) if highlight_labels else set()

    for lbl, sv, ev in zip(labels, start_values, end_values):
        if lbl not in highlight_set:
            ax.plot([0, 1], [sv, ev], color=COLORS["gray200"], linewidth=1.5, zorder=1)
            ax.text(-0.08, sv, f"{lbl}  {sv:,.1f}", ha="right", va="center",
                    fontsize=9, color=COLORS["gray400"])
            ax.text(1.08, ev, f"{ev:,.1f}  {lbl}", ha="left", va="center",
                    fontsize=9, color=COLORS["gray400"])

    for lbl, sv, ev in zip(labels, start_values, end_values):
        if lbl in highlight_set:
            ax.plot([0, 1], [sv, ev], color=COLORS["primary"], linewidth=2.5, zorder=3)
            ax.scatter([0, 1], [sv, ev], color=COLORS["primary"], s=60, zorder=4)
            ax.text(-0.08, sv, f"{lbl}  {sv:,.1f}", ha="right", va="center",
                    fontsize=10, fontweight="bold", color=COLORS["primary"])
            ax.text(1.08, ev, f"{ev:,.1f}  {lbl}", ha="left", va="center",
                    fontsize=10, fontweight="bold", color=COLORS["primary"])

    ax.set_xlim(-0.5, 1.5)
    ax.set_xticks([0, 1])
    ax.set_xticklabels([start_label, end_label], fontsize=12,
                       fontweight="bold", color=COLORS["gray900"])
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.yaxis.set_visible(False)
    ax.tick_params(axis="x", length=0)
    ax.grid(False)
    ax.axvline(0, color=COLORS["gray200"], linewidth=0.8, zorder=0)
    ax.axvline(1, color=COLORS["gray200"], linewidth=0.8, zorder=0)

    if title:
        action_title(ax, title)
    return ax.figure, ax


# ---------------------------------------------------------------------------
# 10. diverging_bar
# ---------------------------------------------------------------------------


def diverging_bar(ax: plt.Axes, categories: Sequence[str],
                  values: Sequence[float],
                  positive_color: Optional[str] = None,
                  negative_color: Optional[str] = None,
                  fmt: Optional[str] = None) -> None:
    """Diverging horizontal bar chart centered at zero.

    Args:
        ax: Matplotlib Axes.
        categories: Category labels.
        values: Values (positive and negative).
        positive_color: Color for positive bars.
        negative_color: Color for negative bars.
        fmt: Format string.
    """
    positive_color = positive_color or COLORS["good"]
    negative_color = negative_color or COLORS["bad"]
    fmt = fmt or "{:+,.1f}"

    cats = list(categories)
    vals = list(values)
    bar_colors = [positive_color if v >= 0 else negative_color for v in vals]

    bars = ax.barh(cats, vals, color=bar_colors, height=0.6)
    ax.axvline(0, color=COLORS["gray600"], linewidth=0.8)

    max_abs = max(abs(v) for v in vals) if vals else 1
    for bar, v in zip(bars, vals):
        offset = max_abs * 0.03
        x_pos = v + offset if v >= 0 else v - offset
        ha = "left" if v >= 0 else "right"
        ax.text(x_pos, bar.get_y() + bar.get_height() / 2,
                fmt.format(v), va="center", ha=ha, fontsize=9,
                color=COLORS["gray900"])

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(False)
    ax.xaxis.set_visible(False)
    ax.grid(False)


# ---------------------------------------------------------------------------
# 11. donut
# ---------------------------------------------------------------------------


def donut(ax: plt.Axes, labels: Sequence[str], values: Sequence[float],
          highlight: Optional[str] = None,
          colors_list: Optional[List[str]] = None,
          center_text: Optional[str] = None,
          center_subtext: Optional[str] = None) -> None:
    """Donut chart with optional center text and highlight.

    Args:
        ax: Matplotlib Axes.
        labels: Segment labels.
        values: Segment values.
        highlight: Label to emphasize (exploded).
        colors_list: Custom colors per segment.
        center_text: Big number in the center.
        center_subtext: Description below center text.
    """
    _cycle = [COLORS["primary"], COLORS["secondary"], COLORS["accent"],
              COLORS["neutral"], COLORS["gray400"], COLORS["gray600"]]

    if colors_list is None:
        colors_list = [_cycle[i % len(_cycle)] for i in range(len(labels))]

    explode = [0.05 if l == highlight else 0 for l in labels]

    wedges, texts, autotexts = ax.pie(
        values, labels=None, colors=colors_list, explode=explode,
        autopct="%1.0f%%", pctdistance=0.8, startangle=90,
        wedgeprops=dict(width=0.4, edgecolor=COLORS["white"], linewidth=2))

    for t in autotexts:
        t.set_fontsize(9)
        t.set_color(COLORS["gray900"])

    if center_text:
        ax.text(0, 0.05, center_text, ha="center", va="center",
                fontsize=24, fontweight="bold", color=COLORS["gray900"])
    if center_subtext:
        ax.text(0, -0.15, center_subtext, ha="center", va="center",
                fontsize=10, color=COLORS["gray600"])

    ax.legend(wedges, labels, loc="center left", bbox_to_anchor=(1, 0.5),
              fontsize=9, frameon=False)


# ---------------------------------------------------------------------------
# 12. area
# ---------------------------------------------------------------------------


def area(ax: plt.Axes, x: Sequence, y_dict: Dict[str, Sequence[float]],
         colors_map: Optional[Dict[str, str]] = None,
         alpha: float = 0.4, stacked: bool = True) -> None:
    """Area chart (stacked or overlapping).

    Args:
        ax: Matplotlib Axes.
        x: Shared x-axis values.
        y_dict: Dict mapping series_name -> y-values.
        colors_map: Optional color mapping.
        alpha: Fill opacity.
        stacked: Stack areas if True.
    """
    _cycle = [COLORS["primary"], COLORS["secondary"], COLORS["accent"],
              COLORS["neutral"]]

    if stacked:
        bottom = np.zeros(len(x))
        for idx, (name, y) in enumerate(y_dict.items()):
            color = (colors_map or {}).get(name, _cycle[idx % len(_cycle)])
            y_arr = np.asarray(y, dtype=float)
            ax.fill_between(x, bottom, bottom + y_arr, alpha=alpha,
                            color=color, label=name)
            ax.plot(x, bottom + y_arr, color=color, linewidth=1.5)
            bottom += y_arr
    else:
        for idx, (name, y) in enumerate(y_dict.items()):
            color = (colors_map or {}).get(name, _cycle[idx % len(_cycle)])
            ax.fill_between(x, 0, y, alpha=alpha, color=color, label=name)
            ax.plot(x, y, color=color, linewidth=1.5)

    ax.legend(fontsize=9, frameon=False)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.yaxis.grid(True, color=COLORS["gray200"], linewidth=0.5)
    ax.set_axisbelow(True)


# ---------------------------------------------------------------------------
# 13. grouped_bar
# ---------------------------------------------------------------------------


def grouped_bar(ax: plt.Axes, categories: Sequence[str],
                groups: Dict[str, Sequence[float]],
                highlight_group: Optional[str] = None,
                fmt: Optional[str] = None) -> None:
    """Grouped bar chart comparing values across categories and groups.

    Args:
        ax: Matplotlib Axes.
        categories: X-axis category labels.
        groups: Dict mapping group_name -> values per category.
        highlight_group: Group to highlight.
        fmt: Format string for labels.
    """
    _cycle = [COLORS["primary"], COLORS["accent"], COLORS["secondary"],
              COLORS["gray600"], COLORS["gray400"]]
    fmt = fmt or "{:,.0f}"

    group_names = list(groups.keys())
    n_groups = len(group_names)
    n_cats = len(categories)
    bar_width = 0.7 / n_groups
    x = np.arange(n_cats)

    for i, gname in enumerate(group_names):
        vals = list(groups[gname])
        offset = (i - (n_groups - 1) / 2) * bar_width

        if highlight_group is not None:
            color = COLORS["primary"] if gname == highlight_group else COLORS["gray200"]
        else:
            color = _cycle[i % len(_cycle)]

        bars = ax.bar(x + offset, vals, width=bar_width * 0.9,
                      color=color, label=gname)

        for bar, v in zip(bars, vals):
            if v > 0:
                ax.text(bar.get_x() + bar.get_width() / 2,
                        bar.get_height() + max(vals) * 0.02,
                        fmt.format(v), ha="center", va="bottom",
                        fontsize=8, color=COLORS["gray900"])

    ax.set_xticks(x)
    ax.set_xticklabels(categories)
    ax.legend(fontsize=9, frameon=False, loc="upper right")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.yaxis.grid(True, color=COLORS["gray100"], linewidth=0.5)
    ax.set_axisbelow(True)


# ---------------------------------------------------------------------------
# 14. bullet
# ---------------------------------------------------------------------------


def bullet(ax: plt.Axes, label: str, actual: float, target: float,
           ranges: Optional[Tuple[float, float, float]] = None,
           fmt: Optional[str] = None) -> None:
    """Bullet chart comparing actual to target with qualitative ranges.

    Args:
        ax: Matplotlib Axes.
        label: Metric label.
        actual: Actual value.
        target: Target value.
        ranges: Tuple of (poor_max, ok_max, good_max) for background.
        fmt: Format string.
    """
    fmt = fmt or "{:,.0f}"

    if ranges is None:
        max_val = max(actual, target) * 1.2
        ranges = (max_val * 0.33, max_val * 0.67, max_val)

    poor, ok, good = ranges
    ax.barh(0, good, height=0.6, color=COLORS["gray100"], zorder=1)
    ax.barh(0, ok, height=0.6, color=COLORS["gray200"], zorder=2)
    ax.barh(0, poor, height=0.6, color=COLORS["gray400"], zorder=3)
    ax.barh(0, actual, height=0.3, color=COLORS["primary"], zorder=4)
    ax.axvline(target, color=COLORS["gray900"], linewidth=2.5, zorder=5)

    ax.text(actual + good * 0.02, 0, fmt.format(actual),
            va="center", fontsize=10, fontweight="bold", color=COLORS["primary"])
    ax.text(target, -0.4, f"Target: {fmt.format(target)}",
            ha="center", fontsize=8, color=COLORS["gray600"])

    ax.set_yticks([0])
    ax.set_yticklabels([label], fontsize=11, fontweight="bold")
    ax.set_xlim(0, good * 1.1)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(False)
    ax.tick_params(axis="y", length=0)
    ax.xaxis.set_visible(False)


# ---------------------------------------------------------------------------
# 15. gauge
# ---------------------------------------------------------------------------


def gauge(ax: plt.Axes, value: float, min_val: float = 0,
          max_val: float = 100, label: Optional[str] = None,
          thresholds: Optional[Tuple[float, float]] = None,
          fmt: Optional[str] = None) -> None:
    """Semi-circle gauge chart.

    Args:
        ax: Matplotlib Axes.
        value: Current value.
        min_val: Minimum scale value.
        max_val: Maximum scale value.
        label: Metric label below the gauge.
        thresholds: (warning, danger) threshold values.
        fmt: Format string.
    """
    fmt = fmt or "{:,.0f}"
    if thresholds is None:
        thresholds = (max_val * 0.33, max_val * 0.67)

    warn, danger = thresholds
    total_range = max_val - min_val

    zones = [
        (warn - min_val, COLORS["bad"]),
        (danger - warn, COLORS["neutral"]),
        (max_val - danger, COLORS["good"]),
    ]

    start_angle = 180
    for arc_val, color in zones:
        sweep = (arc_val / total_range) * 180
        wedge = mpatches.Wedge((0.5, 0), 0.4, start_angle - sweep, start_angle,
                               width=0.12, facecolor=color, edgecolor=COLORS["white"],
                               linewidth=1, transform=ax.transAxes)
        ax.add_patch(wedge)
        start_angle -= sweep

    needle_angle = 180 - ((value - min_val) / total_range) * 180
    needle_rad = math.radians(needle_angle)
    nx = 0.5 + 0.3 * math.cos(needle_rad)
    ny = 0.3 * math.sin(needle_rad)
    ax.annotate("", xy=(nx, ny), xytext=(0.5, 0),
                xycoords="axes fraction", textcoords="axes fraction",
                arrowprops=dict(arrowstyle="-|>", color=COLORS["gray900"], lw=2))

    ax.text(0.5, 0.15, fmt.format(value), ha="center", va="center",
            fontsize=24, fontweight="bold", color=COLORS["gray900"],
            transform=ax.transAxes)
    if label:
        ax.text(0.5, 0.02, label, ha="center", va="center",
                fontsize=11, color=COLORS["gray600"], transform=ax.transAxes)

    ax.set_xlim(0, 1)
    ax.set_ylim(-0.1, 0.5)
    ax.axis("off")
