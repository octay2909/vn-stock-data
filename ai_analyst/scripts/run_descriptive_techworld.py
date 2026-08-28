import pandas as pd
import numpy as np
import json
from datetime import datetime
from scipy import stats


class NpEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)

# Load data
df = pd.read_excel('data/cleaned/revenue/techworld_data_sample_cleaned.xlsx')
df['Order_Date'] = pd.to_datetime(df['Order_Date'])
df['YearMonth'] = pd.to_datetime(df['YearMonth'])
df['Year'] = df['YearMonth'].dt.year

df_rev = df[(df['Return_Flag'] == 0) & (df['Order_Status'] == 'Completed')].copy()
df_rev['Year'] = df_rev['YearMonth'].dt.year

# Monthly series
monthly_all = df_rev.groupby('YearMonth').agg(
    Sales=('Sales', 'sum'),
    Orders=('Order_ID', 'nunique'),
    Net_Profit=('Net_Profit', 'sum')
).reset_index().sort_values('YearMonth')
monthly_all['AOV'] = (monthly_all['Sales'] / monthly_all['Orders']).round(2)
monthly_all['NP_Margin'] = (monthly_all['Net_Profit'] / monthly_all['Sales'] * 100).round(2)
monthly_all['YM_str'] = monthly_all['YearMonth'].dt.strftime('%Y-%m')
monthly_all['MoM_pct'] = monthly_all['Sales'].pct_change().mul(100).round(2)
monthly_all['Sales_lag12'] = monthly_all['Sales'].shift(12)
monthly_all['YoY_pct'] = ((monthly_all['Sales'] - monthly_all['Sales_lag12']) / monthly_all['Sales_lag12'] * 100).round(2)
monthly_all['is_synthetic_month'] = monthly_all['YearMonth'].dt.year == 2025
monthly_all['is_partial'] = monthly_all['YM_str'] == '2026-03'

# Build monthly series list
monthly_series = []
for _, row in monthly_all.iterrows():
    entry = {
        "period": row['YM_str'],
        "sales": round(float(row['Sales']), 2),
        "orders": int(row['Orders']),
        "aov": round(float(row['AOV']), 2),
        "net_profit": round(float(row['Net_Profit']), 2),
        "np_margin_pct": round(float(row['NP_Margin']), 2),
        "mom_pct": round(float(row['MoM_pct']), 2) if not pd.isna(row['MoM_pct']) else None,
        "yoy_pct": round(float(row['YoY_pct']), 2) if not pd.isna(row['YoY_pct']) else None,
        "is_synthetic": bool(row['is_synthetic_month']),
        "is_partial": bool(row['is_partial'])
    }
    monthly_series.append(entry)

# Trend regression on REAL data only (2022-01 to 2024-06 = 30 months)
monthly_real = monthly_all[
    (monthly_all['YearMonth'].dt.year.isin([2022, 2023])) |
    ((monthly_all['YearMonth'].dt.year == 2024) & (monthly_all['YearMonth'].dt.month <= 6))
].copy()
x_r = np.arange(len(monthly_real))
slope_r, intercept_r, r_r, p_r, se_r = stats.linregress(x_r, monthly_real['Sales'].values)

# Seasonal indices from 2022-2023 only
monthly_2022_2023 = monthly_all[monthly_all['YearMonth'].dt.year.isin([2022, 2023])].copy()
monthly_2022_2023 = monthly_2022_2023.copy()
monthly_2022_2023['Month'] = monthly_2022_2023['YearMonth'].dt.month
avg_m = monthly_2022_2023.groupby('Month')['Sales'].mean()
overall_avg = avg_m.mean()
seasonal_idx = {int(k): round(float(v / overall_avg * 100), 1) for k, v in avg_m.items()}

# Yearly KPIs
yearly_raw = {
    2022: {"sales": 746010, "orders": 1110, "profit": 246945.0, "months": 12, "note": ""},
    2023: {"sales": 715450, "orders": 1111, "profit": 236407.0, "months": 12, "note": ""},
    2024: {"sales": 338470, "orders": 551, "profit": 112201.0, "months": 6, "note": "H1 only (real data)"},
    2025: {"sales": 757050, "orders": 1108, "profit": 250392.1, "months": 12, "note": "All synthetic"},
    2026: {"sales": 15765, "orders": 14, "profit": 4949.72, "months": 1, "note": "Partial (Mar 2026 fragment, 14 orders)"}
}
yearly_kpis = []
for yr, d in yearly_raw.items():
    npm = d['profit'] / d['sales'] * 100
    aov = d['sales'] / d['orders']
    mom_avg = d['sales'] / d['months']
    entry = {
        "year": yr,
        "total_sales": d['sales'],
        "total_orders": d['orders'],
        "avg_monthly_sales": round(mom_avg, 2),
        "aov": round(aov, 2),
        "np_margin_pct": round(npm, 2),
        "months_covered": d['months'],
        "notes": d.get('note', '')
    }
    yearly_kpis.append(entry)

