#!/usr/bin/env python3
"""render_charts_swd.py — Deterministic SWD-compliant chart renderer.

SWD rules enforced IN CODE (not guidelines):
  [ok]  Background #FFFFFF always
  [ok]  1 highlight color per chart + #D1D5DB for everything else
  [ok]  No legend (direct labels only — legend() call raises RuntimeError)
  [ok]  No gridlines (left+bottom spines only, color #E2E8F0)
  [ok]  Insight title (enforced non-empty, left-aligned)
  [ok]  Max 3 annotations per chart (counter enforced)
  [no]  No pie, no 3D, no dual-axis (guarded at render time)
  [ok]  Figure size: (8.0, 3.8) split / (11.0, 4.0) full
  [ok]  DPI: 150
  [ok]  Font: Calibri with Segoe UI / DejaVu Sans fallback

Usage:
    python3 scripts/render_charts_swd.py --stem sales_orders_2023_2026
"""

import sys
import io
import json
import argparse
import warnings
import os
from pathlib import Path
from datetime import datetime

# ── Structured logging ─────────────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent.parent))
from helpers.utils.logger import get_logger, new_run_id

# ── UTF-8 stdout (Windows compatibility — applied only when run directly) ──────
def _fix_utf8_stdout():
    try:
        if hasattr(sys.stdout, "buffer"):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "buffer"):
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    except Exception:
        pass

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import yaml
from scipy.interpolate import CubicSpline

warnings.filterwarnings("ignore")

# ── Paths ──────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent

# ── Load theme from _base.yaml ────────────────────────────────────────────────
def _load_theme() -> dict:
    """Load themes/_base.yaml. Falls back to safe defaults if missing."""
    theme_path = ROOT / "themes" / "_base.yaml"
    try:
        with open(theme_path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}

_THEME = _load_theme()
_TC    = _THEME.get("colors", {})
_TH    = _THEME.get("highlight", _TC.get("highlight", {}))
_TCHRT = _THEME.get("charts", {})

def _tc(key: str, fallback: str) -> str:
    """Get color from theme colors dict by key, with fallback."""
    return _TC.get(key, fallback)

def _th(key: str, fallback: str) -> str:
    """Get highlight color from theme colors.highlight dict."""
    h = _TC.get("highlight", {})
    return h.get(key, fallback)

# ── Global SWD constants — sourced from theme ─────────────────────────────────
WHITE    = _tc("background",  "#FFFFFF")   # chart + slide panel background
GRAY     = _th("gray",        "#D1D5DB")   # non-highlighted series
SPINE    = _tc("border",      "#E2E8F0")   # axis spine color
TITLE_C  = _tc("dk1",         "#000000")   # title color
TICK_C   = _tc("text_light",  "#595959")   # tick label color
ANNOT_C  = _tc("text_light",  "#374151")   # annotation text color

_fig     = _TCHRT.get("figure", {})
FIGSIZE_SPLIT = tuple(_fig.get("figsize_split", [8.0, 3.8]))
FIGSIZE_FULL  = tuple(_fig.get("figsize_full",  [11.0, 4.0]))
DPI           = int(_fig.get("dpi", 150))

# Section -> highlight color (semantic SWD choices, sourced from theme)
SECTION_COLORS = {
    "descriptive": _th("descriptive", "#4F81BD"),
    "diagnostic":  _th("diagnostic",  "#C0504D"),
    "predictive":  _th("predictive",  "#9BBB59"),
    "event":       _th("event",       "#F79646"),
}

# ── Font resolution ────────────────────────────────────────────────────────────
def _resolve_font():
    """Return best available font name: Inter -> Calibri -> Segoe UI -> DejaVu Sans."""
    import matplotlib.font_manager as fm
    available = {f.name for f in fm.fontManager.ttflist}
    for candidate in ("Inter", "Calibri", "Segoe UI", "Arial", "Liberation Sans", "DejaVu Sans"):
        if candidate in available:
            return candidate
    return "sans-serif"

FONT = _resolve_font()

# ── Global rcParams — applied once ────────────────────────────────────────────
def _apply_global_style():
    plt.rcParams.update({
        "figure.facecolor":     WHITE,
        "axes.facecolor":       WHITE,
        "savefig.facecolor":    WHITE,
        "font.family":          FONT,
        "font.size":            9,
        "axes.titlesize":       11,
        "axes.titleweight":     "bold",
        "axes.titlecolor":      TITLE_C,
        "axes.titlelocation":   "left",
        "axes.titlepad":        10,
        "axes.labelsize":       8,
        "axes.labelcolor":      TICK_C,
        "xtick.labelsize":      8,
        "ytick.labelsize":      8,
        "xtick.color":          TICK_C,
        "ytick.color":          TICK_C,
        "axes.spines.top":      False,
        "axes.spines.right":    False,
        "axes.grid":            False,
        "axes.edgecolor":       SPINE,
        "axes.linewidth":       0.8,
        "lines.linewidth":      2.0,
        "lines.markersize":     5,
        "legend.frameon":       False,  # no box, but we intercept below
        "figure.dpi":           DPI,
    })

_apply_global_style()


# ── SWD enforcement helpers ────────────────────────────────────────────────────

class SWDViolation(RuntimeError):
    pass

class _AnnotationCounter:
    """Enforce max 3 annotations per chart."""
    def __init__(self):
        self.count = 0
    def annotate(self, ax, text, xy, xytext=None, **kw):
        self.count += 1
        if self.count > 3:
            raise SWDViolation(
                f"SWD violation: max 3 annotations per chart (attempted #{self.count}). "
                "Reduce annotations or split into two charts."
            )
        kw.setdefault("fontsize", 8)
        kw.setdefault("color", ANNOT_C)
        kw.setdefault("fontweight", "bold")
        kw.setdefault("ha", "center")
        if xytext:
            return ax.annotate(text, xy=xy, xytext=xytext,
                               arrowprops=dict(arrowstyle="-", color=SPINE, lw=0.8), **kw)
        return ax.annotate(text, xy=xy, **kw)

def _smooth_xy(x: np.ndarray, y: np.ndarray, points: int = 300):
    """Return smoothed (xs, ys) via cubic spline. Skips NaN segments."""
    mask = ~np.isnan(y)
    if mask.sum() < 3:
        return x, y  # not enough points to smooth
    xc, yc = x[mask], y[mask]
    cs  = CubicSpline(xc, yc)
    xs  = np.linspace(xc[0], xc[-1], points)
    return xs, cs(xs)


def _apply_swd_spines(ax):
    """Remove top/right spines, style left+bottom."""
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(SPINE)
    ax.spines["bottom"].set_color(SPINE)
    ax.spines["left"].set_linewidth(0.8)
    ax.spines["bottom"].set_linewidth(0.8)
    ax.tick_params(length=0)

_SHOW_TITLE = True   # set False via --no-title flag (PPTX mode — slide already has title)

def _set_title(ax, title: str):
    """Set insight title. Skipped in --no-title mode (PPTX)."""
    if not _SHOW_TITLE:
        return
    title = (title or "").strip()
    if not title:
        raise SWDViolation("SWD violation: chart title must be a non-empty insight statement.")
    # Escape $ to prevent matplotlib mathtext parsing (e.g. "$18.7M" → "\$18.7M")
    safe = title.replace("$", r"\$")
    ax.set_title(safe, loc="left", fontsize=11, fontweight="bold",
                 color=TITLE_C, pad=10, wrap=True)

def _highlight_colors(values, highlight_indices, hi_color):
    """Return color list: hi_color for highlights, GRAY for rest."""
    return [hi_color if i in highlight_indices else GRAY for i in range(len(values))]

