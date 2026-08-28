"""
Confidence Scoring Framework (Synthesis Layer).

Synthesizes signals from the 4 validator layers plus sample size into a
single 0-100 confidence score for analytical findings.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Grade thresholds
# ---------------------------------------------------------------------------

_GRADE_THRESHOLDS = [(85, "A"), (70, "B"), (55, "C"), (40, "D"), (0, "F")]

_RECOMMENDATIONS = {
    "A": "HIGH CONFIDENCE -- present as findings",
    "B": "MODERATE CONFIDENCE -- present with caveats",
    "C": "LOW CONFIDENCE -- requires additional validation",
    "D": "INSUFFICIENT -- do not present without investigation",
    "F": "INSUFFICIENT -- do not present without investigation",
}


def _grade_from_score(score: int) -> str:
    """Map a numeric score (0-100) to a letter grade.

    Args:
        score: Integer confidence score.

    Returns:
        str: One of 'A', 'B', 'C', 'D', 'F'.
    """
    for threshold, grade in _GRADE_THRESHOLDS:
        if score >= threshold:
            return grade
    return "F"


def _recommendation_from_grade(grade: str) -> str:
    """Map a letter grade to an actionable recommendation."""
    return _RECOMMENDATIONS.get(grade, _RECOMMENDATIONS["F"])


# ---------------------------------------------------------------------------
# Factor scoring helpers
# ---------------------------------------------------------------------------

def _score_data_completeness(vr: Dict[str, Any]) -> Dict[str, Any]:
    """Score Factor 1: Data Completeness (0-15)."""
    completeness = vr.get("completeness")
    if completeness is None:
        return {"score": 0, "max": 15, "status": "MISSING",
                "detail": "Completeness validation not provided."}

    columns = completeness.get("columns", [])
    if not columns:
        return {"score": 0, "max": 15, "status": "MISSING",
                "detail": "No column completeness data."}

    null_rates = [c.get("null_rate", 0.0) for c in columns]
    overall = sum(null_rates) / len(null_rates) if null_rates else 0.0

    if overall < 0.01:
        return {"score": 15, "max": 15, "status": "PASS",
                "detail": f"Null rate {overall:.2%} — excellent."}
    elif overall < 0.05:
        return {"score": 12, "max": 15, "status": "PASS",
                "detail": f"Null rate {overall:.2%} — good."}
    elif overall < 0.10:
        return {"score": 9, "max": 15, "status": "WARNING",
                "detail": f"Null rate {overall:.2%} — moderate gaps."}
    elif overall < 0.20:
        return {"score": 5, "max": 15, "status": "WARNING",
                "detail": f"Null rate {overall:.2%} — significant gaps."}
    return {"score": 2, "max": 15, "status": "BLOCKER",
            "detail": f"Null rate {overall:.2%} — severe issues."}


def _score_structural_integrity(vr: Dict[str, Any]) -> Dict[str, Any]:
    """Score Factor 2: Structural Integrity (0-15)."""
    pk = vr.get("primary_key")
    ri = vr.get("referential_integrity")
    schema = vr.get("schema")

    if pk is None and ri is None and schema is None:
        return {"score": 0, "max": 15, "status": "MISSING",
                "detail": "Structural integrity not provided."}

    severities: List[str] = []
    details: List[str] = []

    if pk is not None:
        severities.append(pk.get("severity", "PASS"))
        if pk.get("severity") == "BLOCKER":
            details.append(f"PK: {pk.get('null_count', 0)} nulls, "
                           f"{pk.get('duplicate_count', 0)} dups")

    if ri is not None:
        severities.append(ri.get("severity", "PASS"))
        if ri.get("severity") != "PASS":
            details.append(f"RI: {ri.get('orphan_rate', 0):.2%} orphan rate")

    if schema is not None:
        severities.append(schema.get("severity", "PASS"))
        if schema.get("severity") == "BLOCKER":
            details.append(f"Schema: missing {schema.get('missing_columns', [])}")

    if "BLOCKER" in severities:
        score, status = 3, "BLOCKER"
    elif "WARNING" in severities:
        score, status = 10, "WARNING"
    else:
        score, status = 15, "PASS"

    detail = "; ".join(details) if details else "All structural checks passed."
    return {"score": score, "max": 15, "status": status, "detail": detail}


def _score_aggregation_consistency(vr: Dict[str, Any]) -> Dict[str, Any]:
    """Score Factor 3: Aggregation Consistency (0-15)."""
    agg = vr.get("aggregation")
    seg = vr.get("segment_exhaustiveness")

    if agg is None and seg is None:
        return {"score": 0, "max": 15, "status": "MISSING",
                "detail": "Aggregation consistency not provided."}

    severities: List[str] = []
    max_diff = 0.0
    details: List[str] = []

    if agg is not None:
        severities.append(agg.get("severity", "PASS"))
        for m in agg.get("mismatches", []):
            diff = m.get("diff_pct")
            if diff is not None and diff > max_diff:
                max_diff = diff
        if agg.get("mismatches"):
            details.append(f"{len(agg['mismatches'])} mismatch(es)")

    if seg is not None:
        severities.append(seg.get("severity", "PASS"))
        seg_diff = seg.get("diff_pct", 0.0)
        if seg_diff > max_diff:
            max_diff = seg_diff
        if seg.get("missing_rows", 0) > 0:
            details.append(f"{seg['missing_rows']} rows missing")

    if "BLOCKER" in severities or max_diff > 0.05:
        score, status = 3, "BLOCKER"
    elif max_diff > 0.01:
        score, status = 8, "WARNING"
    elif "WARNING" in severities:
        score, status = 12, "WARNING"
    else:
        score, status = 15, "PASS"

    detail = "; ".join(details) if details else "Aggregations consistent."
    return {"score": score, "max": 15, "status": status, "detail": detail}


def _score_temporal_consistency(vr: Dict[str, Any]) -> Dict[str, Any]:
    """Score Factor 4: Temporal Consistency (0-15)."""
    temporal = vr.get("temporal")
    trend = vr.get("trend_continuity")

    if temporal is None and trend is None:
        return {"score": 0, "max": 15, "status": "MISSING",
                "detail": "Temporal consistency not provided."}

    has_structural_break = False
    missing_count = 0
    break_count = 0
    details: List[str] = []

    if temporal is not None:
        missing_count = len(temporal.get("missing_dates", [])) + len(temporal.get("zero_dates", []))
        if temporal.get("duplicate_dates"):
            details.append(f"{len(temporal['duplicate_dates'])} duplicate date(s)")
        if temporal.get("missing_dates"):
            details.append(f"{len(temporal['missing_dates'])} missing date(s)")

    if trend is not None:
        break_count = len(trend.get("breaks", []))
        if break_count > 0:
            details.append(f"{break_count} break(s)")
        if trend.get("severity") == "BLOCKER":
            has_structural_break = True

    if has_structural_break:
        score, status = 3, "BLOCKER"
    elif break_count > 0 or missing_count > 5:
        score, status = 5, "WARNING"
    elif missing_count > 0:
        score, status = 10, "WARNING"
    else:
        score, status = 15, "PASS"

    detail = "; ".join(details) if details else "No temporal issues."
    return {"score": score, "max": 15, "status": status, "detail": detail}


def _score_business_plausibility(vr: Dict[str, Any]) -> Dict[str, Any]:
    """Score Factor 5: Business Plausibility (0-15)."""
    ranges = vr.get("ranges")
    rates = vr.get("rates")
    yoy = vr.get("yoy")

    if ranges is None and rates is None and yoy is None:
        return {"score": 0, "max": 15, "status": "MISSING",
                "detail": "Business plausibility not provided."}

    severities: List[str] = []
    details: List[str] = []

    if ranges is not None:
        for v in ranges.get("violations", []):
            sev = v.get("severity", "PASS")
            severities.append(sev)
            if sev != "PASS":
                details.append(f"Range '{v.get('rule_name', '?')}': {sev}")

    if rates is not None:
        severities.append(rates.get("severity", "PASS"))
        if rates.get("severity") != "PASS":
            details.append(f"Rate: {rates.get('severity')}")

    if yoy is not None:
        severities.append(yoy.get("severity", "PASS"))
        if yoy.get("severity") != "PASS":
            details.append(f"YoY: {yoy.get('interpretation', yoy.get('severity'))}")

    if "BLOCKER" in severities or "FAIL" in severities:
        score, status = 5, "BLOCKER"
    elif "WARNING" in severities:
        score, status = 10, "WARNING"
    else:
        score, status = 15, "PASS"

    detail = "; ".join(details) if details else "All business rules passed."
    return {"score": score, "max": 15, "status": status, "detail": detail}


def _score_simpsons_paradox(vr: Dict[str, Any]) -> Dict[str, Any]:
    """Score Factor 6: Simpson's Paradox Risk (0-15)."""
    simpsons = vr.get("simpsons")
    if simpsons is None:
        return {"score": 0, "max": 15, "status": "MISSING",
                "detail": "Simpson's Paradox scan not provided."}

    paradox_detected = simpsons.get("paradox_detected", False)
    paradoxes_found = simpsons.get("paradoxes_found", 0)
    is_core = simpsons.get("is_core_metric", True)

    if "results" in simpsons and isinstance(simpsons["results"], list):
        if any(r.get("paradox_detected", False) for r in simpsons["results"]):
            paradox_detected = True
            paradoxes_found = sum(
                1 for r in simpsons["results"] if r.get("paradox_detected")
            )

    if not paradox_detected and paradoxes_found == 0:
        return {"score": 15, "max": 15, "status": "PASS",
                "detail": "No Simpson's Paradox detected."}

    if is_core:
        return {"score": 2, "max": 15, "status": "BLOCKER",
                "detail": f"Paradox in core metric ({paradoxes_found} dim(s))."}

    return {"score": 8, "max": 15, "status": "WARNING",
            "detail": f"Paradox in {paradoxes_found} non-critical dim(s)."}


