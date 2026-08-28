"""Generate all 13 chart types for review."""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from pathlib import Path
import numpy as np

import sys; sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import scripts.render_charts_swd as r
r.ROOT = Path(".")
OUT = Path("data/pipeline/sales_orders_2023_2026/chart_images")
OUT.mkdir(exist_ok=True)

# ── 1. VERTICAL BAR ──────────────────────────────────────────────────────────
fig = r.chart_vertical_bar(data={
    "categories": ["Q1'23","Q2'23","Q3'23","Q4'23","Q1'24","Q2'24","Q3'24","Q4'24","Q1'25","Q2'25","Q3'25","Q4'25","Q1'26","Q2'26"],
    "values":     [174878,444397,1131963,3106027,1953739,2264561,2767047,7766236,3911610,3691607,3885621,11575273,5026709,5932701],
    "highlight":  ["Q4'23","Q4'24","Q4'25"],
    "value_format": "M", "y_label": "Revenue (USD)"
}, title="Q4 drives 49-64% of annual revenue -- seasonality is structural",
   hi_color=r.SECTION_COLORS["descriptive"], figsize=r.FIGSIZE_FULL)
r._save_chart(fig, OUT / "01_vertical_bar.png")
print("[ok] 01_vertical_bar")

# ── 2. HORIZONTAL BAR ────────────────────────────────────────────────────────
fig = r.chart_horizontal_bar(data={
    "categories":   ["Software","Support","Training","Services","Hardware"],
    "values":       [82.9, 71.4, 63.7, 52.2, 28.4],
    "highlight":    ["Software"],
    "value_format": "pct", "x_label": "GP Margin 2025 (%)"
}, title="Software margin (82.9%) is 3x Hardware -- product mix is the primary margin lever",
   hi_color=r.SECTION_COLORS["descriptive"], figsize=r.FIGSIZE_SPLIT)
r._save_chart(fig, OUT / "02_horizontal_bar.png")
print("[ok] 02_horizontal_bar")

# ── 3. HIGHLIGHT LINE ────────────────────────────────────────────────────────
fig = r.chart_highlight_line(data={
    "x":  ["Jan'24","Feb'24","Mar'24","Apr'24","May'24","Jun'24","Jul'24","Aug'24","Sep'24","Oct'24","Nov'24","Dec'24",
            "Jan'25","Feb'25","Mar'25","Apr'25","May'25","Jun'25","Jul'25","Aug'25","Sep'25"],
    "y":  [621,698,635,718,756,791,841,896,1030,2187,2312,3267,
           1221,1289,1402,1198,1242,1252,88,96,93],
    "highlight_range":  [18, 20],
    "highlight_points": [18],
    "value_format": "K", "y_label": "Revenue (000 USD)"
}, title="APAC revenue collapsed in Jul-Sep 2025 -- only 31 orders vs 75 prior year",
   hi_color=r.SECTION_COLORS["diagnostic"], figsize=r.FIGSIZE_FULL)
r._save_chart(fig, OUT / "03_highlight_line.png")
print("[ok] 03_highlight_line")

# ── 4. MULTI-LINE ────────────────────────────────────────────────────────────
fig = r.chart_multi_line(data={
    "x": ["Q1'24","Q2'24","Q3'24","Q4'24","Q1'25","Q2'25","Q3'25","Q4'25"],
    "series": [
        {"name": "APAC",          "values": [54.73,50.27,45.41,54.18,43.29,48.91,41.00,50.44], "highlight": True},
        {"name": "Europe",        "values": [49.0, 51.2, 48.5, 48.3, 50.1, 52.3, 51.8, 51.6], "highlight": False},
        {"name": "North America", "values": [49.9, 48.2, 50.1, 51.5, 48.7, 50.2, 49.3, 50.6], "highlight": False},
        {"name": "LatAm",         "values": [50.4, 49.1, 51.2, 50.8, 49.5, 50.3, 48.9, 50.2], "highlight": False},
    ], "y_label": "GP Margin (%)"
}, title="APAC GP margin collapsed to 41% in Q3 2025 -- lowest across all regions",
   hi_color=r.SECTION_COLORS["diagnostic"], figsize=r.FIGSIZE_FULL)
