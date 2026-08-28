"""
Business Rules Validation Helpers (Layer 3 — Plausibility).

Validates analytical results against business plausibility: value ranges,
metric relationships, temporal consistency, segment coverage, non-negativity,
cardinality, and computed rates.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Range validation
# ---------------------------------------------------------------------------

def validate_ranges(df: pd.DataFrame, rules: List[dict]) -> dict:
    """Check values against business-defined min/max ranges.

    Args:
        df: DataFrame to validate.
        rules: List of dicts with keys: column, min, max, label.

    Returns:
        dict with keys: ok, valid, violations.
    """
    if df is None or len(df) == 0 or not rules:
        return {"ok": True, "valid": True, "violations": []}

    violations: List[dict] = []
    for rule in rules:
        col = rule["column"]
        label = rule.get("label", rule.get("name", col))
        rule_min = rule.get("min")
        rule_max = rule.get("max")

        if col not in df.columns:
            violations.append({
                "column": col, "value": None, "rule": label, "count": 0,
                "out_of_range_pct": 0.0, "min_seen": None, "max_seen": None,
                "severity": "WARNING", "rule_name": label, "out_of_range_count": 0,
            })
            continue

        series = df[col].dropna()
        n = len(series)
        if n == 0:
            violations.append({
                "column": col, "value": None, "rule": label, "count": 0,
                "out_of_range_pct": 0.0, "min_seen": None, "max_seen": None,
                "severity": "WARNING", "rule_name": label, "out_of_range_count": 0,
            })
            continue

        mask = pd.Series(False, index=series.index)
        if rule_min is not None:
            mask = mask | (series < rule_min)
        if rule_max is not None:
            mask = mask | (series > rule_max)

        out_count = int(mask.sum())
        out_pct = float(out_count / n)
        min_seen = float(series.min())
        max_seen = float(series.max())
        value = float(series[mask].iloc[0]) if out_count > 0 else None

        if out_pct > 0.05:
            severity = "BLOCKER"
        elif out_count > 0:
            severity = "WARNING"
        else:
            severity = "PASS"

        violations.append({
            "column": col, "value": value, "rule": label, "count": out_count,
            "out_of_range_pct": round(out_pct, 6), "min_seen": min_seen,
            "max_seen": max_seen, "severity": severity,
            "rule_name": label, "out_of_range_count": out_count,
        })

    any_fail = any(v["count"] > 0 for v in violations)
    ok = not any_fail
    return {"ok": ok, "valid": ok, "violations": violations}


# ---------------------------------------------------------------------------
# Metric relationship validation
# ---------------------------------------------------------------------------

def validate_metric_relationships(
    metrics_dict: dict,
    rules: Optional[List[dict]] = None,
) -> dict:
    """Check relationships between metrics.

    Args:
        metrics_dict: Dict mapping metric names to numeric values.
        rules: List of relationship rules with left, right, tolerance.

    Returns:
        dict with keys: ok, violations.
    """
    if rules is None:
        rules = [{"left": "aov * orders", "right": "revenue", "tolerance": 0.05}]

    if not rules or not metrics_dict:
        return {"ok": True, "violations": []}

    violations: List[dict] = []
    for rule in rules:
        left_expr = rule["left"]
        right_expr = rule["right"]
        tolerance = rule.get("tolerance", 0.05)

        try:
            left_val = _eval_metric_expr(left_expr, metrics_dict)
            right_val = _eval_metric_expr(right_expr, metrics_dict)
        except (KeyError, TypeError, ValueError, ZeroDivisionError):
            continue

        if left_val is None or right_val is None:
            continue

        denom = abs(right_val) if right_val != 0 else abs(left_val)
        diff_pct = abs(left_val - right_val) / denom if denom != 0 else 0.0

        if diff_pct > tolerance:
            violations.append({
                "left_expr": left_expr, "right_expr": right_expr,
                "left_value": round(left_val, 6), "right_value": round(right_val, 6),
                "diff_pct": round(diff_pct, 6), "tolerance": tolerance,
            })

    return {"ok": len(violations) == 0, "violations": violations}


def _eval_metric_expr(expr: str, metrics: dict) -> Optional[float]:
    """Safely evaluate a simple arithmetic expression with metric names."""
    safe_expr = expr.strip()
    sorted_names = sorted(metrics.keys(), key=len, reverse=True)
    for name in sorted_names:
        val = metrics[name]
        if val is None or (isinstance(val, float) and np.isnan(val)):
            return None
        safe_expr = safe_expr.replace(name, str(float(val)))

    allowed = set("0123456789.+-*/ ()")
    if not all(c in allowed for c in safe_expr):
        return None

    try:
        result = eval(safe_expr, {"__builtins__": {}}, {})  # noqa: S307
        return float(result)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Temporal consistency (period-over-period)
# ---------------------------------------------------------------------------

def validate_temporal_consistency(
    df: pd.DataFrame,
    date_column: str,
    metric_column: str,
    max_period_change_pct: float = 200,
) -> dict:
    """Check that period-over-period changes are not implausibly large.

    Args:
        df: DataFrame with date and metric columns.
        date_column: Column containing date/datetime values.
        metric_column: Column containing the metric to check.
        max_period_change_pct: Maximum allowed change percentage.

    Returns:
        dict with keys: ok, large_changes.
    """
    if df is None or len(df) < 2:
        return {"ok": True, "large_changes": []}

    if date_column not in df.columns or metric_column not in df.columns:
        return {"ok": True, "large_changes": []}

    working = df[[date_column, metric_column]].dropna().copy()
    if len(working) < 2:
        return {"ok": True, "large_changes": []}

    working = working.sort_values(date_column).reset_index(drop=True)

    large_changes: List[dict] = []
    values = working[metric_column].values
    dates = working[date_column].values

    for i in range(1, len(values)):
        prev = float(values[i - 1])
        curr = float(values[i])

        if prev == 0:
            if curr != 0:
                large_changes.append({
                    "date": _format_date(dates[i]),
                    "previous": prev, "current": curr,
                    "change_pct": float("inf"),
                })
            continue

        change_pct = abs((curr - prev) / prev) * 100
        if change_pct > max_period_change_pct:
            large_changes.append({
                "date": _format_date(dates[i]),
                "previous": round(prev, 6), "current": round(curr, 6),
                "change_pct": round(change_pct, 2),
            })

    return {"ok": len(large_changes) == 0, "large_changes": large_changes}


def _format_date(val: Any) -> str:
    """Convert a date-like value to string."""
    if hasattr(val, "isoformat"):
        return val.isoformat()
    if isinstance(val, np.datetime64):
        ts = pd.Timestamp(val)
        return ts.isoformat()
    return str(val)


# ---------------------------------------------------------------------------
# Segment coverage
# ---------------------------------------------------------------------------

def validate_segment_coverage(
    df: pd.DataFrame,
    segment_column: str,
    expected_segments: Optional[List[str]] = None,
    allow_other: bool = True,
) -> dict:
    """Check that expected segments are present.

    Args:
        df: DataFrame to validate.
        segment_column: Column containing segment values.
        expected_segments: Expected segment values.
        allow_other: If True, unexpected segments are not violations.

    Returns:
        dict with keys: ok, missing_segments, unexpected_segments.
    """
    if df is None or len(df) == 0:
        missing = list(expected_segments) if expected_segments else []
        return {"ok": len(missing) == 0, "missing_segments": missing,
                "unexpected_segments": []}

    if segment_column not in df.columns:
        missing = list(expected_segments) if expected_segments else []
        return {"ok": len(missing) == 0, "missing_segments": missing,
                "unexpected_segments": []}

    actual = set(df[segment_column].dropna().unique())

    if expected_segments is None:
        return {"ok": True, "missing_segments": [], "unexpected_segments": []}

    expected_set = set(expected_segments)
    missing = sorted(expected_set - actual)
    unexpected = sorted(actual - expected_set)

    if allow_other:
        ok = len(missing) == 0
    else:
        ok = len(missing) == 0 and len(unexpected) == 0

    return {"ok": ok, "missing_segments": missing, "unexpected_segments": unexpected}


# ---------------------------------------------------------------------------
# Non-negative validation
# ---------------------------------------------------------------------------

def validate_no_negative(df: pd.DataFrame, columns: List[str]) -> dict:
    """Check that specified columns contain no negative values.

    Args:
        df: DataFrame to validate.
        columns: List of column names to check.

    Returns:
        dict with keys: ok, violations.
    """
    if df is None or len(df) == 0 or not columns:
        return {"ok": True, "violations": []}

    violations: List[dict] = []
    for col in columns:
        if col not in df.columns:
            continue
        series = df[col].dropna()
        if len(series) == 0:
            continue
        neg_mask = series < 0
        neg_count = int(neg_mask.sum())
        if neg_count > 0:
            violations.append({
                "column": col, "negative_count": neg_count,
                "min_value": float(series.min()),
            })

    return {"ok": len(violations) == 0, "violations": violations}


# ---------------------------------------------------------------------------
# Cardinality validation
# ---------------------------------------------------------------------------

def validate_cardinality(
    df: pd.DataFrame,
    column: str,
    expected_min: Optional[int] = None,
    expected_max: Optional[int] = None,
) -> dict:
    """Check that distinct value count is within expected bounds.

    Args:
        df: DataFrame to validate.
        column: Column name to check.
        expected_min: Minimum expected distinct count.
        expected_max: Maximum expected distinct count.

    Returns:
        dict with keys: ok, actual_cardinality, message.
    """
    if df is None or len(df) == 0:
        return {"ok": True, "actual_cardinality": 0,
                "message": "Empty DataFrame."}

    if column not in df.columns:
        return {"ok": False, "actual_cardinality": 0,
                "message": f"Column '{column}' not found."}

    cardinality = int(df[column].nunique())

    issues: List[str] = []
    if expected_min is not None and cardinality < expected_min:
        issues.append(f"Cardinality {cardinality} below minimum {expected_min}.")
    if expected_max is not None and cardinality > expected_max:
        issues.append(f"Cardinality {cardinality} exceeds maximum {expected_max}.")

    if issues:
        return {"ok": False, "actual_cardinality": cardinality,
                "message": " ".join(issues)}

    return {"ok": True, "actual_cardinality": cardinality,
            "message": f"Cardinality {cardinality} within bounds."}


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def validate_business_rules(df: pd.DataFrame, rules_config: dict) -> dict:
    """Run all applicable business rule validations.

    Args:
        df: DataFrame to validate.
        rules_config: Dict specifying which checks to run.

    Returns:
        dict with keys: ok, results, summary.
    """
    results: Dict[str, dict] = {}
    all_ok = True

    if "ranges" in rules_config:
        result = validate_ranges(df, rules_config["ranges"])
        results["ranges"] = result
        if not result["ok"]:
            all_ok = False

    if "no_negative" in rules_config:
        result = validate_no_negative(df, rules_config["no_negative"])
        results["no_negative"] = result
        if not result["ok"]:
            all_ok = False

    if "segment_coverage" in rules_config:
        sc = rules_config["segment_coverage"]
        result = validate_segment_coverage(
            df, segment_column=sc["segment_column"],
            expected_segments=sc.get("expected_segments"),
            allow_other=sc.get("allow_other", True),
        )
        results["segment_coverage"] = result
        if not result["ok"]:
            all_ok = False

    if "temporal" in rules_config:
        tc = rules_config["temporal"]
        result = validate_temporal_consistency(
            df, date_column=tc["date_column"],
            metric_column=tc["metric_column"],
            max_period_change_pct=tc.get("max_period_change_pct", 200),
        )
        results["temporal"] = result
        if not result["ok"]:
            all_ok = False

    if "cardinality" in rules_config:
        for card_rule in rules_config["cardinality"]:
            col = card_rule["column"]
            result = validate_cardinality(
                df, col, expected_min=card_rule.get("expected_min"),
                expected_max=card_rule.get("expected_max"),
            )
            results[f"cardinality_{col}"] = result
            if not result["ok"]:
                all_ok = False

    if "metric_relationships" in rules_config:
        mr = rules_config["metric_relationships"]
        result = validate_metric_relationships(
            mr.get("metrics_dict", {}), rules=mr.get("rules"),
        )
        results["metric_relationships"] = result
        if not result["ok"]:
            all_ok = False

    failed = [k for k, v in results.items() if not v.get("ok", True)]
    summary = (
        f"Business rules: {len(failed)} check(s) failed -- {', '.join(failed)}."
        if failed else f"Business rules: all {len(results)} check(s) passed."
    )

    return {"ok": all_ok, "results": results, "summary": summary}


def get_default_rules() -> dict:
    """Return common-sense default rules for typical product analytics."""
    return {
        "ranges": [
            {"column": "conversion_rate", "min": 0, "max": 1, "label": "Conversion Rate"},
            {"column": "bounce_rate", "min": 0, "max": 1, "label": "Bounce Rate"},
            {"column": "click_through_rate", "min": 0, "max": 1, "label": "CTR"},
            {"column": "retention_rate", "min": 0, "max": 1, "label": "Retention Rate"},
            {"column": "churn_rate", "min": 0, "max": 1, "label": "Churn Rate"},
            {"column": "nps_score", "min": -100, "max": 100, "label": "NPS Score"},
        ],
        "no_negative": [
            "revenue", "orders", "sessions", "users",
            "page_views", "transactions", "quantity",
        ],
        "cardinality": [
            {"column": "device", "expected_min": 2, "expected_max": 10},
            {"column": "country", "expected_min": 1, "expected_max": 300},
        ],
    }


# ---------------------------------------------------------------------------
# Rate validation (legacy)
# ---------------------------------------------------------------------------

def validate_rates(
    df: pd.DataFrame,
    numerator_col: str,
    denominator_col: str,
    expected_range: Tuple[float, float] = (0, 1),
    name: str = "rate",
) -> dict:
    """Validate a computed rate (numerator / denominator).

    Returns:
        dict with keys: valid, out_of_range_count, zero_denominator_count,
        rate_stats, severity.
    """
    if len(df) == 0:
        return {
            "valid": True, "out_of_range_count": 0,
            "zero_denominator_count": 0,
            "rate_stats": {"mean": None, "median": None, "min": None, "max": None},
            "severity": "PASS",
        }

    denom = df[denominator_col]
    zero_denom_mask = (denom == 0) | denom.isna()
    zero_denominator_count = int(zero_denom_mask.sum())

    valid_mask = ~zero_denom_mask
    if valid_mask.sum() == 0:
        return {
            "valid": False, "out_of_range_count": 0,
            "zero_denominator_count": zero_denominator_count,
            "rate_stats": {"mean": None, "median": None, "min": None, "max": None},
            "severity": "BLOCKER",
        }

    rates = df.loc[valid_mask, numerator_col] / df.loc[valid_mask, denominator_col]
    rates = rates.dropna()

    range_min, range_max = expected_range
    out_of_range_mask = (rates < range_min) | (rates > range_max)
    out_of_range_count = int(out_of_range_mask.sum())

    rate_stats = {
        "mean": round(float(rates.mean()), 6),
        "median": round(float(rates.median()), 6),
        "min": round(float(rates.min()), 6),
        "max": round(float(rates.max()), 6),
    }

    out_of_range_pct = out_of_range_count / len(rates) if len(rates) > 0 else 0.0
    if zero_denominator_count > 0 and out_of_range_pct > 0.05:
        severity = "BLOCKER"
    elif out_of_range_count > 0 or zero_denominator_count > 0:
        severity = "WARNING"
    else:
        severity = "PASS"

    return {
        "valid": severity == "PASS",
        "out_of_range_count": out_of_range_count,
        "zero_denominator_count": zero_denominator_count,
        "rate_stats": rate_stats, "severity": severity,
    }


# ---------------------------------------------------------------------------
# YoY change validation (legacy)
# ---------------------------------------------------------------------------

def validate_yoy_change(
    current_value: Optional[float],
    prior_value: Optional[float],
    max_change_pct: float = 2.0,
    metric_name: str = "metric",
) -> dict:
    """Flag implausible year-over-year changes.

    Returns:
        dict with keys: valid, change_pct, direction, severity, interpretation.
    """
    if current_value is None or prior_value is None:
        return {
            "valid": False, "change_pct": None, "direction": "flat",
            "severity": "WARNING",
            "interpretation": f"Cannot compute YoY for {metric_name} — missing value(s).",
        }

    current_value = float(current_value)
    prior_value = float(prior_value)

    if np.isnan(current_value) or np.isnan(prior_value):
        return {
            "valid": False, "change_pct": None, "direction": "flat",
            "severity": "WARNING",
            "interpretation": f"Cannot compute YoY for {metric_name} — NaN value(s).",
        }

    if prior_value == 0:
        if current_value == 0:
            return {
                "valid": True, "change_pct": 0.0, "direction": "flat",
                "severity": "PASS",
                "interpretation": f"{metric_name}: no change (both zero).",
            }
        return {
            "valid": False, "change_pct": float("inf"),
            "direction": "up" if current_value > 0 else "down",
            "severity": "BLOCKER",
            "interpretation": f"{metric_name}: prior is zero, current is {current_value:,.2f}.",
        }

    change = (current_value - prior_value) / abs(prior_value)
    change_pct = round(abs(change), 6)
    direction = "up" if change > 0 else ("down" if change < 0 else "flat")

    if change_pct > max_change_pct:
        severity = "BLOCKER"
        interpretation = (
            f"{metric_name}: {direction} {change_pct:.1%} YoY "
            f"({prior_value:,.2f} -> {current_value:,.2f}). "
            f"Exceeds {max_change_pct:.0%} threshold."
        )
    elif change_pct > max_change_pct * 0.5:
        severity = "WARNING"
        interpretation = (
            f"{metric_name}: {direction} {change_pct:.1%} YoY "
            f"({prior_value:,.2f} -> {current_value:,.2f}). Large change."
        )
    else:
        severity = "PASS"
        interpretation = (
            f"{metric_name}: {direction} {change_pct:.1%} YoY "
            f"({prior_value:,.2f} -> {current_value:,.2f}). Within range."
        )

    return {
        "valid": severity == "PASS", "change_pct": change_pct,
        "direction": direction, "severity": severity,
        "interpretation": interpretation,
    }