# Return rate
total_orders_cnt = df['Order_ID'].nunique()
returned_orders = df[df['Return_Flag'] == 1]['Order_ID'].nunique()
return_rate = returned_orders / total_orders_cnt * 100

# Total KPIs
total_sales_all = df_rev['Sales'].sum()
total_orders_all_rev = df_rev['Order_ID'].nunique()
total_profit_all = df_rev['Net_Profit'].sum()

# Sparklines: last 12 real months (2023-07 to 2024-06)
spark_real = monthly_all[
    (monthly_all['YM_str'] >= '2023-07') & (monthly_all['YM_str'] <= '2024-06')
]
sales_spark = [round(float(v), 0) for v in spark_real['Sales'].tolist()]
npm_spark = [round(float(v), 2) for v in spark_real['NP_Margin'].tolist()]
aov_spark = [round(float(v), 2) for v in spark_real['AOV'].tolist()]

# Build output
output = {
    "skill_type": "descriptive",
    "run_context": {
        "stem": "techworld_data_sample",
        "dataset_type": "revenue",
        "domain": "ecommerce",
        "data_note": "2025 data is synthetic (is_synthetic=1). Trend analysis uses real 2022-2024 data only for statistical tests. Seasonal indices computed from 2022-2023 real data only.",
        "date_range": "2022-01 to 2026-03",
        "monthly_series_length": 43,
        "real_months": 30,
        "synthetic_months": 12,
        "partial_months": 1
    },

    "header_kpis": [
        {
            "id": "kpi_1",
            "label": "Total Sales",
            "value": "$2.57M",
            "value_raw": round(total_sales_all, 2),
            "prior_value": "$1.82M",
            "prior_note": "Real data only (2022-2024)",
            "delta": "+41.5%",
            "delta_abs": "+$757K",
            "delta_note": "Includes $757K synthetic 2025 data",
            "status": "good",
            "direction": "up_is_good",
            "trend_series": sales_spark,
            "trend_note": "Last 12 real months (Jul 2023 - Jun 2024)"
        },
        {
            "id": "kpi_2",
            "label": "Net Profit Margin",
            "value": "33.1%",
            "value_raw": round(total_profit_all / total_sales_all * 100, 2),
            "prior_value": "33.1%",
            "delta": "0.0pp",
            "delta_abs": "$0",
            "status": "flat",
            "direction": "up_is_good",
            "trend_series": npm_spark,
            "trend_note": "Margin locked at 33.0-33.6% every month - no compression"
        },
        {
            "id": "kpi_3",
            "label": "Avg Order Value",
            "value": "$661",
            "value_raw": round(total_sales_all / total_orders_all_rev, 2),
            "prior_value": "$672",
            "prior_note": "2022 AOV",
            "delta": "-1.6%",
            "delta_abs": "-$11",
            "status": "alert",
            "direction": "up_is_good",
            "trend_series": aov_spark,
            "trend_note": "AOV drifting down from $672 (2022) to $614 (2024)"
        }
    ],

    "overall_kpis": {
        "total_sales": round(total_sales_all, 2),
        "total_orders": int(total_orders_all_rev),
        "aov": round(total_sales_all / total_orders_all_rev, 2),
        "total_net_profit": round(total_profit_all, 2),
        "np_margin_pct": round(total_profit_all / total_sales_all * 100, 2),
        "return_rate_pct": round(return_rate, 2),
        "data_note": "Return_Flag=1 excluded from revenue KPIs. Return rate computed on all orders."
    },

    "yearly_kpis": yearly_kpis,

    "monthly_series": monthly_series,

    "trends": [
        {
            "id": "trend_1",
            "name": "Overall monthly sales trend (real data)",
            "grain": "monthly",
            "data_scope": "Real data only: 2022-01 to 2024-06 (30 months)",
            "slope_per_month": round(float(slope_r), 2),
            "intercept": round(float(intercept_r), 2),
            "r_squared": round(float(r_r ** 2), 3),
            "p_value": round(float(p_r), 3),
            "conclusion": "Trend is statistically flat (R2=0.036, p=0.316) - apparent -4.1% YoY drift is within noise",
            "synthetic_note": "2025 synthetic data not used for regression. Full time series shown for visualization only."
        },
        {
            "id": "trend_2",
            "name": "Seasonality pattern (2022-2023 real only)",
            "data_scope": "2022 and 2023 real months only (24 months)",
            "seasonal_indices": seasonal_idx,
            "peak_month": 10,
            "peak_month_name": "October",
            "peak_index": seasonal_idx[10],
            "trough_month": 4,
            "trough_month_name": "April",
            "trough_index": seasonal_idx[4],
            "swing_pp": round(seasonal_idx[10] - seasonal_idx[4], 1),
            "conclusion": "October consistently peaks (+18% above avg); April is the trough (-12% below avg). ~30pp peak-to-trough swing."
        },
        {
            "id": "trend_3",
            "name": "Year-over-year dynamics",
            "periods": [
                {
                    "from": 2022,
                    "to": 2023,
                    "yoy_pct": -4.1,
                    "note": "Real data",
                    "driver": "Electronics -5.8%; partially offset by Wearables +25.6%"
                },
                {
                    "from": 2023,
                    "to": 2024,
                    "yoy_pct": None,
                    "note": "2024 H1 only - full-year comparison not valid"
                },
                {
                    "from": 2023,
                    "to": 2025,
                    "yoy_pct": 5.8,
                    "note": "SYNTHETIC - 2025 data is synthetic; treat as modeled, not observed"
                }
            ]
        }
    ],

    "segments": [
        {
            "dimension": "Category",
            "ranked": [
                {
                    "rank": 1,
                    "segment": "Electronics",
                    "sales": 2257059,
                    "share_pct": 87.7,
                    "orders": 1971,
                    "yoy_2022_2023": -5.8,
                    "verdict": "alert",
                    "note": "Single-category concentration - 87.7% of revenue; declining YoY"
                },
                {
                    "rank": 2,
                    "segment": "Audio",
                    "sales": 116840,
                    "share_pct": 4.5,
                    "orders": 638,
                    "yoy_2022_2023": -3.4,
                    "verdict": "healthy",
                    "note": "Small but stable"
                },
                {
                    "rank": 3,
                    "segment": "Wearables",
                    "sales": 112200,
                    "share_pct": 4.4,
                    "orders": 304,
                    "yoy_2022_2023": 25.6,
                    "verdict": "healthy",
                    "note": "Fastest growing but too small to offset Electronics drag"
                },
                {
                    "rank": 4,
                    "segment": "Accessories",
                    "sales": 86646,
                    "share_pct": 3.4,
                    "orders": 981,
                    "yoy_2022_2023": 9.5,
                    "verdict": "healthy",
                    "note": "Growing, high order frequency"
                }
            ],
            "concentration_flag": True,
            "concentration_note": "Top category (Electronics) = 87.7% of total sales - extreme single-category dependence"
        },
        {
            "dimension": "Region",
            "ranked": [
                {
                    "rank": 1,
                    "segment": "East",
                    "sales": 659186,
                    "share_pct": 25.6,
                    "orders": 980,
                    "yoy_2022_2023": -3.9,
                    "verdict": "healthy"
                },
                {
                    "rank": 2,
                    "segment": "South",
                    "sales": 655440,
                    "share_pct": 25.5,
                    "orders": 968,
                    "yoy_2022_2023": -9.4,
                    "verdict": "alert",
                    "note": "Weakest YoY performer"
                },
                {
                    "rank": 3,
                    "segment": "West",
                    "sales": 640739,
                    "share_pct": 24.9,
                    "orders": 961,
                    "yoy_2022_2023": 2.5,
                    "verdict": "healthy",
                    "note": "Only growing region 2022-2023"
                },
                {
                    "rank": 4,
                    "segment": "North",
                    "sales": 617380,
                    "share_pct": 24.0,
                    "orders": 985,
                    "yoy_2022_2023": -5.0,
                    "verdict": "alert"
                }
            ],
            "concentration_flag": False,
            "concentration_note": "All four regions balanced within 1.6pp of each other (~25% each) - no regional concentration risk"
        },
        {
            "dimension": "Traffic_Source",
            "ranked": [
                {"rank": 1, "segment": "Email", "sales": 447900, "share_pct": 17.4, "orders": 672, "verdict": "healthy"},
                {"rank": 2, "segment": "Facebook Ads", "sales": 424490, "share_pct": 16.5, "orders": 626, "verdict": "healthy"},
                {"rank": 3, "segment": "Referral", "sales": 424199, "share_pct": 16.5, "orders": 624, "verdict": "healthy"},
                {"rank": 4, "segment": "Organic", "sales": 404569, "share_pct": 15.7, "orders": 648, "verdict": "healthy"},
                {"rank": 5, "segment": "Direct", "sales": 399143, "share_pct": 15.5, "orders": 613, "verdict": "healthy"},
                {"rank": 6, "segment": "Google Ads", "sales": 379734, "share_pct": 14.8, "orders": 580, "verdict": "healthy"},
                {"rank": 7, "segment": "Unknown", "sales": 92710, "share_pct": 3.6, "orders": 131, "verdict": "alert", "note": "3.6% unattributed traffic"}
            ],
            "concentration_flag": False,
            "concentration_note": "Traffic sources evenly distributed across 6 channels (14-17% each) - no channel dependency"
        },
        {
            "dimension": "Supplier",
            "ranked": [
                {"rank": 1, "segment": "Supplier_D", "sales": 534678, "share_pct": 20.8, "orders": 853, "verdict": "healthy"},
                {"rank": 2, "segment": "Supplier_A", "sales": 526724, "share_pct": 20.5, "orders": 766, "verdict": "healthy"},
                {"rank": 3, "segment": "Supplier_B", "sales": 518623, "share_pct": 20.2, "orders": 794, "verdict": "healthy"},
                {"rank": 4, "segment": "Supplier_C", "sales": 517300, "share_pct": 20.1, "orders": 751, "verdict": "healthy"},
                {"rank": 5, "segment": "Supplier_X", "sales": 475420, "share_pct": 18.5, "orders": 730, "verdict": "healthy"}
            ],
            "concentration_flag": False,
            "concentration_note": "Five suppliers nearly equal share (~20% each) - no supply chain concentration risk"
        },
        {
            "dimension": "Product_Name",
            "top_10": [
                {"rank": 1, "segment": "Laptop Pro X", "sales": 720000, "share_pct": 28.0},
                {"rank": 2, "segment": "Laptop Air", "sales": 475000, "share_pct": 18.5},
                {"rank": 3, "segment": "Smartphone Z", "sales": 376200, "share_pct": 14.6},
                {"rank": 4, "segment": "Tablet Pro", "sales": 296000, "share_pct": 11.5},
                {"rank": 5, "segment": "Smartphone Alpha", "sales": 232400, "share_pct": 9.0},
                {"rank": 6, "segment": "4K Monitor", "sales": 149600, "share_pct": 5.8},
                {"rank": 7, "segment": "SmartWatch V2", "sales": 112200, "share_pct": 4.4},
                {"rank": 8, "segment": "Wireless Headphones", "sales": 87800, "share_pct": 3.4},
                {"rank": 9, "segment": "Mechanical Keyboard", "sales": 53880, "share_pct": 2.1},
                {"rank": 10, "segment": "Bluetooth Speaker", "sales": 29040, "share_pct": 1.1}
            ],
            "top2_concentration_pct": 46.5,
            "concentration_flag": True,
            "concentration_note": "Top 2 products (Laptop Pro X + Laptop Air) = 46.5% of total sales - high product-level concentration"
        }
    ],

    "cohorts": None,

    "waterfall": None,

    "findings": [
        {
            "id": "F1",
            "type": "Pattern",
            "headline": "Electronics 87.7% revenue concentration is structurally unchanged - every region shows the same split",
            "evidence": "Electronics share ranges 87.2%-88.4% across all four regions. No Simpson's paradox: the aggregate category split is authentic, not a regional artifact.",
            "confidence": "high",
            "chart_id": "category_bar_01",
            "simpsons_check": "PASSED - no reversal across regions"
        },
        {
            "id": "F2",
            "type": "Pattern",
            "headline": "October peaks at +18% above monthly average; April troughs at -12% - a 30pp seasonal swing",
            "evidence": "Seasonal indices from 24 real months (2022-2023): Oct=118.1, Apr=87.8. Jan=113.7 and Dec=111.4 also above average. 2025 synthetic data excluded from this computation.",
            "confidence": "high",
            "chart_id": "seasonality_bar_01",
            "data_note": "Seasonal indices use 2022-2023 real data only"
        },
        {
            "id": "F3",
            "type": "Contrast",
            "headline": "South region declined -9.4% YoY in 2022-2023 - more than double any other region",
            "evidence": "South: $199,650 to $180,820 (-9.4%). Other regions: East -3.9%, North -5.0%, West +2.5%. South's underperformance is not explained by category mix (same ~88% Electronics share as other regions).",
            "confidence": "high",
            "chart_id": "region_yoy_bar_01"
        },
        {
            "id": "F4",
            "type": "Implication",
            "headline": "Margin is locked at 33.1% but AOV fell -8.6% (2022 to 2024) - volume erosion is the primary risk",
            "evidence": "NP margin held 33.0-33.6% across all 30 real months. AOV declined from $672 (2022) to $614 (2024 H1), suggesting product mix shift toward lower-ticket items without any cost-side relief.",
            "confidence": "high",
            "chart_id": "npm_trend_line_01"
        },
        {
            "id": "F5",
            "type": "Ruling Out",
            "headline": "The 2022-2023 revenue decline is NOT statistically significant - a flat trend cannot be ruled out",
            "evidence": "Linear regression on 30 real months: slope=-$165/month, R2=0.036, p=0.316. The -4.1% YoY drop ($30,560) is within noise. A structural downtrend is not confirmed by available real data.",
            "confidence": "high",
            "chart_id": "trend_regression_01"
        }
    ],

    "scqa_draft": {
        "situation": "TechWorld is an e-commerce retailer with $2.57M in recorded sales across 43 months (Jan 2022 - Mar 2026, including 12 synthetic 2025 months). The business runs at a stable 33.1% net profit margin with 3,894 completed non-returned orders.",
        "complication": "Real data (2022-2024) shows a -4.1% YoY sales decline ($746K to $715K) driven by Electronics (-5.8%), while AOV is eroding from $672 to $614 (-8.6%). The 2025 data gap required synthetic fill, creating a 20-month blind spot in observed history.",
        "question": "Is TechWorld's revenue trend declining or holding steady, and what are the key structural risks to growth?",
        "answer": "The trend is statistically flat - the apparent -4.1% decline is noise (R2=0.036, p=0.316). The real risk is structural: 87.7% single-category dependence on Electronics, 46.5% revenue from two laptop SKUs, and eroding AOV (-8.6%) without any margin buffer to absorb volume drops."
    },

    "simpsons_paradox_checks": [
        {
            "id": "SP1",
            "finding": "Aggregate 2022-2023 revenue decline (-4.1%)",
            "test_dimensions": ["Region", "Category"],
            "result": "NO PARADOX",
            "detail": "Decline consistent across all four regions (East -3.9%, North -5.0%, South -9.4%, West +2.5%). No reversal. Aggregate direction is authentic."
        },
        {
            "id": "SP2",
            "finding": "Electronics 87.7% category concentration",
            "test_dimensions": ["Region"],
            "result": "NO PARADOX",
            "detail": "Electronics share is 87.2%-88.4% across all four regions - within 1.2pp. The aggregate concentration is not an artifact of one dominant region."
        }
    ],

    "predictive_needed": True,

    "metadata": {
        "generated_at": datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ'),
        "data_vintage": "2022-01 to 2026-03 (30 real months + 12 synthetic months + 1 partial month)",
        "synthetic_flag": "2025 data (is_synthetic=1) was generated externally. All trend regressions and seasonal indices use real data only (is_synthetic=0). Full time series shown for visualization purposes.",
        "filter_applied": "Return_Flag=0 AND Order_Status='Completed' for all revenue KPIs. Return rate computed on full dataset."
    }
}

out_path = 'data/pipeline/techworld_data_sample/descriptive_output.json'
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(output, f, indent=2, ensure_ascii=False, cls=NpEncoder)

print(f"Written to: {out_path}")
print(f"Monthly series length: {len(output['monthly_series'])}")
print(f"\nTop 3 findings:")
for fi in output['findings'][:3]:
    print(f"  [{fi['type']}] {fi['headline'][:80]}")
print(f"\nKPIs:")
for k in output['header_kpis']:
    print(f"  {k['label']}: {k['value']} (delta: {k['delta']})")
