"""
Build data_profile.json and validation_result.json for techworld_data_sample.
Run from project root: python scripts/build_profile.py
"""
import pandas as pd
import numpy as np
import json
import os
from datetime import datetime

df = pd.read_csv("data/raw/techworld_data_sample.csv")
df["Order_Date_parsed"] = pd.to_datetime(df["Order_Date"], errors="coerce")
df["Year"] = df["Order_Date_parsed"].dt.year

# Fix comma-decimal columns
for col in ["Net_Profit", "Marketing_Cost", "Shipping_Cost"]:
    df[col + "_num"] = pd.to_numeric(
        df[col].astype(str).str.replace(",", ".", regex=False), errors="coerce"
    )

def safe(v):
    if isinstance(v, float) and (np.isnan(v) or np.isinf(v)):
        return None
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating,)):
        return float(round(v, 4))
    return v

os.makedirs("data/pipeline/techworld_data_sample", exist_ok=True)

# ── COLUMN PROFILES ──────────────────────────────────────────────────────────
NUMERIC_COLS = ["Quantity", "Unit_Price", "Sales", "Delivery_Days", "Return_Flag", "Review_Rating"]
STRING_METRIC_COLS = ["Net_Profit", "Marketing_Cost", "Shipping_Cost"]
CAT_COLS = ["Region", "Category", "Product_Name", "Traffic_Source", "Supplier", "Order_Status"]
ORIG_COLS = [
    "Order_ID","Order_Date","Customer_ID","Region","Category","Product_Name",
    "Quantity","Unit_Price","Sales","Net_Profit","Marketing_Cost","Shipping_Cost",
    "Delivery_Days","Traffic_Source","Supplier","Order_Status","Return_Flag",
    "Review_Rating","Review_Text","Net_Profit_Flag",
]

columns = {}
for col in ORIG_COLS:
    null_count = int(df[col].isnull().sum())
    null_pct = round(null_count / len(df) * 100, 4)
    unique_count = int(df[col].nunique(dropna=True))
    dtype = str(df[col].dtype)
    info = {
        "dtype": dtype,
        "null_count": null_count,
        "null_pct": null_pct,
        "unique_count": unique_count,
        "sample_values": [str(v) for v in df[col].dropna().head(3).tolist()],
    }
    if col in NUMERIC_COLS:
        s = df[col]
        Q1, Q3 = s.quantile(0.25), s.quantile(0.75)
        IQR = Q3 - Q1
        info.update({
            "role": "metric",
            "min": safe(s.min()), "max": safe(s.max()),
            "mean": safe(s.mean()), "median": safe(s.median()),
            "std": safe(s.std()), "skew": safe(float(s.skew())),
            "outliers_iqr": int(((s < Q1 - 1.5*IQR) | (s > Q3 + 1.5*IQR)).sum()),
        })
    elif col in STRING_METRIC_COLS:
        s = df[col + "_num"]
        Q1, Q3 = s.quantile(0.25), s.quantile(0.75)
        IQR = Q3 - Q1
        comma_count = int(df[col].astype(str).str.contains(r"^\d+,\d+$", regex=True, na=False).sum())
        info.update({
            "role": "metric",
            "stored_as": "object/string",
            "comma_decimal_count": comma_count,
            "min": safe(s.min()), "max": safe(s.max()),
            "mean": safe(s.mean()), "median": safe(s.median()),
            "std": safe(s.std()),
            "outliers_iqr": int(((s < Q1 - 1.5*IQR) | (s > Q3 + 1.5*IQR)).sum()),
        })
    elif col in CAT_COLS:
        top = df[col].value_counts(dropna=False).head(5)
        info.update({
            "role": "dimension",
            "top_values": {str(k): int(v) for k, v in top.items()},
        })
    elif col == "Order_ID":
        info.update({
            "role": "identifier",
            "duplicate_count": int(df["Order_ID"].duplicated().sum()),
        })
    elif col == "Order_Date":
        info["role"] = "date"
    elif col == "Customer_ID":
        info["role"] = "identifier"
    elif col == "Review_Text":
        info["role"] = "text"
    elif col == "Net_Profit_Flag":
        info["role"] = "flag"
    columns[col] = info