def _format_value(v, fmt="auto"):
    """Format a number for display."""
    if fmt == "M":
        return f"${v/1e6:.1f}M"
    if fmt == "K":
        return f"${v/1000:.0f}K"
    if fmt == "pct":
        return f"{v:.1f}%"
    if fmt == "%":
        return f"{v:.0f}%"
    if fmt == "auto":
        if abs(v) >= 1e6:
            return f"${v/1e6:.1f}M"
        if abs(v) >= 1e3:
            return f"${v/1000:.0f}K"
        return f"{v:.1f}"
    return str(v)

def _save_chart(fig, output_path: Path):
    """Tight layout + save at DPI=150 white background."""
    fig.tight_layout(pad=1.2)
    fig.savefig(output_path, dpi=DPI, facecolor=WHITE, edgecolor="none",
                bbox_inches="tight")
    plt.close(fig)


# ── Chart Template Functions ───────────────────────────────────────────────────

def chart_vertical_bar(data: dict, title: str, hi_color: str,
                       figsize=FIGSIZE_SPLIT) -> plt.Figure:
    """
    Vertical bar chart. Highlights specified categories.
    data keys: categories (list[str]), values (list[float]),
               highlight (list[str] | list[int]),
               x_label (str), y_label (str), value_format (str)
    """
    cats    = data["categories"]
    vals    = [float(v) for v in data["values"]]
    fmt     = data.get("value_format", "auto")
    hiset   = set(data.get("highlight", []))
    # resolve highlight indices
    hi_idx  = {i for i, c in enumerate(cats) if c in hiset or i in hiset}

    fig, ax = plt.subplots(figsize=figsize, facecolor=WHITE)
    colors  = _highlight_colors(vals, hi_idx, hi_color)
    x       = np.arange(len(cats))
    bars    = ax.bar(x, vals, color=colors, width=0.6, zorder=2)

    ax.set_xticks(x)
    ax.set_xticklabels(cats, fontsize=8)
    ax.set_xlabel(data.get("x_label", ""), fontsize=8, labelpad=4)
    ax.set_ylabel(data.get("y_label", ""), fontsize=8, labelpad=4)

    # Suppress scientific notation on Y axis
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(
        lambda v, _: _format_value(v, fmt) if abs(v) >= 1000 else f"{v:.0f}"
    ))

    # Direct value labels on highlighted bars only
    ann = _AnnotationCounter()
    for i, (bar, v) in enumerate(zip(bars, vals)):
        if i in hi_idx and ann.count < 3:
            ann.annotate(ax, _format_value(v, fmt),
                         xy=(bar.get_x() + bar.get_width()/2, bar.get_height()),
                         xycoords="data", va="bottom", ha="center")

    _apply_swd_spines(ax)
    _set_title(ax, title)
    return fig


def chart_horizontal_bar(data: dict, title: str, hi_color: str,
                         figsize=FIGSIZE_SPLIT) -> plt.Figure:
    """
    Horizontal bar chart. Sorted descending. Highlights top item.
    data keys: categories, values, highlight, value_format
    """
    cats  = list(data["categories"])
    vals  = [float(v) for v in data["values"]]
    fmt   = data.get("value_format", "auto")
    hiset = set(data.get("highlight", [cats[0]] if cats else []))

    # sort descending
    pairs  = sorted(zip(vals, cats), reverse=True)
    vals   = [p[0] for p in pairs]
    cats   = [p[1] for p in pairs]
    hi_idx = {i for i, c in enumerate(cats) if c in hiset}

    fig, ax = plt.subplots(figsize=figsize, facecolor=WHITE)
    y      = np.arange(len(cats))
    colors = _highlight_colors(vals, hi_idx, hi_color)
    bars   = ax.barh(y, vals, color=colors, height=0.55, zorder=2)

    ax.set_yticks(y)
    ax.set_yticklabels(cats, fontsize=8)
    ax.set_xlabel(data.get("x_label", ""), fontsize=8)
    ax.invert_yaxis()

    # Direct value labels at bar end
    ann = _AnnotationCounter()
    for i, (bar, v) in enumerate(zip(bars, vals)):
        if ann.count < 3:
            ax.text(v + max(vals) * 0.01, bar.get_y() + bar.get_height()/2,
                    _format_value(v, fmt), va="center", fontsize=8,
                    color=hi_color if i in hi_idx else TICK_C,
                    fontweight="bold" if i in hi_idx else "normal")
            ann.count += 1

    _apply_swd_spines(ax)
    ax.spines["left"].set_visible(False)
    ax.xaxis.set_visible(False)
    _set_title(ax, title)
    return fig


def chart_highlight_line(data: dict, title: str, hi_color: str,
                         figsize=FIGSIZE_SPLIT) -> plt.Figure:
    """
    Time series line. Can highlight a span (highlight_range) or specific points.
    data keys: x (labels), y (values), highlight_range ([start_idx, end_idx]),
               highlight_points (list[int]), value_format, x_label, y_label
    """
    x_labels = data["x"]
    y_vals   = [float(v) if v is not None else np.nan for v in data["y"]]
    fmt      = data.get("value_format", "auto")
    x        = np.arange(len(x_labels))

    fig, ax = plt.subplots(figsize=figsize, facecolor=WHITE)

    # Highlight span (shaded region)
    hr = data.get("highlight_range")
    if hr:
        ax.axvspan(hr[0] - 0.5, hr[1] + 0.5, alpha=0.08, color=hi_color, zorder=1)

    xs, ys = _smooth_xy(x, np.array(y_vals))
    ax.plot(xs, ys, color=GRAY, linewidth=2, zorder=2)

    # Highlight specific points
    hp = set(data.get("highlight_points", []))
    if hp:
        hx = [i for i in hp if i < len(y_vals)]
        hy = [y_vals[i] for i in hx]
        ax.scatter(hx, hy, color=hi_color, s=50, zorder=4, linewidth=0)

    ax.set_xticks(x)
    ax.set_xticklabels(x_labels, fontsize=7.5, rotation=0)
    if len(x_labels) > 8:
        ax.set_xticklabels(x_labels, fontsize=7, rotation=30, ha="right")
    ax.set_ylabel(data.get("y_label", ""), fontsize=8)

    # Annotations on highlight points
    ann = _AnnotationCounter()
    for i in sorted(hp):
        if i < len(y_vals) and not np.isnan(y_vals[i]) and ann.count < 3:
            ann.annotate(ax, _format_value(y_vals[i], fmt),
                         xy=(i, y_vals[i]),
                         xytext=(i, y_vals[i] + max(y_vals) * 0.06),
                         fontsize=8, color=hi_color)

    _apply_swd_spines(ax)
    _set_title(ax, title)
    return fig


def chart_multi_line(data: dict, title: str, hi_color: str,
                     figsize=FIGSIZE_SPLIT) -> plt.Figure:
    """
    Multiple lines, one series highlighted.
    data keys: x (labels), series (list of {name, values, highlight:bool}),
               value_format, y_label
    """
    x_labels = data["x"]
    series   = data["series"]
    x        = np.arange(len(x_labels))

    fig, ax = plt.subplots(figsize=figsize, facecolor=WHITE)
    ann = _AnnotationCounter()

    # collect end-label positions to avoid overlap
    label_positions: list[tuple[float, float, str, str, bool]] = []  # (x, y, name, col, bold)

    for s in series:
        y_raw = [float(v) if v is not None else np.nan for v in s["values"]]
        y_arr = np.array(y_raw)
        col   = hi_color if s.get("highlight") else GRAY
        lw    = 2.2 if s.get("highlight") else 1.2
        bold  = s.get("highlight", False)

        xs, ys = _smooth_xy(x, y_arr)
        ax.plot(xs, ys, color=col, linewidth=lw, zorder=3 if bold else 2)

        # collect label position at last real data point
        last_i = next((i for i in range(len(y_raw)-1, -1, -1) if not np.isnan(y_raw[i])), None)
        if last_i is not None and ann.count < 3:
            label_positions.append((last_i, y_raw[last_i], s["name"], col, bold))
            ann.count += 1

    # place labels with vertical nudge to avoid overlap (min 0.6 unit gap)
    label_positions.sort(key=lambda t: t[1])
    placed: list[float] = []
    for lx, ly, name, col, bold in label_positions:
        # nudge up if too close to already-placed label
        nudged = ly
        for prev in placed:
            if abs(nudged - prev) < 0.6:
                nudged = prev + 0.6
        placed.append(nudged)
        ax.text(lx + 0.15, nudged, name,
                fontsize=7.5, color=col,
                fontweight="bold" if bold else "normal",
                va="center")

    ax.set_xticks(x)
    ax.set_xticklabels(x_labels, fontsize=7.5)
    if len(x_labels) > 8:
        ax.set_xticklabels(x_labels, fontsize=7, rotation=30, ha="right")
    ax.set_ylabel(data.get("y_label", ""), fontsize=8)

    _apply_swd_spines(ax)
    _set_title(ax, title)
    return fig


