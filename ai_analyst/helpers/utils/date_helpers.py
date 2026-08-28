"""Date utility helpers — parsing, grain detection, fiscal calendar, gap filling.

Provides robust date handling for analytics pipelines where date columns
may arrive in various formats and granularities.

Public API:
    detect_date_column()     - Auto-detect the date column in a DataFrame
    detect_grain()           - Detect temporal granularity (daily/weekly/monthly/quarterly/yearly)
    parse_dates()            - Parse a column to datetime with format inference
    date_range_summary()     - Summarize a date range (min, max, span, gaps)
    fill_date_gaps()         - Fill missing dates in a time series
    fiscal_quarter()         - Map a date to fiscal quarter
    fiscal_year()            - Map a date to fiscal year
    relative_period_label()  - Human-readable period label ("Q1 2025", "Jan 2025")
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Date column detection
# ---------------------------------------------------------------------------

_DATE_KEYWORDS: list[str] = [
    "date", "datetime", "timestamp", "time", "period", "month", "year",
    "quarter", "week", "day", "created", "updated", "occurred",
]


def detect_date_column(df: pd.DataFrame) -> str | None:
    """Auto-detect the most likely date column in a DataFrame.

    Strategy:
    1. Return first column already in datetime dtype.
    2. Return first column whose name contains a date keyword.
    3. Try parsing each object/string column; return first that succeeds on >80% of rows.
    4. Return ``None`` if no date column found.

    Parameters
    ----------
    df : pd.DataFrame
        Input DataFrame.

    Returns
    -------
    str or None
        Column name, or ``None`` if not detected.
    """
    # Strategy 1: existing datetime columns
    dt_cols = df.select_dtypes(include=["datetime", "datetime64"]).columns
    if len(dt_cols) > 0:
        return str(dt_cols[0])

    # Strategy 2: name matching
    for col in df.columns:
        col_lower = str(col).lower().replace("_", " ")
        if any(kw in col_lower for kw in _DATE_KEYWORDS):
            # Verify it can actually be parsed
            try:
                parsed = pd.to_datetime(df[col], errors="coerce")
                if parsed.notna().mean() > 0.5:
                    return str(col)
            except (ValueError, TypeError):
                continue

    # Strategy 3: brute-force parse object columns
    for col in df.select_dtypes(include=["object"]).columns:
        try:
            parsed = pd.to_datetime(df[col], errors="coerce", infer_datetime_format=True)
            if parsed.notna().mean() > 0.8:
                return str(col)
        except (ValueError, TypeError):
            continue

    return None


# ---------------------------------------------------------------------------
# Grain detection
# ---------------------------------------------------------------------------

_GRAIN_THRESHOLDS: dict[str, tuple[float, float]] = {
    "daily": (0.5, 2.5),
    "weekly": (5.0, 9.0),
    "monthly": (25.0, 35.0),
    "quarterly": (80.0, 100.0),
    "yearly": (350.0, 380.0),
}


def detect_grain(
    dates: pd.Series,
    *,
    sample_size: int = 100,
) -> str:
    """Detect temporal granularity of a date series.

    Computes the median gap between consecutive sorted dates and maps it
    to the closest standard grain.

    Parameters
    ----------
    dates : pd.Series
        Series of datetime values.
    sample_size : int
        Max number of consecutive gaps to sample for performance.

    Returns
    -------
    str
        One of ``"daily"``, ``"weekly"``, ``"monthly"``, ``"quarterly"``,
        ``"yearly"``, or ``"irregular"``.
    """
    dt = pd.to_datetime(dates, errors="coerce").dropna().sort_values().reset_index(drop=True)
    if len(dt) < 3:
        return "irregular"

    gaps = dt.diff().dropna().dt.days
    if len(gaps) > sample_size:
        gaps = gaps.sample(n=sample_size, random_state=42)

    median_gap = float(gaps.median())

    for grain, (lo, hi) in _GRAIN_THRESHOLDS.items():
        if lo <= median_gap <= hi:
            return grain

    return "irregular"


# ---------------------------------------------------------------------------
# Date parsing
# ---------------------------------------------------------------------------

def parse_dates(
    series: pd.Series,
    *,
    format: str | None = None,
    dayfirst: bool = False,
) -> pd.Series:
    """Parse a Series to datetime with optional format specification.

    Parameters
    ----------
    series : pd.Series
        Raw date values (strings, ints, or mixed).
    format : str or None
        Explicit strftime format. If ``None``, pandas infers.
    dayfirst : bool
        If ``True``, parse ambiguous dates as DD/MM/YYYY.

    Returns
    -------
    pd.Series
        Datetime Series. Unparseable values become ``NaT``.
    """
    if format:
        return pd.to_datetime(series, format=format, errors="coerce")
    return pd.to_datetime(series, dayfirst=dayfirst, errors="coerce", infer_datetime_format=True)


# ---------------------------------------------------------------------------
# Date range summary
# ---------------------------------------------------------------------------

def date_range_summary(dates: pd.Series) -> dict[str, Any]:
    """Summarize a date series: min, max, span, gap count, grain.

    Parameters
    ----------
    dates : pd.Series
        Datetime Series.

    Returns
    -------
    dict
        Keys: ``min_date``, ``max_date``, ``span_days``, ``n_records``,
        ``n_gaps``, ``grain``, ``gap_dates`` (list of missing dates for
        daily grain, empty otherwise).
    """
    dt = pd.to_datetime(dates, errors="coerce").dropna().sort_values()
    if len(dt) == 0:
        return {
            "min_date": None,
            "max_date": None,
            "span_days": 0,
            "n_records": 0,
            "n_gaps": 0,
            "grain": "unknown",
            "gap_dates": [],
        }

    min_date = dt.iloc[0]
    max_date = dt.iloc[-1]
    span_days = (max_date - min_date).days
    grain = detect_grain(dt)

    # Detect gaps for daily grain
    gap_dates: list[str] = []
    if grain == "daily":
        full_range = pd.date_range(start=min_date, end=max_date, freq="D")
        missing = full_range.difference(dt)
        gap_dates = [d.strftime("%Y-%m-%d") for d in missing]

    return {
        "min_date": min_date.strftime("%Y-%m-%d"),
        "max_date": max_date.strftime("%Y-%m-%d"),
        "span_days": span_days,
        "n_records": len(dt),
        "n_gaps": len(gap_dates),
        "grain": grain,
        "gap_dates": gap_dates[:50],  # Cap to avoid huge lists
    }


# ---------------------------------------------------------------------------
# Gap filling
# ---------------------------------------------------------------------------

_GRAIN_FREQ_MAP: dict[str, str] = {
    "daily": "D",
    "weekly": "W-MON",
    "monthly": "MS",
    "quarterly": "QS",
    "yearly": "YS",
}


def fill_date_gaps(
    df: pd.DataFrame,
    date_col: str,
    *,
    grain: str | None = None,
    fill_value: float = 0.0,
    fill_method: str | None = None,
) -> pd.DataFrame:
    """Fill missing dates in a time series DataFrame.

    Parameters
    ----------
    df : pd.DataFrame
        Input DataFrame with a date column.
    date_col : str
        Name of the date column.
    grain : str or None
        Temporal grain. If ``None``, auto-detected.
    fill_value : float
        Value for numeric columns when ``fill_method`` is ``None``.
    fill_method : str or None
        Pandas fill method (``"ffill"``, ``"bfill"``). If ``None``,
        numeric columns are filled with ``fill_value``.

    Returns
    -------
    pd.DataFrame
        DataFrame with continuous date index and filled gaps.
    """
    df = df.copy()
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    df = df.dropna(subset=[date_col]).sort_values(date_col)

    if grain is None:
        grain = detect_grain(df[date_col])

    freq = _GRAIN_FREQ_MAP.get(grain)
    if freq is None:
        return df  # Can't fill irregular grain

    full_range = pd.date_range(
        start=df[date_col].min(),
        end=df[date_col].max(),
        freq=freq,
    )

    df = df.set_index(date_col).reindex(full_range)
    df.index.name = date_col

    if fill_method:
        df = df.fillna(method=fill_method)
    else:
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        df[numeric_cols] = df[numeric_cols].fillna(fill_value)

    return df.reset_index()


# ---------------------------------------------------------------------------
# Fiscal calendar
# ---------------------------------------------------------------------------

def fiscal_quarter(
    date: datetime | pd.Timestamp,
    *,
    fiscal_start_month: int = 1,
) -> int:
    """Map a date to its fiscal quarter (1–4).

    Parameters
    ----------
    date : datetime or pd.Timestamp
        Input date.
    fiscal_start_month : int
        Month when fiscal year begins (1=Jan, 4=Apr, 7=Jul, 10=Oct).

    Returns
    -------
    int
        Fiscal quarter number (1–4).
    """
    month = date.month
    adjusted = (month - fiscal_start_month) % 12
    return adjusted // 3 + 1


def fiscal_year(
    date: datetime | pd.Timestamp,
    *,
    fiscal_start_month: int = 1,
) -> int:
    """Map a date to its fiscal year.

    Parameters
    ----------
    date : datetime or pd.Timestamp
        Input date.
    fiscal_start_month : int
        Month when fiscal year begins.

    Returns
    -------
    int
        Fiscal year (e.g., 2025).
    """
    if fiscal_start_month == 1:
        return date.year
    if date.month >= fiscal_start_month:
        return date.year + 1
    return date.year


# ---------------------------------------------------------------------------
# Period labeling
# ---------------------------------------------------------------------------

_MONTH_ABBR: list[str] = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
]


def relative_period_label(
    date: datetime | pd.Timestamp,
    grain: str = "monthly",
) -> str:
    """Generate a human-readable period label for a date.

    Parameters
    ----------
    date : datetime or pd.Timestamp
        Input date.
    grain : str
        Temporal grain: ``"daily"``, ``"weekly"``, ``"monthly"``,
        ``"quarterly"``, ``"yearly"``.

    Returns
    -------
    str
        Label like ``"Jan 2025"``, ``"Q1 2025"``, ``"2025"``,
        ``"W03 2025"``, or ``"2025-01-15"``.
    """
    if grain == "yearly":
        return str(date.year)
    if grain == "quarterly":
        q = (date.month - 1) // 3 + 1
        return f"Q{q} {date.year}"
    if grain == "monthly":
        return f"{_MONTH_ABBR[date.month - 1]} {date.year}"
    if grain == "weekly":
        iso_week = date.isocalendar()[1]
        return f"W{iso_week:02d} {date.year}"
    # daily or irregular
    return date.strftime("%Y-%m-%d")