def _score_sample_size(metadata: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Score Factor 7: Sample Size (0-10)."""
    if metadata is None or "row_count" not in metadata:
        return {"score": 0, "max": 10, "status": "MISSING",
                "detail": "Sample size metadata not provided."}

    n = metadata["row_count"]
    if n > 10000:
        return {"score": 10, "max": 10, "status": "PASS",
                "detail": f"{n:,} rows — large sample."}
    elif n > 1000:
        return {"score": 8, "max": 10, "status": "PASS",
                "detail": f"{n:,} rows — adequate."}
    elif n > 100:
        return {"score": 5, "max": 10, "status": "WARNING",
                "detail": f"{n:,} rows — moderate, interpret with caution."}
    elif n > 30:
        return {"score": 3, "max": 10, "status": "WARNING",
                "detail": f"{n:,} rows — small sample."}
    return {"score": 1, "max": 10, "status": "BLOCKER",
            "detail": f"{n:,} rows — very small."}


# ---------------------------------------------------------------------------
# Validator presence detection
# ---------------------------------------------------------------------------

_VALIDATOR_KEYS = {
    "structural": {"completeness", "primary_key", "referential_integrity", "schema"},
    "logical": {"aggregation", "segment_exhaustiveness", "temporal", "trend_continuity"},
    "business": {"ranges", "rates", "yoy"},
    "simpsons": {"simpsons"},
}


def _validators_present(vr: Dict[str, Any]) -> Dict[str, bool]:
    """Determine which validator layers have provided results."""
    return {
        layer: any(vr.get(k) is not None for k in keys)
        for layer, keys in _VALIDATOR_KEYS.items()
    }


# ---------------------------------------------------------------------------
# Main scoring function
# ---------------------------------------------------------------------------

def score_confidence(
    validation_results: Dict[str, Any],
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Compute a 0-100 confidence score from validation results.

    7 factors (max points):
        1. Data Completeness       (0-15)
        2. Structural Integrity    (0-15)
        3. Aggregation Consistency (0-15)
        4. Temporal Consistency    (0-15)
        5. Business Plausibility   (0-15)
        6. Simpson's Paradox Risk  (0-15)
        7. Sample Size             (0-10)

    Args:
        validation_results: Dict with validator outputs.
        metadata: Optional dict with 'row_count'.

    Returns:
        dict with keys: score, grade, factors, blockers,
        interpretation, recommendation.
    """
    if not validation_results:
        return {
            "score": 0, "grade": "F", "factors": {},
            "blockers": ["No validation results provided."],
            "interpretation": "No validation results. Run all 4 layers.",
            "recommendation": _recommendation_from_grade("F"),
        }

    factors = {
        "data_completeness": _score_data_completeness(validation_results),
        "structural_integrity": _score_structural_integrity(validation_results),
        "aggregation_consistency": _score_aggregation_consistency(validation_results),
        "temporal_consistency": _score_temporal_consistency(validation_results),
        "business_plausibility": _score_business_plausibility(validation_results),
        "simpsons_paradox_risk": _score_simpsons_paradox(validation_results),
        "sample_size": _score_sample_size(metadata),
    }

    scored_max = sum(f["max"] for f in factors.values() if f["status"] != "MISSING")
    scored_actual = sum(f["score"] for f in factors.values() if f["status"] != "MISSING")

    total_score = int(round(scored_actual / scored_max * 100)) if scored_max > 0 else 0
    total_score = max(0, min(100, total_score))

    blockers: List[str] = [
        f"{name}: {f['detail']}"
        for name, f in factors.items() if f["status"] == "BLOCKER"
    ]

    present = _validators_present(validation_results)
    missing_layers = [l for l, p in present.items() if not p]
    is_partial = len(missing_layers) > 0
    grade = _grade_from_score(total_score)

    if is_partial and grade in ("A", "B"):
        grade = "C"

    scored_factors = [n for n, f in factors.items() if f["status"] != "MISSING"]
    missing_factors = [n for n, f in factors.items() if f["status"] == "MISSING"]

    parts = [f"Confidence: {total_score}/100 (Grade {grade}). "
             f"Scored {len(scored_factors)} of 7 factors."]
    if missing_factors:
        parts.append(f"Missing: {', '.join(missing_factors)}.")
    if blockers:
        parts.append(f"Blockers ({len(blockers)}): " + "; ".join(blockers))
    if is_partial:
        parts.append(f"Grade capped at C (missing: {', '.join(missing_layers)}).")

    return {
        "score": total_score, "grade": grade, "factors": factors,
        "blockers": blockers, "interpretation": " ".join(parts),
        "recommendation": _recommendation_from_grade(grade),
    }


# ---------------------------------------------------------------------------
# Badge formatter
# ---------------------------------------------------------------------------

def format_confidence_badge(score_result: Dict[str, Any]) -> str:
    """Format a confidence score for embedding in narratives.

    Args:
        score_result: Dict returned by score_confidence().

    Returns:
        str: Formatted badge string.
    """
    score = score_result.get("score", 0)
    grade = score_result.get("grade", "F")
    factors = score_result.get("factors", {})

    level_map = {"A": "High confidence", "B": "Moderate confidence",
                 "C": "Low confidence"}
    level = level_map.get(grade, "Insufficient confidence")

    lines = [f"Confidence: {score}/100 ({grade}) -- {level}"]

    for name, f in factors.items():
        if f["status"] == "BLOCKER":
            lines.append(f"  BLOCKER {f['detail']}")
        elif f["status"] == "WARNING":
            lines.append(f"  * {f['detail']}")

    missing = [n for n, f in factors.items() if f["status"] == "MISSING"]
    if missing:
        lines.append(f"  (!) Missing: {', '.join(missing)}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Score merger
# ---------------------------------------------------------------------------

def merge_confidence_scores(scores_list: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Merge multiple confidence results from different analysis steps.

    Args:
        scores_list: List of dicts from score_confidence().

    Returns:
        dict with same format as score_confidence().
    """
    if not scores_list:
        return {
            "score": 0, "grade": "F", "factors": {},
            "blockers": ["No scores provided."],
            "interpretation": "No scores to merge.",
            "recommendation": _recommendation_from_grade("F"),
        }

    if len(scores_list) == 1:
        return scores_list[0]

    total_score = sum(s.get("score", 0) for s in scores_list)
    avg_score = max(0, min(100, int(round(total_score / len(scores_list)))))

    all_blockers: List[str] = []
    for s in scores_list:
        for b in s.get("blockers", []):
            if b not in all_blockers:
                all_blockers.append(b)

    merged_factors: Dict[str, Dict[str, Any]] = {}
    all_factor_names: set = set()
    for s in scores_list:
        for name in s.get("factors", {}):
            all_factor_names.add(name)

    _status_priority = {"BLOCKER": 0, "WARNING": 1, "MISSING": 2, "PASS": 3}

    for name in all_factor_names:
        instances = [
            s["factors"][name] for s in scores_list
            if name in s.get("factors", {})
        ]
        if not instances:
            continue

        worst_status = min(
            (f["status"] for f in instances),
            key=lambda st: _status_priority.get(st, 99),
        )
        min_score = min(f["score"] for f in instances)
        max_val = max(f["max"] for f in instances)
        details = [f["detail"] for f in instances if f["detail"]]
        detail = details[0] if len(set(details)) == 1 else " | ".join(details)

        merged_factors[name] = {
            "score": min_score, "max": max_val,
            "status": worst_status, "detail": detail,
        }

    grade = _grade_from_score(avg_score)

    _grade_rank = {"A": 0, "B": 1, "C": 2, "D": 3, "F": 4}
    worst_grade = max(
        (s.get("grade", "F") for s in scores_list),
        key=lambda g: _grade_rank.get(g, 4),
    )
    if worst_grade in ("D", "F") and grade in ("A", "B"):
        grade = "C"

    interpretation = (
        f"Merged {len(scores_list)} scores. Average: {avg_score}/100 ({grade}). "
        f"Individual: {', '.join(str(s.get('score', 0)) for s in scores_list)}."
    )
    if all_blockers:
        interpretation += f" Blockers: {'; '.join(all_blockers)}"

    return {
        "score": avg_score, "grade": grade, "factors": merged_factors,
        "blockers": all_blockers, "interpretation": interpretation,
        "recommendation": _recommendation_from_grade(grade),
    }
