import pandas as pd
import numpy as np
from scipy import stats
import json
from datetime import datetime

df = pd.read_excel('data/cleaned/revenue/techworld_data_sample_cleaned.xlsx')
rev = df[df['Return_Flag'] == 0].copy()
rev['year'] = rev['Order_Date'].dt.year
rev['month'] = rev['Order_Date'].dt.month

# Monthly series
monthly = rev.groupby('YearMonth').agg(
    sales=('Sales', 'sum'),
    orders=('Order_ID', 'nunique'),
    net_profit=('Net_Profit', 'sum'),
    marketing_cost=('Marketing_Cost', 'sum')
).reset_index().sort_values('YearMonth').reset_index(drop=True)
monthly['aov'] = monthly['sales'] / monthly['orders']
monthly['np_margin'] = monthly['net_profit'] / monthly['sales'] * 100
monthly['mom_growth_pct'] = monthly['sales'].pct_change() * 100

monthly_map = dict(zip(monthly['YearMonth'], monthly['sales']))

def yoy(row):
    yr = int(row['YearMonth'][:4])
    mo = row['YearMonth'][5:]
    if yr == 2026:
        return None  # 2025 gap
    prev = f"{yr-1}-{mo}"
    if prev in monthly_map:
        return round((row['sales'] - monthly_map[prev]) / monthly_map[prev] * 100, 2)
    return None

monthly['yoy_growth_pct'] = monthly.apply(yoy, axis=1)

# Trend (exclude partial 2026-03)
monthly_fit = monthly[monthly['YearMonth'] != '2026-03'].copy().reset_index(drop=True)
monthly_fit['t'] = np.arange(len(monthly_fit))
slope, intercept, r_value, p_value, se = stats.linregress(monthly_fit['t'], monthly_fit['sales'])
r2 = r_value**2
trend_dir = 'declining' if slope < -50 else ('growing' if slope > 50 else 'flat')

# Seasonality (2022+2023 full years)
full_years = monthly_fit[monthly_fit['YearMonth'] < '2024-01'].copy()
full_years['month_num'] = full_years['YearMonth'].str[5:].astype(int)
seas = full_years.groupby('month_num')['sales'].mean().to_dict()
overall_mean = full_years['sales'].mean()
seas_index = {k: round(v/overall_mean*100, 1) for k, v in seas.items()}
MONTHS = {1:'Jan',2:'Feb',3:'Mar',4:'Apr',5:'May',6:'Jun',7:'Jul',8:'Aug',9:'Sep',10:'Oct',11:'Nov',12:'Dec'}
peak_m = max(seas_index, key=seas_index.get)
trough_m = min(seas_index, key=seas_index.get)

# Overall KPIs
total_sales = float(rev['Sales'].sum())
total_orders = int(rev['Order_ID'].nunique())
aov_overall = total_sales / total_orders
total_net_profit = float(rev['Net_Profit'].sum())
net_profit_margin_pct = (total_net_profit / total_sales) * 100
return_rate_pct = float(df['Return_Flag'].mean() * 100)

# By year
by_year = rev.groupby('year').agg(
    sales=('Sales', 'sum'),
    orders=('Order_ID', 'nunique'),
    net_profit=('Net_Profit', 'sum')
).reset_index()
by_year['aov'] = by_year['sales'] / by_year['orders']
by_year['np_margin_pct'] = by_year['net_profit'] / by_year['sales'] * 100

notes_map = {2022: 'full year', 2023: 'full year', 2024: 'partial - Jan-Jun only', 2026: 'partial - Mar only (2025 absent)'}
by_year_list = []
for _, r in by_year.iterrows():
    by_year_list.append({
        'year': int(r['year']),
        'sales': round(float(r['sales']), 0),
        'orders': int(r['orders']),
        'aov': round(float(r['aov']), 2),
        'net_profit': round(float(r['net_profit']), 0),
        'np_margin_pct': round(float(r['np_margin_pct']), 2),
        'note': notes_map.get(int(r['year']), '')
    })

# By region
rev_r = rev.dropna(subset=['Region'])
by_region_df = rev_r.groupby('Region').agg(sales=('Sales','sum'), orders=('Order_ID','nunique')).reset_index()
total_r = by_region_df['sales'].sum()
by_region_df['pct_share'] = by_region_df['sales'] / total_r * 100
by_region_df = by_region_df.sort_values('sales', ascending=False)
region_22 = rev_r[rev_r['year']==2022].groupby('Region')['Sales'].sum()
region_23 = rev_r[rev_r['year']==2023].groupby('Region')['Sales'].sum()