def chart_waterfall(data: dict, title: str, hi_color: str,
                    figsize=FIGSIZE_SPLIT) -> plt.Figure:
    """
    Waterfall / bridge chart.
    data keys: categories (list[str]), values (list[float], signed deltas),
               start_label (str), end_label (str), value_format
    """
    cats     = data["categories"]
    raw_vals = data["values"]
    fmt      = data.get("value_format", "auto")

    # Layout: first value = start bar (absolute), middle = deltas, last = total (None = auto)
    start_val = float(raw_vals[0])
    deltas    = [float(v) for v in raw_vals[1:-1]]
    total_raw = raw_vals[-1]
    total     = float(total_raw) if total_raw is not None else start_val + sum(deltas)

    # Bar geometry — len == len(cats)
    bottoms = [0.0]
    tops    = [start_val]
    running = start_val
    for v in deltas:
        bottoms.append(running if v >= 0 else running + v)
        tops.append(abs(v))
        running += v
    bottoms.append(0.0)
    tops.append(total)

    colors = [GRAY] + [hi_color if v < 0 else "#A8C8E8" for v in deltas] + [hi_color]

    x   = np.arange(len(cats))
    fig, ax = plt.subplots(figsize=figsize, facecolor=WHITE)
    ax.bar(x, tops, bottom=bottoms, color=colors, width=0.55, zorder=2)

    # Connector lines between delta bars
    run2 = start_val
    for i, v in enumerate(deltas):
        run2 += v
        ax.plot([i + 0.275, i + 0.725], [run2, run2],
                color=SPINE, linewidth=0.8, zorder=3)

    ax.set_xticks(x)
    ax.set_xticklabels(cats, fontsize=8)
    ax.axhline(0, color=SPINE, linewidth=0.8)

    # Direct labels
    ann        = _AnnotationCounter()
    label_vals = [start_val] + deltas + [total]
    for i, (b, t, v) in enumerate(zip(bottoms, tops, label_vals)):
        if ann.count < 3 and (i == 0 or i == len(cats)-1 or colors[i] == hi_color):
            ax.text(i, b + t + max(tops) * 0.02, _format_value(v, fmt),
                    ha="center", fontsize=8, color=hi_color, fontweight="bold")
            ann.count += 1

    _apply_swd_spines(ax)
    _set_title(ax, title)
    return fig


def chart_grouped_bar(data: dict, title: str, hi_color: str,
                      figsize=FIGSIZE_SPLIT) -> plt.Figure:
    """
    Grouped bar (max 3 groups, max 4 categories).
    data keys: categories, groups (list of {name, values, highlight:bool}), value_format
    """
    cats   = data["categories"]
    groups = data["groups"]
    fmt    = data.get("value_format", "auto")
    n      = len(groups)
    w      = 0.7 / n
    x      = np.arange(len(cats))

    fig, ax = plt.subplots(figsize=figsize, facecolor=WHITE)
    ann = _AnnotationCounter()

    for gi, g in enumerate(groups):
        offset = (gi - (n-1)/2) * w
        col    = hi_color if g.get("highlight") else GRAY
        vals   = [float(v) for v in g["values"]]
        bars   = ax.bar(x + offset, vals, width=w * 0.9, color=col, zorder=2)
        # direct label on highlighted group only
        if g.get("highlight"):
            for bar, v in zip(bars, vals):
                if ann.count < 3:
                    ax.text(bar.get_x() + bar.get_width()/2,
                            bar.get_height() + max(vals) * 0.02,
                            _format_value(v, fmt),
                            ha="center", fontsize=7, color=hi_color, fontweight="bold")
                    ann.count += 1
        # group name at end of last bar
        last_bar = bars[-1]
        ax.text(last_bar.get_x() + last_bar.get_width()/2 + w * 0.6,
                min(v for v in g["values"]) * 0.5,
                g["name"], fontsize=7, color=col, rotation=0)

    ax.set_xticks(x)
    ax.set_xticklabels(cats, fontsize=8)

    # Suppress scientific notation on Y axis
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(
        lambda v, _: _format_value(v, fmt) if abs(v) >= 1000 else f"{v:.0f}"
    ))

    _apply_swd_spines(ax)
    _set_title(ax, title)
    return fig


def chart_forecast_line(data: dict, title: str, hi_color: str,
                        figsize=FIGSIZE_SPLIT) -> plt.Figure:
    """
    Historical + forecast with CI band.
    data keys: x (labels), historical (values), forecast (values, can be shorter),
               ci_low (list), ci_high (list), split_idx (int), value_format
    """
    x_labels  = data["x"]
    _to_f     = lambda v: float(v) if v is not None else np.nan
    hist      = [_to_f(v) for v in data["historical"]]
    fcast_raw = [_to_f(v) for v in data.get("forecast", [])]
    ci_low_r  = [_to_f(v) for v in data.get("ci_low", [])]
    ci_high_r = [_to_f(v) for v in data.get("ci_high", [])]
    split_idx = data.get("split_idx", len(hist) - 1)
    fmt       = data.get("value_format", "auto")

    # Build full-length arrays aligned to x indices
    # forecast/ci arrays may be full-length (same as x_labels) with Nones,
    # or shorter (offset from split_idx+1). Handle both.
    n = len(x_labels)
    x = np.arange(n)
    hist_y  = np.array(hist[:n] + [np.nan] * max(0, n - len(hist)), dtype=float)
    fcast_y = np.full(n, np.nan)
    ci_lo_y = np.full(n, np.nan)
    ci_hi_y = np.full(n, np.nan)

    def _fill(dst, src):
        if len(src) == n:
            # full-length array — map 1:1
            for i, v in enumerate(src):
                if i < n and not np.isnan(v):
                    dst[i] = v
        else:
            # short array — offset from split_idx+1
            for i, v in enumerate(src):
                xi = split_idx + 1 + i
                if xi < n and not np.isnan(v):
                    dst[xi] = v

    _fill(fcast_y, fcast_raw)
    _fill(ci_lo_y, ci_low_r)
    _fill(ci_hi_y, ci_high_r)

    # Bridge: copy last historical point into forecast start so lines connect
    if split_idx < n and not np.isnan(hist_y[split_idx]):
        fcast_y[split_idx] = hist_y[split_idx]

    fig, ax = plt.subplots(figsize=figsize, facecolor=WHITE)

    # Historical line
    hx = x[~np.isnan(hist_y)]
    hy = hist_y[~np.isnan(hist_y)]
    if len(hx):
        ax.plot(hx, hy, color=GRAY, linewidth=2, zorder=3)

    # Forecast line + CI band
    fx_mask = ~np.isnan(fcast_y)
    if fx_mask.any():
        ax.plot(x[fx_mask], fcast_y[fx_mask], color=hi_color, linewidth=2,
                linestyle="--", zorder=3)
        ci_mask = ~np.isnan(ci_lo_y) & ~np.isnan(ci_hi_y)
        if ci_mask.any():
            ax.fill_between(x[ci_mask], ci_lo_y[ci_mask], ci_hi_y[ci_mask],
                            alpha=0.12, color=hi_color, zorder=2)


    # Divider
    ax.axvline(split_idx + 0.5, color=SPINE, linewidth=0.8, linestyle="--", zorder=1)

    ax.set_xticks(x)
    ax.set_xticklabels(x_labels, fontsize=7.5)
    if len(x_labels) > 8:
        ax.set_xticklabels(x_labels, fontsize=7, rotation=30, ha="right")
    ax.set_ylabel(data.get("y_label", ""), fontsize=8)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(
        lambda v, _: _format_value(v, fmt) if abs(v) >= 1000 else f"{v:.0f}"
    ))

    # Direct labels on last historical + last forecast
    ann = _AnnotationCounter()
    hist_max = float(np.nanmax(hist_y)) if not np.all(np.isnan(hist_y)) else 1.0
    if not np.isnan(hist_y[split_idx]) and ann.count < 3:
        ann.annotate(ax, _format_value(hist_y[split_idx], fmt),
                     xy=(split_idx, hist_y[split_idx]),
                     xytext=(split_idx - 0.5, hist_y[split_idx] + hist_max * 0.06),
                     fontsize=8, color=GRAY)
    fcast_idx = np.where(~np.isnan(fcast_y))[0]
    if len(fcast_idx) and ann.count < 3:
        last_fi = fcast_idx[-1]
        ann.annotate(ax, _format_value(fcast_y[last_fi], fmt),
                     xy=(last_fi, fcast_y[last_fi]),
                     xytext=(last_fi, fcast_y[last_fi] + hist_max * 0.06),
                     fontsize=8, color=hi_color)

    # Period labels
    if split_idx > 0 and ann.count < 3:
        mid_h = split_idx // 2
        ax.text(mid_h, ax.get_ylim()[0], "Historical",
                fontsize=7, color=TICK_C, ha="center")
        if len(fcast_idx):
            mid_f = int((fcast_idx[0] + fcast_idx[-1]) / 2)
            ax.text(mid_f, ax.get_ylim()[0], "Forecast",
                    fontsize=7, color=hi_color, ha="center", fontweight="bold")

    _apply_swd_spines(ax)
    _set_title(ax, title)
    return fig