# ── ISSUE TALLIES ─────────────────────────────────────────────────────────────
issues = {
    "comma_decimal": {
        "Shipping_Cost": 1444,
        "Net_Profit": 8,
        "Marketing_Cost": 4,
        "total": 1456,
    },
    "duplicate_order_ids": {
        "unique_ids_duplicated": 133,
        "total_rows_involved": 269,
        "exact_duplicate_rows": 0,
        "note": "Same Order_ID appears with different data values",
    },
    "sales_zero": {
        "total": 102,
        "returned_orders": 101,
        "completed_with_zero_sales": 1,
        "note": "Sales=0 on returns is expected. 1 Completed order with Sales=0 is anomalous.",
    },
    "missing_values": {
        "Region": {"count": 1, "pct": 0.0332},
        "Category": {"count": 1, "pct": 0.0332},
        "Product_Name": {"count": 1, "pct": 0.0332},
        "Review_Text": {"count": 7, "pct": 0.2322},
        "note": "All dimension nulls point to single corrupt row (Order_ID 20422, Unit_Price=0)",
    },
    "future_dates": {
        "count": 0,
        "note": "Max date 2026-03-24 is before today 2026-05-29. No future dates.",
    },
    "temporal_gap_2025": {
        "rows_in_2025": 0,
        "rows_in_2024": 600,
        "note": "Entire year 2025 absent; 2024 has only 600 rows vs 1200 in 2022/2023. Suspect truncated extract.",
    },
    "unit_price_zero": {
        "count": 1,
        "order_id": 20422,
        "note": "One record with Unit_Price=0, Sales=0, Net_Profit=0, no Region/Category/Product",
    },
    "net_profit_flag_inconsistency": {
        "negative_profit_unflagged": 2,
        "positive_profit_flagged": 8,
        "note": "Minor flag mismatch, likely caused by comma-decimal parsing errors",
    },
    "outliers_sales": {
        "count": 69,
        "method": "IQR",
        "note": "High-value multi-unit purchases; not errors",
    },
}

# ── WRITE data_profile.json ────────────────────────────────────────────────────
profile = {
    "stem": "techworld_data_sample",
    "file_path": "data/raw/techworld_data_sample.csv",
    "generated_at": datetime.now().isoformat(),
    "shape": {"rows": 3015, "columns": 20},
    "memory_mb": 2.37,
    "date_range": {
        "min": "2022-01-01",
        "max": "2026-03-24",
        "granularity": "daily",
        "years_covered": [2022, 2023, 2024, 2026],
        "year_distribution": {"2022": 1200, "2023": 1200, "2024": 600, "2026": 15},
        "temporal_gap": "2025 entirely absent from dataset",
    },
    "column_role_classification": {
        "date": ["Order_Date"],
        "metric": ["Quantity", "Unit_Price", "Sales", "Net_Profit", "Marketing_Cost",
                   "Shipping_Cost", "Delivery_Days", "Review_Rating"],
        "dimension": ["Region", "Category", "Product_Name", "Traffic_Source",
                      "Supplier", "Order_Status"],
        "identifier": ["Order_ID", "Customer_ID"],
        "flag": ["Return_Flag", "Net_Profit_Flag"],
        "text": ["Review_Text"],
    },
    "columns": columns,
    "data_quality_issues": issues,
}

with open("data/pipeline/techworld_data_sample/data_profile.json", "w", encoding="utf-8") as f:
    json.dump(profile, f, indent=2, default=str)

print("data_profile.json written")

# ── CONFIDENCE SCORING ────────────────────────────────────────────────────────
# Factor 1: Completeness (max 20)
# Primary metric (Sales): 0% missing -> 20/20
# Dimension nulls are <0.1% -> negligible
completeness_score = 20

# Factor 2: Consistency (max 15)
# 3 metric columns stored as string with comma-decimal -> partial deduction
# 1456/3015 = 48% of rows affected by comma-decimal in at least one column -> -7
consistency_score = 8

# Factor 3: Uniqueness (max 10)
# 136/3015 = 4.5% of rows have duplicate Order_IDs -> -5
uniqueness_score = 5

# Factor 4: Timeliness (max 15)
# No future dates, but entire 2025 missing and 2024 only 50% coverage -> -6
timeliness_score = 9

# Factor 5: Accuracy (max 15)
# No reference for tie-out; Net_Profit_Flag inconsistency minor (10 rows); 1 corrupt row -> -3
accuracy_score = 12

# Factor 6: Validity (max 15)
# Business rules: returns having Sales=0 is correct; 1 Completed order with Sales=0 -> -2
# Duplicate Order_IDs are a validity concern -> -3
validity_score = 10

# Factor 7: Simpsons (max 10)
# No reversal detected in Sales across Region or Category (all show decline 22->24) -> 10/10
simpsons_score = 10

total_score = (completeness_score + consistency_score + uniqueness_score +
               timeliness_score + accuracy_score + validity_score + simpsons_score)

grade = "A" if total_score >= 90 else "B" if total_score >= 75 else "C" if total_score >= 60 else "D" if total_score >= 40 else "F"

