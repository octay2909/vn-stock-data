# Pipeline Run Log — Revenue Q1 2026 Analysis & Q3 2026 Forecast
**Date:** 2026-05-20  
**Dataset:** `data/raw/ecommerce_orders_2025-01-01_to_2026-06-30.csv`  
**Question:** Tại sao revenue Q1 2026 thay đổi? Dự báo Q3 2026?  
**Mode:** `--bypass` (auto-confirm, output = HTML + PPTX)  
**Pipeline ID:** `ecommerce_orders_2025-01-01_to_2026-06-30_20260520`

---

## Phase 0 — Blueprint (Triage)

- **File:** 500 rows × 9 columns, date range 2025-01-01 → 2026-06-30
- **Columns:** order_date, customer_id, segment, region, product, revenue, quantity, discount_rate, churn_flag
- **Question Level:** L3 (Diagnostic + Predictive/Forecasting)
- **Execution plan:** Descriptive → Diagnostic → Predictive (forecasting)
- **Output format:** Both (HTML + PPTX)
- **Bypass:** true → auto-confirmed, halt only on grade F

---

## Phase 1 — Understand (Parallel)

### Question Framer
**Output:** `data/pipeline/.../structured_questions.json`

Reformulated question:
> "Why did monthly revenue change in Q1 2026 compared to Q4 2025 and Q1 2025, which customer segments, regions, and products drove the change, and to what degree did discount rate and order volume explain the shift? Forecast monthly revenue for Q3 2026 (July, August, September 2026)."

4 sub-questions defined:
| ID | Focus | Layer |
|----|-------|-------|
| SQ1 | Monthly revenue trend Q1 2026 vs Q4 2025 and Q1 2025 | Descriptive |
| SQ2 | Segment / region / product decomposition | Diagnostic |
| SQ3 | Discount rate and quantity as causal factors | Diagnostic |
| SQ4 | Forecast Jul, Aug, Sep 2026 with confidence intervals | Predictive |

3 header KPIs: Q1 2026 Revenue · QoQ Change · YoY Change

### Data Profiler
**Output:** `data/pipeline/.../data_profile.json` + `validation_result.json`  
**Confidence Grade: B (80/100) — PROCEED**

| Column | Nulls | Notes |
|--------|-------|-------|
| order_date | 0% | 2025-01-01 to 2026-06-22 |
| customer_id | 0% | 486 unique |
| segment | 0% | SMB 197, Mid-Market 191, Enterprise 112 |
| region | 1% | North 136, East 128, South 120, West 111 |
| product | 0% | Platform 245, Analytics 174, Support 81 |
| revenue | 1% | Min $75, Max $9,507, Mean $1,405 |
| quantity | 0% | Range 1-16, Mean 5.96 |
| discount_rate | 1% | Range 0-30%, Mean 14.3% |
| churn_flag | 0% | 23.4% churn rate |

**Key profiler findings:**
- 28 future-dated records (after 2026-05-20) → excluded from actuals
- March 2026: 20 orders vs Jan/Feb 31-34 orders (core diagnostic signal)
- **Simpson's Paradox detected (Layer 4):** East (−10%) and West (−12%) declined but North (+142%) and South (+58%) surged → aggregate masks regional divergence

---

## Phase 2 — Analyze (Parallel)

### Descriptive Analyst
**Output:** `data/pipeline/.../descriptive_output.json`  
*(472 actuals filtered to 2026-05-20 cutoff)*

**3 Header KPIs:**
| KPI | Value | Delta |
|-----|-------|-------|
| Q1 2026 Revenue | $130,384 | +16.0% YoY / +42.2% QoQ |
| AOV Q1 2026 | $1,552 | +10.0% QoQ |
| Avg Discount Rate | 14.0% | +0.5pp QoQ (flat) |