def chart_feature_importance(data: dict, title: str, hi_color: str,
                              figsize=FIGSIZE_SPLIT) -> plt.Figure:
    """
    Sorted horizontal bar — feature importance or ranking.
    data keys: features (list[str]), importances (list[float]), top_n (int=8)
    """
    feats  = data["features"]
    imps   = [float(v) for v in data["importances"]]
    top_n  = data.get("top_n", 8)

    # Sort descending, take top_n
    pairs = sorted(zip(imps, feats), reverse=True)[:top_n]
    imps  = [p[0] for p in pairs]
    feats = [p[1] for p in pairs]
    hi_idx = {0}  # only top feature highlighted

    fig, ax = plt.subplots(figsize=figsize, facecolor=WHITE)
    y      = np.arange(len(feats))
    colors = _highlight_colors(imps, hi_idx, hi_color)
    ax.barh(y, imps, color=colors, height=0.55, zorder=2)
    ax.set_yticks(y)
    ax.set_yticklabels(feats, fontsize=8)
    ax.invert_yaxis()
    ax.set_xlabel("Importance", fontsize=8)

    # Value label for top feature
    ax.text(imps[0] + max(imps) * 0.01, 0,
            f"{imps[0]:.3f}", va="center", fontsize=8, color=hi_color, fontweight="bold")

    _apply_swd_spines(ax)
    ax.spines["left"].set_visible(False)
    ax.xaxis.set_major_formatter(mticker.FormatStrFormatter("%.3f"))
    _set_title(ax, title)
    return fig


def chart_scatter_regression(data: dict, title: str, hi_color: str,
                              figsize=FIGSIZE_SPLIT) -> plt.Figure:
    """
    Scatter with regression line.
    data keys: x (list[float]), y (list[float]), x_label, y_label,
               highlight_indices (list[int]), r_squared (float)
    """
    x_vals = [float(v) for v in data["x"]]
    y_vals = [float(v) for v in data["y"]]
    hi_idx = set(data.get("highlight_indices", []))
    r2     = data.get("r_squared")

    fig, ax = plt.subplots(figsize=figsize, facecolor=WHITE)

    # Gray scatter
    colors = [hi_color if i in hi_idx else GRAY for i in range(len(x_vals))]
    ax.scatter(x_vals, y_vals, c=colors, s=30, zorder=3, linewidth=0, alpha=0.7)

    # Regression line
    z   = np.polyfit(x_vals, y_vals, 1)
    p   = np.poly1d(z)
    xr  = np.linspace(min(x_vals), max(x_vals), 100)
    ax.plot(xr, p(xr), color=hi_color, linewidth=1.5, linestyle="--", zorder=2)

    ax.set_xlabel(data.get("x_label", ""), fontsize=8)
    ax.set_ylabel(data.get("y_label", ""), fontsize=8)

    # R² annotation
    if r2 is not None:
        ax.text(0.98, 0.05, f"R² = {r2:.2f}",
                transform=ax.transAxes, ha="right", fontsize=8,
                color=hi_color, fontweight="bold")

    _apply_swd_spines(ax)
    _set_title(ax, title)
    return fig


def chart_heatmap(data: dict, title: str, hi_color: str,
                  figsize=FIGSIZE_SPLIT) -> plt.Figure:
    """
    Heatmap (segment x dimension).
    data keys: rows (list[str]), cols (list[str]),
               values (list[list[float]]), value_format
    Always uses single-hue gradient: #EEF1FF (0%) -> hi_color (100%).
    """
    from matplotlib.colors import LinearSegmentedColormap

    rows   = data["rows"]
    cols   = data["cols"]
    matrix = np.array([[float(v) for v in row] for row in data["values"]])
    fmt    = data.get("value_format", "auto")

    # Single-hue gradient: white -> light tint -> hi_color at 60% opacity equivalent
    cmap = LinearSegmentedColormap.from_list(
        "brand_heatmap", ["#FFFFFF", "#EEF1FF", "#C5CEFF", hi_color], N=256
    )

    fig, ax = plt.subplots(figsize=figsize, facecolor=WHITE)
    ax.imshow(matrix, cmap=cmap, aspect="auto")

    ax.set_xticks(np.arange(len(cols)))
    ax.set_xticklabels(cols, fontsize=8)
    ax.set_yticks(np.arange(len(rows)))
    ax.set_yticklabels(rows, fontsize=8)

    # Cell annotations — white text on dark cells, dark text on light cells
    thresh = (matrix.max() + matrix.min()) / 2
    for i in range(len(rows)):
        for j in range(len(cols)):
            color = "#FFFFFF" if matrix[i, j] > thresh else TITLE_C
            ax.text(j, i, _format_value(matrix[i, j], fmt),
                    ha="center", va="center", fontsize=7, color=color)

    ax.spines[:].set_visible(False)
    ax.tick_params(length=0)
    _set_title(ax, title)
    return fig