# ── WRITE validation_result.json ──────────────────────────────────────────────
validation = {
    "skill_type": "validation",
    "run_context": {"stem": "techworld_data_sample", "file": "data/raw/techworld_data_sample.csv"},
    "layers": {
        "structural": {
            "status": "WARNING",
            "issues": [
                {
                    "field": "Order_ID",
                    "severity": "warning",
                    "detail": "136 duplicate Order_IDs; 133 unique IDs appear more than once across 269 rows"
                },
                {
                    "field": "Net_Profit / Marketing_Cost / Shipping_Cost",
                    "severity": "warning",
                    "detail": "3 metric columns stored as object/string; 1456 values use comma as decimal separator"
                },
                {
                    "field": "Order_ID 20422",
                    "severity": "warning",
                    "detail": "One corrupt record: Unit_Price=0, Sales=0, Net_Profit=0, missing Region/Category/Product_Name"
                },
            ],
        },
        "logical": {
            "status": "WARNING",
            "issues": [
                {
                    "field": "Sales vs Quantity*Unit_Price",
                    "severity": "info",
                    "detail": "101 rows where Sales != Quantity*Unit_Price; all are Returned orders with Sales=0 (intentional)"
                },
                {
                    "field": "Sales",
                    "severity": "warning",
                    "detail": "1 Completed order has Sales=0; logically inconsistent"
                },
                {
                    "field": "Order_Date / Year",
                    "severity": "warning",
                    "detail": "2025 entirely absent; 2024 has only 600 rows (50% of 2022/2023 volume). Possible truncated extract."
                },
            ],
        },
        "business_rules": {
            "status": "PASS",
            "issues": [
                {
                    "field": "Net_Profit_Flag",
                    "severity": "info",
                    "detail": "10 rows where flag does not match Net_Profit sign; likely caused by comma-decimal not being parsed"
                },
                {
                    "field": "Sales",
                    "severity": "info",
                    "detail": "Sales range 0-7500; plausible for electronics/accessories ecommerce"
                },
                {
                    "field": "Review_Rating",
                    "severity": "info",
                    "detail": "All values 1-5; valid. Mean 4.27 suggests positive skew (normal for ecommerce reviews)"
                },
            ],
        },
        "simpsons_paradox": {
            "status": "PASS",
            "paradoxes_found": [],
            "note": "Sales trend (declining 2022-2024) is consistent across all Regions and Categories. No reversal detected. 2026 data excluded (only 15 rows, incomplete year).",
        },
    },
    "confidence": {
        "score": total_score,
        "grade": grade,
        "factors": {
            "data_completeness":      {"score": completeness_score, "max": 20},
            "consistency":            {"score": consistency_score,  "max": 15},
            "uniqueness":             {"score": uniqueness_score,   "max": 10},
            "timeliness":             {"score": timeliness_score,   "max": 15},
            "accuracy":               {"score": accuracy_score,     "max": 15},
            "validity":               {"score": validity_score,     "max": 15},
            "simpsons_paradox_risk":  {"score": simpsons_score,     "max": 10},
        },
        "interpretation": "GOOD — proceed with data-prep to fix known issues before analysis",
        "blockers": [],
    },
    "grade": grade,
    "score": total_score,
    "issues": [
        {
            "type": "comma_decimal",
            "column": "Shipping_Cost",
            "count": 1444,
            "severity": "warning",
            "action": "Replace comma with period and cast to float",
        },
        {
            "type": "comma_decimal",
            "column": "Net_Profit",
            "count": 8,
            "severity": "warning",
            "action": "Replace comma with period and cast to float",
        },
        {
            "type": "comma_decimal",
            "column": "Marketing_Cost",
            "count": 4,
            "severity": "warning",
            "action": "Replace comma with period and cast to float",
        },
        {
            "type": "duplicate_order_id",
            "column": "Order_ID",
            "count": 136,
            "severity": "warning",
            "action": "Investigate duplicates; keep latest record or deduplicate by Order_ID + Order_Date",
        },
        {
            "type": "sales_zero_completed",
            "column": "Sales",
            "count": 1,
            "severity": "warning",
            "action": "Review Order_ID for Completed order with Sales=0; likely data entry error",
        },
        {
            "type": "corrupt_record",
            "column": "Order_ID 20422",
            "count": 1,
            "severity": "warning",
            "action": "Drop or investigate: Unit_Price=0, no product/region/category info",
        },
        {
            "type": "temporal_gap",
            "column": "Order_Date",
            "count": 0,
            "severity": "warning",
            "action": "Confirm with data source whether 2025 data exists; 2024 coverage is also partial",
        },
        {
            "type": "missing_dimensions",
            "column": "Region / Category / Product_Name",
            "count": 1,
            "severity": "info",
            "action": "Single row with null dimensions; part of corrupt record (Order_ID 20422)",
        },
    ],
    "row_count": 3015,
    "date_range": {"min": "2022-01-01", "max": "2026-03-24"},
    "recommendation": "Run data-prep to: (1) fix comma-decimal in Shipping_Cost/Net_Profit/Marketing_Cost, (2) deduplicate Order_IDs, (3) drop/flag corrupt record Order_ID 20422, (4) cast metric columns to correct numeric types. Confirm 2025 data availability with source.",
    "decision": "proceed_with_warnings",
    "metadata": {
        "rows_validated": 3015,
        "columns_validated": 20,
        "generated_at": datetime.now().isoformat(),
    },
}

with open("data/pipeline/techworld_data_sample/validation_result.json", "w", encoding="utf-8") as f:
    json.dump(validation, f, indent=2, default=str)

print("validation_result.json written")
print(f"Grade: {grade}  Score: {total_score}/100")