by_region_list = []
for _, r in by_region_df.iterrows():
    reg = r['Region']
    v22 = region_22.get(reg, 0)
    v23 = region_23.get(reg, 0)
    chg = (v23 - v22) / v22 * 100 if v22 > 0 else None
    trend_d = 'growing' if chg and chg > 1 else ('declining' if chg and chg < -1 else 'flat')
    by_region_list.append({
        'region': reg,
        'sales': round(float(r['sales']), 0),
        'orders': int(r['orders']),
        'pct_share': round(float(r['pct_share']), 2),
        'yoy_2022_2023_pct': round(chg, 1) if chg is not None else None,
        'trend_direction': trend_d
    })

# By category
rev_c = rev.dropna(subset=['Category'])
by_cat_df = rev_c.groupby('Category').agg(sales=('Sales','sum'), orders=('Order_ID','nunique')).reset_index()
total_c = by_cat_df['sales'].sum()
by_cat_df['pct_share'] = by_cat_df['sales'] / total_c * 100
by_cat_df = by_cat_df.sort_values('sales', ascending=False)
cat_22 = rev_c[rev_c['year']==2022].groupby('Category')['Sales'].sum()
cat_23 = rev_c[rev_c['year']==2023].groupby('Category')['Sales'].sum()

by_cat_list = []
for _, r in by_cat_df.iterrows():
    cat = r['Category']
    v22 = cat_22.get(cat, 0)
    v23 = cat_23.get(cat, 0)
    chg = (v23 - v22) / v22 * 100 if v22 > 0 else None
    trend_d = 'growing' if chg and chg > 1 else ('declining' if chg and chg < -1 else 'flat')
    by_cat_list.append({
        'category': cat,
        'sales': round(float(r['sales']), 0),
        'orders': int(r['orders']),
        'pct_share': round(float(r['pct_share']), 2),
        'yoy_2022_2023_pct': round(chg, 1) if chg is not None else None,
        'trend_direction': trend_d
    })

# Top 10 products
rev_p = rev.dropna(subset=['Product_Name'])
by_prod_df = rev_p.groupby('Product_Name').agg(sales=('Sales','sum'), orders=('Order_ID','nunique')).reset_index()
by_prod_df['pct_share'] = by_prod_df['sales'] / by_prod_df['sales'].sum() * 100
by_prod_df = by_prod_df.sort_values('sales', ascending=False).head(10)
by_prod_list = [{'product_name': r['Product_Name'], 'sales': round(float(r['sales']), 0),
                 'orders': int(r['orders']), 'pct_share': round(float(r['pct_share']), 2)}
                for _, r in by_prod_df.iterrows()]

# By traffic source
by_ts_df = rev.groupby('Traffic_Source').agg(sales=('Sales','sum'), orders=('Order_ID','nunique')).reset_index()
by_ts_df['pct_share'] = by_ts_df['sales'] / by_ts_df['sales'].sum() * 100
by_ts_df = by_ts_df.sort_values('sales', ascending=False)
by_ts_list = [{'traffic_source': r['Traffic_Source'], 'sales': round(float(r['sales']), 0),
               'orders': int(r['orders']), 'pct_share': round(float(r['pct_share']), 2)}
              for _, r in by_ts_df.iterrows()]

# By supplier
by_sup_df = rev.groupby('Supplier').agg(sales=('Sales','sum'), orders=('Order_ID','nunique')).reset_index()
by_sup_df['pct_share'] = by_sup_df['sales'] / by_sup_df['sales'].sum() * 100
by_sup_df = by_sup_df.sort_values('sales', ascending=False)
by_sup_list = [{'supplier': r['Supplier'], 'sales': round(float(r['sales']), 0),
                'orders': int(r['orders']), 'pct_share': round(float(r['pct_share']), 2)}
               for _, r in by_sup_df.iterrows()]

# Header KPIs (trend series = last 12 months of main data: Jul 2023 - Jun 2024)
recent_12 = monthly[(monthly['YearMonth'] >= '2023-07') & (monthly['YearMonth'] <= '2024-06')]
sales_series = [int(x) for x in recent_12['sales'].tolist()]
margin_series = [round(float(x), 2) for x in recent_12['np_margin'].tolist()]
aov_series = [round(float(x), 0) for x in recent_12['aov'].tolist()]