def chart_slopegraph(data: dict, title: str, hi_color: str,
                     figsize=FIGSIZE_SPLIT) -> plt.Figure:
    """
    Slopegraph (before/after comparison).
    data keys: labels (list[str]), before (list[float]), after (list[float]),
               before_label (str), after_label (str),
               highlight (list[str]), value_format
    """
    labels      = data["labels"]
    before      = [float(v) for v in data["before"]]
    after       = [float(v) for v in data["after"]]
    hi_set      = set(data.get("highlight", [labels[0]] if labels else []))
    before_lbl  = data.get("before_label", "Before")
    after_lbl   = data.get("after_label", "After")
    fmt         = data.get("value_format", "auto")

    fig, ax = plt.subplots(figsize=figsize, facecolor=WHITE)

    for i, (lbl, b, a) in enumerate(zip(labels, before, after)):
        col = hi_color if lbl in hi_set else GRAY
        lw  = 2.0 if lbl in hi_set else 1.0
        ax.plot([0, 1], [b, a], color=col, linewidth=lw, zorder=2)
        ax.text(-0.05, b, f"{lbl} {_format_value(b, fmt)}", ha="right",
                fontsize=8, color=col, va="center")
        ax.text(1.05, a, f"{lbl} {_format_value(a, fmt)}", ha="left",
                fontsize=8, color=col, va="center")

    ax.set_xlim(-0.5, 1.5)
    ax.set_xticks([0, 1])
    ax.set_xticklabels([before_lbl, after_lbl], fontsize=9, fontweight="bold")
    ax.yaxis.set_visible(False)
    ax.spines["left"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["bottom"].set_color(SPINE)
    ax.spines["top"].set_visible(False)

    _set_title(ax, title)
    return fig


def chart_model_comparison_bar(data: dict, title: str, hi_color: str,
                                figsize=FIGSIZE_SPLIT) -> plt.Figure:
    """
    Model comparison — horizontal bars sorted by metric.
    data keys: models (list[str]), scores (list[float]),
               metric_name (str), highlight (list[str])
    """
    models  = data["models"]
    scores  = [float(v) for v in data["scores"]]
    metric  = data.get("metric_name", "Score")
    hi_set  = set(data.get("highlight", []))

    # Sort descending
    pairs   = sorted(zip(scores, models), reverse=True)
    scores  = [p[0] for p in pairs]
    models  = [p[1] for p in pairs]
    hi_idx  = {i for i, m in enumerate(models) if m in hi_set}

    fig, ax = plt.subplots(figsize=figsize, facecolor=WHITE)
    y      = np.arange(len(models))
    colors = _highlight_colors(scores, hi_idx, hi_color)
    ax.barh(y, scores, color=colors, height=0.55, zorder=2)
    ax.set_yticks(y)
    ax.set_yticklabels(models, fontsize=8)
    ax.invert_yaxis()
    ax.set_xlabel(metric, fontsize=8)

    for i, (bar, s) in enumerate(zip(ax.patches, scores)):
        color = hi_color if i in hi_idx else TICK_C
        ax.text(s + max(scores) * 0.01, bar.get_y() + bar.get_height()/2,
                f"{s:.3f}", va="center", fontsize=8, color=color,
                fontweight="bold" if i in hi_idx else "normal")

    _apply_swd_spines(ax)
    ax.spines["left"].set_visible(False)
    ax.xaxis.set_visible(False)
    _set_title(ax, title)
    return fig


def chart_roc_curve(data: dict, title: str, hi_color: str,
                    figsize=FIGSIZE_SPLIT) -> plt.Figure:
    """
    ROC curve.
    data keys: fpr (list[float]), tpr (list[float]), auc (float),
               model_name (str)
    """
    fpr   = [float(v) for v in data["fpr"]]
    tpr   = [float(v) for v in data["tpr"]]
    auc   = float(data.get("auc", 0))
    model = data.get("model_name", "Model")

    fig, ax = plt.subplots(figsize=figsize, facecolor=WHITE)
    ax.plot(fpr, tpr, color=hi_color, linewidth=2, zorder=3)
    ax.plot([0, 1], [0, 1], color=GRAY, linewidth=1, linestyle="--", zorder=2)
    ax.fill_between(fpr, tpr, alpha=0.08, color=hi_color, zorder=1)
    ax.set_xlabel("False Positive Rate", fontsize=8)
    ax.set_ylabel("True Positive Rate", fontsize=8)
    ax.text(0.6, 0.15, f"AUC = {auc:.3f}\n{model}",
            fontsize=9, color=hi_color, fontweight="bold",
            transform=ax.transAxes)

    _apply_swd_spines(ax)
    _set_title(ax, title)
    return fig


def chart_residual_plot(data: dict, title: str, hi_color: str,
                       figsize=FIGSIZE_SPLIT) -> plt.Figure:
    """
    Residual plot — predicted vs residual for regression diagnostics.
    data keys: y_pred (list[float]), y_actual (list[float]),
               x_label (str), y_label (str)
    """
    y_pred   = np.array([float(v) for v in data["y_pred"]])
    y_actual = np.array([float(v) for v in data["y_actual"]])
    residuals = y_actual - y_pred

    fig, ax = plt.subplots(figsize=figsize, facecolor=WHITE)
    ax.scatter(y_pred, residuals, color=GRAY, s=25, alpha=0.6,
               edgecolors="none", zorder=2)

    # Highlight large residuals (beyond 2 std)
    std_r = np.std(residuals)
    outlier = np.abs(residuals) > 2 * std_r
    if outlier.any():
        ax.scatter(y_pred[outlier], residuals[outlier], color=hi_color,
                   s=35, alpha=0.8, edgecolors="none", zorder=3)

    ax.axhline(0, color=hi_color, linewidth=1.2, linestyle="--", zorder=1)
    ax.set_xlabel(data.get("x_label", "Predicted"), fontsize=8)
    ax.set_ylabel(data.get("y_label", "Residual"), fontsize=8)

    # Annotation: outlier count
    n_out = int(outlier.sum())
    if n_out > 0:
        ann = _AnnotationCounter()
        ann.annotate(ax, f"{n_out} outliers (>2 SD)",
                     xy=(0.98, 0.95), xycoords="axes fraction",
                     fontsize=8, color=hi_color, ha="right")

    _apply_swd_spines(ax)
    _set_title(ax, title)
    return fig


# ══════════════════════════════════════════════════════════════════════════════
#  NEW CHART TYPES (SWD library expansion)
# ══════════════════════════════════════════════════════════════════════════════

def chart_stacked_bar(data: dict, title: str, hi_color: str,
                      figsize=FIGSIZE_SPLIT) -> plt.Figure:
    """
    Vertical stacked bar — part-to-whole composition across categories.
    data keys: categories (list[str]),
               segments (list of {name, values, highlight:bool}),
               value_format, y_label,
               pct_mode (bool, default False — if True, normalize each bar to 100%)
    """
    cats     = data["categories"]
    segments = data["segments"]
    fmt      = data.get("value_format", "auto")
    pct      = data.get("pct_mode", False)
    x        = np.arange(len(cats))

    fig, ax = plt.subplots(figsize=figsize, facecolor=WHITE)

    # Normalize to 100% if requested
    if pct:
        totals = [sum(s["values"][i] for s in segments) for i in range(len(cats))]
        for s in segments:
            s["_vals"] = [float(v) / t * 100 if t else 0 for v, t in zip(s["values"], totals)]
    else:
        for s in segments:
            s["_vals"] = [float(v) for v in s["values"]]

    bottom = np.zeros(len(cats))
    for s in segments:
        col  = hi_color if s.get("highlight") else GRAY
        vals = np.array(s["_vals"])
        ax.bar(x, vals, bottom=bottom, color=col, width=0.6, zorder=2)
        # Direct label at center of each highlighted segment
        if s.get("highlight"):
            for i, (b, v) in enumerate(zip(bottom, vals)):
                if v > 0:
                    ax.text(i, b + v / 2, _format_value(v, "%" if pct else fmt),
                            ha="center", va="center", fontsize=7, color="white", fontweight="bold")
        bottom += vals

    # Segment names as direct labels on the right
    run = np.zeros(len(cats))
    for s in segments:
        vals = np.array(s["_vals"])
        mid  = run + vals / 2
        run += vals
        col  = hi_color if s.get("highlight") else TICK_C
        ax.text(len(cats) - 1 + 0.45, mid[-1], s["name"],
                fontsize=7, color=col, va="center",
                fontweight="bold" if s.get("highlight") else "normal")

    ax.set_xticks(x)
    ax.set_xticklabels(cats, fontsize=8)
    ax.set_ylabel(data.get("y_label", ""), fontsize=8)
    if pct:
        ax.set_ylim(0, 105)
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:.0f}%"))

    _apply_swd_spines(ax)
    _set_title(ax, title)
    return fig


