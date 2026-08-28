"""
Logical Validation Helpers (Layer 2).

Validates LOGICAL consistency of analytical results: aggregation integrity,
trend continuity, segment exhaustiveness, temporal consistency, percentage
sums, monotonicity, ratio bounds, group balance, and future-date detection.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import numpy as np
import pandas as pd

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))  # reach ai_analyst/
from helpers.utils.logger import get_logger

_log = get_logger(__name__)


# ===================================================================
# NEW API — consistent ok-based return dicts
# ===================================================================

def validate_aggregation_consistency(
    detail_df: pd.DataFrame,
    summary_df: pd.DataFrame,
    *args: Any,
    **kwargs: Any,
) -> dict:
    """Check that detail-level data aggregates to match summary totals.

    Supports both new API (metric_column=, group_column=) and legacy API
    (group_col=, metric_col=, agg=).

    Args:
        detail_df: Row-level detail DataFrame.
        summary_df: Pre-aggregated summary DataFrame.

    Returns:
        dict with ok-based or severity-based keys depending on call style.
    """
    legacy_keywords = {"group_col", "metric_col", "agg"}
    if legacy_keywords & set(kwargs.keys()):
        return _aggregation_consistency_legacy(detail_df, summary_df, *args, **kwargs)

    if (len(args) >= 2 and isinstance(args[0], str) and isinstance(args[1], str)
            and "metric_column" not in kwargs and "group_column" not in kwargs):
        legacy_kw = {k: v for k, v in kwargs.items() if k not in ("agg",)}
        if len(args) > 2:
            legacy_kw["agg"] = args[2]
        return _aggregation_consistency_legacy(
            detail_df, summary_df, group_col=args[0], metric_col=args[1], **legacy_kw,
        )

    return _aggregation_consistency_new(detail_df, summary_df, *args, **kwargs)


def _aggregation_consistency_new(
    detail_df: pd.DataFrame,
    summary_df: pd.DataFrame,
    metric_column: Optional[str] = None,
    group_column: Optional[str] = None,
    tolerance: float = 0.01,
) -> dict:
    """New ok-based aggregation consistency check."""
    try:
        if detail_df is None or summary_df is None:
            return {"ok": False, "expected_total": 0.0, "actual_total": 0.0,
                    "difference": 0.0, "tolerance": tolerance}

        if len(detail_df) == 0 and len(summary_df) == 0:
            return {"ok": True, "expected_total": 0.0, "actual_total": 0.0,
                    "difference": 0.0, "tolerance": tolerance}

        if group_column is not None:
            detail_agg = detail_df.groupby(group_column)[metric_column].sum()
            summary_agg = (
                summary_df.set_index(group_column)[metric_column]
                if group_column in summary_df.columns
                else pd.Series(dtype=float)
            )
            expected_total = float(detail_agg.sum())
            actual_total = float(summary_agg.sum()) if len(summary_agg) > 0 else 0.0
        else:
            expected_total = float(detail_df[metric_column].sum())
            actual_total = float(summary_df[metric_column].sum())

        difference = abs(expected_total - actual_total)
        denominator = abs(expected_total) if expected_total != 0 else abs(actual_total)
        relative_diff = difference / denominator if denominator != 0 else 0.0

        return {
            "ok": relative_diff <= tolerance,
            "expected_total": round(expected_total, 6),
            "actual_total": round(actual_total, 6),
            "difference": round(difference, 6),
            "tolerance": tolerance,
        }
    except Exception as e:
        _log.warning("check_failed", error=str(e))
        return {"ok": False, "expected_total": 0.0, "actual_total": 0.0,
                "difference": 0.0, "tolerance": tolerance}


def _aggregation_consistency_legacy(
    detail_df: pd.DataFrame,
    summary_df: pd.DataFrame,
    group_col: Optional[str] = None,
    metric_col: Optional[str] = None,
    agg: str = "sum",
    tolerance: float = 0.01,
) -> dict:
    """Legacy severity-based aggregation consistency check."""
    if len(detail_df) == 0 and len(summary_df) == 0:
        return {"valid": True, "mismatches": [], "severity": "PASS"}
    if len(detail_df) == 0 or len(summary_df) == 0:
        return {"valid": False, "mismatches": [], "severity": "BLOCKER"}

    re_agg = detail_df.groupby(group_col)[metric_col].agg(agg).reset_index()
    re_agg.columns = [group_col, "expected"]

    summary_subset = summary_df[[group_col, metric_col]].copy()
    summary_subset.columns = [group_col, "actual"]

    merged = pd.merge(re_agg, summary_subset, on=group_col, how="outer")

    mismatches: List[dict] = []
    for _, row in merged.iterrows():
        expected = row.get("expected")
        actual = row.get("actual")

        if pd.isna(expected) or pd.isna(actual):
            mismatches.append({
                "group": row[group_col],
                "expected": None if pd.isna(expected) else float(expected),
                "actual": None if pd.isna(actual) else float(actual),
                "diff_pct": None,
            })
            continue

        expected = float(expected)
        actual = float(actual)
        denominator = abs(expected) if expected != 0 else abs(actual)
        diff_pct = abs(actual - expected) / denominator if denominator != 0 else 0.0

        if diff_pct > tolerance:
            mismatches.append({
                "group": row[group_col], "expected": expected,
                "actual": actual, "diff_pct": round(diff_pct, 6),
            })

    if len(mismatches) == 0:
        severity = "PASS"
    elif any(m["diff_pct"] is None or m["diff_pct"] > 0.05 for m in mismatches):
        severity = "BLOCKER"
    else:
        severity = "WARNING"

    return {"valid": severity == "PASS", "mismatches": mismatches, "severity": severity}


validate_aggregation_consistency_legacy = _aggregation_consistency_legacy


def validate_percentages_sum(
    df: pd.DataFrame,
    pct_column: str,
    group_column: Optional[str] = None,
    expected_sum: float = 100.0,
    tolerance: float = 1.0,
) -> dict:
    """Check that a percentage column sums to the expected total.

    Args:
        df: DataFrame containing the percentage column.
        pct_column: Column holding percentage values.
        group_column: Optional column for within-group checks.
        expected_sum: Expected total (default 100.0).
        tolerance: Allowed absolute deviation (default 1.0).

    Returns:
        dict with keys: ok, actual_sum, difference.
    """
    try:
        if df is None or len(df) == 0:
            return {"ok": True, "actual_sum": 0.0, "difference": 0.0}

        if group_column is not None:
            worst_diff = 0.0
            worst_sum = expected_sum
            for _name, grp in df.groupby(group_column):
                grp_sum = float(grp[pct_column].sum())
                diff = abs(grp_sum - expected_sum)
                if diff > worst_diff:
                    worst_diff = diff
                    worst_sum = grp_sum
            return {
                "ok": worst_diff <= tolerance,
                "actual_sum": round(worst_sum, 6),
                "difference": round(worst_diff, 6),
            }
        else:
            actual_sum = float(df[pct_column].sum())
            difference = abs(actual_sum - expected_sum)
            return {
                "ok": difference <= tolerance,
                "actual_sum": round(actual_sum, 6),
                "difference": round(difference, 6),
            }
    except Exception as e:
        _log.warning("check_failed", error=str(e))
        return {"ok": False, "actual_sum": 0.0, "difference": 0.0}


def validate_monotonic(
    df: pd.DataFrame,
    column: str,
    direction: str = "increasing",
    strict: bool = False,
) -> dict:
    """Check that a column is monotonically increasing or decreasing.

    Args:
        df: DataFrame containing the column.
        column: Column name to validate.
        direction: 'increasing' or 'decreasing'.
        strict: If True, equal consecutive values are violations.

    Returns:
        dict with keys: ok, violations_count, first_violation_index.
    """
    try:
        if df is None or len(df) < 2:
            return {"ok": True, "violations_count": 0, "first_violation_index": None}

        series = df[column].dropna()
        if len(series) < 2:
            return {"ok": True, "violations_count": 0, "first_violation_index": None}

        values = series.values
        indices = series.index.tolist()
        violations_count = 0
        first_violation_index = None

        for i in range(1, len(values)):
            if direction == "increasing":
                violation = (values[i] < values[i - 1]) if not strict else (values[i] <= values[i - 1])
            else:
                violation = (values[i] > values[i - 1]) if not strict else (values[i] >= values[i - 1])

            if violation:
                violations_count += 1
                if first_violation_index is None:
                    first_violation_index = indices[i]

        return {
            "ok": violations_count == 0,
            "violations_count": violations_count,
            "first_violation_index": first_violation_index,
        }
    except Exception as e:
        _log.warning("check_failed", error=str(e))
        return {"ok": False, "violations_count": 0, "first_violation_index": None}


def validate_trend_consistency(
    values: Union[list, np.ndarray, pd.Series],
    window: int = 3,
    max_zscore: float = 3.0,
) -> dict:
    """Check for implausible spikes/drops via rolling z-scores.

    Args:
        values: Ordered numeric sequence.
        window: Rolling window size (default 3).
        max_zscore: Threshold (default 3.0).

    Returns:
        dict with keys: ok, anomalies (list of dicts).
    """
    try:
        s = pd.Series(values, dtype=float).dropna().reset_index(drop=True)
        if len(s) <= window:
            return {"ok": True, "anomalies": []}

        rolling_mean = s.rolling(window=window, min_periods=window).mean()
        rolling_std = s.rolling(window=window, min_periods=window).std()

        anomalies: List[dict] = []
        for i in range(window, len(s)):
            rm = rolling_mean.iloc[i - 1]
            rs = rolling_std.iloc[i - 1]
            if rs is None or pd.isna(rs) or rs == 0:
                continue
            zscore = abs(s.iloc[i] - rm) / rs
            if zscore > max_zscore:
                anomalies.append({
                    "index": int(i), "value": float(s.iloc[i]),
                    "zscore": round(float(zscore), 4),
                })

        return {"ok": len(anomalies) == 0, "anomalies": anomalies}
    except Exception as e:
        _log.warning("check_failed", error=str(e))
        return {"ok": False, "anomalies": []}


def validate_ratio_bounds(
    df: pd.DataFrame,
    numerator_col: str,
    denominator_col: str,
    min_ratio: float = 0.0,
    max_ratio: float = 1.0,
) -> dict:
    """Check that computed ratios fall within given bounds.

    Args:
        df: DataFrame with numerator and denominator columns.
        numerator_col: Column name for the numerator.
        denominator_col: Column name for the denominator.
        min_ratio: Minimum acceptable ratio (default 0.0).
        max_ratio: Maximum acceptable ratio (default 1.0).

    Returns:
        dict with keys: ok, out_of_bounds_count, out_of_bounds_sample.
    """
    try:
        if df is None or len(df) == 0:
            return {"ok": True, "out_of_bounds_count": 0, "out_of_bounds_sample": []}

        denom = df[denominator_col]
        numer = df[numerator_col]
        valid_mask = (denom != 0) & denom.notna() & numer.notna()
        if valid_mask.sum() == 0:
            return {"ok": True, "out_of_bounds_count": 0, "out_of_bounds_sample": []}

        ratios = numer[valid_mask] / denom[valid_mask]
        oob_mask = (ratios < min_ratio) | (ratios > max_ratio)
        oob_count = int(oob_mask.sum())

        sample: List[dict] = []
        for idx in ratios[oob_mask].head(5).index:
            sample.append({
                "index": idx if not isinstance(idx, (np.integer,)) else int(idx),
                "ratio": round(float(ratios.loc[idx]), 6),
            })

        return {"ok": oob_count == 0, "out_of_bounds_count": oob_count,
                "out_of_bounds_sample": sample}
    except Exception as e:
        _log.warning("check_failed", error=str(e))
        return {"ok": False, "out_of_bounds_count": 0, "out_of_bounds_sample": []}


def validate_group_balance(
    df: pd.DataFrame,
    group_column: str,
    min_group_size: int = 10,
    max_imbalance_ratio: float = 100.0,
) -> dict:
    """Check that groups are not extremely imbalanced.

    Args:
        df: DataFrame containing the grouping column.
        group_column: Column defining the groups.
        min_group_size: Minimum acceptable size per group.
        max_imbalance_ratio: Maximum allowed ratio of largest to smallest.

    Returns:
        dict with keys: ok, group_sizes, imbalance_ratio.
    """
    try:
        if df is None or len(df) == 0:
            return {"ok": True, "group_sizes": {}, "imbalance_ratio": 0.0}

        counts = df[group_column].value_counts()
        group_sizes = {str(k): int(v) for k, v in counts.items()}

        if len(counts) == 0:
            return {"ok": True, "group_sizes": group_sizes, "imbalance_ratio": 0.0}

        max_size = int(counts.max())
        min_size = int(counts.min())

        if min_size == 0:
            imbalance_ratio = float("inf")
        else:
            imbalance_ratio = float(max_size) / float(min_size)

        too_small = any(v < min_group_size for v in counts.values)
        too_imbalanced = imbalance_ratio > max_imbalance_ratio

        return {
            "ok": not too_small and not too_imbalanced,
            "group_sizes": group_sizes,
            "imbalance_ratio": round(imbalance_ratio, 4),
        }
    except Exception as e:
        _log.warning("check_failed", error=str(e))
        return {"ok": False, "group_sizes": {}, "imbalance_ratio": 0.0}


def validate_no_future_dates(
    df: pd.DataFrame,
    date_column: str,
    reference_date: Optional[Union[str, datetime, pd.Timestamp]] = None,
) -> dict:
    """Check for dates that are in the future.

    Args:
        df: DataFrame containing a date/datetime column.
        date_column: Column name with date values.
        reference_date: The "now" to compare against.

    Returns:
        dict with keys: ok, future_count, max_date.
    """
    try:
        if df is None or len(df) == 0:
            return {"ok": True, "future_count": 0, "max_date": None}

        dates = pd.to_datetime(df[date_column], errors="coerce")
        ref = pd.Timestamp(reference_date) if reference_date is not None else pd.Timestamp.now()

        future_mask = dates > ref
        future_count = int(future_mask.sum())
        max_date = str(dates.max()) if dates.notna().any() else None

        return {"ok": future_count == 0, "future_count": future_count, "max_date": max_date}
    except Exception as e:
        _log.warning("check_failed", error=str(e))
        return {"ok": False, "future_count": 0, "max_date": None}


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def run_logical_checks(
    detail_df: Optional[pd.DataFrame] = None,
    summary_df: Optional[pd.DataFrame] = None,
    config: Optional[dict] = None,
) -> dict:
    """Orchestrate a set of logical validation checks.

    Args:
        detail_df: Optional detail-level DataFrame.
        summary_df: Optional summary-level DataFrame.
        config: Optional configuration dict.

    Returns:
        dict with keys: ok, checks_run, checks_passed, results.
    """
    cfg = config or {}
    results: Dict[str, Any] = {}

    metric_col = cfg.get("metric_column")
    if detail_df is not None and summary_df is not None and metric_col:
        results["aggregation_consistency"] = validate_aggregation_consistency(
            detail_df, summary_df, metric_column=metric_col,
            group_column=cfg.get("group_column"),
            tolerance=cfg.get("tolerance", 0.01),
        )

    pct_col = cfg.get("pct_column")
    working_df = detail_df if detail_df is not None else summary_df
    if working_df is not None and pct_col and pct_col in working_df.columns:
        results["percentages_sum"] = validate_percentages_sum(
            working_df, pct_column=pct_col, group_column=cfg.get("group_column"),
        )

    mono_col = cfg.get("monotonic_column")
    if working_df is not None and mono_col and mono_col in working_df.columns:
        results["monotonic"] = validate_monotonic(
            working_df, column=mono_col,
            direction=cfg.get("monotonic_direction", "increasing"),
        )

    trend_vals = cfg.get("trend_values")
    if trend_vals is not None:
        results["trend_consistency"] = validate_trend_consistency(
            trend_vals, window=cfg.get("trend_window", 3),
            max_zscore=cfg.get("trend_max_zscore", 3.0),
        )

    num_col = cfg.get("numerator_col")
    den_col = cfg.get("denominator_col")
    if working_df is not None and num_col and den_col:
        if num_col in working_df.columns and den_col in working_df.columns:
            results["ratio_bounds"] = validate_ratio_bounds(
                working_df, numerator_col=num_col, denominator_col=den_col,
                min_ratio=cfg.get("min_ratio", 0.0),
                max_ratio=cfg.get("max_ratio", 1.0),
            )

    bal_col = cfg.get("balance_column")
    if working_df is not None and bal_col and bal_col in working_df.columns:
        results["group_balance"] = validate_group_balance(
            working_df, group_column=bal_col,
            min_group_size=cfg.get("min_group_size", 10),
            max_imbalance_ratio=cfg.get("max_imbalance_ratio", 100.0),
        )

    date_col = cfg.get("date_column")
    if working_df is not None and date_col and date_col in working_df.columns:
        results["no_future_dates"] = validate_no_future_dates(
            working_df, date_column=date_col,
            reference_date=cfg.get("reference_date"),
        )

    checks_run = len(results)
    checks_passed = sum(1 for r in results.values() if r.get("ok", False))

    return {
        "ok": checks_run > 0 and checks_passed == checks_run,
        "checks_run": checks_run,
        "checks_passed": checks_passed,
        "results": results,
    }


# ===================================================================
# LEGACY API
# ===================================================================

def validate_trend_continuity(
    series: Union[list, np.ndarray, pd.Series],
    max_gap_pct: float = 0.5,
) -> dict:
    """Check for sudden jumps in a numeric series (legacy API).

    Returns:
        dict with keys: valid, breaks, severity.
    """
    s = pd.Series(series).dropna()
    if len(s) < 2:
        return {"valid": True, "breaks": [], "severity": "PASS"}

    breaks: List[dict] = []
    values = s.values
    indices = s.index.tolist()

    for i in range(1, len(values)):
        prev_val = float(values[i - 1])
        curr_val = float(values[i])

        if prev_val == 0:
            if curr_val != 0:
                breaks.append({
                    "index": indices[i], "prev_value": prev_val,
                    "curr_value": curr_val, "change_pct": float("inf"),
                })
            continue

        change_pct = abs(curr_val - prev_val) / abs(prev_val)
        if change_pct > max_gap_pct:
            breaks.append({
                "index": indices[i], "prev_value": prev_val,
                "curr_value": curr_val, "change_pct": round(change_pct, 6),
            })

    if len(breaks) == 0:
        severity = "PASS"
    elif len(breaks) <= 2:
        severity = "WARNING"
    else:
        severity = "BLOCKER"

    return {"valid": severity == "PASS", "breaks": breaks, "severity": severity}


def validate_segment_exhaustiveness(
    df: pd.DataFrame,
    segment_col: str,
    metric_col: str,
) -> dict:
    """Verify segments are mutually exclusive and collectively exhaustive (legacy).

    Returns:
        dict with keys: valid, segment_sum, total, diff_pct, missing_rows, severity.
    """
    if len(df) == 0:
        return {"valid": True, "segment_sum": 0.0, "total": 0.0,
                "diff_pct": 0.0, "missing_rows": 0, "severity": "PASS"}

    total = float(df[metric_col].sum())
    segment_sum = float(df.groupby(segment_col)[metric_col].sum().sum())

    denominator = abs(total) if total != 0 else abs(segment_sum)
    diff_pct = abs(segment_sum - total) / denominator if denominator != 0 else 0.0

    null_segment_mask = df[segment_col].isna()
    missing_rows = int(null_segment_mask.sum())

    if diff_pct > 0.01 or missing_rows > 0:
        severity = "BLOCKER"
    elif diff_pct > 0.001:
        severity = "WARNING"
    else:
        severity = "PASS"

    return {
        "valid": severity == "PASS",
        "segment_sum": round(segment_sum, 6),
        "total": round(total, 6),
        "diff_pct": round(diff_pct, 6),
        "missing_rows": missing_rows,
        "severity": severity,
    }


def validate_temporal_consistency(
    df: pd.DataFrame,
    date_col: str,
    metric_col: str,
    expected_freq: str = "D",
) -> dict:
    """Check for missing/duplicate dates and zero-value gaps (legacy).

    Returns:
        dict with keys: valid, missing_dates, duplicate_dates, zero_dates, severity.
    """
    if len(df) == 0:
        return {"valid": True, "missing_dates": [], "duplicate_dates": [],
                "zero_dates": [], "severity": "PASS"}

    dates = pd.to_datetime(df[date_col])

    date_counts = dates.value_counts()
    duplicate_dates = sorted(
        str(d.date()) if hasattr(d, "date") else str(d)
        for d in date_counts[date_counts > 1].index
    )

    min_date = dates.min()
    max_date = dates.max()

    if min_date == max_date:
        return {
            "valid": len(duplicate_dates) == 0,
            "missing_dates": [], "duplicate_dates": duplicate_dates,
            "zero_dates": [],
            "severity": "WARNING" if duplicate_dates else "PASS",
        }

    expected_range = pd.date_range(start=min_date, end=max_date, freq=expected_freq)
    actual_dates = set(dates.dt.normalize())
    expected_dates = set(expected_range.normalize())
    missing = sorted(expected_dates - actual_dates)
    missing_dates = [str(d.date()) for d in missing]

    working = df.copy()
    working["_parsed_date"] = dates
    working = working.sort_values("_parsed_date")

    inner = working.iloc[1:-1] if len(working) > 2 else pd.DataFrame()
    zero_dates: List[str] = []
    if len(inner) > 0:
        zero_mask = inner[metric_col].isna() | (inner[metric_col] == 0)
        zero_dates = sorted(
            str(d.date()) if hasattr(d, "date") else str(d)
            for d in inner.loc[zero_mask, "_parsed_date"]
        )

    n_issues = len(missing_dates) + len(duplicate_dates) + len(zero_dates)
    total_expected = len(expected_range)
    issue_rate = n_issues / total_expected if total_expected > 0 else 0.0

    if len(duplicate_dates) > 0 or issue_rate > 0.1:
        severity = "BLOCKER"
    elif n_issues > 0:
        severity = "WARNING"
    else:
        severity = "PASS"

    return {
        "valid": severity == "PASS",
        "missing_dates": missing_dates,
        "duplicate_dates": duplicate_dates,
        "zero_dates": zero_dates,
        "severity": severity,
    }
