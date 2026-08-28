import argparse
import csv
import json
import re
import sys
from datetime import datetime, date
from collections import defaultdict
from pathlib import Path
import math

# ---------------------------------------------------------------------------
# CP5 — Structured logging
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).parent.parent))
from helpers.utils.logger import get_logger, new_run_id

# ---------------------------------------------------------------------------
# CP1 — Dynamic config: read stem from CLI, load column mapping from
#        pipeline_state.json instead of hardcoding paths and column names
# ---------------------------------------------------------------------------
_BASE = Path(__file__).parent.parent

def _load_pipeline_state(stem: str) -> dict:
    state_path = _BASE / "data" / "pipeline" / stem / "pipeline_state.json"
    if not state_path.exists():
        return {}
    with open(state_path, encoding="utf-8") as f:
        return json.load(f)

def _parse_args():
    parser = argparse.ArgumentParser(description="Descriptive compute for AI Analyst pipeline")
    parser.add_argument("--stem", required=True, help="Dataset stem")
    parser.add_argument("--run-id", default=None, help="Pipeline run ID for tracing")
    return parser.parse_args()

args = _parse_args()

# CP6 — Sanitize stem
if not re.match(r'^[\w\-\.]+$', args.stem):
    print(f"ERROR: Invalid stem '{args.stem}'", file=sys.stderr)
    sys.exit(1)

STEM = args.stem
run_id = args.run_id or new_run_id()
log = get_logger(__name__, run_id=run_id, stem=STEM)

# Load pipeline state for dynamic config
_state_path = _BASE / "data" / "pipeline" / STEM / "pipeline_state.json"
state = _load_pipeline_state(STEM)
log.info("pipeline_state_loaded", keys=list(state.keys()))

# CP2 — Validate pipeline_state has required fields before use
_required_state_fields = ["file_path", "columns"]
_missing = [f for f in _required_state_fields if f not in state]
if _missing:
    log.error("pipeline_state_invalid", missing=_missing, path=str(_state_path))
    sys.exit(1)
if not state.get("file_path"):
    log.error("pipeline_state_invalid", reason="file_path is empty", path=str(_state_path))
    sys.exit(1)
if not isinstance(state.get("columns"), list) or len(state.get("columns", [])) == 0:
    log.error("pipeline_state_invalid", reason="columns list is empty or missing", path=str(_state_path))
    sys.exit(1)

# CP1 — Derive config dynamically from pipeline_state.json
_date_range = state.get("date_range", "")
_cutoff_str = _date_range.split(" to ")[-1].strip() if " to " in _date_range else ""
try:
    CUTOFF = datetime.strptime(_cutoff_str, "%Y-%m-%d").date() if _cutoff_str else date.today()
except ValueError:
    CUTOFF = date.today()
    log.warning("cutoff_fallback", reason="could not parse date_range from pipeline_state", cutoff=str(CUTOFF))

log.info("cutoff_set", cutoff=str(CUTOFF))

# CP1 — Input file path from pipeline_state (not hardcoded)
_file_path = state.get("file_path", "")
if not _file_path:
    log.error("missing_file_path", reason="pipeline_state.json has no 'file_path' key")
    sys.exit(1)
INPUT_PATH = _BASE / _file_path

# CP1 — Column mapping from pipeline_state (auto-detected from CSV header if missing)
_columns = state.get("columns", [])
COL_DATE     = next((c for c in _columns if "date" in c.lower()), "order_date")
COL_REVENUE  = next((c for c in _columns if "rev" in c.lower() or "amount" in c.lower() or "sales" in c.lower()), "revenue")
COL_QTY      = next((c for c in _columns if "qty" in c.lower() or "quant" in c.lower()), "quantity")
COL_DISCOUNT = next((c for c in _columns if "disc" in c.lower()), "discount_rate")
COL_CUSTOMER = next((c for c in _columns if "cust" in c.lower() or "client" in c.lower()), "customer_id")
COL_SEGMENT  = next((c for c in _columns if "seg" in c.lower()), "segment")
COL_REGION   = next((c for c in _columns if "reg" in c.lower() or "geo" in c.lower()), "region")
COL_PRODUCT  = next((c for c in _columns if "prod" in c.lower() or "item" in c.lower() or "sku" in c.lower()), "product")
COL_CHURN    = next((c for c in _columns if "churn" in c.lower()), "churn_flag")