cur_sales = float(monthly[monthly['YearMonth']=='2024-06']['sales'].values[0])
prior_sales = float(monthly[monthly['YearMonth']=='2023-06']['sales'].values[0])
cur_margin = float(monthly[monthly['YearMonth']=='2024-06']['np_margin'].values[0])
prior_margin = float(monthly[monthly['YearMonth']=='2023-06']['np_margin'].values[0])
cur_aov = float(monthly[monthly['YearMonth']=='2024-06']['aov'].values[0])
prior_aov = float(monthly[monthly['YearMonth']=='2023-06']['aov'].values[0])

header_kpis = [
    {
        "id": "kpi_1",
        "label": "Monthly Sales",
        "value": f"${cur_sales/1000:.1f}K",
        "delta": f"{(cur_sales-prior_sales)/prior_sales*100:+.1f}%",
        "delta_abs": f"${cur_sales-prior_sales:+,.0f}",
        "prior_value": f"${prior_sales/1000:.1f}K",
        "status": "good" if cur_sales > prior_sales else "alert",
        "direction": "up_is_good",
        "trend_series": sales_series,
        "note": "Completed non-returned orders, Jun 2024 vs Jun 2023"
    },
    {
        "id": "kpi_2",
        "label": "Net Profit Margin",
        "value": f"{cur_margin:.1f}%",
        "delta": f"{cur_margin-prior_margin:+.2f}pp",
        "delta_abs": f"{cur_margin-prior_margin:+.2f}pp",
        "prior_value": f"{prior_margin:.1f}%",
        "status": "good" if cur_margin >= prior_margin else "alert",
        "direction": "up_is_good",
        "trend_series": margin_series,
        "note": "Net_Profit / Sales, completed non-returned orders"
    },
    {
        "id": "kpi_3",
        "label": "Avg Order Value",
        "value": f"${cur_aov:.0f}",
        "delta": f"{(cur_aov-prior_aov)/prior_aov*100:+.1f}%",
        "delta_abs": f"${cur_aov-prior_aov:+.0f}",
        "prior_value": f"${prior_aov:.0f}",
        "status": "good" if cur_aov > prior_aov else "alert",
        "direction": "up_is_good",
        "trend_series": aov_series,
        "note": "Sales / unique orders, Jun 2024 vs Jun 2023"
    }
]

# Monthly series output
monthly_series_out = []
for _, r in monthly.iterrows():
    yoy_val = r['yoy_growth_pct']
    mom_val = r['mom_growth_pct']
    monthly_series_out.append({
        'month': r['YearMonth'],
        'sales': int(r['sales']),
        'orders': int(r['orders']),
        'net_profit': round(float(r['net_profit']), 2),
        'aov': round(float(r['aov']), 2),
        'np_margin_pct': round(float(r['np_margin']), 2),
        'mom_growth_pct': round(float(mom_val), 2) if mom_val is not None and not pd.isna(mom_val) else None,
        'yoy_growth_pct': round(float(yoy_val), 2) if yoy_val is not None and not pd.isna(yoy_val) else None
    })

trend_out = {
    "direction": trend_dir,
    "slope_per_month": round(float(slope), 2),
    "r_squared": round(float(r2), 4),
    "p_value": round(float(p_value), 4),
    "interpretation": (
        "Linear fit on 30 monthly data points (Jan 2022 to Jun 2024) shows slope of "
        + f"${slope:.0f}/month (R2={r2:.3f}, p={p_value:.3f}). "
        + "Trend is statistically insignificant: revenue is flat with high MoM noise (~17% std). "
        + "2022 to 2023 decline of -4.1% is concentrated in Electronics and South region. "
        + "2024 continues modest drift at $52K-62K per month."
    )
}

seas_out = {
    "method": "Average by month number across 2022-2023 full years",
    "peak_month": MONTHS[peak_m],
    "peak_index": seas_index[peak_m],
    "trough_month": MONTHS[trough_m],
    "trough_index": seas_index[trough_m],
    "monthly_indices": {MONTHS[k]: v for k, v in sorted(seas_index.items())},
    "interpretation": (
        "October is the strongest month (index=" + str(seas_index[peak_m]) + ", +18% above average). "
        + "April is the weakest (index=" + str(seas_index[trough_m]) + ", -12% below average). "
        + "Moderate seasonal swing of ~30pp peak-to-trough."
    )
}