r._save_chart(fig, OUT / "04_multi_line.png")
print("[ok] 04_multi_line")

# ── 5. WATERFALL ─────────────────────────────────────────────────────────────
# Pass only the delta values; last bar (total) computed from sum
fig = r.chart_waterfall(data={
    "categories":   ["APAC 2024", "Hardware mix", "Q3 collapse", "Discount", "Consumer mix", "APAC 2025"],
    "values":       [51.9, -2.1, -1.2, -0.6, -0.3, None],
    "start_value":  0,
    "value_format": "pct"
}, title="Hardware mix shift drove 54% of APAC margin erosion -- 4 causes totalling -4.2pp",
   hi_color=r.SECTION_COLORS["diagnostic"], figsize=r.FIGSIZE_FULL)
r._save_chart(fig, OUT / "05_waterfall.png")
print("[ok] 05_waterfall")

# ── 6. GROUPED BAR ───────────────────────────────────────────────────────────
fig = r.chart_grouped_bar(data={
    "categories": ["2023", "2024", "2025"],
    "groups": [
        {"name": "Enterprise", "values": [2566833, 8188448, 14854109], "highlight": True},
        {"name": "SMB",        "values": [1479756, 4770375, 5091394],  "highlight": False},
        {"name": "Consumer",   "values": [810678,  1792760, 3118608],  "highlight": False},
    ], "value_format": "M"
}, title="Enterprise grew 5.8x in 3 years -- SMB growth stalled at +7% in 2025",
   hi_color=r.SECTION_COLORS["descriptive"], figsize=r.FIGSIZE_FULL)
r._save_chart(fig, OUT / "06_grouped_bar.png")
print("[ok] 06_grouped_bar")

# ── 7. SLOPEGRAPH ────────────────────────────────────────────────────────────
fig = r.chart_slopegraph(data={
    "labels":       ["APAC", "Europe", "LatAm", "North America"],
    "before":       [51.9, 49.0, 50.4, 49.9],
    "after":        [48.0, 51.4, 49.7, 49.7],
    "before_label": "2024", "after_label": "2025",
    "highlight":    ["APAC"], "value_format": "pct"
}, title="Only APAC lost margin in 2025 -- fell -3.9pp while Europe improved +2.4pp",
   hi_color=r.SECTION_COLORS["diagnostic"], figsize=r.FIGSIZE_SPLIT)
r._save_chart(fig, OUT / "07_slopegraph.png")
print("[ok] 07_slopegraph")

# ── 8. HEATMAP ───────────────────────────────────────────────────────────────
fig = r.chart_heatmap(data={
    "rows": ["Hardware","Services","Software","Support","Training"],
    "cols": ["APAC","Europe","LatAm","N. America"],
    "values": [
        [27.3, 29.1, 28.8, 28.2],
        [51.8, 52.6, 51.2, 52.5],
        [82.9, 82.9, 82.9, 82.9],
        [71.2, 71.6, 71.4, 71.5],
        [63.4, 64.1, 63.2, 63.8],
    ],
    "value_format": "pct"
}, title="Software margin universal at 82.9% -- Hardware is the only region-sensitive drag",
   hi_color=r.SECTION_COLORS["descriptive"], figsize=r.FIGSIZE_FULL)
r._save_chart(fig, OUT / "08_heatmap.png")
print("[ok] 08_heatmap")

# ── 9. FORECAST LINE ─────────────────────────────────────────────────────────
fig = r.chart_forecast_line(data={
    "x":          ["Q1'24","Q2'24","Q3'24","Q4'24","Q1'25","Q2'25","Q3'25","Q4'25","Q1'26","Q2'26","Q3'26","Q4'26"],
    "historical": [1953739,2264561,2767047,7766236,3911610,3691607,3885621,11575273,5026709,5932701,None,None],
    "forecast":   [None,None,None,None,None,None,None,None,None,None,8000000,10700000],
    "ci_low":     [None,None,None,None,None,None,None,None,None,None,5400000,8000000],
    "ci_high":    [None,None,None,None,None,None,None,None,None,None,10700000,13300000],
    "split_idx":  9, "value_format": "M", "y_label": "Revenue (USD)"
}, title="H2 2026 forecast $18.7M -- full year projected at $29.6M (+28% vs 2025)",
   hi_color=r.SECTION_COLORS["predictive"], figsize=r.FIGSIZE_FULL)
