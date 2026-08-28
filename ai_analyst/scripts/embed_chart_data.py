#!/usr/bin/env python3
"""
embed_chart_data.py — Embeds actual data arrays into story_arc.json chart_requirements.
Run once before render_charts_swd.py.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PIPELINE = ROOT / "data" / "pipeline" / "techworld_data"


def load(name):
    with open(PIPELINE / name, encoding="utf-8") as f:
        return json.load(f)


def save(obj, name):
    with open(PIPELINE / name, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)


def main():
    arc = load("story_arc.json")
    desc = load("descriptive_output.json")
    diag = load("diagnostic_output.json")
    pred = load("predictive_output.json")

    # ── Build month label list from monthly_trend ─────────────────────────────
    monthly_trend = desc["monthly_trend"]
    month_labels = []
    for m in monthly_trend:
        yr, mo = m["month"].split("-")
        month_abbr = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
        month_labels.append(f"{month_abbr[int(mo)-1]} {yr[-2:]}")  # e.g. "Jan 22"

    revenues = [m["revenue"] for m in monthly_trend]
    net_profits = [m["net_profit"] for m in monthly_trend]
    orders_list = [m["orders"] for m in monthly_trend]

    # ── Electronics monthly revenue ───────────────────────────────────────────
    electronics_monthly = desc["by_category"]["Electronics"]["monthly_revenue"]

    # ── Build data for each chart_requirement ────────────────────────────────
    data_map = {}

    # 1. monthly_revenue_trend — highlight_line
    data_map["monthly_revenue_trend"] = {
        "x": month_labels,
        "y": revenues,
        "highlight_points": [1, 13],    # Feb 2022 (idx 1) and Feb 2023 (idx 13) as low points
        "value_format": "K",
        "y_label": "Monthly Revenue ($)",
    }

    # 2. yoy_kpi_comparison — grouped_bar: show Revenue, Net Profit, Orders as % YoY change
    yoy = desc["yoy_comparison"]
    data_map["yoy_kpi_comparison"] = {
        "categories": ["Revenue", "Net Profit", "Orders"],
        "groups": [
            {
                "name": "2022 (Jan-Sep)",
                "values": [
                    yoy["y2022_jan_sep_revenue"] / 1e6,
                    yoy["y2022_jan_sep_profit"] / 1e6,
                    yoy["y2022_jan_sep_orders"] / 1000,
                ],
                "highlight": False,
            },
            {
                "name": "2023 (Jan-Sep)",
                "values": [
                    yoy["y2023_jan_sep_revenue"] / 1e6,
                    yoy["y2023_jan_sep_profit"] / 1e6,
                    yoy["y2023_jan_sep_orders"] / 1000,
                ],
                "highlight": True,
            },
        ],
        "value_format": "auto",
        "y_label": "Value (M$ or K orders)",
    }

    # 3. category_revenue_share — horizontal_bar sorted descending, highlight Electronics
    by_cat = desc["by_category"]
    cat_names = ["Electronics", "Wearables", "Audio", "Accessories"]
    cat_revenues = [by_cat[c]["revenue"] for c in cat_names]
    data_map["category_revenue_share"] = {
        "categories": cat_names,
        "values": cat_revenues,
        "highlight": ["Electronics"],
        "value_format": "M",
        "x_label": "Revenue ($)",
    }

    # 4. region_slope_comparison — slopegraph: 2022 revenue vs 2023 revenue by region
    by_reg = desc["by_region"]
    reg_names = ["East", "West", "North", "South"]
    # Annual 2022 and 2023 from diagnostic annual_revenue_by_region
    annual = diag["regional_divergence"]["annual_revenue_by_region"]
    reg_2022 = [annual["2022"][r] for r in reg_names]
    reg_2023 = [annual["2023"][r] for r in reg_names]
    data_map["region_slope_comparison"] = {
        "labels": reg_names,
        "before": [v / 1000 for v in reg_2022],   # in $K
        "after": [v / 1000 for v in reg_2023],
        "before_label": "2022",
        "after_label": "2023",
        "highlight": ["West"],   # West is the only positive region
        "value_format": "K",
    }

    # 5. segment_revenue_breakdown — horizontal_bar: high-value vs standard
    seg = desc["segment_analysis"]
    data_map["segment_revenue_breakdown"] = {
        "categories": ["High-Value (>$1K)", "Standard (<$1K)"],
        "values": [seg["high_value"]["revenue"], seg["standard"]["revenue"]],
        "highlight": ["High-Value (>$1K)"],
        "value_format": "M",
        "x_label": "Revenue ($)",
    }

    # 6. feb_seasonal_trough — highlight_line: same as monthly trend but highlight Feb months
    data_map["feb_seasonal_trough"] = {
        "x": month_labels,
        "y": revenues,
        "highlight_points": [1, 13],  # Feb 2022 idx=1, Feb 2023 idx=13
        "highlight_range": [1, 1],    # shade Feb 2022
        "value_format": "K",
        "y_label": "Monthly Revenue ($)",
    }

    # 7. volume_price_decomposition — horizontal_bar (2 bars: Volume 70%, Price 30%)
    data_map["volume_price_decomposition"] = {
        "categories": ["Volume Effect", "Price Effect"],
        "values": [69.9, 30.1],
        "highlight": ["Volume Effect"],
        "value_format": "pct",
        "x_label": "% of Revenue Variance Explained",
    }

    # 8. orders_vs_revenue_scatter — scatter_regression: orders vs revenue per month
    data_map["orders_vs_revenue_scatter"] = {
        "x": orders_list,
        "y": revenues,
        "x_label": "Monthly Orders",
        "y_label": "Monthly Revenue ($)",
        "highlight_indices": [],
        "r_squared": round(0.774 ** 2, 3),   # r=0.774 -> r²=0.599
    }

    # 9. category_concentration_bar — horizontal_bar: same data as category_revenue_share
    data_map["category_concentration_bar"] = {
        "categories": cat_names,
        "values": cat_revenues,
        "highlight": ["Electronics"],
        "value_format": "M",
        "x_label": "Revenue ($)",
    }

    # 10. electronics_vs_total_trend — multi_line: Electronics monthly revenue vs total
    data_map["electronics_vs_total_trend"] = {
        "x": month_labels,
        "series": [
            {
                "name": "Total",
                "values": revenues,
                "highlight": False,
            },
            {
                "name": "Electronics",
                "values": electronics_monthly,
                "highlight": True,
            },
        ],
        "value_format": "K",
        "y_label": "Monthly Revenue ($)",
    }

    # 11. regional_yoy_comparison — slopegraph: 2022 vs 2023 annual revenue by region
    #     Same data as region_slope_comparison but highlight East (worst)
    data_map["regional_yoy_comparison"] = {
        "labels": reg_names,
        "before": [v / 1000 for v in reg_2022],
        "after": [v / 1000 for v in reg_2023],
        "before_label": "2022",
        "after_label": "2023",
        "highlight": ["East"],   # highlight worst performer
        "value_format": "K",
    }

    # 12. south_category_trend — highlight_line: South monthly revenue (21 months)
    south_monthly = by_reg["South"]["monthly_revenue"]
    data_map["south_category_trend"] = {
        "x": month_labels,
        "y": south_monthly,
        "highlight_points": [4, 5],   # May/Jun 2022 are local troughs
        "value_format": "K",
        "y_label": "South Monthly Revenue ($)",
    }

    # 13. forecast_line_q4 — forecast_line: 21 historical + 3 forecast months
    forecast = pred["forecast"]
    all_x = month_labels + ["Oct 23", "Nov 23", "Dec 23"]
    historical = revenues + [None, None, None]
    forecast_vals = [None] * 21 + [f["predicted"] for f in forecast]
    ci_low = [None] * 21 + [f["lower_95"] for f in forecast]
    ci_high = [None] * 21 + [f["upper_95"] for f in forecast]
    data_map["forecast_line_q4"] = {
        "x": all_x,
        "historical": historical,
        "forecast": forecast_vals,
        "ci_low": ci_low,
        "ci_high": ci_high,
        "split_idx": 20,    # last historical point is index 20 (Sep 2023)
        "value_format": "K",
        "y_label": "Monthly Revenue ($)",
    }

    # 14. model_comparison_mape — model_comparison_bar: 3 models by MAPE
    models_data = pred["models"]
    data_map["model_comparison_mape"] = {
        "models": ["Linear Trend", "Holt-Winters", "ARIMA"],
        "scores": [
            models_data["linear_trend"]["mape"],
            models_data["holt_winters"]["mape"],
            models_data["arima"]["mape"],
        ],
        "metric_name": "MAPE (%)",
        "highlight": ["Linear Trend"],   # best model
    }

    # ── Embed data into chart_requirements ────────────────────────────────────
    updated = 0
    skipped = 0
    for req in arc["chart_requirements"]:
        cid = req["chart_id"]
        if cid in data_map:
            req["data"] = data_map[cid]
            updated += 1
            print(f"  [ok]  Embedded data for: {cid}")
        else:
            skipped += 1
            print(f"  [--]  No mapping found for: {cid}")

    save(arc, "story_arc.json")
    print(f"\nDone: {updated} charts updated, {skipped} skipped -> story_arc.json saved.")


if __name__ == "__main__":
    main()
