"""
Statistical testing utilities for the AI Data Analyst.

All functions return structured dicts with results, p-values, and
human-readable interpretations.

Usage:
    from ai_analyst.helpers.stats_helpers import (
        two_sample_proportion_test, two_sample_mean_test,
        mann_whitney_test, confidence_interval, chi_squared_test,
        bootstrap_ci, format_significance, interpret_effect_size,
        adjust_pvalues, characterize_distribution, rank_dimensions,
        sample_size_proportion, sample_size_mean, detectable_effect,
    )
"""

from __future__ import annotations

import math
from typing import Any, Callable, Dict, List, Optional, Union

import numpy as np
import pandas as pd
from scipy import stats


# ---------------------------------------------------------------------------
# Human-readable formatting helpers
# ---------------------------------------------------------------------------

def format_significance(p_value: float, alpha: float = 0.05) -> str:
    """Return a human-readable significance statement.

    Args:
        p_value: The p-value from a statistical test.
        alpha: Significance threshold (default 0.05).

    Returns:
        str: e.g. "Highly significant (p<0.001)"
    """
    if p_value < 0.001:
        return "Highly significant (p<0.001)"
    elif p_value < alpha:
        return f"Statistically significant (p={p_value:.3f})"
    else:
        return f"Not statistically significant (p={p_value:.3f})"


def interpret_effect_size(d: float, test_type: str = "cohens_d") -> str:
    """Translate a numeric effect size into a plain-English label.

    Args:
        d: The effect-size value (always taken as absolute value).
        test_type: Currently supports "cohens_d".

    Returns:
        str: e.g. "Small effect (d=0.15)"
    """
    d_abs = abs(d)

    if test_type == "cohens_d":
        if d_abs < 0.2:
            label = "Small"
        elif d_abs <= 0.8:
            label = "Medium"
        else:
            label = "Large"
        return f"{label} effect (d={d_abs:.2f})"

    return f"Effect size = {d_abs:.2f}"


# ---------------------------------------------------------------------------
# Proportion test (conversion rates, CTR, signup rates)
# ---------------------------------------------------------------------------

def two_sample_proportion_test(
    successes_a: int,
    n_a: int,
    successes_b: int,
    n_b: int,
    alpha: float = 0.05,
) -> Dict[str, Any]:
    """Z-test for comparing conversion rates between two groups.

    Args:
        successes_a: Number of successes in group A.
        n_a: Total observations in group A.
        successes_b: Number of successes in group B.
        n_b: Total observations in group B.
        alpha: Significance threshold (default 0.05).

    Returns:
        dict with keys: test, p_value, z_stat, significant, prop_a, prop_b,
        diff, ci_lower, ci_upper, interpretation.
    """
    prop_a = successes_a / n_a
    prop_b = successes_b / n_b
    diff = prop_b - prop_a

    pooled = (successes_a + successes_b) / (n_a + n_b)
    se_pooled = math.sqrt(pooled * (1 - pooled) * (1 / n_a + 1 / n_b))

    z_stat = diff / se_pooled if se_pooled > 0 else 0.0
    p_value = 2 * (1 - stats.norm.cdf(abs(z_stat)))

    se_diff = math.sqrt(
        prop_a * (1 - prop_a) / n_a + prop_b * (1 - prop_b) / n_b
    )
    z_crit = stats.norm.ppf(1 - alpha / 2)
    ci_lower = diff - z_crit * se_diff
    ci_upper = diff + z_crit * se_diff

    return {
        "test": "z-test proportions",
        "p_value": float(p_value),
        "z_stat": float(z_stat),
        "significant": bool(p_value < alpha),
        "prop_a": float(prop_a),
        "prop_b": float(prop_b),
        "diff": float(diff),
        "ci_lower": float(ci_lower),
        "ci_upper": float(ci_upper),
        "interpretation": format_significance(p_value, alpha),
    }


# ---------------------------------------------------------------------------
# Mean comparison (Welch's t-test)
# ---------------------------------------------------------------------------