log.info("column_mapping", date=COL_DATE, revenue=COL_REVENUE, segment=COL_SEGMENT,
         region=COL_REGION, product=COL_PRODUCT, customer=COL_CUSTOMER)

# ---------------------------------------------------------------------------
# Load raw data
# ---------------------------------------------------------------------------
if not INPUT_PATH.exists():
    log.error("input_file_missing", path=str(INPUT_PATH))
    sys.exit(1)

rows = []
with open(INPUT_PATH, newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        rows.append(row)

log.info("data_loaded", row_count=len(rows), path=str(INPUT_PATH))

# Parse and filter actuals only
actuals = []
for row in rows:
    try:
        d = datetime.strptime(row[COL_DATE], "%Y-%m-%d").date()
    except (KeyError, ValueError) as e:
        log.warning("row_parse_error", field=COL_DATE, error=str(e))
        continue
    if d <= CUTOFF:
        rev = float(row[COL_REVENUE]) if row.get(COL_REVENUE, "").strip() else None
        qty = int(float(row[COL_QTY])) if row.get(COL_QTY, "").strip() else None
        dr  = float(row[COL_DISCOUNT]) if row.get(COL_DISCOUNT, "").strip() else None
        churn_raw = row.get(COL_CHURN, "0").strip()
        actuals.append({
            "date": d,
            "month": d.strftime("%Y-%m"),
            "year": d.year,
            "quarter": f"{d.year}-Q{(d.month-1)//3+1}",
            "customer_id": row.get(COL_CUSTOMER, ""),
            "segment": row.get(COL_SEGMENT, ""),
            "region": row.get(COL_REGION, "").strip() or None,
            "product": row.get(COL_PRODUCT, ""),
            "revenue": rev,
            "quantity": qty,
            "discount_rate": dr,
            "churn_flag": int(float(churn_raw)) if churn_raw else 0,
        })

print(f"Total actuals (<=2026-05-20): {len(actuals)}")

# --- 1. Monthly revenue aggregation ---
monthly = defaultdict(lambda: {"revenue": 0.0, "count": 0, "qty_sum": 0, "qty_count": 0, "dr_sum": 0.0, "dr_count": 0})
for r in actuals:
    m = r["month"]
    if r["revenue"] is not None:
        monthly[m]["revenue"] += r["revenue"]
        monthly[m]["count"] += 1
    if r["quantity"] is not None:
        monthly[m]["qty_sum"] += r["quantity"]
        monthly[m]["qty_count"] += 1
    if r["discount_rate"] is not None:
        monthly[m]["dr_sum"] += r["discount_rate"]
        monthly[m]["dr_count"] += 1

months_sorted = sorted(monthly.keys())
print("\n--- Monthly Revenue ---")
monthly_out = {}
for m in months_sorted:
    d2 = monthly[m]
    aov = d2["revenue"] / d2["count"] if d2["count"] else 0
    avg_qty = d2["qty_sum"] / d2["qty_count"] if d2["qty_count"] else 0
    avg_dr = d2["dr_sum"] / d2["dr_count"] if d2["dr_count"] else 0
    print(f"{m}: rev={d2['revenue']:.2f}, orders={d2['count']}, AOV={aov:.2f}, avg_qty={avg_qty:.2f}, avg_dr={avg_dr:.4f}")
    monthly_out[m] = {
        "revenue": round(d2["revenue"], 2),
        "order_count": d2["count"],
        "aov": round(aov, 2),
        "avg_qty": round(avg_qty, 2),
        "avg_discount_rate": round(avg_dr, 4)
    }

# --- 2. Quarterly totals ---
quarterly = defaultdict(lambda: {"revenue": 0.0, "count": 0, "qty_sum": 0, "qty_count": 0, "dr_sum": 0.0, "dr_count": 0})
for r in actuals:
    q = r["quarter"]
    if r["revenue"] is not None:
        quarterly[q]["revenue"] += r["revenue"]
        quarterly[q]["count"] += 1
    if r["quantity"] is not None:
        quarterly[q]["qty_sum"] += r["quantity"]
        quarterly[q]["qty_count"] += 1
    if r["discount_rate"] is not None:
        quarterly[q]["dr_sum"] += r["discount_rate"]
        quarterly[q]["dr_count"] += 1

quarters_sorted = sorted(quarterly.keys())
print("\n--- Quarterly Revenue ---")
qtr_summary = {}
for q in quarters_sorted:
    d2 = quarterly[q]
    aov = d2["revenue"] / d2["count"] if d2["count"] else 0
    avg_qty = d2["qty_sum"] / d2["qty_count"] if d2["qty_count"] else 0
    avg_dr = d2["dr_sum"] / d2["dr_count"] if d2["dr_count"] else 0
    print(f"{q}: rev={d2['revenue']:.2f}, orders={d2['count']}, AOV={aov:.2f}")
    qtr_summary[q] = {
        "total_revenue": round(d2["revenue"], 2),
        "order_count": d2["count"],
        "aov": round(aov, 2),
        "avg_qty": round(avg_qty, 2),
        "avg_discount_rate": round(avg_dr, 4)
    }

# --- 3. QoQ and YoY ---
q4_2025 = quarterly["2025-Q4"]["revenue"]
q1_2026 = quarterly["2026-Q1"]["revenue"]
q1_2025 = quarterly["2025-Q1"]["revenue"]
q2_2026 = quarterly["2026-Q2"]["revenue"]
q2_2025 = quarterly["2025-Q2"]["revenue"]
q3_2025 = quarterly["2025-Q3"]["revenue"]

qoq_q1 = (q1_2026 - q4_2025) / q4_2025 * 100
yoy_q1 = (q1_2026 - q1_2025) / q1_2025 * 100
qoq_q2 = (q2_2026 - q1_2026) / q1_2026 * 100
print(f"\nQ1 2026 QoQ (vs Q4 2025): {qoq_q1:.1f}%")
print(f"Q1 2026 YoY (vs Q1 2025): {yoy_q1:.1f}%")
print(f"Q2 2026 partial QoQ (vs Q1 2026): {qoq_q2:.1f}%")

# --- 4. Segment breakdown Q1 2026 vs Q4 2025 ---
seg_q = defaultdict(lambda: defaultdict(float))
seg_q_cnt = defaultdict(lambda: defaultdict(int))
for r in actuals:
    if r["revenue"] is not None:
        seg_q[r["segment"]][r["quarter"]] += r["revenue"]
        seg_q_cnt[r["segment"]][r["quarter"]] += 1

print("\n--- Segment Revenue ---")
seg_results = {}
for seg in sorted(seg_q.keys()):
    q4 = seg_q[seg].get("2025-Q4", 0)
    q1 = seg_q[seg].get("2026-Q1", 0)
    q1_25 = seg_q[seg].get("2025-Q1", 0)
    chg_qoq = (q1 - q4) / q4 * 100 if q4 else 0
    chg_yoy = (q1 - q1_25) / q1_25 * 100 if q1_25 else 0
    pct_of_total = q1 / q1_2026 * 100 if q1_2026 else 0
    print(f"{seg}: Q4={q4:.2f}, Q1_2026={q1:.2f}, QoQ={chg_qoq:.1f}%, YoY={chg_yoy:.1f}%, share={pct_of_total:.1f}%")
    seg_results[seg] = {
        "q1_2025": round(q1_25, 2),
        "q4_2025": round(q4, 2),
        "q1_2026": round(q1, 2),
        "change_pct_qoq": round(chg_qoq, 1),
        "change_pct_yoy": round(chg_yoy, 1),
        "share_of_q1_2026_pct": round(pct_of_total, 1)
    }

# --- Region breakdown ---
reg_q = defaultdict(lambda: defaultdict(float))
for r in actuals:
    if r["revenue"] is not None and r["region"]:
        reg_q[r["region"]][r["quarter"]] += r["revenue"]

print("\n--- Region Revenue ---")
reg_results = {}
for reg in sorted(reg_q.keys()):
    q4 = reg_q[reg].get("2025-Q4", 0)
    q1 = reg_q[reg].get("2026-Q1", 0)
    q1_25 = reg_q[reg].get("2025-Q1", 0)
    chg_qoq = (q1 - q4) / q4 * 100 if q4 else 0
    chg_yoy = (q1 - q1_25) / q1_25 * 100 if q1_25 else 0
    pct_of_total = q1 / q1_2026 * 100 if q1_2026 else 0
    print(f"{reg}: Q4={q4:.2f}, Q1_2026={q1:.2f}, QoQ={chg_qoq:.1f}%, share={pct_of_total:.1f}%")
    reg_results[reg] = {
        "q1_2025": round(q1_25, 2),
        "q4_2025": round(q4, 2),
        "q1_2026": round(q1, 2),
        "change_pct_qoq": round(chg_qoq, 1),
        "change_pct_yoy": round(chg_yoy, 1),
        "share_of_q1_2026_pct": round(pct_of_total, 1)
    }

# --- Product breakdown ---
prod_q = defaultdict(lambda: defaultdict(float))
for r in actuals:
    if r["revenue"] is not None:
        prod_q[r["product"]][r["quarter"]] += r["revenue"]

print("\n--- Product Revenue ---")
prod_results = {}
for prod in sorted(prod_q.keys()):
    q4 = prod_q[prod].get("2025-Q4", 0)
    q1 = prod_q[prod].get("2026-Q1", 0)
    q1_25 = prod_q[prod].get("2025-Q1", 0)
    chg_qoq = (q1 - q4) / q4 * 100 if q4 else 0
    chg_yoy = (q1 - q1_25) / q1_25 * 100 if q1_25 else 0
    pct = q1 / q1_2026 * 100 if q1_2026 else 0
    print(f"{prod}: Q4={q4:.2f}, Q1_2026={q1:.2f}, QoQ={chg_qoq:.1f}%, share={pct:.1f}%")
    prod_results[prod] = {
        "q1_2025": round(q1_25, 2),
        "q4_2025": round(q4, 2),
        "q1_2026": round(q1, 2),
        "change_pct_qoq": round(chg_qoq, 1),
        "change_pct_yoy": round(chg_yoy, 1),
        "share_of_q1_2026_pct": round(pct, 1)
    }

# --- 6. Top 5 customers Q1 2026 ---
cust_q1 = defaultdict(float)
cust_q1_orders = defaultdict(int)
cust_seg = {}
for r in actuals:
    if r["quarter"] == "2026-Q1" and r["revenue"] is not None:
        cust_q1[r["customer_id"]] += r["revenue"]
        cust_q1_orders[r["customer_id"]] += 1
        cust_seg[r["customer_id"]] = r["segment"]

top5 = sorted(cust_q1.items(), key=lambda x: x[1], reverse=True)[:5]
print("\n--- Top 5 Customers Q1 2026 ---")
top5_out = []
for cid, rev in top5:
    print(f"{cid}: {rev:.2f} ({cust_seg.get(cid,'?')}, {cust_q1_orders[cid]} orders)")
    top5_out.append({"customer_id": cid, "revenue": round(rev, 2), "segment": cust_seg.get(cid), "order_count": cust_q1_orders[cid]})

# --- 7. Segment x Region heatmap Q1 2026 ---
heat = defaultdict(lambda: defaultdict(float))
heat_cnt = defaultdict(lambda: defaultdict(int))
for r in actuals:
    if r["quarter"] == "2026-Q1" and r["revenue"] is not None and r["region"]:
        heat[r["segment"]][r["region"]] += r["revenue"]
        heat_cnt[r["segment"]][r["region"]] += 1

print("\n--- Heatmap Seg x Region Q1 2026 ---")
heatmap_out = []
regions_all = ["East", "West", "North", "South"]
segments_all = ["SMB", "Mid-Market", "Enterprise"]
for seg in segments_all:
    for reg in regions_all:
        val = heat[seg].get(reg, 0)
        cnt = heat_cnt[seg].get(reg, 0)
        if val > 0:
            print(f"{seg} x {reg}: {val:.2f} ({cnt} orders)")
        heatmap_out.append({"segment": seg, "region": reg, "revenue": round(val, 2), "order_count": cnt})

# --- March 2026 deep dive ---
print("\n--- March 2026 by segment ---")
mar26_seg = defaultdict(lambda: {"rev": 0.0, "cnt": 0, "dr_sum": 0.0, "dr_cnt": 0})
for r in actuals:
    if r["month"] == "2026-03":
        if r["revenue"] is not None:
            mar26_seg[r["segment"]]["rev"] += r["revenue"]
            mar26_seg[r["segment"]]["cnt"] += 1
        if r["discount_rate"] is not None:
            mar26_seg[r["segment"]]["dr_sum"] += r["discount_rate"]
            mar26_seg[r["segment"]]["dr_cnt"] += 1

mar26_seg_out = {}
for seg in sorted(mar26_seg.keys()):
    d2 = mar26_seg[seg]
    aov = d2["rev"] / d2["cnt"] if d2["cnt"] else 0
    avg_dr = d2["dr_sum"] / d2["dr_cnt"] if d2["dr_cnt"] else 0
    print(f"{seg}: rev={d2['rev']:.2f}, orders={d2['cnt']}, AOV={aov:.2f}, avg_dr={avg_dr:.4f}")
    mar26_seg_out[seg] = {"revenue": round(d2["rev"], 2), "order_count": d2["cnt"], "aov": round(aov, 2), "avg_discount_rate": round(avg_dr, 4)}

print("\n--- March 2026 by region ---")
mar26_reg = defaultdict(lambda: {"rev": 0.0, "cnt": 0})
for r in actuals:
    if r["month"] == "2026-03" and r["region"]:
        if r["revenue"] is not None:
            mar26_reg[r["region"]]["rev"] += r["revenue"]
            mar26_reg[r["region"]]["cnt"] += 1

mar26_reg_out = {}
for reg in sorted(mar26_reg.keys()):
    d2 = mar26_reg[reg]
    print(f"{reg}: rev={d2['rev']:.2f}, orders={d2['cnt']}")
    mar26_reg_out[reg] = {"revenue": round(d2["rev"], 2), "order_count": d2["cnt"]}

# --- Churn analysis Q1 2026 ---
print("\n--- Q1 2026 churn flag analysis ---")
churn_rev = defaultdict(float)
churn_cnt = defaultdict(int)
for r in actuals:
    if r["quarter"] == "2026-Q1" and r["revenue"] is not None:
        churn_rev[r["churn_flag"]] += r["revenue"]
        churn_cnt[r["churn_flag"]] += 1
for cf in [0, 1]:
    print(f"churn_flag={cf}: rev={churn_rev[cf]:.2f}, orders={churn_cnt[cf]}")

# --- MoM change series ---
print("\n--- Month-over-Month ---")
mom_series = []
prev_rev = None
for m in months_sorted:
    cur_rev = monthly[m]["revenue"]
    mom_pct = None
    if prev_rev and prev_rev > 0:
        mom_pct = round((cur_rev - prev_rev) / prev_rev * 100, 1)
    mom_series.append({"month": m, "revenue": round(cur_rev, 2), "mom_pct": mom_pct})
    if mom_pct is not None:
        print(f"{m}: {cur_rev:.2f} ({mom_pct:+.1f}%)")
    else:
        print(f"{m}: {cur_rev:.2f} (base)")
    prev_rev = cur_rev

# --- Anomaly detection rolling 3-month ---
print("\n--- Anomalies ---")
rev_list = [monthly[m]["revenue"] for m in months_sorted]
anomalies = []
for i, m in enumerate(months_sorted):
    if i < 3:
        continue
    window = rev_list[i-3:i]
    mean = sum(window) / len(window)
    variance = sum((x - mean)**2 for x in window) / len(window)
    std = variance**0.5
    if std > 0:
        z = (rev_list[i] - mean) / std
        if abs(z) > 2:
            print(f"ANOMALY {m}: rev={rev_list[i]:.2f}, rolling_mean={mean:.2f}, z={z:.2f}")
            anomalies.append({"month": m, "revenue": round(rev_list[i], 2), "rolling_mean": round(mean, 2), "z_score": round(z, 2)})

# --- Inflection points ---
print("\n--- Inflection Points ---")
inflections = []
for i in range(1, len(months_sorted) - 1):
    prev = rev_list[i-1]
    cur = rev_list[i]
    nxt = rev_list[i+1]
    # local peak or trough
    if cur > prev and cur > nxt:
        print(f"PEAK: {months_sorted[i]} ({cur:.2f})")
        inflections.append({"month": months_sorted[i], "type": "peak", "revenue": round(cur, 2)})
    elif cur < prev and cur < nxt:
        print(f"TROUGH: {months_sorted[i]} ({cur:.2f})")
        inflections.append({"month": months_sorted[i], "type": "trough", "revenue": round(cur, 2)})

# --- Simpson paradox check: segment within each region ---
print("\n--- Simpson Paradox: Segment trends within each region ---")
seg_reg_q = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))
for r in actuals:
    if r["revenue"] is not None and r["region"]:
        seg_reg_q[r["region"]][r["segment"]][r["quarter"]] += r["revenue"]