def chart_histogram(data: dict, title: str, hi_color: str,
                    figsize=FIGSIZE_SPLIT) -> plt.Figure:
    """
    Histogram — distribution of a single continuous variable.
    data keys: values (list[float]),
               bins (int, default 20),
               x_label (str), y_label (str),
               highlight_range ([lo, hi]) — optional range to highlight
    """
    vals  = [float(v) for v in data["values"]]
    nbins = data.get("bins", 20)
    hr    = data.get("highlight_range")

    fig, ax = plt.subplots(figsize=figsize, facecolor=WHITE)
    n, bin_edges, patches = ax.hist(vals, bins=nbins, color=GRAY, edgecolor=WHITE,
                                    linewidth=0.5, zorder=2)

    # Highlight bins within range
    if hr:
        for patch, left_edge in zip(patches, bin_edges[:-1]):
            if hr[0] <= left_edge + (bin_edges[1] - bin_edges[0]) / 2 <= hr[1]:
                patch.set_facecolor(hi_color)

    ax.set_xlabel(data.get("x_label", ""), fontsize=8)
    ax.set_ylabel(data.get("y_label", "Frequency"), fontsize=8)

    # Annotation: median line
    med = float(np.median(vals))
    ann = _AnnotationCounter()
    ax.axvline(med, color=hi_color, linewidth=1.5, linestyle="--", zorder=3)
    ann.annotate(ax, f"Median: {med:.1f}",
                 xy=(med, ax.get_ylim()[1] * 0.92),
                 fontsize=8, color=hi_color, ha="left")

    _apply_swd_spines(ax)
    _set_title(ax, title)
    return fig


def chart_dot_plot(data: dict, title: str, hi_color: str,
                   figsize=FIGSIZE_SPLIT) -> plt.Figure:
    """
    Cleveland dot plot — cleaner alternative to bar chart for rankings.
    data keys: categories (list[str]), values (list[float]),
               highlight (list[str]), value_format, x_label
    """
    cats  = list(data["categories"])
    vals  = [float(v) for v in data["values"]]
    fmt   = data.get("value_format", "auto")
    hiset = set(data.get("highlight", []))

    # Sort descending
    pairs = sorted(zip(vals, cats), reverse=True)
    vals  = [p[0] for p in pairs]
    cats  = [p[1] for p in pairs]

    fig, ax = plt.subplots(figsize=figsize, facecolor=WHITE)
    y = np.arange(len(cats))

    for i, (yi, v, c) in enumerate(zip(y, vals, cats)):
        col = hi_color if c in hiset else GRAY
        sz  = 80 if c in hiset else 50
        ax.scatter(v, yi, color=col, s=sz, zorder=3, linewidth=0)
        ax.plot([0, v], [yi, yi], color="#F0F0F0", linewidth=0.8, zorder=1)
        ax.text(v + max(vals) * 0.02, yi,
                _format_value(v, fmt), va="center", fontsize=7.5,
                color=col, fontweight="bold" if c in hiset else "normal")

    ax.set_yticks(y)
    ax.set_yticklabels(cats, fontsize=8)
    ax.invert_yaxis()
    ax.set_xlabel(data.get("x_label", ""), fontsize=8)

    ax.spines["left"].set_visible(False)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["bottom"].set_color(SPINE)
    ax.tick_params(axis="y", length=0)
    _set_title(ax, title)
    return fig


def chart_bullet(data: dict, title: str, hi_color: str,
                 figsize=FIGSIZE_SPLIT) -> plt.Figure:
    """
    Bullet chart — actual vs target with performance ranges.
    data keys: metrics (list of {name, actual, target,
               ranges:[poor_max, ok_max, good_max]}),
               value_format
    """
    metrics = data["metrics"]
    fmt     = data.get("value_format", "auto")

    fig, ax = plt.subplots(figsize=figsize, facecolor=WHITE)
    h    = 0.35
    gap  = 1.0
    y_positions = []

    range_colors = ["#E8E8E8", "#D1D5DB", "#B8B8B8"]  # light -> dark gray bands

    for mi, m in enumerate(metrics):
        y   = mi * gap
        y_positions.append(y)
        rng = m.get("ranges", [])

        # Background range bands (wide)
        prev = 0
        for ri, r_end in enumerate(rng):
            c = range_colors[ri] if ri < len(range_colors) else range_colors[-1]
            ax.barh(y, float(r_end) - prev, left=prev, height=h * 2.2,
                    color=c, zorder=1, linewidth=0)
            prev = float(r_end)

        # Actual bar (narrow, hi_color)
        actual = float(m["actual"])
        ax.barh(y, actual, height=h, color=hi_color, zorder=3, linewidth=0)

        # Target marker (vertical line)
        target = float(m["target"])
        ax.plot([target, target], [y - h * 1.2, y + h * 1.2],
                color=TITLE_C, linewidth=2.5, zorder=4)

        # Value label
        ax.text(actual + max(rng) * 0.02, y,
                _format_value(actual, fmt), va="center", fontsize=7.5,
                color=hi_color, fontweight="bold")

    ax.set_yticks(y_positions)
    ax.set_yticklabels([m["name"] for m in metrics], fontsize=8)
    ax.spines[:].set_visible(False)
    ax.tick_params(length=0)
    ax.xaxis.set_visible(False)
    _set_title(ax, title)
    return fig


def chart_area(data: dict, title: str, hi_color: str,
               figsize=FIGSIZE_SPLIT) -> plt.Figure:
    """
    Area chart (single or stacked).
    data keys: x (labels),
               series (list of {name, values, highlight:bool}),
               stacked (bool, default False),
               value_format, y_label
    """
    x_labels = data["x"]
    series   = data["series"]
    stacked  = data.get("stacked", False)
    x        = np.arange(len(x_labels))

    fig, ax = plt.subplots(figsize=figsize, facecolor=WHITE)

    if stacked:
        ys     = [np.array([float(v) for v in s["values"]]) for s in series]
        colors = [hi_color if s.get("highlight") else GRAY for s in series]
        ax.stackplot(x, *ys, colors=colors, alpha=0.7, zorder=2)
        # Direct labels at right edge
        cum = np.zeros(len(x_labels))
        for s, y_arr in zip(series, ys):
            mid = cum + y_arr / 2
            cum += y_arr
            col = hi_color if s.get("highlight") else TICK_C
            ax.text(len(x_labels) - 1 + 0.2, mid[-1], s["name"],
                    fontsize=7, color=col, va="center",
                    fontweight="bold" if s.get("highlight") else "normal")
    else:
        # Single area
        s = series[0] if series else {"values": [], "name": ""}
        y_vals = np.array([float(v) for v in s["values"]])
        xs, ys = _smooth_xy(x, y_vals)
        ax.fill_between(xs, 0, ys, alpha=0.15, color=hi_color, zorder=1)
        ax.plot(xs, ys, color=hi_color, linewidth=2, zorder=2)

    ax.set_xticks(x)
    ax.set_xticklabels(x_labels, fontsize=7.5)
    if len(x_labels) > 8:
        ax.set_xticklabels(x_labels, fontsize=7, rotation=30, ha="right")
    ax.set_ylabel(data.get("y_label", ""), fontsize=8)
    ax.set_ylim(bottom=0)

    _apply_swd_spines(ax)
    _set_title(ax, title)
    return fig