def two_sample_mean_test(
    series_a: Union[list, np.ndarray, pd.Series],
    series_b: Union[list, np.ndarray, pd.Series],
    alpha: float = 0.05,
) -> Dict[str, Any]:
    """Welch's t-test for comparing means between two groups.

    Args:
        series_a: Array-like of values for group A.
        series_b: Array-like of values for group B.
        alpha: Significance threshold (default 0.05).

    Returns:
        dict with keys: test, p_value, t_stat, significant, mean_a, mean_b,
        diff, effect_size, effect_label, interpretation.
    """
    a = np.asarray(series_a, dtype=float)
    b = np.asarray(series_b, dtype=float)

    t_stat, p_value = stats.ttest_ind(a, b, equal_var=False)

    mean_a = float(np.mean(a))
    mean_b = float(np.mean(b))
    diff = mean_b - mean_a

    n_a, n_b = len(a), len(b)
    var_a, var_b = float(np.var(a, ddof=1)), float(np.var(b, ddof=1))
    pooled_std = math.sqrt(
        ((n_a - 1) * var_a + (n_b - 1) * var_b) / (n_a + n_b - 2)
    )
    cohens_d = diff / pooled_std if pooled_std > 0 else 0.0

    return {
        "test": "welch_t",
        "p_value": float(p_value),
        "t_stat": float(t_stat),
        "significant": bool(p_value < alpha),
        "mean_a": mean_a,
        "mean_b": mean_b,
        "diff": float(diff),
        "effect_size": float(cohens_d),
        "effect_label": interpret_effect_size(cohens_d),
        "interpretation": format_significance(p_value, alpha),
    }


# ---------------------------------------------------------------------------
# Non-parametric comparison (skewed data)
# ---------------------------------------------------------------------------

def mann_whitney_test(
    series_a: Union[list, np.ndarray, pd.Series],
    series_b: Union[list, np.ndarray, pd.Series],
    alpha: float = 0.05,
) -> Dict[str, Any]:
    """Mann-Whitney U test for comparing distributions.

    Args:
        series_a: Array-like of values for group A.
        series_b: Array-like of values for group B.
        alpha: Significance threshold (default 0.05).

    Returns:
        dict with keys: test, p_value, u_stat, significant, median_a,
        median_b, rank_biserial, interpretation.
    """
    a = np.asarray(series_a, dtype=float)
    b = np.asarray(series_b, dtype=float)

    u_stat, p_value = stats.mannwhitneyu(a, b, alternative="two-sided")

    n_a, n_b = len(a), len(b)
    rank_biserial = 1 - (2 * u_stat) / (n_a * n_b) if (n_a * n_b) > 0 else 0.0

    return {
        "test": "mann_whitney_u",
        "p_value": float(p_value),
        "u_stat": float(u_stat),
        "significant": bool(p_value < alpha),
        "median_a": float(np.median(a)),
        "median_b": float(np.median(b)),
        "rank_biserial": float(rank_biserial),
        "interpretation": format_significance(p_value, alpha),
    }


# ---------------------------------------------------------------------------
# Confidence interval (single sample)
# ---------------------------------------------------------------------------

def confidence_interval(
    series: Union[list, np.ndarray, pd.Series],
    confidence: float = 0.95,
) -> Dict[str, Any]:
    """Compute a confidence interval for the mean of a single sample.

    Args:
        series: Array-like of numeric values.
        confidence: Confidence level (default 0.95).

    Returns:
        dict with keys: mean, ci_lower, ci_upper, std, n, confidence.
    """
    a = np.asarray(series, dtype=float)
    n = len(a)
    mean = float(np.mean(a))
    std = float(np.std(a, ddof=1))
    se = std / math.sqrt(n)

    t_crit = stats.t.ppf((1 + confidence) / 2, df=n - 1)
    margin = t_crit * se

    return {
        "mean": mean,
        "ci_lower": float(mean - margin),
        "ci_upper": float(mean + margin),
        "std": std,
        "n": n,
        "confidence": confidence,
    }


# ---------------------------------------------------------------------------
# Chi-squared test (contingency tables)
# ---------------------------------------------------------------------------

