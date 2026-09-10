#!/usr/bin/env python3
"""Tinh metrics 30 ngay gan nhat cho tung ticker (stdlib only)."""
import csv, json, os, re, statistics as st
from datetime import date

ROOT = "/home/user/vn-stock-data"
CSV = os.path.join(ROOT, "data", "stock_data.csv")
OUT = os.path.join(ROOT, "data", "pipeline", "stock_metrics.json")
WINDOW = 30

# --- config tickers (parse toi thieu, khong can pyyaml) ---
tickers = []
with open(os.path.join(ROOT, "config.yaml")) as f:
    in_tickers = False
    for line in f:
        if re.match(r"^tickers:", line):
            in_tickers = True
            continue
        if in_tickers:
            m = re.match(r"^\s*-\s*([A-Z0-9]+)\s*$", line)
            if m:
                tickers.append(m.group(1))
            elif line.strip() and not line.startswith(" "):
                break
top_picks = 3

rows = {}
with open(CSV) as f:
    for r in csv.DictReader(f):
        rows.setdefault(r["Ticker"], []).append(r)

latest_date = max(r["Date"] for rs in rows.values() for r in rs)

metrics = {}
missing = []
for t in tickers:
    rs = sorted(rows.get(t, []), key=lambda r: r["Date"])
    if len(rs) < 5:
        missing.append(t)
        continue
    w = rs[-WINDOW:]
    closes = [float(r["Close"]) for r in w]
    vols = [float(r["Volume"]) for r in w]
    dates = [r["Date"] for r in w]

    ret = (closes[-1] / closes[0] - 1) * 100
    daily = [(closes[i] / closes[i - 1] - 1) * 100 for i in range(1, len(closes))]
    vol_pct = st.pstdev(daily) if len(daily) > 1 else 0.0

    # slope hoi quy tuyen tinh, chuan hoa theo gia trung binh -> %/ngay
    n = len(closes)
    xs = list(range(n))
    mx, my = sum(xs) / n, sum(closes) / n
    num = sum((xs[i] - mx) * (closes[i] - my) for i in range(n))
    den = sum((x - mx) ** 2 for x in xs)
    slope = num / den if den else 0.0
    slope_pct = slope / my * 100

    if slope_pct > 0.15:
        trend = "Tăng"
    elif slope_pct < -0.15:
        trend = "Giảm"
    else:
        trend = "Sideway"

    v7 = sum(vols[-7:]) / len(vols[-7:])
    vavg = sum(vols) / len(vols)
    vtrend = (v7 / vavg - 1) * 100 if vavg else 0.0

    metrics[t] = {
        "ticker": t,
        "sessions": n,
        "from": dates[0],
        "to": dates[-1],
        "close_first": round(closes[0], 2),
        "close_last": round(closes[-1], 2),
        "return_30d_pct": round(ret, 2),
        "volatility_pct": round(vol_pct, 2),
        "slope_pct_per_day": round(slope_pct, 3),
        "trend": trend,
        "volume_7d_avg": round(v7),
        "volume_window_avg": round(vavg),
        "volume_trend_pct": round(vtrend, 1),
        "risk_adj": round(ret / vol_pct, 2) if vol_pct else 0.0,
        "closes": [round(c, 2) for c in closes],
        "dates": dates,
    }

# --- xep hang: z-score tong hop ---
def z(vals):
    m = sum(vals) / len(vals)
    s = st.pstdev(vals) or 1.0
    return [(v - m) / s for v in vals]

ts = list(metrics)
zr = z([metrics[t]["return_30d_pct"] for t in ts])
zv = z([-metrics[t]["volatility_pct"] for t in ts])
zs = z([metrics[t]["slope_pct_per_day"] for t in ts])
for i, t in enumerate(ts):
    metrics[t]["score"] = round(0.45 * zr[i] + 0.30 * zv[i] + 0.25 * zs[i], 3)

ranked = sorted(ts, key=lambda t: metrics[t]["score"], reverse=True)
n = len(ranked)
mid_end = top_picks + max(1, (n - top_picks) // 2 + 1)
for i, t in enumerate(ranked):
    metrics[t]["rank"] = i + 1
    if i < top_picks:
        metrics[t]["bucket"] = "buy"
        metrics[t]["recommendation"] = "✅ Nên xem xét"
    elif i < mid_end:
        metrics[t]["bucket"] = "watch"
        metrics[t]["recommendation"] = "⚠️ Theo dõi thêm"
    else:
        metrics[t]["bucket"] = "avoid"
        metrics[t]["recommendation"] = "❌ Tránh / chờ"

out = {
    "generated_on": date.today().isoformat(),
    "data_latest_date": latest_date,
    "window_sessions": WINDOW,
    "tickers_missing": missing,
    "ranking": ranked,
    "metrics": metrics,
}
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)

print("latest:", latest_date, "| missing:", missing)
hdr = f"{'#':>2} {'Tik':<4} {'Ret30D':>7} {'Vol':>6} {'Slope':>7} {'Trend':<8} {'VolTr':>7} {'Score':>6}"
print(hdr)
for t in ranked:
    m = metrics[t]
    print(f"{m['rank']:>2} {t:<4} {m['return_30d_pct']:>6.2f}% {m['volatility_pct']:>5.2f}% "
          f"{m['slope_pct_per_day']:>6.3f}% {m['trend']:<8} {m['volume_trend_pct']:>6.1f}% {m['score']:>6.2f}")