paradox_checks = []
for reg in sorted(seg_reg_q.keys()):
    reg_q4 = reg_q[reg].get("2025-Q4", 0)
    reg_q1 = reg_q[reg].get("2026-Q1", 0)
    reg_dir = "UP" if reg_q1 > reg_q4 else "DOWN"
    seg_dirs = {}
    for seg in sorted(seg_reg_q[reg].keys()):
        s_q4 = seg_reg_q[reg][seg].get("2025-Q4", 0)
        s_q1 = seg_reg_q[reg][seg].get("2026-Q1", 0)
        s_dir = "UP" if s_q1 > s_q4 else "DOWN"
        s_chg = (s_q1 - s_q4) / s_q4 * 100 if s_q4 else None
        seg_dirs[seg] = {"direction": s_dir, "change_pct": round(s_chg, 1) if s_chg is not None else None, "q4": round(s_q4, 2), "q1_2026": round(s_q1, 2)}
        print(f"  {reg}/{seg}: Q4={s_q4:.2f}, Q1={s_q1:.2f}, {s_dir} ({s_chg:.1f}% if s_q4 else 'N/A')")
    # Check for paradox
    all_same_dir = all(v["direction"] == reg_dir for v in seg_dirs.values())
    paradox_checks.append({
        "dimension": "region",
        "sub_group": reg,
        "aggregate_direction": reg_dir,
        "aggregate_q4": round(reg_q4, 2),
        "aggregate_q1_2026": round(reg_q1, 2),
        "segment_breakdown": seg_dirs,
        "paradox_detected": not all_same_dir
    })
    if not all_same_dir:
        print(f"  *** PARADOX in {reg}: aggregate={reg_dir} but segments diverge ***")