def chi_squared_test(
    observed_table: Union[list, np.ndarray, pd.DataFrame],
    alpha: float = 0.05,
) -> Dict[str, Any]:
    """Chi-squared test of independence for a contingency table.

    Args:
        observed_table: 2D array-like or DataFrame of observed counts.
        alpha: Significance threshold (default 0.05).

    Returns:
        dict with keys: test, p_value, chi2_stat, significant, dof,
        expected, interpretation.
    """
    observed = np.asarray(observed_table)
    chi2_stat, p_value, dof, expected = stats.chi2_contingency(observed)

    return {
        "test": "chi_squared",
        "p_value": float(p_value),
        "chi2_stat": float(chi2_stat),
        "significant": bool(p_value < alpha),
        "dof": int(dof),
        "expected": expected,
        "interpretation": format_significance(p_value, alpha),
    }


# ---------------------------------------------------------------------------
# Bootstrap confidence interval (non-parametric)
# ---------------------------------------------------------------------------

def bootstrap_ci(
    series: Union[list, np.ndarray, pd.Series],
    stat_func: Optional[Callable] = None,
    n_bootstrap: int = 1000,
    confidence: float = 0.95,
) -> Dict[str, Any]:
    """Non-parametric confidence interval via bootstrapping.

    Args:
        series: Array-like of numeric values.
        stat_func: Callable returning a scalar. Defaults to np.mean.
        n_bootstrap: Number of bootstrap resamples (default 1000).
        confidence: Confidence level (default 0.95).

    Returns:
        dict with keys: stat, ci_lower, ci_upper, n_bootstrap, confidence.
    """
    if stat_func is None:
        stat_func = np.mean

    a = np.asarray(series, dtype=float)
    observed_stat = float(stat_func(a))

    rng = np.random.default_rng()
    boot_stats = np.array([
        stat_func(rng.choice(a, size=len(a), replace=True))
        for _ in range(n_bootstrap)
    ])

    alpha_half = (1 - confidence) / 2
    ci_lower = float(np.percentile(boot_stats, 100 * alpha_half))
    ci_upper = float(np.percentile(boot_stats, 100 * (1 - alpha_half)))

    return {
        "stat": observed_stat,
        "ci_lower": ci_lower,
        "ci_upper": ci_upper,
        "n_bootstrap": n_bootstrap,
        "confidence": confidence,
    }


# ---------------------------------------------------------------------------
# Multiple-testing correction
# ---------------------------------------------------------------------------

def adjust_pvalues(
    pvalues: Union[list, np.ndarray],
    method: str = "benjamini-hochberg",
) -> Dict[str, Any]:
    """Adjust p-values for multiple comparisons.

    Args:
        pvalues: List or array of raw p-values.
        method: "benjamini-hochberg" (default), "bonferroni", or "holm".

    Returns:
        dict with keys: adjusted, method, n_significant_raw,
        n_significant_adjusted, interpretation.
    """
    pvals = np.asarray(pvalues, dtype=float)
    n = len(pvals)

    if n == 0:
        return {
            "adjusted": [], "method": method,
            "n_significant_raw": 0, "n_significant_adjusted": 0,
            "interpretation": "No p-values provided.",
        }

    if method == "bonferroni":
        adjusted = np.minimum(pvals * n, 1.0)

    elif method == "holm":
        order = np.argsort(pvals)
        sorted_pvals = pvals[order]
        adjusted_sorted = np.zeros(n)
        for i in range(n):
            adjusted_sorted[i] = sorted_pvals[i] * (n - i)
        for i in range(1, n):
            adjusted_sorted[i] = max(adjusted_sorted[i], adjusted_sorted[i - 1])
        adjusted_sorted = np.minimum(adjusted_sorted, 1.0)
        adjusted = np.zeros(n)
        adjusted[order] = adjusted_sorted

    elif method == "benjamini-hochberg":
        order = np.argsort(pvals)
        sorted_pvals = pvals[order]
        adjusted_sorted = np.zeros(n)
        for i in range(n):
            rank = i + 1
            adjusted_sorted[i] = sorted_pvals[i] * n / rank
        for i in range(n - 2, -1, -1):
            adjusted_sorted[i] = min(adjusted_sorted[i], adjusted_sorted[i + 1])
        adjusted_sorted = np.minimum(adjusted_sorted, 1.0)
        adjusted = np.zeros(n)
        adjusted[order] = adjusted_sorted

    else:
        raise ValueError(
            f"Unknown method '{method}'. "
            "Choose 'benjamini-hochberg', 'bonferroni', or 'holm'."
        )

    n_sig_raw = int(np.sum(pvals < 0.05))
    n_sig_adj = int(np.sum(adjusted < 0.05))

    interpretation = (
        f"{n_sig_raw} of {n} tests significant before correction; "
        f"{n_sig_adj} after {method} correction."
    )
    if n_sig_raw > n_sig_adj:
        interpretation += (
            f" {n_sig_raw - n_sig_adj} result(s) were likely false positives."
        )

    return {
        "adjusted": [float(p) for p in adjusted],
        "method": method,
        "n_significant_raw": n_sig_raw,
        "n_significant_adjusted": n_sig_adj,
        "interpretation": interpretation,
    }


