"""
Analytics Helpers — RFM, concentration, control charts, segment comparison.

Higher-level analytical functions returning structured dicts with
human-readable interpretations.

Usage:
    from ai_analyst.helpers.analytics_helpers import (
        rfm_analysis, concentration_analysis, compare_segments,
        score_findings, control_chart, synthesize_insights,
    )
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

import numpy as np
import pandas as pd
from scipy import stats


# ---------------------------------------------------------------------------
# RFM Analysis
# ---------------------------------------------------------------------------


def rfm_analysis(df: pd.DataFrame, customer_col: str, date_col: str,
                 revenue_col: str,
                 reference_date: Optional[str] = None) -> Dict[str, Any]:
    """Compute RFM segmentation.

    Args:
        df: Transaction-level DataFrame.
        customer_col: Customer identifier column.
        date_col: Order date column.
        revenue_col: Revenue column.
        reference_date: Date for recency calc. Defaults to max date + 1 day.

    Returns:
        Dict with keys: df, segment_summary, interpretation.
    """
    if df is None or len(df) == 0:
        return {"df": pd.DataFrame(), "segment_summary": pd.DataFrame(),
                "interpretation": "Empty dataset — cannot compute RFM."}

    data = df[[customer_col, date_col, revenue_col]].copy()
    data[date_col] = pd.to_datetime(data[date_col])

    ref = (pd.to_datetime(reference_date) if reference_date
           else data[date_col].max() + pd.Timedelta(days=1))

    rfm = data.groupby(customer_col).agg(
        recency=(date_col, lambda x: (ref - x.max()).days),
        frequency=(date_col, "count"),
        monetary=(revenue_col, "sum"),
    ).reset_index()
    rfm.columns = ["customer", "recency", "frequency", "monetary"]
    n = len(rfm)

    if n == 1:
        rfm["R"] = rfm["F"] = rfm["M"] = 3
        rfm["RFM_Score"] = "333"
        rfm["segment"] = "Other"
        summary = pd.DataFrame([{"segment": "Other", "count": 1, "pct": 100.0,
                                  "avg_monetary": float(rfm["monetary"].iloc[0]),
                                  "avg_frequency": float(rfm["frequency"].iloc[0])}])
        return {"df": rfm, "segment_summary": summary,
                "interpretation": "Only 1 customer — RFM requires multiple customers."}

    rfm["R"] = _safe_qcut(rfm["recency"], 5, [5, 4, 3, 2, 1])
    rfm["F"] = _safe_qcut(rfm["frequency"], 5, [1, 2, 3, 4, 5])
    rfm["M"] = _safe_qcut(rfm["monetary"], 5, [1, 2, 3, 4, 5])
    rfm["RFM_Score"] = rfm["R"].astype(str) + rfm["F"].astype(str) + rfm["M"].astype(str)
    rfm["segment"] = rfm.apply(_assign_rfm_segment, axis=1)

    summary = (rfm.groupby("segment")
               .agg(count=("customer", "count"),
                    avg_monetary=("monetary", "mean"),
                    avg_frequency=("frequency", "mean"))
               .reset_index())
    summary["pct"] = (summary["count"] / summary["count"].sum() * 100).round(1)
    summary = summary[["segment", "count", "pct", "avg_monetary", "avg_frequency"]]
    summary = summary.sort_values("count", ascending=False).reset_index(drop=True)

    top = summary.iloc[0]
    interp = (f"RFM across {n:,} customers: {len(summary)} segments. "
              f"Largest: {top['segment']} ({top['count']:,}, {top['pct']:.1f}%).")
    return {"df": rfm, "segment_summary": summary, "interpretation": interp}


def _safe_qcut(series: pd.Series, q: int, labels: list) -> pd.Series:
    """Quintile scoring handling ties gracefully."""
    try:
        return pd.qcut(series, q=q, labels=labels, duplicates="drop").astype(int)
    except ValueError:
        for fewer in range(q - 1, 1, -1):
            try:
                return pd.qcut(series, q=fewer, labels=labels[:fewer],
                               duplicates="drop").astype(int)
            except ValueError:
                continue
        return pd.Series([3] * len(series), index=series.index)


def _assign_rfm_segment(row: pd.Series) -> str:
    """Map RFM scores to named segment."""
    r, f, m = int(row["R"]), int(row["F"]), int(row["M"])
    if r >= 4 and f >= 4 and m >= 4:
        return "Champions"
    if f >= 3 and m >= 3:
        return "Loyal"
    if r <= 2 and f >= 3:
        return "At Risk"
    if r <= 2 and f <= 2 and m <= 2:
        return "Lost"
    return "Other"


# ---------------------------------------------------------------------------
# Concentration Analysis
# ---------------------------------------------------------------------------


def concentration_analysis(df: pd.DataFrame, value_col: str,
                           entity_col: Optional[str] = None) -> Dict[str, Any]:
    """Analyze distribution concentration (Gini, Pareto, Lorenz).

    Args:
        df: DataFrame with values.
        value_col: Column to measure concentration of.
        entity_col: Optional entity column for aggregation.

    Returns:
        Dict with gini, top_10/20/50_pct_share, pareto_ratio,
        lorenz_curve, interpretation.
    """
    empty = {"gini": 0.0, "top_10_pct_share": 0.0, "top_20_pct_share": 0.0,
             "top_50_pct_share": 0.0, "pareto_ratio": 0.0,
             "lorenz_curve": {"x": [], "y": []}}

    if df is None or len(df) == 0:
        return {**empty, "interpretation": "Empty dataset."}

    if entity_col is not None:
        values = df.groupby(entity_col)[value_col].sum().values.astype(float)
    else:
        values = df[value_col].dropna().values.astype(float)

    n = len(values)
    if n == 0:
        return {**empty, "interpretation": "No valid values."}

    total = float(np.sum(values))
    if total == 0:
        return {**empty, "pareto_ratio": 100.0,
                "interpretation": "All values are zero."}

    sorted_v = np.sort(values)
    cumulative = np.cumsum(sorted_v)
    gini = float((2 * np.sum(np.arange(1, n+1) * sorted_v)) / (n * total) - (n+1) / n)
    gini = max(0.0, min(1.0, gini))

    sorted_desc = np.sort(values)[::-1]
    cumsum_desc = np.cumsum(sorted_desc)

    def _top_pct(pct: float) -> float:
        k = max(1, int(np.ceil(n * pct / 100)))
        return float(cumsum_desc[min(k, n) - 1] / total)

    top_10, top_20, top_50 = _top_pct(10), _top_pct(20), _top_pct(50)
    pareto_idx = int(np.searchsorted(cumsum_desc, total * 0.80, side="left")) + 1
    pareto_ratio = float(pareto_idx / n * 100)

    lorenz_y = np.concatenate([[0], cumulative / total])
    lorenz_x = np.linspace(0, 1, n + 1)

    label = ("highly concentrated" if gini > 0.6
             else "moderately concentrated" if gini > 0.4
             else "relatively evenly distributed")

    interp = (f"Distribution is {label} (Gini={gini:.3f}). "
              f"Top 10%: {top_10:.1%}, top 20%: {top_20:.1%}. "
              f"{pareto_ratio:.1f}% produce 80% of value.")

    return {"gini": gini, "top_10_pct_share": top_10, "top_20_pct_share": top_20,
            "top_50_pct_share": top_50, "pareto_ratio": pareto_ratio,
            "lorenz_curve": {"x": lorenz_x.tolist(), "y": lorenz_y.tolist()},
            "interpretation": interp}


# ---------------------------------------------------------------------------
# Segment Comparison
# ---------------------------------------------------------------------------


def compare_segments(df: pd.DataFrame, segment_col: str, metric_col: str,
                     test: str = "auto") -> Dict[str, Any]:
    """Compare metric across segments with automatic test selection.

    Args:
        df: DataFrame with segment and metric columns.
        segment_col: Segment column.
        metric_col: Numeric metric column.
        test: 'auto', 'mann-whitney', or 't-test'.

    Returns:
        Dict with summary, pairwise results, interpretation.
    """
    if df is None or len(df) == 0:
        return {"summary": pd.DataFrame(), "pairwise": [],
                "interpretation": "Empty dataset."}

    data = df[[segment_col, metric_col]].dropna()
    groups = data.groupby(segment_col)[metric_col]
    group_data = {name: vals.values.astype(float) for name, vals in groups if len(vals) > 0}

    summary_rows = [
        {"segment": name, "mean": float(np.mean(v)), "median": float(np.median(v)),
         "std": float(np.std(v, ddof=1)) if len(v) > 1 else 0.0, "count": len(v)}
        for name, v in group_data.items()
    ]
    summary = pd.DataFrame(summary_rows)

    if len(group_data) < 2:
        return {"summary": summary, "pairwise": [],
                "interpretation": f"Only {len(group_data)} segment(s)."}

    if test == "auto":
        use_np = any(len(v) < 30 for v in group_data.values())
        if not use_np:
            for v in group_data.values():
                if len(v) >= 3:
                    _, p = stats.shapiro(v[:5000])
                    if p < 0.05:
                        use_np = True
                        break
        selected = "mann-whitney" if use_np else "t-test"
    else:
        selected = test

    names = list(group_data.keys())
    pairs = [(names[i], names[j]) for i in range(len(names)) for j in range(i+1, len(names))]
    n_comp = len(pairs)
    pairwise = []

    for a, b in pairs:
        va, vb = group_data[a], group_data[b]
        if selected == "mann-whitney":
            try:
                stat_val, p = stats.mannwhitneyu(va, vb, alternative="two-sided")
            except ValueError:
                stat_val, p = 0.0, 1.0
            test_used = "mann-whitney"
        else:
            stat_val, p = stats.ttest_ind(va, vb, equal_var=False)
            test_used = "welch-t"

        diff = float(np.mean(va) - np.mean(vb))
        pooled = np.sqrt(((len(va)-1)*np.var(va, ddof=1) + (len(vb)-1)*np.var(vb, ddof=1))
                         / max(len(va)+len(vb)-2, 1))
        d = float(diff / pooled) if pooled > 0 else 0.0
        p_adj = min(float(p) * n_comp, 1.0)

        pairwise.append({"seg_a": a, "seg_b": b, "test_used": test_used,
                         "stat": float(stat_val), "p_value": float(p),
                         "p_adjusted": p_adj, "significant": p_adj < 0.05,
                         "effect_size": d})

    n_sig = sum(1 for r in pairwise if r["significant"])
    interp = (f"Compared {metric_col} across {len(group_data)} segments "
              f"({selected}, {n_comp} pairs, Bonferroni). "
              f"{n_sig} significant.")
    return {"summary": summary, "pairwise": pairwise, "interpretation": interp}


# ---------------------------------------------------------------------------
# Control Chart
# ---------------------------------------------------------------------------


def control_chart(series: pd.Series, sigma: int = 3,
                  window: Optional[int] = None) -> Dict[str, Any]:
    """Shewhart control chart with Western Electric rules.

    Args:
        series: Pandas Series with values.
        sigma: Std devs for control limits (default 3).
        window: Optional rolling window.

    Returns:
        Dict with center_line, ucl, lcl, violations, in_control,
        rules_checked, interpretation.
    """
    if series is None or len(series) == 0:
        return {"center_line": np.nan, "ucl": np.nan, "lcl": np.nan,
                "violations": [], "in_control": True, "rules_checked": [],
                "interpretation": "Empty series."}

    values = series.dropna()
    if len(values) < 2:
        return {"center_line": float(values.iloc[0]) if len(values) == 1 else np.nan,
                "ucl": np.nan, "lcl": np.nan, "violations": [],
                "in_control": True, "rules_checked": [],
                "interpretation": "Insufficient data."}

    if window is not None and window >= 2:
        center = values.rolling(window=window, min_periods=2).mean()
        std = values.rolling(window=window, min_periods=2).std(ddof=1)
    else:
        center = float(values.mean())
        std = float(values.std(ddof=1))

    ucl = center + sigma * std
    lcl = center - sigma * std

    if window is not None and window >= 2:
        center_arr = center.values
        std_arr = std.values
    else:
        center_arr = np.full(len(values), center)
        std_arr = np.full(len(values), std)

    vals = values.values.astype(float)
    idx = values.index

    with np.errstate(divide="ignore", invalid="ignore"):
        z = np.where(std_arr > 0, (vals - center_arr) / std_arr, 0.0)

    violations = []
    seen = set()

    # Rule 1: beyond 3-sigma
    for i in range(len(vals)):
        if not np.isnan(z[i]) and abs(z[i]) > sigma:
            if (i, "R1") not in seen:
                seen.add((i, "R1"))
                violations.append({"index": idx[i], "value": float(vals[i]),
                                   "rule": "Rule 1",
                                   "description": f"Beyond {sigma}-sigma (z={z[i]:.2f})"})

    # Rule 2: 2/3 beyond 2-sigma same side
    for i in range(2, len(vals)):
        if any(np.isnan(z[i-k]) for k in range(3)):
            continue
        for threshold, side in [(2, "upper"), (-2, "lower")]:
            check = [z[i-k] > threshold for k in range(3)] if side == "upper" \
                else [z[i-k] < threshold for k in range(3)]
            if sum(check) >= 2 and (i, "R2") not in seen:
                seen.add((i, "R2"))
                violations.append({"index": idx[i], "value": float(vals[i]),
                                   "rule": "Rule 2",
                                   "description": f"2/3 beyond 2-sigma ({side})"})

    # Rule 4: 8 consecutive same side
    for i in range(7, len(vals)):
        if any(np.isnan(z[i-k]) for k in range(8)):
            continue
        above = all(vals[i-k] > center_arr[i-k] for k in range(8))
        below = all(vals[i-k] < center_arr[i-k] for k in range(8))
        if (above or below) and (i, "R4") not in seen:
            seen.add((i, "R4"))
            violations.append({"index": idx[i], "value": float(vals[i]),
                               "rule": "Rule 4",
                               "description": f"8 consecutive {'above' if above else 'below'} center"})

    in_control = len(violations) == 0
    mode = "rolling" if window and window >= 2 else "global"
    interp = (f"Control chart ({mode}, {sigma}-sigma): "
              f"{'IN CONTROL' if in_control else f'OUT OF CONTROL, {len(violations)} violations'}.")

    return {"center_line": center, "ucl": ucl, "lcl": lcl,
            "violations": violations, "in_control": in_control,
            "rules_checked": ["Rule 1", "Rule 2", "Rule 4"],
            "interpretation": interp}


# ---------------------------------------------------------------------------
# Score Findings
# ---------------------------------------------------------------------------


def score_findings(findings: List[Dict]) -> Dict[str, Any]:
    """Rank findings by 4-factor business impact (0-100).

    Args:
        findings: List of finding dicts.

    Returns:
        Dict with ranked_findings, top_finding, interpretation.
    """
    if not findings:
        return {"ranked_findings": [], "top_finding": None,
                "interpretation": "No findings to score."}

    scored = []
    for f in findings:
        factors = _score_single(f)
        scored.append({**f, "factors": factors, "score": sum(factors.values())})

    scored.sort(key=lambda x: x["score"], reverse=True)
    for i, item in enumerate(scored):
        item["rank"] = i + 1

    top = scored[0]
    interp = (f"{len(scored)} findings scored. Top: {top.get('description', '?')} "
              f"(score={top['score']}/100).")
    return {"ranked_findings": scored, "top_finding": top, "interpretation": interp}


def _score_single(f: Dict) -> Dict[str, int]:
    """Compute 4-factor score for a single finding."""
    baseline = f.get("baseline_value", 0)
    metric = f.get("metric_value", 0)
    if baseline == 0:
        magnitude = 15 if metric != 0 else 5
    else:
        pct = abs(metric - baseline) / abs(baseline)
        magnitude = 25 if pct > 0.5 else 20 if pct > 0.2 else 15 if pct > 0.1 else 10 if pct > 0.05 else 5

    aff = f.get("affected_pct", 0)
    breadth = 25 if aff > 0.5 else 20 if aff > 0.3 else 15 if aff > 0.1 else 10 if aff > 0.05 else 5

    actionability = 25 if f.get("actionable", False) else 5
    if f.get("effect_size") and f["effect_size"] > 0.5:
        actionability = min(actionability + 5, 25)

    conf = max(0, min(25, int(round(f.get("confidence", 0) * 25))))
    if f.get("p_value") is not None and f["p_value"] < 0.05:
        conf = min(conf + 5, 25)

    return {"magnitude": magnitude, "breadth": breadth,
            "actionability": actionability, "confidence": conf}


# ---------------------------------------------------------------------------
# Synthesize Insights
# ---------------------------------------------------------------------------


def synthesize_insights(findings: List[Dict],
                        metadata: Optional[Dict] = None) -> Dict[str, Any]:
    """Group findings, detect contradictions, produce narrative structure.

    Args:
        findings: List of finding dicts.
        metadata: Optional context dict.

    Returns:
        Dict with headline, theme_groups, contradictions, narrative_flow,
        action_items, interpretation.
    """
    metadata = metadata or {}
    if not findings:
        return {"headline": "No findings.", "theme_groups": [],
                "contradictions": [], "narrative_flow": [],
                "action_items": [], "interpretation": "No findings."}

    scored = score_findings(findings)
    ranked = scored["ranked_findings"]

    # Group by theme
    groups: Dict[str, list] = {}
    for f in ranked:
        theme = (f.get("category", "") or "Other").capitalize()
        groups.setdefault(theme, []).append(f)
    theme_groups = [{"theme": t, "findings": fs, "count": len(fs)}
                    for t, fs in sorted(groups.items())]

    # Contradictions
    contradictions = []
    for i in range(len(ranked)):
        for j in range(i+1, len(ranked)):
            a, b = ranked[i], ranked[j]
            if (a.get("metric_name") and b.get("metric_name")
                    and a["metric_name"] == b["metric_name"]
                    and a.get("direction") in ("up", "down")
                    and b.get("direction") in ("up", "down")
                    and a["direction"] != b["direction"]):
                contradictions.append({
                    "finding_a": a.get("description", ""),
                    "finding_b": b.get("description", ""),
                    "nature": f"{a['metric_name']} shows opposite directions."})

    # Action items
    actions = [{"action": f"Act on: {f['description']}", "priority": "high" if f["score"] >= 70 else "medium",
                "metric": f.get("metric_name", "")}
               for f in ranked if f.get("actionable")]

    top = ranked[0]
    headline = f"Key insight: {top.get('description', '')}"
    interp = (f"Analysis produced {len(ranked)} findings across {len(theme_groups)} themes. "
              f"Top finding: {top.get('description', '')} (score={top['score']}/100).")

    return {"headline": headline, "theme_groups": theme_groups,
            "contradictions": contradictions,
            "narrative_flow": ["[Context] Baseline", f"[Tension] {headline}",
                               "[Resolution] Recommended actions"],
            "action_items": actions, "interpretation": interp}
