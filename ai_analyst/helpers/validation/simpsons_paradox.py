"""
Simpson's Paradox Scanner (Layer 4).

Scans analytical results for Simpson's Paradox — where a trend in
aggregated data reverses when split into segments.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _determine_direction(value_a: float, value_b: float) -> str:
    """Compare two values and return a direction label."""
    if value_a > value_b:
        return "positive"
    elif value_a < value_b:
        return "negative"
    return "neutral"


def _compute_severity(n_reversals: int, n_total_segments: int) -> str:
    """Compute severity based on reversal ratio."""
    if n_total_segments == 0 or n_reversals == 0:
        return "none"
    ratio = n_reversals / n_total_segments
    if ratio <= 0.25:
        return "low"
    elif ratio <= 0.5:
        return "medium"
    return "high"


def _resolve_comparison_groups(series: pd.Series):
    """Identify the two comparison groups from a column."""
    if pd.api.types.is_numeric_dtype(series) and series.nunique() > 2:
        median_val = series.median()
        mask_a = series <= median_val
        mask_b = series > median_val
        return f"<= {median_val}", f"> {median_val}", mask_a, mask_b

    counts = series.value_counts()
    if len(counts) < 2:
        return None, None, None, None

    label_a = counts.index[0]
    label_b = counts.index[1]
    return label_a, label_b, series == label_a, series == label_b


def _empty_result(message: str) -> dict:
    """Return a default result dict for edge cases."""
    return {
        "paradox_detected": False, "aggregate_direction": "neutral",
        "segment_results": [], "reversals": [],
        "explanation": message, "severity": "none",
    }


# ---------------------------------------------------------------------------
# Core paradox check
# ---------------------------------------------------------------------------

def check_simpsons_paradox(
    df: pd.DataFrame,
    metric_column: Optional[str] = None,
    segment_column: Optional[str] = None,
    comparison_column: Optional[str] = None,
    agg_func: str = "mean",
    metric_col: Optional[str] = None,
    group_col: Optional[str] = None,
    segment_col: Optional[str] = None,
) -> dict:
    """Check for Simpson's Paradox across a single segmentation dimension.

    Supports both new API (metric_column, segment_column, comparison_column)
    and legacy API (metric_col, group_col, segment_col).

    Args:
        df: DataFrame containing the data.
        metric_column: Numeric metric column.
        segment_column: Column to segment by.
        comparison_column: Binary/categorical grouping column.
        agg_func: Aggregation function — "mean" or "sum".

    Returns:
        dict with keys: paradox_detected, aggregate_direction,
        segment_results, reversals, explanation, severity.
    """
    _metric = metric_column or metric_col
    _comparison = comparison_column or group_col
    _segment = segment_column or segment_col
    _is_legacy = metric_col is not None or group_col is not None

    if _metric is None or _comparison is None or _segment is None:
        return _empty_result("Missing required parameters.")

    if len(df) == 0:
        return _empty_result("DataFrame is empty.")

    working = df.dropna(subset=[_metric, _comparison, _segment])
    if len(working) < 2:
        return _empty_result("Insufficient non-null data.")

    label_a, label_b, mask_a, mask_b = _resolve_comparison_groups(working[_comparison])
    if label_a is None:
        return _empty_result(f"Only one group in '{_comparison}'.")

    subset = working[mask_a | mask_b].copy()
    agg_fn = np.mean if agg_func == "mean" else np.sum

    agg_a = float(agg_fn(subset.loc[mask_a[subset.index], _metric]))
    agg_b = float(agg_fn(subset.loc[mask_b[subset.index], _metric]))
    aggregate_direction = _determine_direction(agg_a, agg_b)

    segment_results: List[dict] = []
    for segment_value, seg_df in subset.groupby(_segment):
        if isinstance(label_a, str) and ("<=" in str(label_a) or ">" in str(label_a)):
            seg_mask_a = mask_a[seg_df.index]
            seg_mask_b = mask_b[seg_df.index]
        else:
            seg_mask_a = seg_df[_comparison] == label_a
            seg_mask_b = seg_df[_comparison] == label_b

        vals_a = seg_df.loc[seg_mask_a, _metric]
        vals_b = seg_df.loc[seg_mask_b, _metric]

        if len(vals_a) == 0 or len(vals_b) == 0:
            continue

        seg_val_a = float(agg_fn(vals_a))
        seg_val_b = float(agg_fn(vals_b))
        seg_direction = _determine_direction(seg_val_a, seg_val_b)

        segment_results.append({
            "segment": segment_value, "direction": seg_direction,
            "value_a": round(seg_val_a, 6), "value_b": round(seg_val_b, 6),
        })

    non_neutral = [s for s in segment_results if s["direction"] != "neutral"]

    if len(non_neutral) == 0 or aggregate_direction == "neutral":
        result = {
            "paradox_detected": False,
            "aggregate_direction": aggregate_direction,
            "segment_results": segment_results, "reversals": [],
            "explanation": f"No directional comparison possible.",
            "severity": "none",
        }
        if _is_legacy:
            result.update(_legacy_fields(result))
        return result

    reversals = [
        s["segment"] for s in non_neutral
        if s["direction"] != aggregate_direction
    ]
    agree_count = len(non_neutral) - len(reversals)
    paradox_detected = len(reversals) > agree_count
    severity = _compute_severity(len(reversals), len(non_neutral))

    if paradox_detected:
        explanation = (
            f"Simpson's Paradox detected on '{_segment}'. "
            f"Aggregate: {label_a} {'>' if aggregate_direction == 'positive' else '<'} "
            f"{label_b} ({agg_func} {_metric}: {agg_a:.4f} vs {agg_b:.4f}). "
            f"But in {len(reversals)} of {len(non_neutral)} segments, "
            f"direction reverses. Reversing: {reversals}."
        )
    else:
        explanation = (
            f"No paradox on '{_segment}'. "
            f"{agree_count} of {len(non_neutral)} segments agree."
        )
        if reversals:
            explanation += f" Note: {len(reversals)} reversal(s): {reversals}."

    result = {
        "paradox_detected": paradox_detected,
        "aggregate_direction": aggregate_direction,
        "segment_results": segment_results,
        "reversals": reversals,
        "explanation": explanation,
        "severity": severity,
    }

    if _is_legacy:
        result.update(_legacy_fields(result))

    return result


def _legacy_fields(result: dict) -> dict:
    """Map new-style result keys to legacy field names."""
    direction_map = {"positive": "A>B", "negative": "B>A", "neutral": "equal"}

    legacy_segment_directions = []
    for seg in result.get("segment_results", []):
        legacy_segment_directions.append({
            "segment": seg["segment"],
            "direction": direction_map.get(seg["direction"], seg["direction"]),
            "group_a_val": seg["value_a"], "group_b_val": seg["value_b"],
        })

    if result["paradox_detected"]:
        legacy_severity = "BLOCKER"
    elif len(result.get("reversals", [])) > 0:
        legacy_severity = "INFO"
    else:
        legacy_severity = "PASS"

    return {
        "aggregate_direction": direction_map.get(
            result["aggregate_direction"], result["aggregate_direction"]
        ),
        "segment_directions": legacy_segment_directions,
        "reversal_segments": result.get("reversals", []),
        "severity": legacy_severity,
    }


# ---------------------------------------------------------------------------
# Multi-segment scanner
# ---------------------------------------------------------------------------

def check_simpsons_multi_segment(
    df: pd.DataFrame,
    metric_column: str,
    segment_columns: List[str],
    comparison_column: str,
    agg_func: str = "mean",
) -> dict:
    """Run the paradox check across multiple segmentation dimensions.

    Args:
        df: DataFrame containing the data.
        metric_column: Numeric metric column.
        segment_columns: List of segment column names.
        comparison_column: Grouping column.
        agg_func: "mean" or "sum".

    Returns:
        dict with keys: scanned, paradoxes_found, results, interpretation.
    """
    if not segment_columns:
        return {"scanned": 0, "paradoxes_found": 0, "results": {},
                "interpretation": "No segment columns provided."}

    results: Dict[str, dict] = {}
    paradox_count = 0

    for seg_col in segment_columns:
        if seg_col not in df.columns:
            results[seg_col] = _empty_result(f"Column '{seg_col}' not found.")
            continue

        result = check_simpsons_paradox(
            df, metric_column=metric_column, segment_column=seg_col,
            comparison_column=comparison_column, agg_func=agg_func,
        )
        results[seg_col] = result
        if result["paradox_detected"]:
            paradox_count += 1

    if paradox_count == 0:
        interpretation = (
            f"Scanned {len(segment_columns)} dimension(s) — none detected."
        )
    else:
        paradox_dims = [
            col for col in segment_columns
            if results.get(col, {}).get("paradox_detected", False)
        ]
        interpretation = (
            f"Simpson's Paradox in {paradox_count} of "
            f"{len(segment_columns)} dimension(s): {paradox_dims}."
        )

    return {
        "scanned": len(segment_columns), "paradoxes_found": paradox_count,
        "results": results, "interpretation": interpretation,
    }


# ---------------------------------------------------------------------------
# Weighted vs unweighted comparison
# ---------------------------------------------------------------------------

def weighted_vs_unweighted(
    df: pd.DataFrame,
    metric_column: str,
    weight_column: str,
    segment_column: str,
) -> dict:
    """Compare weighted average vs unweighted average per segment.

    Args:
        df: DataFrame containing the data.
        metric_column: Column with the metric values.
        weight_column: Column with the weights.
        segment_column: Column defining the segments.

    Returns:
        dict with keys: paradox_detected, weighted_result,
        unweighted_result, difference, segment_details, explanation.
    """
    working = df.dropna(subset=[metric_column, weight_column, segment_column])

    if len(working) == 0:
        return {
            "paradox_detected": False, "weighted_result": None,
            "unweighted_result": None, "difference": 0.0,
            "segment_details": [], "explanation": "No valid data.",
        }

    valid_weights = working[working[weight_column] > 0].copy()
    if len(valid_weights) == 0:
        return {
            "paradox_detected": False, "weighted_result": None,
            "unweighted_result": None, "difference": 0.0,
            "segment_details": [], "explanation": "All weights zero/negative.",
        }

    segment_details: List[dict] = []
    segment_means: List[float] = []

    for seg_val, seg_df in valid_weights.groupby(segment_column):
        seg_mean = float(seg_df[metric_column].mean())
        seg_weight_sum = float(seg_df[weight_column].sum())
        seg_weighted_mean = float(
            np.average(seg_df[metric_column], weights=seg_df[weight_column])
        )
        segment_details.append({
            "segment": seg_val, "mean": seg_mean,
            "weighted_mean": seg_weighted_mean,
            "total_weight": seg_weight_sum, "count": len(seg_df),
        })
        segment_means.append(seg_mean)

    weighted_result = float(
        np.average(valid_weights[metric_column], weights=valid_weights[weight_column])
    )
    unweighted_result = float(np.mean(segment_means))
    difference = weighted_result - unweighted_result

    paradox_detected = (
        abs(difference) > 0.01 * max(abs(weighted_result), abs(unweighted_result), 1e-9)
    )

    if paradox_detected:
        explanation = (
            f"Weighted ({weighted_result:.4f}) differs from unweighted "
            f"({unweighted_result:.4f}) by {difference:.4f}. "
            f"Segment size imbalance may be influencing results."
        )
    else:
        explanation = (
            f"Weighted ({weighted_result:.4f}) and unweighted "
            f"({unweighted_result:.4f}) are consistent."
        )

    return {
        "paradox_detected": paradox_detected,
        "weighted_result": weighted_result,
        "unweighted_result": unweighted_result,
        "difference": difference,
        "segment_details": segment_details,
        "explanation": explanation,
    }


# ---------------------------------------------------------------------------
# Report generator
# ---------------------------------------------------------------------------

def generate_paradox_report(check_result: dict) -> str:
    """Format a check result into a markdown report.

    Args:
        check_result: Dict from check_simpsons_paradox or multi_segment.

    Returns:
        str: Markdown-formatted report.
    """
    lines = ["## Simpson's Paradox Check", ""]

    if "scanned" in check_result:
        lines.append(f"**Dimensions scanned:** {check_result['scanned']}")
        lines.append(f"**Paradoxes found:** {check_result['paradoxes_found']}")
        lines.append("")
        lines.append(check_result.get("interpretation", ""))
        lines.append("")

        results = check_result.get("results", {})
        if isinstance(results, dict):
            for col_name, res in results.items():
                lines.append(f"### Segment: {col_name}")
                lines.append("")
                lines.append(_format_single_result(res))
                lines.append("")
        return "\n".join(lines)

    lines.append(_format_single_result(check_result))
    return "\n".join(lines)


def _format_single_result(result: dict) -> str:
    """Format a single paradox check result as markdown."""
    lines: List[str] = []
    detected = result.get("paradox_detected", False)
    status = "DETECTED" if detected else "NOT DETECTED"
    severity = result.get("severity", "none")

    lines.append(f"**Status:** {status}")
    lines.append(f"**Severity:** {severity}")
    lines.append(f"**Aggregate direction:** {result.get('aggregate_direction', 'N/A')}")
    lines.append("")

    segment_results = result.get("segment_results", [])
    if segment_results:
        lines.append("| Segment | Direction | Value A | Value B |")
        lines.append("|---------|-----------|---------|---------|")
        for seg in segment_results:
            lines.append(
                f"| {seg['segment']} | {seg['direction']} "
                f"| {seg['value_a']:.4f} | {seg['value_b']:.4f} |"
            )
        lines.append("")

    reversals = result.get("reversals", [])
    if reversals:
        lines.append(f"**Reversals:** {', '.join(str(r) for r in reversals)}")
        lines.append("")

    explanation = result.get("explanation", "")
    if explanation:
        lines.append(f"> {explanation}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Segment suggestion heuristic
# ---------------------------------------------------------------------------

def suggest_segments_to_check(
    df: pd.DataFrame,
    metric_column: str,
    categorical_columns: Optional[List[str]] = None,
    max_segments: int = 5,
) -> List[str]:
    """Identify segment columns most likely to reveal paradoxes.

    Args:
        df: DataFrame to analyze.
        metric_column: The metric column.
        categorical_columns: Explicit list of columns to consider.
        max_segments: Maximum number of suggestions to return.

    Returns:
        List of column names ranked by likelihood, most likely first.
    """
    if metric_column not in df.columns:
        return []

    if categorical_columns is None:
        candidates = [
            col for col in df.columns
            if col != metric_column
            and (df[col].dtype == "object" or df[col].dtype.name == "category"
                 or pd.api.types.is_bool_dtype(df[col]))
        ]
    else:
        candidates = [
            col for col in categorical_columns
            if col in df.columns and col != metric_column
        ]

    if not candidates:
        return []

    scored: List[tuple] = []
    for col in candidates:
        non_null = df[col].dropna()
        if len(non_null) == 0:
            continue

        n_unique = non_null.nunique()
        if n_unique < 2 or n_unique > 50:
            continue

        group_sizes = non_null.value_counts().values
        cv = float(np.std(group_sizes) / np.mean(group_sizes)) if np.mean(group_sizes) > 0 else 0.0
        cardinality_penalty = 1.0 / (1.0 + max(0, n_unique - 10) * 0.1)
        score = cv * cardinality_penalty
        scored.append((col, score))

    scored.sort(key=lambda x: x[1], reverse=True)
    return [col for col, _ in scored[:max_segments]]


# ---------------------------------------------------------------------------
# Legacy API: scan_dimensions
# ---------------------------------------------------------------------------

def scan_dimensions(
    df: pd.DataFrame,
    metric_col: str,
    group_col: str,
    candidate_segments: List[str],
) -> dict:
    """Legacy wrapper around check_simpsons_multi_segment.

    Args:
        df: DataFrame.
        metric_col: Metric column.
        group_col: Grouping column.
        candidate_segments: List of segment columns.

    Returns:
        dict with keys: scanned, paradoxes_found, results (list), interpretation.
    """
    if not candidate_segments:
        return {"scanned": 0, "paradoxes_found": 0, "results": [],
                "interpretation": "No candidate segments."}

    results: List[dict] = []
    paradox_count = 0

    for seg_col in candidate_segments:
        if seg_col not in df.columns:
            results.append({
                "paradox_detected": False, "aggregate_direction": "equal",
                "segment_directions": [], "reversal_segments": [],
                "explanation": f"Column '{seg_col}' not found.",
                "severity": "WARNING",
            })
            continue

        result = check_simpsons_paradox(
            df, metric_col=metric_col, group_col=group_col, segment_col=seg_col,
        )
        results.append(result)
        if result["paradox_detected"]:
            paradox_count += 1

    if paradox_count == 0:
        interpretation = f"Scanned {len(candidate_segments)} — none detected."
    else:
        paradox_dims = [
            candidate_segments[i]
            for i, r in enumerate(results) if r.get("paradox_detected", False)
        ]
        interpretation = (
            f"Simpson's Paradox in {paradox_count} of "
            f"{len(candidate_segments)}: {paradox_dims}."
        )

    return {
        "scanned": len(candidate_segments), "paradoxes_found": paradox_count,
        "results": results, "interpretation": interpretation,
    }