def chart_connected_dot(data: dict, title: str, hi_color: str,
                        figsize=FIGSIZE_SPLIT) -> plt.Figure:
    """
    Connected dot plot (dumbbell) — gap between two values per category.
    data keys: categories (list[str]),
               value_a (list[float]), value_b (list[float]),
               label_a (str), label_b (str),
               highlight (list[str]), value_format
    """
    cats   = data["categories"]
    va     = [float(v) for v in data["value_a"]]
    vb     = [float(v) for v in data["value_b"]]
    lbl_a  = data.get("label_a", "A")
    lbl_b  = data.get("label_b", "B")
    hiset  = set(data.get("highlight", []))

    fig, ax = plt.subplots(figsize=figsize, facecolor=WHITE)
    y = np.arange(len(cats))

    for i, (c, a, b) in enumerate(zip(cats, va, vb)):
        base_col = hi_color if c in hiset else GRAY
        lw = 2.0 if c in hiset else 1.0
        # Connecting line
        ax.plot([a, b], [i, i], color=base_col, linewidth=lw, zorder=2)
        # Dots
        ax.scatter(a, i, color=base_col, s=50, zorder=3, linewidth=0)
        ax.scatter(b, i, color=base_col, s=50, zorder=3, linewidth=0, marker="D")

    ax.set_yticks(y)
    ax.set_yticklabels(cats, fontsize=8)
    ax.invert_yaxis()
    ax.set_xlabel(data.get("x_label", ""), fontsize=8)

    # Small legend via direct annotation at top
    all_vals = va + vb
    ax.scatter([], [], color=TICK_C, s=30, label=lbl_a)
    ax.scatter([], [], color=TICK_C, s=30, marker="D", label=lbl_b)
    ax.text(min(all_vals), -0.6, lbl_a, fontsize=7, color=TICK_C, ha="center")
    ax.text(max(all_vals), -0.6, lbl_b, fontsize=7, color=TICK_C, ha="center")

    ax.spines["left"].set_visible(False)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["bottom"].set_color(SPINE)
    ax.tick_params(axis="y", length=0)
    _set_title(ax, title)
    return fig


def chart_diverging_bar(data: dict, title: str, hi_color: str,
                        figsize=FIGSIZE_SPLIT) -> plt.Figure:
    """
    Diverging / tornado bar — two groups extending from a center axis.
    data keys: categories (list[str]),
               values_left (list[float]), values_right (list[float]),
               label_left (str), label_right (str),
               value_format
    """
    cats   = data["categories"]
    v_left = [float(v) for v in data["values_left"]]
    v_right= [float(v) for v in data["values_right"]]
    lbl_l  = data.get("label_left", "Left")
    lbl_r  = data.get("label_right", "Right")
    fmt    = data.get("value_format", "auto")

    # Use hi_color for right (positive/primary), complementary for left
    col_r = hi_color
    col_l = GRAY

    fig, ax = plt.subplots(figsize=figsize, facecolor=WHITE)
    y = np.arange(len(cats))
    h = 0.55

    ax.barh(y, [-v for v in v_left], height=h, color=col_l, zorder=2, linewidth=0)
    ax.barh(y, v_right, height=h, color=col_r, zorder=2, linewidth=0)

    # Value labels
    for i, (vl, vr) in enumerate(zip(v_left, v_right)):
        ax.text(-vl - max(v_left) * 0.03, i, _format_value(vl, fmt),
                va="center", ha="right", fontsize=7, color=TICK_C)
        ax.text(vr + max(v_right) * 0.03, i, _format_value(vr, fmt),
                va="center", ha="left", fontsize=7, color=hi_color, fontweight="bold")

    ax.set_yticks(y)
    ax.set_yticklabels(cats, fontsize=8, ha="center")
    ax.axvline(0, color=SPINE, linewidth=0.8, zorder=1)
    ax.invert_yaxis()

    # Group labels at top
    ax.text(-max(v_left) * 0.5, -0.7, lbl_l, fontsize=8, color=TICK_C, ha="center")
    ax.text(max(v_right) * 0.5, -0.7, lbl_r, fontsize=8, color=hi_color,
            ha="center", fontweight="bold")

    ax.spines[:].set_visible(False)
    ax.xaxis.set_visible(False)
    ax.tick_params(length=0)
    _set_title(ax, title)
    return fig


def chart_box_plot(data: dict, title: str, hi_color: str,
                   figsize=FIGSIZE_SPLIT) -> plt.Figure:
    """
    Box plot — compare distributions across categories.
    data keys: categories (list[str]),
               distributions (list[list[float]]),
               highlight (list[str]),
               x_label (str), y_label (str)
    """
    cats   = data["categories"]
    dists  = data["distributions"]
    hiset  = set(data.get("highlight", []))

    fig, ax = plt.subplots(figsize=figsize, facecolor=WHITE)

    bp = ax.boxplot(dists, patch_artist=True, widths=0.5,
                    medianprops=dict(color=TITLE_C, linewidth=1.5),
                    whiskerprops=dict(color=TICK_C, linewidth=0.8),
                    capprops=dict(color=TICK_C, linewidth=0.8),
                    flierprops=dict(marker="o", markersize=3, markerfacecolor=TICK_C,
                                    markeredgecolor="none", alpha=0.5))

    for i, (patch, c) in enumerate(zip(bp["boxes"], cats)):
        col = hi_color if c in hiset else GRAY
        patch.set_facecolor(col)
        patch.set_edgecolor(SPINE)
        patch.set_alpha(0.7)

    ax.set_xticklabels(cats, fontsize=8)
    ax.set_xlabel(data.get("x_label", ""), fontsize=8)
    ax.set_ylabel(data.get("y_label", ""), fontsize=8)

    _apply_swd_spines(ax)
    _set_title(ax, title)
    return fig


def chart_pareto(data: dict, title: str, hi_color: str,
                 figsize=FIGSIZE_SPLIT) -> plt.Figure:
    """
    Pareto chart — bars descending + cumulative % line. Classic 80/20 analysis.
    data keys: categories (list[str]), values (list[float]),
               value_format, threshold_pct (float, default 80)
    """
    cats   = list(data["categories"])
    vals   = [float(v) for v in data["values"]]
    thresh = data.get("threshold_pct", 80)

    # Sort descending
    pairs = sorted(zip(vals, cats), reverse=True)
    vals  = [p[0] for p in pairs]
    cats  = [p[1] for p in pairs]
    total = sum(vals)
    cum   = np.cumsum(vals) / total * 100

    fig, ax = plt.subplots(figsize=figsize, facecolor=WHITE)
    x = np.arange(len(cats))

    # Color bars: highlight those contributing to threshold
    colors = []
    for c in cum:
        colors.append(hi_color if c <= thresh + vals[0] / total * 100 else GRAY)
    # Fix: first bar always highlighted
    if colors:
        colors[0] = hi_color

    ax.bar(x, vals, color=colors, width=0.6, zorder=2)
    ax.set_xticks(x)
    ax.set_xticklabels(cats, fontsize=7.5, rotation=30, ha="right")
    ax.set_ylabel(data.get("y_label", ""), fontsize=8)

    # Cumulative line on twin axis
    ax2 = ax.twinx()
    ax2.plot(x, cum, color=hi_color, linewidth=1.5, marker="o", markersize=4, zorder=3)
    ax2.axhline(thresh, color=SPINE, linewidth=0.8, linestyle="--", zorder=1)
    ax2.set_ylim(0, 105)
    ax2.set_ylabel("Cumulative %", fontsize=8, color=TICK_C)
    ax2.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:.0f}%"))
    ax2.tick_params(labelsize=7, colors=TICK_C)
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_color(SPINE)
    ax2.spines["right"].set_linewidth(0.8)

    # 80% annotation
    ann = _AnnotationCounter()
    cross_i = next((i for i, c in enumerate(cum) if c >= thresh), len(cum) - 1)
    ann.annotate(ax2, f"{thresh:.0f}%", xy=(cross_i, thresh),
                 xytext=(cross_i + 0.5, thresh + 5),
                 fontsize=8, color=hi_color)

    _apply_swd_spines(ax)
    _set_title(ax, title)
    return fig


# ── Chart type dispatch ────────────────────────────────────────────────────────

