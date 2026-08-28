"""
Structural Validation Helpers (Layer 1).

Validates the STRUCTURE of data before analysis begins: schema conformance,
primary key integrity, completeness, date range coverage, referential
integrity, value domains, and row counts.

Each function returns a dict with an ``ok`` boolean.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Set, Union

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Compatible dtype groups
# ---------------------------------------------------------------------------

_NUMERIC_DTYPES: Set[str] = {
    "int8", "int16", "int32", "int64",
    "uint8", "uint16", "uint32", "uint64",
    "float16", "float32", "float64",
}
_DATETIME_DTYPES: Set[str] = {
    "datetime64[ns]", "datetime64[us]", "datetime64[ms]", "datetime64[s]",
}
_STRING_DTYPES: Set[str] = {"object", "string", "str"}


def _dtypes_compatible(actual: str, expected: str) -> bool:
    """Return True if actual and expected dtype names are compatible."""
    actual_lower = str(actual).lower()
    expected_lower = str(expected).lower()
    if actual_lower == expected_lower:
        return True
    if actual_lower in _NUMERIC_DTYPES and expected_lower in _NUMERIC_DTYPES:
        return True
    if actual_lower in _DATETIME_DTYPES and expected_lower in _DATETIME_DTYPES:
        return True
    if actual_lower in _STRING_DTYPES and expected_lower in _STRING_DTYPES:
        return True
    return False


# ---------------------------------------------------------------------------
# 1. Schema validation
# ---------------------------------------------------------------------------

def validate_schema(
    df: pd.DataFrame,
    expected_columns: Optional[List[str]] = None,
    expected_types: Optional[Dict[str, str]] = None,
    expected_dtypes: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """Check that df has the expected columns and types.

    Args:
        df: The data to validate.
        expected_columns: Column names that must be present.
        expected_types: Mapping of column name -> expected dtype string.
        expected_dtypes: Legacy alias for expected_types.

    Returns:
        dict with keys: ok, valid, issues, warnings, missing_columns,
        dtype_mismatches, extra_columns, severity.
    """
    if expected_types is None and expected_dtypes is not None:
        expected_types = expected_dtypes

    issues: List[str] = []
    warnings: List[str] = []
    missing_columns: List[str] = []
    dtype_mismatches: List[Dict[str, str]] = []
    extra_columns: List[str] = []

    if df is None or (isinstance(df, pd.DataFrame) and df.columns.empty):
        if expected_columns:
            missing_columns = list(expected_columns)
            issues.append(f"DataFrame has no columns; expected {expected_columns}")
        return {
            "ok": len(issues) == 0, "valid": len(issues) == 0,
            "issues": issues, "warnings": warnings,
            "missing_columns": missing_columns,
            "dtype_mismatches": dtype_mismatches,
            "extra_columns": extra_columns,
            "severity": "BLOCKER" if issues else "PASS",
        }

    actual_columns = set(df.columns.tolist())

    if expected_columns is not None:
        for col in expected_columns:
            if col not in actual_columns:
                missing_columns.append(col)
                issues.append(f"Missing required column: '{col}'")

    if expected_columns is not None:
        expected_set = set(expected_columns)
        extra_columns = sorted(actual_columns - expected_set)

    if expected_types is not None:
        for col, expected_dtype in expected_types.items():
            if col not in actual_columns:
                continue
            actual_dtype = str(df[col].dtype)
            if not _dtypes_compatible(actual_dtype, expected_dtype):
                dtype_mismatches.append({
                    "column": col, "expected": str(expected_dtype),
                    "actual": actual_dtype,
                })
                warnings.append(
                    f"Column '{col}' has dtype '{actual_dtype}', "
                    f"expected '{expected_dtype}'"
                )

    if missing_columns:
        severity = "BLOCKER"
    elif dtype_mismatches:
        severity = "WARNING"
    else:
        severity = "PASS"

    ok = len(issues) == 0
    return {
        "ok": ok, "valid": ok, "issues": issues, "warnings": warnings,
        "missing_columns": missing_columns,
        "dtype_mismatches": dtype_mismatches,
        "extra_columns": extra_columns, "severity": severity,
    }


# ---------------------------------------------------------------------------
# 2. Primary key validation
# ---------------------------------------------------------------------------

def validate_primary_key(
    df: pd.DataFrame,
    key_columns: List[str],
) -> Dict[str, Any]:
    """Check that key_columns form a unique, non-null primary key.

    Args:
        df: The data to validate.
        key_columns: Column names forming the composite primary key.

    Returns:
        dict with keys: ok, valid, duplicate_count, duplicate_sample,
        duplicate_examples, null_count, severity.
    """
    if len(df) == 0:
        return {
            "ok": True, "valid": True, "duplicate_count": 0,
            "duplicate_sample": pd.DataFrame(),
            "duplicate_examples": pd.DataFrame(),
            "null_count": 0, "severity": "PASS",
        }

    null_mask = df[key_columns].isna().any(axis=1)
    null_count = int(null_mask.sum())

    dup_mask = df.duplicated(subset=key_columns, keep=False)
    duplicate_rows = df[dup_mask]
    duplicate_count = int(
        duplicate_rows.drop_duplicates(subset=key_columns).shape[0]
    )
    duplicate_sample = duplicate_rows.head(5).copy()

    if null_count > 0 or duplicate_count > 0:
        severity = "BLOCKER"
    else:
        severity = "PASS"

    ok = severity == "PASS"
    return {
        "ok": ok, "valid": ok, "duplicate_count": duplicate_count,
        "duplicate_sample": duplicate_sample,
        "duplicate_examples": duplicate_sample,
        "null_count": null_count, "severity": severity,
    }


# ---------------------------------------------------------------------------
# 3. Completeness validation
# ---------------------------------------------------------------------------

def validate_completeness(
    df: pd.DataFrame,
    required_columns: Optional[List[str]] = None,
    threshold: float = 0.95,
) -> Dict[str, Any]:
    """Check null rates across columns.

    Args:
        df: The data to validate.
        required_columns: Columns to inspect. If None, all columns.
        threshold: Minimum non-null fraction required (default 0.95).

    Returns:
        dict with keys: ok, column_stats, columns, overall_severity,
        summary_text.
    """
    columns_to_check = required_columns if required_columns else df.columns.tolist()
    n = len(df)

    if n == 0:
        column_stats = [
            {"name": col, "null_count": 0, "null_rate": 0.0,
             "passes_threshold": True, "severity": "PASS"}
            for col in columns_to_check
        ]
        return {
            "ok": True, "column_stats": column_stats,
            "columns": column_stats, "overall_severity": "WARNING",
            "summary_text": "DataFrame is empty.",
        }

    max_null_rate = 1.0 - threshold
    column_stats: List[Dict[str, Any]] = []

    for col in columns_to_check:
        if col not in df.columns:
            column_stats.append({
                "name": col, "null_count": n, "null_rate": 1.0,
                "passes_threshold": False, "severity": "BLOCKER",
            })
            continue

        null_count = int(df[col].isna().sum())
        null_rate = float(null_count / n)
        passes = null_rate <= max_null_rate

        if null_rate > 0.2:
            severity = "BLOCKER"
        elif null_rate >= max_null_rate:
            severity = "WARNING"
        else:
            severity = "PASS"

        column_stats.append({
            "name": col, "null_count": null_count,
            "null_rate": round(null_rate, 6),
            "passes_threshold": passes, "severity": severity,
        })

    severities = {c["severity"] for c in column_stats}
    if "BLOCKER" in severities:
        overall_severity = "BLOCKER"
    elif "WARNING" in severities:
        overall_severity = "WARNING"
    else:
        overall_severity = "PASS"

    ok = all(c["passes_threshold"] for c in column_stats)

    blocker_cols = [c["name"] for c in column_stats if c["severity"] == "BLOCKER"]
    warning_cols = [c["name"] for c in column_stats if c["severity"] == "WARNING"]
    parts: List[str] = []
    if blocker_cols:
        parts.append(f"{len(blocker_cols)} column(s) with >20% nulls: {blocker_cols}")
    if warning_cols:
        parts.append(f"{len(warning_cols)} column(s) with elevated nulls: {warning_cols}")
    if not parts:
        parts.append(f"All {len(column_stats)} column(s) within acceptable thresholds.")

    return {
        "ok": ok, "column_stats": column_stats, "columns": column_stats,
        "overall_severity": overall_severity, "summary_text": " ".join(parts),
    }


# ---------------------------------------------------------------------------
# 4. Date range validation
# ---------------------------------------------------------------------------

def validate_date_range(
    df: pd.DataFrame,
    date_column: str,
    expected_start: Optional[str] = None,
    expected_end: Optional[str] = None,
    max_gap_days: Optional[int] = None,
) -> Dict[str, Any]:
    """Check temporal coverage of a date column.

    Args:
        df: The data to validate.
        date_column: Name of the date/datetime column.
        expected_start: Earliest expected date (ISO format).
        expected_end: Latest expected date (ISO format).
        max_gap_days: Maximum allowed gap in days.

    Returns:
        dict with keys: ok, actual_start, actual_end, gaps, issues.
    """
    issues: List[str] = []
    gaps: List[Dict[str, Any]] = []

    if len(df) == 0:
        return {"ok": True, "actual_start": None, "actual_end": None,
                "gaps": [], "issues": issues}

    if date_column not in df.columns:
        issues.append(f"Date column '{date_column}' not found")
        return {"ok": False, "actual_start": None, "actual_end": None,
                "gaps": [], "issues": issues}

    dates = pd.to_datetime(df[date_column], errors="coerce").dropna().sort_values()

    if len(dates) == 0:
        issues.append(f"No valid dates in column '{date_column}'")
        return {"ok": False, "actual_start": None, "actual_end": None,
                "gaps": [], "issues": issues}

    actual_start = dates.min()
    actual_end = dates.max()
    actual_start_str = str(actual_start.date())
    actual_end_str = str(actual_end.date())

    if expected_start is not None:
        expected_start_dt = pd.to_datetime(expected_start)
        if actual_start > expected_start_dt:
            issues.append(f"Data starts at {actual_start_str}, expected {expected_start}")
        elif actual_start < expected_start_dt:
            issues.append(f"Data starts at {actual_start_str}, before expected {expected_start}")

    if expected_end is not None:
        expected_end_dt = pd.to_datetime(expected_end)
        if actual_end < expected_end_dt:
            issues.append(f"Data ends at {actual_end_str}, expected {expected_end}")
        elif actual_end > expected_end_dt:
            issues.append(f"Data ends at {actual_end_str}, after expected {expected_end}")

    if max_gap_days is not None and len(dates) >= 2:
        unique_dates = dates.dt.normalize().drop_duplicates().sort_values()
        diffs = unique_dates.diff().dropna()
        for idx, diff in diffs.items():
            gap_days = diff.days
            if gap_days > max_gap_days:
                gap_end_date = unique_dates.loc[idx]
                gap_start_date = gap_end_date - diff
                gaps.append({
                    "start": str(gap_start_date.date()),
                    "end": str(gap_end_date.date()),
                    "gap_days": gap_days,
                })
        if gaps:
            issues.append(f"Found {len(gaps)} gap(s) exceeding {max_gap_days} day(s)")

    return {
        "ok": len(issues) == 0, "actual_start": actual_start_str,
        "actual_end": actual_end_str, "gaps": gaps, "issues": issues,
    }


# ---------------------------------------------------------------------------
# 5. Referential integrity validation
# ---------------------------------------------------------------------------

def validate_referential_integrity(
    _pos_arg1: Optional[pd.DataFrame] = None,
    _pos_arg2: Optional[pd.DataFrame] = None,
    _pos_arg3: str = "",
    _pos_arg4: str = "",
    *,
    df_child: Optional[pd.DataFrame] = None,
    df_parent: Optional[pd.DataFrame] = None,
    child_key: str = "",
    parent_key: str = "",
    parent_df: Optional[pd.DataFrame] = None,
    child_df: Optional[pd.DataFrame] = None,
) -> Dict[str, Any]:
    """Check that all child_key values exist in parent_key.

    Supports both new keyword API and legacy positional API.

    Args:
        df_child: Child (fact) table.
        df_parent: Parent (lookup) table.
        child_key: Column name in df_child.
        parent_key: Column name in df_parent.

    Returns:
        dict with keys: ok, valid, orphan_count, orphan_sample,
        orphan_examples, orphan_rate, severity.
    """
    resolved_parent = df_parent if df_parent is not None else parent_df
    resolved_child = df_child if df_child is not None else child_df
    resolved_parent_key = parent_key
    resolved_child_key = child_key

    if _pos_arg1 is not None and resolved_parent is None:
        resolved_parent = _pos_arg1
    if _pos_arg2 is not None and resolved_child is None:
        resolved_child = _pos_arg2
    if _pos_arg3 and not resolved_parent_key:
        resolved_parent_key = _pos_arg3
    if _pos_arg4 and not resolved_child_key:
        resolved_child_key = _pos_arg4

    if resolved_child is None or resolved_parent is None:
        return {
            "ok": False, "valid": False, "orphan_count": 0,
            "orphan_sample": [], "orphan_examples": [],
            "orphan_rate": 0.0, "severity": "BLOCKER",
        }

    if len(resolved_child) == 0:
        return {
            "ok": True, "valid": True, "orphan_count": 0,
            "orphan_sample": [], "orphan_examples": [],
            "orphan_rate": 0.0, "severity": "PASS",
        }

    parent_values = set(resolved_parent[resolved_parent_key].dropna().unique())
    child_values = resolved_child[resolved_child_key].dropna()

    orphan_mask = ~child_values.isin(parent_values)
    orphan_count = int(orphan_mask.sum())
    orphan_rate = float(orphan_count / len(resolved_child)) if len(resolved_child) > 0 else 0.0
    orphan_sample = child_values[orphan_mask].unique().tolist()[:10]

    if orphan_rate > 0.05:
        severity = "BLOCKER"
    elif orphan_rate > 0:
        severity = "WARNING"
    else:
        severity = "PASS"

    ok = orphan_count == 0
    return {
        "ok": ok, "valid": severity == "PASS",
        "orphan_count": orphan_count, "orphan_sample": orphan_sample,
        "orphan_examples": orphan_sample,
        "orphan_rate": round(orphan_rate, 6), "severity": severity,
    }


# ---------------------------------------------------------------------------
# 6. Value domain validation
# ---------------------------------------------------------------------------

def validate_value_domain(
    df: pd.DataFrame,
    column: str,
    valid_values: Optional[Sequence[Any]] = None,
    min_val: Optional[Union[int, float]] = None,
    max_val: Optional[Union[int, float]] = None,
) -> Dict[str, Any]:
    """Check that values in column fall within an expected domain.

    Args:
        df: The data to validate.
        column: Column to inspect.
        valid_values: Set of allowed categorical values.
        min_val: Minimum allowed value (inclusive).
        max_val: Maximum allowed value (inclusive).

    Returns:
        dict with keys: ok, out_of_range_count, unexpected_values, issues.
    """
    issues: List[str] = []
    out_of_range_count = 0
    unexpected_values: List[Any] = []

    if column not in df.columns:
        issues.append(f"Column '{column}' not found")
        return {"ok": False, "out_of_range_count": 0,
                "unexpected_values": [], "issues": issues}

    series = df[column].dropna()

    if valid_values is not None:
        valid_set = set(valid_values)
        actual_set = set(series.unique())
        unexpected = actual_set - valid_set
        if unexpected:
            unexpected_values = sorted(str(v) for v in unexpected)
            mask = series.isin(unexpected)
            out_of_range_count += int(mask.sum())
            issues.append(f"Found {len(unexpected)} unexpected value(s): {unexpected_values[:5]}")

    if min_val is not None:
        below = series[series < min_val]
        if len(below) > 0:
            out_of_range_count += len(below)
            issues.append(f"{len(below)} value(s) below minimum {min_val}")

    if max_val is not None:
        above = series[series > max_val]
        if len(above) > 0:
            out_of_range_count += len(above)
            issues.append(f"{len(above)} value(s) above maximum {max_val}")

    return {
        "ok": len(issues) == 0, "out_of_range_count": out_of_range_count,
        "unexpected_values": unexpected_values, "issues": issues,
    }


# ---------------------------------------------------------------------------
# 7. Row count validation
# ---------------------------------------------------------------------------

def validate_row_count(
    df: pd.DataFrame,
    min_rows: int = 1,
    max_rows: Optional[int] = None,
) -> Dict[str, Any]:
    """Check that df has an acceptable number of rows.

    Args:
        df: The data to validate.
        min_rows: Minimum required row count (default 1).
        max_rows: Maximum allowed row count.

    Returns:
        dict with keys: ok, row_count, message.
    """
    row_count = len(df)
    issues: List[str] = []

    if row_count < min_rows:
        issues.append(f"Row count {row_count:,} is below minimum {min_rows:,}")
    if max_rows is not None and row_count > max_rows:
        issues.append(f"Row count {row_count:,} exceeds maximum {max_rows:,}")

    ok = len(issues) == 0
    message = f"Row count: {row_count:,}" if ok else "; ".join(issues)
    return {"ok": ok, "row_count": row_count, "message": message}


# ---------------------------------------------------------------------------
# 8. Orchestrator
# ---------------------------------------------------------------------------

def run_structural_checks(
    df: pd.DataFrame,
    config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Run all applicable structural checks based on config.

    Args:
        df: The data to validate.
        config: Dict controlling which checks to run.

    Returns:
        dict with keys: overall_ok, checks_run, checks_passed,
        checks_failed, details.
    """
    if config is None:
        config = {}

    details: Dict[str, Dict[str, Any]] = {}

    if "expected_columns" in config or "expected_types" in config:
        details["schema"] = validate_schema(
            df, expected_columns=config.get("expected_columns"),
            expected_types=config.get("expected_types"),
        )

    if "primary_key" in config:
        details["primary_key"] = validate_primary_key(
            df, key_columns=config["primary_key"],
        )

    if "required_columns" in config:
        details["completeness"] = validate_completeness(
            df, required_columns=config["required_columns"],
            threshold=config.get("completeness_threshold", 0.95),
        )

    if "date_column" in config:
        details["date_range"] = validate_date_range(
            df, date_column=config["date_column"],
            expected_start=config.get("expected_start"),
            expected_end=config.get("expected_end"),
            max_gap_days=config.get("max_gap_days"),
        )

    if "parent_df" in config:
        details["referential_integrity"] = validate_referential_integrity(
            df_child=df, df_parent=config["parent_df"],
            child_key=config.get("child_key", ""),
            parent_key=config.get("parent_key", ""),
        )

    if "value_domain" in config:
        vd = config["value_domain"]
        details["value_domain"] = validate_value_domain(
            df, column=vd.get("column", ""),
            valid_values=vd.get("valid_values"),
            min_val=vd.get("min_val"), max_val=vd.get("max_val"),
        )

    min_rows = config.get("min_rows")
    max_rows = config.get("max_rows")
    if min_rows is not None or max_rows is not None:
        details["row_count"] = validate_row_count(
            df, min_rows=min_rows if min_rows is not None else 1,
            max_rows=max_rows,
        )

    if not details:
        details["schema"] = validate_schema(df)
        details["completeness"] = validate_completeness(df)
        details["row_count"] = validate_row_count(df, min_rows=1)

    checks_run = len(details)
    checks_passed = sum(1 for r in details.values() if r.get("ok", False))
    checks_failed = checks_run - checks_passed

    return {
        "overall_ok": checks_failed == 0, "checks_run": checks_run,
        "checks_passed": checks_passed, "checks_failed": checks_failed,
        "details": details,
    }