# ---------------------------------------------------------------------------
# Distribution characterization
# ---------------------------------------------------------------------------

def characterize_distribution(
    series: Union[list, np.ndarray, pd.Series],
    name: Optional[str] = None,
) -> Dict[str, Any]:
    """Profile a numeric series' distribution shape.

    Computes descriptive statistics, tests for normality, estimates modality,
    and produces a human-readable shape description.

    Args:
        series: pd.Series of numeric values.
        name: Optional label for the series.

    Returns:
        dict with keys: name, n, mean, median, std, min, max, p5, p25, p75,
        p95, skewness, kurtosis, normality_test, modality, shape_description.
    """
    s = pd.Series(series).dropna()
    label = name or getattr(series, "name", None) or "series"
    n = len(s)

    if n < 3:
        return {
            "name": label, "n": n,
            "mean": float(s.mean()) if n > 0 else None,
            "median": float(s.median()) if n > 0 else None,
            "std": None, "min": float(s.min()) if n > 0 else None,
            "max": float(s.max()) if n > 0 else None,
            "p5": None, "p25": None, "p75": None, "p95": None,
            "skewness": None, "kurtosis": None,
            "normality_test": None, "modality": "insufficient data",
            "shape_description": "Too few values to characterize.",
        }

    mean_val = float(s.mean())
    median_val = float(s.median())
    std_val = float(s.std())

    if n < 5000:
        stat_val, p_norm = stats.shapiro(s.values)
    else:
        stat_val, p_norm = stats.normaltest(s.values)

    normality_test = {
        "statistic": float(stat_val),
        "p_value": float(p_norm),
        "is_normal": bool(p_norm >= 0.05),
    }

    skewness = float(stats.skew(s.values))
    kurtosis = float(stats.kurtosis(s.values))

    modality = _estimate_modality(s.values)

    shape_parts: List[str] = []
    if abs(skewness) < 0.5:
        shape_parts.append("approximately symmetric")
    elif skewness > 0:
        shape_parts.append("right-skewed")
    else:
        shape_parts.append("left-skewed")

    if kurtosis > 1:
        shape_parts.append("heavy-tailed")
    elif kurtosis < -1:
        shape_parts.append("light-tailed")

    if modality != "unimodal":
        shape_parts.append(modality)

    shape_description = ", ".join(shape_parts)

    return {
        "name": label, "n": n, "mean": mean_val, "median": median_val,
        "std": std_val, "min": float(s.min()), "max": float(s.max()),
        "p5": float(np.percentile(s.values, 5)),
        "p25": float(np.percentile(s.values, 25)),
        "p75": float(np.percentile(s.values, 75)),
        "p95": float(np.percentile(s.values, 95)),
        "skewness": skewness, "kurtosis": kurtosis,
        "normality_test": normality_test, "modality": modality,
        "shape_description": shape_description,
    }


def _estimate_modality(values: np.ndarray) -> str:
    """Simple histogram-based modality estimate."""
    n = len(values)
    n_bins = min(max(int(math.sqrt(n)), 10), 50)
    counts, _ = np.histogram(values, bins=n_bins)

    peaks = 0
    for i in range(1, len(counts) - 1):
        if counts[i] > counts[i - 1] and counts[i] > counts[i + 1]:
            peaks += 1

    if len(counts) >= 2:
        if counts[0] > counts[1]:
            peaks += 1
        if counts[-1] > counts[-2]:
            peaks += 1

    if peaks <= 1:
        return "unimodal"
    elif peaks == 2:
        return "bimodal"
    else:
        return "multimodal"