r._save_chart(fig, OUT / "09_forecast_line.png")
print("[ok] 09_forecast_line")

# ── 10. FEATURE IMPORTANCE ───────────────────────────────────────────────────
fig = r.chart_feature_importance(data={
    "features":    ["Segment_Enterprise","Region_APAC","Category_Hardware","Q4_flag","Discount_pct","Channel_Reseller","YoY_growth","Month"],
    "importances": [0.312, 0.218, 0.187, 0.143, 0.072, 0.038, 0.021, 0.009],
    "top_n": 8
}, title="Enterprise segment and APAC region drive 53% of revenue variance",
   hi_color=r.SECTION_COLORS["predictive"], figsize=r.FIGSIZE_SPLIT)
r._save_chart(fig, OUT / "10_feature_importance.png")
print("[ok] 10_feature_importance")

# ── 11. SCATTER REGRESSION ───────────────────────────────────────────────────
np.random.seed(42)
discount   = np.random.uniform(0, 25, 120)
gp_margin  = 55 - 0.6 * discount + np.random.normal(0, 3, 120)
hi_idx     = [int(i) for i in np.where(discount > 20)[0]]
fig = r.chart_scatter_regression(data={
    "x": discount.tolist(), "y": gp_margin.tolist(),
    "x_label": "Discount (%)", "y_label": "GP Margin (%)",
    "highlight_indices": hi_idx, "r_squared": 0.74
}, title="Each 1pp discount reduces GP margin by 0.6pp -- discipline is critical",
   hi_color=r.SECTION_COLORS["diagnostic"], figsize=r.FIGSIZE_SPLIT)
r._save_chart(fig, OUT / "11_scatter_regression.png")
print("[ok] 11_scatter_regression")

# ── 12. MODEL COMPARISON BAR ─────────────────────────────────────────────────
fig = r.chart_model_comparison_bar(data={
    "models":      ["XGBoost","LightGBM","Prophet","SARIMA","Linear Trend"],
    "scores":      [0.847, 0.831, 0.762, 0.718, 0.621],
    "metric_name": "R2 Score",
    "highlight":   ["XGBoost"]
}, title="XGBoost best forecast model -- R2=0.847, 14pp above SARIMA baseline",
   hi_color=r.SECTION_COLORS["predictive"], figsize=r.FIGSIZE_SPLIT)
r._save_chart(fig, OUT / "12_model_comparison.png")
print("[ok] 12_model_comparison")

# ── 13. ROC CURVE ────────────────────────────────────────────────────────────
from sklearn.datasets import make_classification
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_curve, auc as sk_auc
X, y = make_classification(n_samples=400, n_features=8, random_state=42)
clf  = LogisticRegression(random_state=42).fit(X, y)
probs = clf.predict_proba(X)[:, 1]
fpr, tpr, _ = roc_curve(y, probs)
fig = r.chart_roc_curve(data={
    "fpr": fpr.tolist(), "tpr": tpr.tolist(),
    "auc": sk_auc(fpr, tpr), "model_name": "Churn Risk Model"
}, title="Churn model AUC=0.97 -- correctly ranks 97% of at-risk customers",
   hi_color=r.SECTION_COLORS["predictive"], figsize=r.FIGSIZE_SPLIT)
r._save_chart(fig, OUT / "13_roc_curve.png")
print("[ok] 13_roc_curve")

# ══════════════════════════════════════════════════════════════════════════════
#  NEW 9 CHART TYPES
# ══════════════════════════════════════════════════════════════════════════════