segments = [
    {
        "dimension": "Region",
        "analysis": by_region_list,
        "verdict": "Balanced across all four regions (within 1.3pp share). East leads at 25.8%. South declining fastest (-9.4% YoY) warrants monitoring.",
        "concentration": "top_1_pct_share: 25.8% (balanced)"
    },
    {
        "dimension": "Category",
        "analysis": by_cat_list,
        "verdict": "Highly concentrated: Electronics at 87.7% creates single-category dependency risk. Wearables fastest-growing (+25.6%) but too small to offset Electronics decline.",
        "concentration": "top_1_pct_share: 87.7% (CONCENTRATED)"
    },
    {
        "dimension": "Traffic_Source",
        "analysis": by_ts_list,
        "verdict": "Email (17.5%) and Referral (16.8%) are top channels. Paid channels (Facebook + Google Ads) = 29.2% combined. Unknown = 5.1% attribution gap.",
        "concentration": "top_1_pct_share: 17.5% (Email)"
    },
    {
        "dimension": "Supplier",
        "analysis": by_sup_list,
        "verdict": "Five suppliers share revenue almost equally (~20% each). No supplier concentration risk.",
        "concentration": "top_1_pct_share: 21.1% (Supplier_A)"
    }
]

trends_out = [
    {"period": "2022 full year", "sales": 746010, "yoy_change_pct": None, "note": "Baseline year"},
    {"period": "2023 full year", "sales": 715450, "yoy_change_pct": -4.1, "note": "Electronics fell -5.8%; South region -9.4%"},
    {"period": "2024 Jan-Jun", "sales": 338470, "yoy_change_pct": -0.8, "note": "H1 2024 vs H1 2023: $338K vs $341K"},
    {"period": "2026 Mar partial", "sales": 15765, "yoy_change_pct": None, "note": "14 orders only; 2025 gap means no YoY comparison"}
]

paradox_checks = [
    {
        "finding_tested": "Overall Sales declined -4.1% from 2022 to 2023",
        "grouped_by": "Region",
        "result": "No paradox. East -3.9%, North -5.0%, South -9.4%, West +2.5%. Aggregate direction consistent with majority of regions.",
        "paradox_detected": False
    },
    {
        "finding_tested": "Overall Sales declined -4.1% from 2022 to 2023",
        "grouped_by": "Category",
        "result": "No reversal, but nuance: Electronics drove 125% of aggregate decline while Accessories (+9.5%) and Wearables (+25.6%) grew. Small segment growth masked by Electronics weight (87.7%).",
        "paradox_detected": False,
        "note": "Monitor as Wearables/Accessories share grows; eventual paradox possible if Electronics share falls below 70%."
    },
    {
        "finding_tested": "Electronics dominates at 87.7% share",
        "grouped_by": "Region",
        "result": "Electronics concentration consistent across all regions (~86-89%). Not a regional composition artifact.",
        "paradox_detected": False
    }
]

findings = [
    {
        "id": "F1",
        "type": "Pattern",
        "headline": "Revenue is flat at ~$60K/month: the apparent -4.1% YoY decline is statistically insignificant (R2=0.04, p=0.32), not a structural trend",
        "evidence": "Linear regression on 30 monthly points: slope=-$165/month, R2=0.036, p=0.316. MoM volatility std=17.5% dwarfs any drift signal.",
        "confidence": "high",
        "chart_id": "monthly_sales_line"
    },
    {
        "id": "F2",
        "type": "Contrast",
        "headline": "Electronics (-5.8% YoY) drags aggregate revenue while Wearables (+25.6%) and Accessories (+9.5%) grow -- but both together are only 12% of total sales",
        "evidence": "Electronics = 87.7% of total sales ($1.59M of $1.82M). Its $38K decline accounts for 125% of the aggregate $30.6K revenue drop from 2022 to 2023.",
        "confidence": "high",
        "chart_id": "category_bar_share"
    },
    {
        "id": "F3",
        "type": "Pattern",
        "headline": "October peaks +18% above monthly average every year; April troughs -12% below -- moderate seasonal cycle driven by hardware upgrade timing",
        "evidence": "Seasonality indices from 2022-2023: Oct=118.1, Jan=113.7, Dec=111.4 vs Apr=87.8, May=89.6. Peak-to-trough swing of ~30pp.",
        "confidence": "medium",
        "chart_id": "seasonality_chart"
    },
    {
        "id": "F4",
        "type": "Ruling Out",
        "headline": "Margin compression is NOT happening: Net Profit Margin held at exactly 33% throughout 2022-2024, ruling out any profitability deterioration",
        "evidence": "NP margin by year: 2022=33.10%, 2023=33.04%, 2024 H1=33.15%. Monthly range in 2024: 32.8%-33.6%. Zero structural change.",
        "confidence": "high",
        "chart_id": "margin_line"
    },
    {
        "id": "F5",
        "type": "Implication",
        "headline": "87.7% concentration in Electronics means top 2 products (Laptop Pro X + Laptop Air) control 44.9% of total revenue -- a single product-line shock moves the whole business",
        "evidence": "Laptop Pro X: $483K (26.6%); Laptop Air: $333K (18.3%). Combined $816K of $1.82M total. No diversification cushion in other categories.",
        "confidence": "high",
        "chart_id": "product_bar_top10"
    }
]