# ---------------------------------------------------------------------------
# Dimension ranking (eta-squared / ANOVA)
# ---------------------------------------------------------------------------

def rank_dimensions(
    df: pd.DataFrame,
    metric_col: str,
    dimension_cols: List[str],
) -> List[Dict[str, Any]]:
    """Rank categorical dimensions by their explanatory power for a metric.

    Uses eta-squared (one-way ANOVA) to measure how much variance each
    dimension explains.

    Args:
        df: DataFrame with metric and dimension columns.
        metric_col: Name of the numeric metric column.
        dimension_cols: List of categorical dimension column names.

    Returns:
        list of dicts sorted by eta_squared descending with keys:
        dimension, eta_squared, n_groups, f_statistic, p_value, rank,
        interpretation.
    """
    results: List[Dict[str, Any]] = []
    data = df.dropna(subset=[metric_col])

    for dim in dimension_cols:
        subset = data.dropna(subset=[dim])
        groups = [
            group[metric_col].values
            for _, group in subset.groupby(dim)
            if len(group) >= 2
        ]

        if len(groups) < 2:
            results.append({
                "dimension": dim, "eta_squared": 0.0, "n_groups": len(groups),
                "f_statistic": 0.0, "p_value": 1.0, "rank": 0,
                "interpretation": f"'{dim}' has fewer than 2 valid groups.",
            })
            continue

        f_stat, p_value = stats.f_oneway(*groups)

        grand_mean = subset[metric_col].mean()
        ss_total = float(np.sum((subset[metric_col].values - grand_mean) ** 2))
        ss_between = sum(
            len(g) * (np.mean(g) - grand_mean) ** 2 for g in groups
        )
        eta_sq = float(ss_between / ss_total) if ss_total > 0 else 0.0

        if eta_sq < 0.01:
            effect_label = "negligible"
        elif eta_sq < 0.06:
            effect_label = "small"
        elif eta_sq < 0.14:
            effect_label = "medium"
        else:
            effect_label = "large"

        results.append({
            "dimension": dim, "eta_squared": eta_sq,
            "n_groups": len(groups), "f_statistic": float(f_stat),
            "p_value": float(p_value), "rank": 0,
            "interpretation": (
                f"'{dim}' explains {eta_sq:.1%} of variance in {metric_col} "
                f"({effect_label} effect). "
                f"{format_significance(p_value)}"
            ),
        })

    results.sort(key=lambda x: x["eta_squared"], reverse=True)
    for i, r in enumerate(results):
        r["rank"] = i + 1

    return results


# ---------------------------------------------------------------------------
# Power analysis
# ---------------------------------------------------------------------------

def sample_size_proportion(
    baseline_rate: float,
    mde: float,
    alpha: float = 0.05,
    power: float = 0.80,
) -> Dict[str, Any]:
    """Calculate required sample size per group for a proportion test.

    Args:
        baseline_rate: Current conversion rate (e.g. 0.10 for 10%).
        mde: Minimum detectable effect as relative change (e.g. 0.05 for 5%).
        alpha: Significance level (default 0.05).
        power: Statistical power (default 0.80).

    Returns:
        dict with keys: sample_size_per_group, total_sample_size,
        baseline_rate, expected_rate, absolute_difference, interpretation.
    """
    p1 = baseline_rate
    p2 = p1 * (1 + mde)
    delta = abs(p2 - p1)

    if delta == 0:
        return {
            "sample_size_per_group": float("inf"),
            "total_sample_size": float("inf"),
            "baseline_rate": p1, "expected_rate": p2,
            "absolute_difference": 0.0,
            "interpretation": "MDE is zero — infinite sample required.",
        }

    z_alpha = stats.norm.ppf(1 - alpha / 2)
    z_beta = stats.norm.ppf(power)

    n = (z_alpha + z_beta) ** 2 * (
        p1 * (1 - p1) + p2 * (1 - p2)
    ) / delta ** 2
    n_per_group = int(math.ceil(n))

    return {
        "sample_size_per_group": n_per_group,
        "total_sample_size": n_per_group * 2,
        "baseline_rate": float(p1),
        "expected_rate": float(p2),
        "absolute_difference": float(delta),
        "interpretation": (
            f"Need {n_per_group:,} users per group ({n_per_group * 2:,} total) "
            f"to detect a {mde:.1%} relative lift from {p1:.2%} to {p2:.2%} "
            f"with {power:.0%} power at alpha={alpha}."
        ),
    }