# ── 14. STACKED BAR ─────────────────────────────────────────────────────────
fig = r.chart_stacked_bar(data={
    "categories": ["2023", "2024", "2025"],
    "segments": [
        {"name": "Software",  "values": [1200000, 3400000, 6800000], "highlight": True},
        {"name": "Hardware",  "values": [2100000, 4600000, 5200000], "highlight": False},
        {"name": "Services",  "values": [800000, 2100000, 3500000],  "highlight": False},
        {"name": "Training",  "values": [400000, 900000, 1400000],   "highlight": False},
    ],
    "value_format": "M", "y_label": "Revenue (USD)"
}, title="Software grew from 27% to 40% of revenue mix -- structural shift",
   hi_color=r.SECTION_COLORS["descriptive"], figsize=r.FIGSIZE_FULL)
r._save_chart(fig, OUT / "14_stacked_bar.png")
print("[ok] 14_stacked_bar")

# ── 15. HISTOGRAM ────────────────────────────────────────────────────────────
np.random.seed(42)
order_vals = np.concatenate([
    np.random.lognormal(8.5, 1.0, 300),
    np.random.lognormal(10.0, 0.5, 100),
])
fig = r.chart_histogram(data={
    "values": order_vals.tolist(),
    "bins": 30,
    "x_label": "Order Value (USD)", "y_label": "Frequency",
    "highlight_range": [20000, 80000]
}, title="Order values cluster around $5K with a second peak at $22K -- bimodal",
   hi_color=r.SECTION_COLORS["descriptive"], figsize=r.FIGSIZE_FULL)
r._save_chart(fig, OUT / "15_histogram.png")
print("[ok] 15_histogram")

# ── 16. DOT PLOT ─────────────────────────────────────────────────────────────
fig = r.chart_dot_plot(data={
    "categories": ["Germany","Japan","USA","UK","France","Brazil","India","Australia"],
    "values":     [92.3, 88.7, 85.4, 81.2, 78.9, 72.1, 68.4, 65.8],
    "highlight":  ["Germany","Japan"],
    "value_format": "pct", "x_label": "Customer Satisfaction Score (%)"
}, title="Germany and Japan lead satisfaction at 90%+ -- 20pp above Australia",
   hi_color=r.SECTION_COLORS["descriptive"], figsize=r.FIGSIZE_SPLIT)
r._save_chart(fig, OUT / "16_dot_plot.png")
print("[ok] 16_dot_plot")

# ── 17. BULLET CHART ────────────────────────────────────────────────────────
fig = r.chart_bullet(data={
    "metrics": [
        {"name": "Revenue",     "actual": 23.1, "target": 25.0, "ranges": [15, 20, 30]},
        {"name": "GP Margin",   "actual": 52.8, "target": 55.0, "ranges": [40, 50, 60]},
        {"name": "NPS",         "actual": 72,   "target": 75,   "ranges": [50, 65, 85]},
        {"name": "Retention %", "actual": 91.2, "target": 90.0, "ranges": [70, 85, 100]},
    ],
    "value_format": "auto"
}, title="Revenue and GP margin below target -- Retention exceeds goal",
   hi_color=r.SECTION_COLORS["descriptive"], figsize=r.FIGSIZE_SPLIT)
r._save_chart(fig, OUT / "17_bullet.png")
print("[ok] 17_bullet")

# ── 18. AREA CHART ──────────────────────────────────────────────────────────
fig = r.chart_area(data={
    "x": ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"],
    "series": [
        {"name": "Organic",  "values": [4200,4800,5100,5600,6200,6800,7100,7400,7200,6900,7800,8200], "highlight": True},
        {"name": "Paid",     "values": [2100,2300,2800,3100,3400,3200,2900,2700,3000,3500,4000,4200], "highlight": False},
        {"name": "Referral", "values": [800,900,1000,1100,1200,1300,1100,1000,1200,1400,1500,1600],   "highlight": False},
    ],
    "stacked": True, "y_label": "Sessions"
}, title="Organic traffic drives 55% of total sessions -- grew 95% YoY",
   hi_color=r.SECTION_COLORS["descriptive"], figsize=r.FIGSIZE_FULL)
