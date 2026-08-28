"""
Deep Profiler — advanced data quality and statistical profiling.

Builds on schema_profiler for deeper analysis: distribution shapes,
temporal patterns, correlations, and anomaly detection.

Usage:
    from ai_analyst.helpers.deep_profiler import (
        profile_distributions, profile_temporal_patterns,
        profile_correlations, profile_completeness, profile_anomalies,
    )
"""

from __future__ import annotations

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # reach ai_analyst/
from helpers.utils.logger import get_logger

from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

_log = get_logger(__name__)


# ---------------------------------------------------------------------------
# Distribution profiling
# ---------------------------------------------------------------------------

def profile_distributions(
    df: pd.DataFrame,
    numeric_cols: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """Profile distribution shape for all numeric columns.

    Computes descriptive statistics, percentiles, skewness, kurtosis,
    and suggests the most likely distribution shape and recommended
    transform for each numeric column.

    Args:
        df: DataFrame to profile.
        numeric_cols: Optional list of columns. If None, auto-detect numeric.

    Returns:
        list of dicts, one per column with keys: column, n_values, n_unique,
        mean, median, std, skewness, kurtosis, p1..p99, iqr,
        n_outliers_iqr, shape, recommended_transform.
    """
    if numeric_cols is None:
        numeric_cols = df.select_dtypes(include="number").columns.tolist()

    results: List[Dict[str, Any]] = []
    for col in numeric_cols:
        if col not in df.columns:
            continue

        series = df[col].dropna()
        n_values = len(series)
        if n_values == 0:
            results.append({
                "column": col, "n_values": 0, "n_unique": 0,
                "mean": None, "median": None, "std": None,
                "skewness": None, "kurtosis": None,
                "p1": None, "p5": None, "p25": None, "p75": None,
                "p95": None, "p99": None, "iqr": None,
                "n_outliers_iqr": 0, "shape": "empty",
                "recommended_transform": None,
            })
            continue

        try:
            n_unique = int(series.nunique())
            mean = float(series.mean())
            median = float(series.median())
            std = float(series.std())
            skewness = float(series.skew())
            kurtosis = float(series.kurtosis())

            p1 = float(series.quantile(0.01))
            p5 = float(series.quantile(0.05))
            p25 = float(series.quantile(0.25))
            p75 = float(series.quantile(0.75))
            p95 = float(series.quantile(0.95))
            p99 = float(series.quantile(0.99))

            iqr = p75 - p25
            lower_fence = p25 - 1.5 * iqr
            upper_fence = p75 + 1.5 * iqr
            n_outliers_iqr = int(
                ((series < lower_fence) | (series > upper_fence)).sum()
            )

            shape = _classify_shape(series, skewness, kurtosis, n_unique)
            recommended_transform = _recommend_transform(series, skewness)

            results.append({
                "column": col, "n_values": n_values, "n_unique": n_unique,
                "mean": mean, "median": median, "std": std,
                "skewness": skewness, "kurtosis": kurtosis,
                "p1": p1, "p5": p5, "p25": p25, "p75": p75,
                "p95": p95, "p99": p99, "iqr": iqr,
                "n_outliers_iqr": n_outliers_iqr, "shape": shape,
                "recommended_transform": recommended_transform,
            })
        except Exception as e:
            _log.debug("distribution_profile_failed", column=col, error=str(e))
            results.append({
                "column": col, "n_values": n_values, "n_unique": 0,
                "mean": None, "median": None, "std": None,
                "skewness": None, "kurtosis": None,
                "p1": None, "p5": None, "p25": None, "p75": None,
                "p95": None, "p99": None, "iqr": None,
                "n_outliers_iqr": 0, "shape": "unknown",
                "recommended_transform": None,
            })

    return results


def _classify_shape(
    series: pd.Series,
    skewness: float,
    kurtosis: float,
    n_unique: int,
) -> str:
    """Classify the distribution shape from summary statistics.

    Uses skewness, kurtosis, and a simple bimodality check to assign
    one of: normal, right-skewed, left-skewed, bimodal, uniform,
    heavy-tailed.
    """
    if abs(skewness) < 0.5 and kurtosis < -1.0:
        return "uniform"

    if kurtosis > 3.0:
        return "heavy-tailed"

    if n_unique > 10:
        try:
            hist_counts, _ = np.histogram(series, bins=min(50, n_unique))
            if _has_two_peaks(hist_counts):
                return "bimodal"
        except Exception as e:
            _log.debug("bimodality_check_failed", error=str(e))

    if skewness > 1.0:
        return "right-skewed"
    elif skewness < -1.0:
        return "left-skewed"

    return "normal"


def _has_two_peaks(counts: np.ndarray) -> bool:
    """Simple peak detection for bimodality.

    Checks if the histogram counts have at least two local maxima
    with a valley between them that drops below 60% of the lower peak.
    """
    if len(counts) < 5:
        return False

    smoothed = np.convolve(counts, np.ones(3) / 3, mode="same")

    peaks = []
    for i in range(1, len(smoothed) - 1):
        if smoothed[i] > smoothed[i - 1] and smoothed[i] > smoothed[i + 1]:
            peaks.append((i, smoothed[i]))

    if len(peaks) < 2:
        return False

    peaks_sorted = sorted(peaks, key=lambda p: p[1], reverse=True)[:2]
    left_idx = min(peaks_sorted[0][0], peaks_sorted[1][0])
    right_idx = max(peaks_sorted[0][0], peaks_sorted[1][0])
    valley = min(smoothed[left_idx:right_idx + 1])
    lower_peak = min(peaks_sorted[0][1], peaks_sorted[1][1])

    return valley < lower_peak * 0.6


def _recommend_transform(series: pd.Series, skewness: float) -> Optional[str]:
    """Suggest a transform to normalise the distribution.

    Returns "log" for right-skewed with all positive values,
    "sqrt" for moderate right skew, or None.
    """
    if abs(skewness) < 1.0:
        return None

    if skewness > 1.0:
        if series.min() > 0:
            return "log"
        if series.min() >= 0:
            return "sqrt"

    return None


# ---------------------------------------------------------------------------
# Temporal pattern profiling
# ---------------------------------------------------------------------------

def profile_temporal_patterns(
    df: pd.DataFrame,
    date_col: str,
    metric_cols: Optional[List[str]] = None,
    freq: str = "D",
) -> Dict[str, Any]:
    """Analyze temporal patterns in the data.

    Checks date coverage, detects gaps, day-of-week and monthly patterns,
    trend direction, and basic seasonality.

    Args:
        df: DataFrame with date column.
        date_col: Name of the date column.
        metric_cols: Optional list of metric columns. If None, auto-detect.
        freq: Expected frequency ("D" daily, "W" weekly, "M" monthly).

    Returns:
        dict with keys: date_range, expected_periods, actual_periods,
        coverage_pct, gaps, day_of_week_pattern, monthly_pattern,
        trend, seasonality_detected.
    """
    _empty = {
        "date_range": None, "expected_periods": 0, "actual_periods": 0,
        "coverage_pct": 0.0, "gaps": [], "day_of_week_pattern": {},
        "monthly_pattern": {}, "trend": "unknown",
        "seasonality_detected": False,
    }

    if date_col not in df.columns:
        return _empty

    if metric_cols is None:
        metric_cols = df.select_dtypes(include="number").columns.tolist()

    dates = pd.to_datetime(df[date_col], errors="coerce")
    valid_mask = dates.notna()
    dates = dates[valid_mask]
    data = df.loc[valid_mask].copy()
    data["_parsed_date"] = dates

    if len(dates) == 0:
        return _empty

    date_min = dates.min()
    date_max = dates.max()
    date_range = {
        "min": str(date_min.date()) if hasattr(date_min, "date") else str(date_min),
        "max": str(date_max.date()) if hasattr(date_max, "date") else str(date_max),
    }

    try:
        expected = pd.date_range(start=date_min, end=date_max, freq=freq)
        expected_periods = len(expected)
    except Exception as e:
        _log.debug("date_range_build_failed", date_col=date_col, freq=freq, error=str(e))
        expected_periods = 0
        expected = pd.DatetimeIndex([])

    if freq == "D":
        actual_dates = dates.dt.date.unique()
    elif freq == "W":
        actual_dates = dates.dt.to_period("W").unique()
    elif freq == "M":
        actual_dates = dates.dt.to_period("M").unique()
    else:
        actual_dates = dates.dt.date.unique()

    actual_periods = len(actual_dates)
    coverage_pct = round(
        100.0 * actual_periods / expected_periods, 2
    ) if expected_periods > 0 else 0.0

    # Find gaps (daily frequency)
    gaps: List[Dict[str, Any]] = []
    if freq == "D" and expected_periods > 0:
        try:
            expected_set = set(expected.date)
            actual_set = set(
                pd.to_datetime(pd.Series(list(actual_dates))).dt.date
            )
            missing = sorted(expected_set - actual_set)
            gaps = _group_consecutive_dates(missing)
        except Exception as e:
            _log.debug("gap_detection_failed", date_col=date_col, error=str(e))

    # Day-of-week pattern
    day_of_week_pattern: Dict[str, float] = {}
    if freq == "D" and metric_cols:
        primary_metric = metric_cols[0]
        if primary_metric in data.columns:
            try:
                dow = data.copy()
                dow["_dow"] = data["_parsed_date"].dt.day_name()
                dow_means = dow.groupby("_dow")[primary_metric].mean()
                day_of_week_pattern = {
                    str(k): round(float(v), 4) for k, v in dow_means.items()
                }
            except Exception as e:
                _log.debug("day_of_week_pattern_failed", date_col=date_col, metric=primary_metric, error=str(e))

    # Monthly pattern
    monthly_pattern: Dict[str, float] = {}
    if metric_cols:
        primary_metric = metric_cols[0]
        if primary_metric in data.columns:
            try:
                data_m = data.copy()
                data_m["_month"] = data["_parsed_date"].dt.month
                month_means = data_m.groupby("_month")[primary_metric].mean()
                day_names = {
                    1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr",
                    5: "May", 6: "Jun", 7: "Jul", 8: "Aug",
                    9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec",
                }
                monthly_pattern = {
                    day_names.get(int(k), str(k)): round(float(v), 4)
                    for k, v in month_means.items()
                }
            except Exception as e:
                _log.debug("monthly_pattern_failed", date_col=date_col, metric=primary_metric, error=str(e))

    trend = _detect_trend(data, date_col="_parsed_date", metric_cols=metric_cols)
    seasonality_detected = _detect_seasonality(monthly_pattern)

    return {
        "date_range": date_range,
        "expected_periods": expected_periods,
        "actual_periods": actual_periods,
        "coverage_pct": coverage_pct,
        "gaps": gaps,
        "day_of_week_pattern": day_of_week_pattern,
        "monthly_pattern": monthly_pattern,
        "trend": trend,
        "seasonality_detected": seasonality_detected,
    }


def _group_consecutive_dates(missing_dates: list) -> List[Dict[str, Any]]:
    """Group consecutive missing dates into gap ranges."""
    if not missing_dates:
        return []

    from datetime import timedelta

    gaps: List[Dict[str, Any]] = []
    start = missing_dates[0]
    prev = missing_dates[0]

    for d in missing_dates[1:]:
        if (d - prev).days <= 1:
            prev = d
        else:
            gaps.append({
                "start": str(start), "end": str(prev),
                "n_missing": (prev - start).days + 1,
            })
            start = d
            prev = d

    gaps.append({
        "start": str(start), "end": str(prev),
        "n_missing": (prev - start).days + 1,
    })
    return gaps


def _detect_trend(
    data: pd.DataFrame,
    date_col: str,
    metric_cols: List[str],
) -> str:
    """Detect overall trend direction using a simple linear fit.

    Returns one of: "increasing", "decreasing", "stable", "volatile".
    """
    if not metric_cols:
        return "unknown"

    primary_metric = metric_cols[0]
    if primary_metric not in data.columns or date_col not in data.columns:
        return "unknown"

    try:
        sorted_data = data.sort_values(date_col).copy()
        values = sorted_data[primary_metric].dropna().values
        if len(values) < 5:
            return "unknown"

        x = np.arange(len(values), dtype=float)
        coefficients = np.polyfit(x, values, 1)
        slope = coefficients[0]

        mean_val = np.mean(values)
        if mean_val == 0:
            return "stable"

        relative_slope = slope / abs(mean_val)

        fitted = np.polyval(coefficients, x)
        residuals = values - fitted
        cv = np.std(residuals) / abs(mean_val) if mean_val != 0 else 0

        if cv > 0.5:
            return "volatile"
        elif relative_slope > 0.01:
            return "increasing"
        elif relative_slope < -0.01:
            return "decreasing"
        else:
            return "stable"
    except Exception as e:
        _log.debug("trend_detection_failed", metric=metric_cols[0] if metric_cols else None, error=str(e))
        return "unknown"


def _detect_seasonality(monthly_pattern: Dict[str, float]) -> bool:
    """Check if monthly pattern shows meaningful seasonal variation.

    Returns True if the coefficient of variation across months exceeds 20%.
    """
    if not monthly_pattern or len(monthly_pattern) < 3:
        return False

    try:
        values = list(monthly_pattern.values())
        mean_val = np.mean(values)
        if mean_val == 0:
            return False
        cv = np.std(values) / abs(mean_val)
        return cv > 0.2
    except Exception as e:
        _log.debug("seasonality_detection_failed", error=str(e))
        return False


# ---------------------------------------------------------------------------
# Correlation profiling
# ---------------------------------------------------------------------------

def profile_correlations(
    df: pd.DataFrame,
    numeric_cols: Optional[List[str]] = None,
    threshold: float = 0.5,
) -> List[Dict[str, Any]]:
    """Find significant correlations between numeric columns.

    Computes the Pearson correlation matrix and returns pairs whose
    absolute correlation exceeds the threshold, sorted by strength.

    Args:
        df: DataFrame.
        numeric_cols: Optional list. If None, auto-detect.
        threshold: Minimum absolute correlation to report (default 0.5).

    Returns:
        list of dicts sorted by abs correlation descending with keys:
        col_a, col_b, correlation, abs_correlation, strength, direction.
    """
    if numeric_cols is None:
        numeric_cols = df.select_dtypes(include="number").columns.tolist()

    if len(numeric_cols) < 2:
        return []

    try:
        corr_matrix = df[numeric_cols].corr()
    except Exception as e:
        _log.debug("correlation_matrix_failed", error=str(e))
        return []

    results: List[Dict[str, Any]] = []
    seen: set = set()

    for i, col_a in enumerate(numeric_cols):
        for j, col_b in enumerate(numeric_cols):
            if i >= j:
                continue
            pair_key = (col_a, col_b)
            if pair_key in seen:
                continue
            seen.add(pair_key)

            try:
                corr_val = float(corr_matrix.loc[col_a, col_b])
            except Exception as e:
                _log.debug("correlation_lookup_failed", col_a=col_a, col_b=col_b, error=str(e))
                continue

            if pd.isna(corr_val):
                continue

            abs_corr = abs(corr_val)
            if abs_corr < threshold:
                continue

            if abs_corr >= 0.9:
                strength = "very_strong"
            elif abs_corr >= 0.7:
                strength = "strong"
            elif abs_corr >= 0.5:
                strength = "moderate"
            else:
                strength = "weak"

            direction = "positive" if corr_val > 0 else "negative"

            results.append({
                "col_a": col_a, "col_b": col_b,
                "correlation": round(corr_val, 4),
                "abs_correlation": round(abs_corr, 4),
                "strength": strength, "direction": direction,
            })

    results.sort(key=lambda r: r["abs_correlation"], reverse=True)
    return results


# ---------------------------------------------------------------------------
# Completeness profiling
# ---------------------------------------------------------------------------

def profile_completeness(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Assess completeness of each column.

    For every column, counts nulls, zeros (numeric), empty strings (object),
    and flags constant columns.

    Args:
        df: DataFrame.

    Returns:
        list of dicts with keys: column, total_rows, non_null, null_count,
        null_pct, status, zero_count, empty_string_count, constant.
    """
    total_rows = len(df)
    results: List[Dict[str, Any]] = []

    for col in df.columns:
        series = df[col]
        null_count = int(series.isnull().sum())
        non_null = total_rows - null_count
        null_pct = round(
            100.0 * null_count / total_rows, 2
        ) if total_rows > 0 else 0.0

        if null_pct == 0:
            status = "COMPLETE"
        elif null_pct < 5:
            status = "GOOD"
        elif null_pct < 50:
            status = "WARNING"
        else:
            status = "CRITICAL"

        zero_count = 0
        if pd.api.types.is_numeric_dtype(series):
            try:
                zero_count = int((series == 0).sum())
            except Exception as e:
                _log.debug("zero_count_failed", column=col, error=str(e))

        empty_string_count = 0
        if pd.api.types.is_string_dtype(series) or pd.api.types.is_object_dtype(series):
            try:
                empty_string_count = int(
                    series.dropna().astype(str).str.strip().eq("").sum()
                )
            except Exception as e:
                _log.debug("empty_string_count_failed", column=col, error=str(e))

        try:
            constant = bool(series.dropna().nunique() <= 1) if non_null > 0 else True
        except Exception as e:
            _log.debug("constant_check_failed", column=col, error=str(e))
            constant = False

        results.append({
            "column": col, "total_rows": total_rows, "non_null": non_null,
            "null_count": null_count, "null_pct": null_pct, "status": status,
            "zero_count": zero_count, "empty_string_count": empty_string_count,
            "constant": constant,
        })

    return results


# ---------------------------------------------------------------------------
# Anomaly profiling
# ---------------------------------------------------------------------------

def profile_anomalies(
    df: pd.DataFrame,
    date_col: Optional[str] = None,
    metric_cols: Optional[List[str]] = None,
    window: int = 14,
    threshold: float = 2.0,
) -> Dict[str, Any]:
    """Detect anomalies across multiple metrics using rolling statistics.

    The input DataFrame should be pre-aggregated to daily/weekly granularity.

    Args:
        df: DataFrame (pre-aggregated to daily/weekly).
        date_col: Date column name (required for time-series detection).
        metric_cols: List of metric columns. If None, auto-detect numeric.
        window: Rolling window size.
        threshold: Number of std devs for anomaly band.

    Returns:
        dict with keys: metrics_scanned, total_anomalies, by_metric, summary.
    """
    if metric_cols is None:
        metric_cols = df.select_dtypes(include="number").columns.tolist()

    if date_col is None or date_col not in df.columns:
        return {
            "metrics_scanned": 0, "total_anomalies": 0, "by_metric": [],
            "summary": "No date column provided; cannot run anomaly detection.",
        }

    try:
        ts = df.copy()
        ts[date_col] = pd.to_datetime(ts[date_col], errors="coerce")
        ts = ts.dropna(subset=[date_col]).sort_values(date_col)
    except Exception as e:
        _log.debug("anomaly_date_parse_failed", date_col=date_col, error=str(e))
        return {
            "metrics_scanned": 0, "total_anomalies": 0, "by_metric": [],
            "summary": "Could not parse date column for anomaly detection.",
        }

    by_metric: List[Dict[str, Any]] = []
    total_anomalies = 0

    for metric in metric_cols:
        if metric not in ts.columns:
            continue
        try:
            result = _scan_single_metric(ts, date_col, metric, window, threshold)
            by_metric.append(result)
            total_anomalies += result["n_anomalies"]
        except Exception as e:
            _log.debug("anomaly_metric_scan_failed", metric=metric, error=str(e))
            by_metric.append({
                "metric": metric, "n_anomalies": 0,
                "spikes": [], "drops": [],
            })

    metrics_scanned = len(by_metric)
    if total_anomalies == 0:
        summary = (
            f"Scanned {metrics_scanned} metric(s). "
            "No anomalies detected — all metrics appear stable."
        )
    else:
        anomaly_parts = []
        for m in by_metric:
            if m["n_anomalies"] > 0:
                anomaly_parts.append(
                    f"{m['metric']}: {len(m['spikes'])} spike(s), "
                    f"{len(m['drops'])} drop(s)"
                )
        summary = (
            f"Scanned {metrics_scanned} metric(s), "
            f"found {total_anomalies} anomalie(s). "
            + "; ".join(anomaly_parts)
        )

    return {
        "metrics_scanned": metrics_scanned,
        "total_anomalies": total_anomalies,
        "by_metric": by_metric,
        "summary": summary,
    }


def _scan_single_metric(
    ts: pd.DataFrame,
    date_col: str,
    metric_col: str,
    window: int,
    threshold: float,
) -> Dict[str, Any]:
    """Run anomaly detection on a single metric column.

    Uses rolling mean +/- (threshold * rolling std) bands.
    """
    rolling_mean = ts[metric_col].rolling(window, min_periods=3).mean()
    rolling_std = ts[metric_col].rolling(window, min_periods=3).std()
    upper = rolling_mean + threshold * rolling_std
    lower = rolling_mean - threshold * rolling_std

    spikes: List[Dict[str, Any]] = []
    drops: List[Dict[str, Any]] = []

    for idx in ts.index:
        val = ts.loc[idx, metric_col]
        mean_val = rolling_mean.loc[idx]
        upper_val = upper.loc[idx]
        lower_val = lower.loc[idx]
        date_val = ts.loc[idx, date_col]

        if pd.isna(upper_val) or pd.isna(val):
            continue

        date_str = (
            str(date_val.date()) if hasattr(date_val, "date") else str(date_val)
        )

        if val > upper_val and mean_val != 0:
            pct_above = round(100.0 * (val - mean_val) / abs(mean_val), 1)
            spikes.append({
                "date": date_str, "value": round(float(val), 4),
                "pct_above": pct_above,
            })
        elif val < lower_val and mean_val != 0:
            pct_below = round(100.0 * (mean_val - val) / abs(mean_val), 1)
            drops.append({
                "date": date_str, "value": round(float(val), 4),
                "pct_below": pct_below,
            })

    return {
        "metric": metric_col,
        "n_anomalies": len(spikes) + len(drops),
        "spikes": spikes,
        "drops": drops,
    }