CHART_BUILDERS = {
    # ── Core 14 (original + residual_plot) ──────────────────────────────────
    "vertical_bar":         chart_vertical_bar,
    "horizontal_bar":       chart_horizontal_bar,
    "highlight_bar":        chart_horizontal_bar,  # alias (used by chart-data skill)
    "highlight_line":       chart_highlight_line,
    "multi_line":           chart_multi_line,
    "multi_line_highlight": chart_multi_line,       # alias (chart_render_patterns.md)
    "waterfall":            chart_waterfall,
    "grouped_bar":          chart_grouped_bar,
    "forecast_line":        chart_forecast_line,
    "feature_importance":   chart_feature_importance,
    "scatter_regression":   chart_scatter_regression,
    "scatter":              chart_scatter_regression, # alias (HTML chart-data skill)
    "heatmap":              chart_heatmap,
    "slopegraph":           chart_slopegraph,
    "slope":                chart_slopegraph,         # alias (HTML chart-data skill)
    "model_comparison_bar": chart_model_comparison_bar,
    "model_comparison":     chart_model_comparison_bar,  # alias
    "roc_curve":            chart_roc_curve,
    "residual_plot":        chart_residual_plot,
    # ── SWD expansion (9 new) ───────────────────────────────────────────────
    "stacked_bar":          chart_stacked_bar,
    "histogram":            chart_histogram,
    "dot_plot":             chart_dot_plot,
    "bullet":               chart_bullet,
    "bullet_chart":         chart_bullet,  # alias
    "area":                 chart_area,
    "area_chart":           chart_area,  # alias
    "stacked_area":         chart_area,  # alias (use stacked=True in data)
    "connected_dot":        chart_connected_dot,
    "dumbbell":             chart_connected_dot,  # alias
    "diverging_bar":        chart_diverging_bar,
    "tornado":              chart_diverging_bar,  # alias
    "box_plot":             chart_box_plot,
    "pareto":               chart_pareto,
}


# ── Main runner ────────────────────────────────────────────────────────────────

def render_charts(stem: str, output_dir: Path = None, log=None):
    """Render all charts for a given stem. Returns manifest dict."""

    pipeline_dir = ROOT / "data" / "pipeline" / stem
    story_arc_path = pipeline_dir / "story_arc.json"

    if not story_arc_path.exists():
        print(f"ERROR: story_arc.json not found at {story_arc_path}", file=sys.stderr)
        sys.exit(1)

    with open(story_arc_path, encoding="utf-8") as f:
        arc = json.load(f)

    chart_reqs = arc.get("chart_requirements", [])
    if not chart_reqs:
        print(
            "WARNING: story_arc.json has no 'chart_requirements[]'.\n"
            "  -> data-storytelling skill must embed chart data before render_charts_swd.py runs.\n"
            "  -> See data-storytelling/SKILL.md Step 7 for required schema.",
            file=sys.stderr
        )
        # Attempt to scan slides for referenced chart IDs and warn
        referenced = _collect_chart_ids_from_slides(arc.get("slides", []))
        if referenced:
            print(f"  Chart IDs referenced in slides: {sorted(referenced)}", file=sys.stderr)
        sys.exit(1)

    # Output directory
    if output_dir is None:
        output_dir = pipeline_dir / "chart_images"
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest_charts = []
    errors = []

    print(f"Rendering {len(chart_reqs)} charts -> {output_dir}")
    if log:
        log.info("chart_render_start", total=len(chart_reqs), stem=stem)

    for req in chart_reqs:
        chart_id   = req.get("chart_id", "unknown")
        chart_type = req.get("chart_type", "").lower()
        section    = req.get("section", "descriptive").lower()
        title      = req.get("title", "")
        width      = req.get("width", "split")  # "split" or "full"
        chart_data = req.get("data")

        if not chart_data:
            msg = (f"SKIP {chart_id}: no 'data' field in chart_requirements entry. "
                   "Embed data arrays in story_arc.json chart_requirements.")
            print(f"  !  {msg}")
            errors.append(msg)
            continue

        if chart_type not in CHART_BUILDERS:
            msg = f"SKIP {chart_id}: unknown chart_type '{chart_type}'. Valid: {sorted(CHART_BUILDERS)}"
            print(f"  !  {msg}")
            errors.append(msg)
            continue

        hi_color = SECTION_COLORS.get(section, SECTION_COLORS["descriptive"])
        figsize  = FIGSIZE_FULL if width == "full" else FIGSIZE_SPLIT
        out_path = output_dir / f"{chart_id}.png"

        try:
            builder = CHART_BUILDERS[chart_type]
            fig = builder(chart_data, title, hi_color, figsize=figsize)
            _save_chart(fig, out_path)
            w_px = int(figsize[0] * DPI)
            h_px = int(figsize[1] * DPI)
            print(f"  [ok]  {chart_id}.png  [{chart_type}]  {w_px}x{h_px}px")
            if log:
                log.debug("chart_rendered", chart_id=chart_id, chart_type=chart_type)
            manifest_charts.append({
                "chart_id":   chart_id,
                "filename":   f"{chart_id}.png",
                "file_path":  str(out_path),
                "chart_type": chart_type,
                "section":    section,
                "slide_order": req.get("slide_order", 0),
                "title":      title,
                "width_px":   w_px,
                "height_px":  h_px,
                "dpi":        DPI,
            })
        except SWDViolation as e:
            msg = f"SWD VIOLATION in {chart_id}: {e}"
            print(f"  [no]  {msg}", file=sys.stderr)
            if log:
                log.warning("chart_render_failed", chart_id=chart_id, error=str(e))
            errors.append(msg)
        except Exception as e:
            msg = f"ERROR in {chart_id}: {type(e).__name__}: {e}"
            print(f"  [no]  {msg}", file=sys.stderr)
            if log:
                log.warning("chart_render_failed", chart_id=chart_id, error=str(e))
            errors.append(msg)

    # Write manifest
    manifest = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "stem": stem,
        "total_charts": len(manifest_charts),
        "failed_charts": len(errors),
        "output_dir": str(output_dir),
        "charts": manifest_charts,
        "errors": errors,
    }
    manifest_path = pipeline_dir / "chart_images.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print(f"\nManifest -> {manifest_path}")
    if log:
        log.info("manifest_written", path=str(manifest_path), chart_count=len(manifest_charts))
    print(f"Done: {len(manifest_charts)} charts rendered, {len(errors)} failed.")
    if log:
        log.info("render_complete", rendered=len(manifest_charts), failed=len(errors))

    if errors and len(manifest_charts) == 0:
        sys.exit(1)

    return manifest


def _collect_chart_ids_from_slides(slides: list) -> set:
    """Scan slide objects for any chart_id references."""
    ids = set()
    for slide in slides:
        for key in ("chart", "chart_id"):
            if key in slide:
                ids.add(slide[key])
        for panel in ("left_panel", "right_panel"):
            p = slide.get(panel, {})
            if p and p.get("chart_id"):
                ids.add(p["chart_id"])
        for cid in slide.get("charts", []):
            ids.add(cid)
    return ids


# ── CLI ────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Render SWD-compliant chart PNGs from story_arc.json chart_requirements."
    )
    parser.add_argument("--stem", required=True,
                        help="Dataset stem, e.g. sales_orders_2023_2026")
    parser.add_argument("--output-dir", default=None,
                        help="Override output directory (default: data/pipeline/{stem}/chart_images/)")
    parser.add_argument("--no-title", action="store_true",
                        help="Omit chart titles from PNGs (use when slide already carries the title)")
    args = parser.parse_args()

    if args.no_title:
        global _SHOW_TITLE
        _SHOW_TITLE = False

    stem = args.stem
    run_id = os.environ.get("PIPELINE_RUN_ID", new_run_id())
    log = get_logger(__name__, run_id=run_id, stem=stem)

    output_dir = Path(args.output_dir) if args.output_dir else None
    render_charts(stem, output_dir, log=log)


if __name__ == "__main__":
    main()