r._save_chart(fig, OUT / "18_area.png")
print("[ok] 18_area")

# ── 19. CONNECTED DOT (DUMBBELL) ────────────────────────────────────────────
fig = r.chart_connected_dot(data={
    "categories": ["Enterprise","SMB","Consumer","Government","Education"],
    "value_a":    [48.2, 42.1, 38.5, 51.3, 44.7],
    "value_b":    [55.8, 44.3, 35.2, 53.1, 49.8],
    "label_a": "2024", "label_b": "2025",
    "highlight": ["Enterprise","Education"],
    "x_label": "GP Margin (%)"
}, title="Enterprise margin improved +7.6pp -- Consumer declined -3.3pp",
   hi_color=r.SECTION_COLORS["diagnostic"], figsize=r.FIGSIZE_SPLIT)
r._save_chart(fig, OUT / "19_connected_dot.png")
print("[ok] 19_connected_dot")

# ── 20. DIVERGING BAR (TORNADO) ─────────────────────────────────────────────
fig = r.chart_diverging_bar(data={
    "categories":   ["Discount +5pp","Volume -10%","COGS +8%","FX rate","Price +3%"],
    "values_left":  [3.2, 2.1, 1.8, 0.9, 0.0],
    "values_right": [0.0, 0.0, 0.0, 0.0, 1.5],
    "label_left": "Margin Decrease", "label_right": "Margin Increase",
    "value_format": "pct"
}, title="Discount increase is the #1 sensitivity factor at -3.2pp margin impact",
   hi_color=r.SECTION_COLORS["diagnostic"], figsize=r.FIGSIZE_SPLIT)
r._save_chart(fig, OUT / "20_diverging_bar.png")
print("[ok] 20_diverging_bar")

# ── 21. BOX PLOT ─────────────────────────────────────────────────────────────
np.random.seed(42)
fig = r.chart_box_plot(data={
    "categories": ["APAC","Europe","LatAm","N. America"],
    "distributions": [
        np.random.normal(45, 12, 80).tolist(),
        np.random.normal(52, 8, 80).tolist(),
        np.random.normal(48, 10, 80).tolist(),
        np.random.normal(50, 9, 80).tolist(),
    ],
    "highlight": ["APAC"],
    "x_label": "Region", "y_label": "GP Margin (%)"
}, title="APAC margin has widest variance (SD=12) -- inconsistent pricing discipline",
   hi_color=r.SECTION_COLORS["diagnostic"], figsize=r.FIGSIZE_SPLIT)
r._save_chart(fig, OUT / "21_box_plot.png")
print("[ok] 21_box_plot")

# ── 22. PARETO ───────────────────────────────────────────────────────────────
fig = r.chart_pareto(data={
    "categories": ["Late delivery","Wrong item","Damaged","Missing parts","Billing error","Other"],
    "values":     [342, 187, 124, 89, 56, 32],
    "value_format": "auto", "y_label": "Complaint Count"
}, title="Late delivery + wrong item = 64% of all complaints -- top 2 priorities",
   hi_color=r.SECTION_COLORS["diagnostic"], figsize=r.FIGSIZE_FULL)
r._save_chart(fig, OUT / "22_pareto.png")
print("[ok] 22_pareto")

# ── 23. RESIDUAL PLOT ────────────────────────────────────────────────────────
np.random.seed(42)
y_actual = np.random.normal(50, 10, 150)
y_pred   = y_actual + np.random.normal(0, 4, 150)
# inject a few outliers
y_pred[:5] += 25
fig = r.chart_residual_plot(data={
    "y_pred": y_pred.tolist(),
    "y_actual": y_actual.tolist(),
    "x_label": "Predicted Revenue ($M)",
    "y_label": "Residual"
}, title="5 outliers beyond 2 SD -- investigate APAC Q4 over-predictions",
   hi_color=r.SECTION_COLORS["predictive"], figsize=r.FIGSIZE_SPLIT)
r._save_chart(fig, OUT / "23_residual_plot.png")
print("[ok] 23_residual_plot")

print(f"\nAll 23 charts -> {OUT}")