def sample_size_mean(
    baseline_mean: float,
    baseline_std: float,
    mde: float,
    alpha: float = 0.05,
    power: float = 0.80,
) -> Dict[str, Any]:
    """Calculate required sample size per group for a mean comparison test.

    Args:
        baseline_mean: Current mean value.
        baseline_std: Standard deviation of the metric.
        mde: Minimum detectable effect as absolute difference.
        alpha: Significance level (default 0.05).
        power: Statistical power (default 0.80).

    Returns:
        dict with keys: sample_size_per_group, total_sample_size,
        effect_size_d, interpretation.
    """
    if mde == 0:
        return {
            "sample_size_per_group": float("inf"),
            "total_sample_size": float("inf"),
            "effect_size_d": 0.0,
            "interpretation": "MDE is zero — infinite sample required.",
        }

    z_alpha = stats.norm.ppf(1 - alpha / 2)
    z_beta = stats.norm.ppf(power)

    n = (z_alpha + z_beta) ** 2 * 2 * baseline_std ** 2 / mde ** 2
    n_per_group = int(math.ceil(n))
    effect_d = float(mde / baseline_std) if baseline_std > 0 else 0.0

    return {
        "sample_size_per_group": n_per_group,
        "total_sample_size": n_per_group * 2,
        "effect_size_d": effect_d,
        "interpretation": (
            f"Need {n_per_group:,} observations per group "
            f"({n_per_group * 2:,} total) to detect a difference of "
            f"{mde:,.2f} (Cohen's d={effect_d:.2f}) "
            f"with {power:.0%} power at alpha={alpha}."
        ),
    }


def detectable_effect(
    n_per_group: int,
    baseline_rate: Optional[float] = None,
    baseline_std: Optional[float] = None,
    alpha: float = 0.05,
    power: float = 0.80,
) -> Dict[str, Any]:
    """Given a fixed sample size, calculate the minimum detectable effect.

    Args:
        n_per_group: Available sample size per group.
        baseline_rate: If provided, calculates MDE for a proportion test.
        baseline_std: If provided, calculates MDE for a mean test.
        alpha: Significance level (default 0.05).
        power: Statistical power (default 0.80).

    Returns:
        dict with keys: mde_absolute, mde_relative (if proportion),
        interpretation.
    """
    if baseline_rate is None and baseline_std is None:
        raise ValueError("Provide either baseline_rate or baseline_std.")

    z_alpha = stats.norm.ppf(1 - alpha / 2)
    z_beta = stats.norm.ppf(power)

    if baseline_rate is not None:
        p = baseline_rate
        mde_abs = (z_alpha + z_beta) * math.sqrt(
            2 * p * (1 - p) / n_per_group
        )
        mde_rel = float(mde_abs / p) if p > 0 else 0.0

        return {
            "mde_absolute": float(mde_abs),
            "mde_relative": mde_rel,
            "interpretation": (
                f"With {n_per_group:,} users per group, the smallest "
                f"detectable change is {mde_abs:.4f} ({mde_rel:.1%} relative) "
                f"from a baseline rate of {p:.2%} at {power:.0%} power."
            ),
        }
    else:
        mde_abs = (z_alpha + z_beta) * baseline_std * math.sqrt(
            2 / n_per_group
        )
        effect_d = float(mde_abs / baseline_std) if baseline_std > 0 else 0.0

        return {
            "mde_absolute": float(mde_abs),
            "interpretation": (
                f"With {n_per_group:,} observations per group, the smallest "
                f"detectable difference is {mde_abs:,.2f} "
                f"(Cohen's d={effect_d:.2f}) at {power:.0%} power."
            ),
        }