**Quarterly breakdown:**
| Quarter | Revenue | QoQ | YoY |
|---------|---------|-----|-----|
| Q1 2025 | $112,404 | — | — |
| Q2 2025 | $134,987 | +20.1% | — |
| Q3 2025 | $99,051 | −26.6% | — |
| Q4 2025 | $91,693 | −7.4% | — |
| Q1 2026 | $130,384 | +42.2% | +16.0% |

**Within Q1 2026:**
- January: $51,926
- February: $53,457 ← peak
- March: $25,002 ← trough

**Key segment/region/product findings:**
- North region: 38.5% of Q1 2026 revenue, +142% QoQ
- Platform product: 61% share, +72% YoY
- Enterprise/West: $0 in Q1 2026 vs $10,892 in Q4 2025 (complete absence)
- Mid-Market QoQ rebound (+77%) is base-period inflated; YoY still negative

**Waterfall QoQ drivers:**
- North Surge: +$29,465
- Platform Expansion: +$33,281
- March within-quarter drag: −$28,455

**2 Simpson's Paradoxes confirmed:**
- SP1: East/West aggregate down, but North/South surged → aggregate misleads
- SP2 (high severity): East aggregate down but Enterprise/Mid-Market grew within East; West Enterprise had zero orders but Mid-Market/SMB grew

**2 Ruling-Out findings:**
- F6: Discounting did NOT cause March drop — order volume (−41%) drove it
- F7: Q1 growth was NOT a whale-customer effect — top 5 customers = only 17.7% of revenue

### Diagnostic Investigator
**Output:** `data/pipeline/.../diagnostic_output.json`

**Verdict:**
> March 2026 followed an established seasonal pattern (Mar/Feb ratio ~0.47 in both years); within that trough, the absence of Enterprise large-deal Platform orders (revenue −86%) was the primary controllable driver, concentrated in East-region deals.

**Root causes ranked:**
| Rank | Driver | Impact | Confidence | Actionable |
|------|--------|--------|-----------|------------|
| 1 | Structural March seasonality — recurring cyclical trough | 53% | High | No |
| 2 | Enterprise large-deal velocity — zero high-value Platform orders in March | 35% | High | Yes |
| 3 | Order volume shortfall (−11 orders) — Enterprise + Mid-Market pipeline thin | 15% | High | Yes |
| 4 | East region Enterprise Platform concentration — geographic risk | 10% | Medium | Partially |
| 5 | Platform AOV decline (downstream of Enterprise exit) | 5% | Medium | No |

**6 Hypotheses tested:**
| Hypothesis | Status | Evidence |
|-----------|--------|---------|
| H1: Enterprise segment collapse | Confirmed | 70% of revenue drop, −$19,988 |
| H2: Volume-price decomposition | Confirmed | 69% volume, 31% AOV (both from Enterprise absence) |
| H3: Discount rate spike | Rejected | Only 2.3pp increase → $682 counterfactual (2.4% of drop) |
| H4: Churn-flag customers | Rejected | Active customers drove 73% of drop; churn_flag is static |
| H5: Regional Simpson's Paradox | Partially confirmed | East/West real decline, but caused by Enterprise symptom |
| H6: Platform AOV decline | Partially confirmed | Downstream of H1 Enterprise exit |

**Key evidence:**
- Enterprise Feb 2026: $23,125 (9 orders) → Mar 2026: $3,137 (4 orders) = **−86.4%**
- 3 missing large Enterprise Platform deals account for the collapse
- SMB grew in March (+21%) → broader market was NOT soft
- Enterprise rebounded April ($10,258, 7 orders) → deal timing, not permanent loss
- Mar/Feb ratio: 0.46 (2025) vs 0.47 (2026) → pattern is structural

---

## Phase 3 — Predict (Forecasting)

**Output:** `data/pipeline/.../predictive_output.json`

**Training data:** 16-month monthly series (Jan 2025 – Apr 2026)  
**Model selection (4 models trained):**
| Rank | Model | Test MAPE | vs Baseline |
|------|-------|-----------|-------------|
| 1 | **Trend-Adjusted Seasonal Naive** | **8.16%** | **+48.6% better** |
| 2 | Seasonal Naive (baseline) | 15.88% | — |
| 3 | Linear Trend + Seasonal Decomp | 24.28% | worse |
| 4 | Holt Damped Trend | 38.75% | worse |