print("\n=== ALL COMPUTED ===")
output_dict = {
    "monthly": monthly_out,
    "quarterly": qtr_summary,
    "segments": seg_results,
    "regions": reg_results,
    "products": prod_results,
    "top5_customers_q1_2026": top5_out,
    "heatmap_q1_2026": heatmap_out,
    "march_2026_segment": mar26_seg_out,
    "march_2026_region": mar26_reg_out,
    "churn_q1_2026": {str(k): {"revenue": round(churn_rev[k],2), "orders": churn_cnt[k]} for k in [0,1]},
    "mom_series": mom_series,
    "anomalies": anomalies,
    "inflections": inflections,
    "paradox_checks": paradox_checks,
    "key_metrics": {
        "q1_2026_revenue": round(q1_2026, 2),
        "q4_2025_revenue": round(q4_2025, 2),
        "q1_2025_revenue": round(q1_2025, 2),
        "qoq_pct": round(qoq_q1, 1),
        "yoy_pct": round(yoy_q1, 1),
        "q2_2026_partial_revenue": round(q2_2026, 2),
        "q2_2025_revenue": round(q2_2025, 2),
        "q3_2025_revenue": round(q3_2025, 2)
    }
}

# Print JSON to stdout for agent capture
print(json.dumps(output_dict, indent=2))

# Automatically write to pipeline directory for deterministic runs
out_dir = _BASE / "data" / "pipeline" / STEM
out_dir.mkdir(parents=True, exist_ok=True)
out_file = out_dir / "descriptive_output.json"
with open(out_file, "w", encoding="utf-8") as f:
    json.dump(output_dict, f, indent=2, ensure_ascii=False)
log.info("descriptive_output_saved", path=str(out_file))