scqa = {
    "situation": "TechWorld is an e-commerce retailer generating $1.82M in completed sales across 2,786 orders from Jan 2022 to Jun 2024, averaging ~$60K/month at a stable 33% net profit margin.",
    "complication": "Sales have drifted from $746K (2022) to $715K (2023, -4.1%) with 2024 H1 tracking similarly. Electronics (87.7% of revenue) declined -5.8% YoY while Wearables/Accessories are growing but too small to offset. The 2025 data gap creates a 20-month blind spot limiting forecasting confidence.",
    "question": "Will monthly Sales recover, hold flat, or continue declining over the next 3 months, and what is driving the trend?",
    "answer": "Revenue is holding flat, not in structural decline: the linear trend is statistically insignificant (R2=0.04). The next quarter forecast should converge on $55K-65K/month with moderate October seasonality uplift. The primary risk is single-category dependency on Electronics (87.7%), not a broad demand collapse. Margin health at 33% is not a concern."
}

output = {
    "skill_type": "descriptive",
    "stem": "techworld_data_sample",
    "headline": "TechWorld revenue is flat at ~$60K/month -- mild -4.1% YoY drift driven entirely by Electronics softness while profitability holds steady at 33% net margin",
    "kpis": {
        "total_sales": round(total_sales, 0),
        "total_orders": total_orders,
        "avg_order_value": round(aov_overall, 2),
        "total_net_profit": round(total_net_profit, 2),
        "net_profit_margin_pct": round(net_profit_margin_pct, 2),
        "return_rate_pct": round(return_rate_pct, 2)
    },
    "header_kpis": header_kpis,
    "monthly_series": monthly_series_out,
    "by_year": by_year_list,
    "by_region": by_region_list,
    "by_category": by_cat_list,
    "by_product_top10": by_prod_list,
    "by_traffic_source": by_ts_list,
    "by_supplier": by_sup_list,
    "trend": trend_out,
    "seasonality": seas_out,
    "trends": trends_out,
    "segments": segments,
    "cohorts": None,
    "waterfall": None,
    "findings": findings,
    "scqa_draft": scqa,
    "simpsons_paradox_checks": paradox_checks,
    "predictive_needed": True,
    "predictive_type": "forecasting",
    "key_findings": [
        "Revenue is flat (~$60K/month, R2=0.04): the -4.1% YoY drift is statistically insignificant noise, not a structural decline.",
        "Electronics (87.7% of sales) fell -5.8% YoY and drove 125% of the aggregate decline; Wearables (+25.6%) and Accessories (+9.5%) are growing but too small to compensate.",
        "Net Profit Margin is unchanged at 33% across 2022-2024: profitability is not eroding.",
        "October is peak month (+18% above avg); April is trough (-12%); moderate seasonal swing of ~30pp.",
        "Top 2 products (Laptop Pro X + Laptop Air) concentrate 44.9% of total sales: high single-segment forecast risk."
    ],
    "metadata": {
        "generated_at": datetime.now().isoformat(),
        "filter_applied": "Return_Flag=0 for all revenue KPIs (excludes 92 returned orders of 2,878 cleaned rows)",
        "data_range": "2022-01 to 2026-03 (2025 entirely absent; 2024 Jan-Jun only; 2026 partial March only)",
        "monthly_data_points": 31,
        "monthly_data_points_for_trend": 30
    }
}

output_path = 'data/pipeline/techworld_data_sample/descriptive_output.json'
with open(output_path, 'w') as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

print(f"Written: {output_path}")
print(f"Header KPIs: {len(output['header_kpis'])} (must be 3)")
print(f"Monthly series: {len(output['monthly_series'])} months")
print(f"Findings: {len(output['findings'])}")
ruling_out = [f for f in output['findings'] if f['type'] == 'Ruling Out']
print(f"Ruling Out findings: {len(ruling_out)}")
print(f"Simpsons checks: {len(output['simpsons_paradox_checks'])}")
print(f"Predictive needed: {output['predictive_needed']}")
print("DONE")