**Note:** Holt-Winters requires ≥24 months (2 full seasonal cycles); only 16 months available → replaced by Holt and decomposition variants.

**Optimal trend factor:** 1.160 (matches confirmed Q1 2026 YoY growth of +16.0%)

**Q3 2026 Forecast:**
| Month | Point | 80% CI | 95% CI | YoY |
|-------|-------|--------|--------|-----|
| July 2026 | **$31,853** | $26,344 – $37,362 | $23,430 – $40,276 | +16.0% |
| August 2026 | **$45,216** | $38,855 – $51,577 | $35,490 – $54,942 | +16.0% |
| September 2026 | **$37,827** | $30,714 – $44,939 | $26,953 – $48,700 | +16.0% |
| **Q3 Total** | **$114,896** | $95,913 – $133,879 | $85,874 – $143,918 | **+16.0% YoY** |

*Q3 2025 actual: $99,051*

**Key assumptions:**
- Within-quarter seasonality preserved: Aug/Jul = 1.420, Sep/Aug = 0.837 (mirrors 2025)
- September is a forecast trough (recurring third-month-of-quarter pattern)

**Primary risk:** Enterprise deal lumpiness can shift any monthly actual by ±$10–15K

---

## Phase 4 — Output

### Phase 4a — Story Building (Parallel)

**HTML story (report_context.json):**
- SCQA: Situation (strong Q1 context) → Complication (March −53%) → Question (structural or timing?) → Answer (seasonal + Enterprise timing, Q3 on track)
- 3 narrative sections: Descriptive / Diagnostic / Predictive
- 10 chart specifications with embedded data

**PPTX story (story_arc.json):**
- 16 slides, Pyramid Principle structure
- 4 sections: Setup (1-3) / What Happened (4-6) / Why It Happened (7-11) / What's Next (12-16)
- 13 charts with fully embedded data arrays
- Opening hook: "Q1 2026 surged 42% yet March collapsed 53% — two stories, one quarter"

### Phase 4b — Rendering

**Visualizer:** `chart_specs.json` — 9 D3.js chart specs with embedded data  
**Chart render:** 13/13 SWD-compliant matplotlib PNGs at 1200×570px, 150 dpi

**Bug fixed:** `render_html.py:416` — `sections[].charts` stored as list of strings (chart IDs) but `build_chart_html()` expected dicts. Fixed by normalizing strings to `{"chart_id": str}` in `build_section_html()`.

### Phase 4c — Final Files (Parallel)

| Output | Path | Size |
|--------|------|------|
| HTML Report | `data/reports/descriptive/ecommerce_orders_.../report.html` | 16.2 KB |
| PPTX Deck | `data/reports/descriptive/ecommerce_orders_.../slidedeck.pptx` | 626.4 KB |

**PPTX slide list (16 slides):**
1. COVER — "Q1 2026 hit $130K — March collapsed 53%, North drove 76% of gains"
2. BACKGROUND — B2B e-commerce with lumpy Enterprise deals
3. FRAMEWORK_3COL — Three analytical layers
4. INSIGHT_CHART — Q1 2026 grew 42% QoQ yet March dropped 53%
5. INSIGHT_CHART — North drove 76% of Q1 gain (Simpson's Paradox)
6. INSIGHT_CHART — Platform dominates at 61% (waterfall)
7. FINDINGS_OVERVIEW — March dip: 53% seasonal, 35% Enterprise timing
8. INSIGHT_CHART — March is structurally weak every year (seasonal pattern)
9. INSIGHT_CHART — Enterprise fell 86% in March, rebounded April
10. INSIGHT_CHART — East/West declined but Enterprise grew inside both
11. FRAMEWORK_3COL — Two hypotheses ruled out (H3 discount, H4 churn)
12. INSIGHT_CHART — Q3 2026 forecast $114,896
13. INSIGHT_CHART — Model comparison (MAPE 8.16% winner)
14. CONCLUSIONS_OVERVIEW — Q1 real growth, March seasonal, Q3 needs Enterprise focus
15. STRATEGY_MAPS — Three-phase roadmap
16. RECS_TABLE — Five quantified actions (~$44K at-risk annual revenue)

---

## Phase 5 — Quality Gate

**Verdict: PASS**  
**13/13 metrics verified independently from raw CSV**

| Metric | Claimed | Verified | Delta |
|--------|---------|----------|-------|
| Q1 2026 Revenue | $130,384 | $130,384.42 | 0.0003% |
| Q4 2025 Revenue | $91,693 | $91,693.41 | 0.0004% |
| QoQ Q4→Q1 | +42.2% | +42.20% | 0.000% |
| YoY Q1 2025→Q1 2026 | +16.0% | +16.00% | 0.000% |
| March 2026 Revenue | $25,002 | $25,002.10 | 0.0004% |
| February 2026 Revenue | $53,457 | $53,456.61 | 0.0007% |
| Feb→Mar MoM | −53% | −53.23% | 0.434% |
| Enterprise Feb 2026 | $23,125 (9 orders) | $23,124.89 | 0.0005% |
| Enterprise Mar 2026 | $3,137 (4 orders) | $3,136.94 | 0.0019% |
| Enterprise Feb→Mar | −86.4% | −86.43% | 0.035% |
| North QoQ | +142% | +141.86% | 0.099% |
| North Q1 share | 38.5% | 38.53% | 0.078% |
| Q3 2025 actual | $99,051 | $99,051.15 | 0.0002% |

**2 non-blocking warnings:**
- W1: Row count discrepancy — pipeline counted 472 actuals vs 468 verified (4 blank-revenue rows counted as orders, no metric impact)
- W2: 5 blank-region rows (1%) included in totals but invisible to regional attribution (2 in Q1 2026 Jan/Feb)

---

## Output Files

```
data/reports/descriptive/ecommerce_orders_2025-01-01_to_2026-06-30/
├── report.html        (16.2 KB — interactive HTML with D3.js charts)
└── slidedeck.pptx     (626.4 KB — 16-slide consulting deck)

data/pipeline/ecommerce_orders_2025-01-01_to_2026-06-30/
├── pipeline_state.json
├── structured_questions.json
├── data_profile.json
├── validation_result.json
├── descriptive_output.json
├── diagnostic_output.json
├── predictive_output.json
├── report_context.json
├── story_arc.json
├── chart_specs.json
├── chart_images.json
├── chart_images/           (13 PNG files @ 1200×570px)
└── quality_gate.json
```

---

## Code Changes Made

| File | Change | Reason |
|------|--------|--------|
| `scripts/render_html.py:416` | Normalize `sections[].charts` items: if string → wrap as `{"chart_id": str}` | story-builder writes chart list as string IDs; renderer expected dicts |

---

## Key Insights (Executive Summary)

**Câu hỏi 1 — Tại sao revenue Q1 2026 thay đổi?**

Q1 2026 revenue = $130,384 (+42% QoQ, +16% YoY). Biến động có hai chiều:
- **Tăng mạnh:** North region +142%, Platform +72% YoY → tăng trưởng thật sự
- **March dip (−53% MoM):** Kết hợp của seasonal pattern lặp lại (Mar/Feb = 0.47 ở cả 2 năm) và Enterprise deal timing (−86% Enterprise, chiếm 70% tổng giảm). April rebound xác nhận timing, không mất khách.
- **Loại trừ:** discount rate và churn flag không phải nguyên nhân.

**Câu hỏi 2 — Dự báo Q3 2026?**

Q3 2026 forecast: **$114,896** (+16% YoY vs Q3 2025 = $99,051)
- July: $31,853 | August: $45,216 | September: $37,827
- 80% CI: $95,913 – $133,879
- Rủi ro: Enterprise deal lumpiness ±$10–15K/tháng
