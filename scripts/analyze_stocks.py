#!/usr/bin/env python3
"""Tinh metrics mo ta cho 10 ma trong config.yaml tu 30 phien gan nhat.

Output: data/pipeline/stock_metrics.json
Chi dung thu vien chuan (moi truong khong co pandas).
"""
import csv
import json
import os
import re
from collections import defaultdict
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_PATH = os.path.join(ROOT, "data", "stock_data.csv")
CONFIG_PATH = os.path.join(ROOT, "config.yaml")
OUT_PATH = os.path.join(ROOT, "data", "pipeline", "stock_metrics.json")

WINDOW = 30  # so phien gan nhat dua vao phan tich


def load_tickers(path):
    """Doc danh sach ticker tu config.yaml (parser toi thieu, khong can PyYAML)."""
    tickers, in_block = [], False
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if re.match(r"^tickers:\s*$", line):
                in_block = True
                continue
            if in_block:
                m = re.match(r"^\s*-\s*([A-Za-z0-9.]+)\s*$", line)
                if m:
                    tickers.append(m.group(1))
                elif line.strip() and not line.lstrip().startswith("#"):
                    break
    return tickers


def load_rows(path):
    by_ticker = defaultdict(list)
    with open(path, encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            try:
                close = float(row["Close"])
                volume = float(row["Volume"])
            except (TypeError, ValueError):
                continue  # bo qua phien thieu data
            by_ticker[row["Ticker"]].append((row["Date"], close, volume))
    for series in by_ticker.values():
        series.sort(key=lambda r: r[0])
    return by_ticker


def slope(values):
    """Slope hoi quy tuyen tinh don gian theo chi so phien."""
    n = len(values)
    mean_x = (n - 1) / 2
    mean_y = sum(values) / n
    num = sum((i - mean_x) * (v - mean_y) for i, v in enumerate(values))
    den = sum((i - mean_x) ** 2 for i in range(n))
    return num / den if den else 0.0


def stdev(values):
    n = len(values)
    if n < 2:
        return 0.0
    mean = sum(values) / n
    return (sum((v - mean) ** 2 for v in values) / (n - 1)) ** 0.5


def compute(series):
    """series: list (date, close, volume) da sort tang dan, toi da WINDOW phien."""
    closes = [c for _, c, _ in series]
    volumes = [v for _, _, v in series]
    first, last = closes[0], closes[-1]

    ret_30d = (last / first - 1) * 100

    daily = [(closes[i] / closes[i - 1] - 1) * 100 for i in range(1, len(closes))]
    vol = stdev(daily)

    # Slope chuan hoa ve %/phien de so sanh giua cac ma khac gia
    slope_pct = slope(closes) / (sum(closes) / len(closes)) * 100
    if slope_pct > 0.15:
        trend = "tang"
    elif slope_pct < -0.15:
        trend = "giam"
    else:
        trend = "sideway"

    avg_all = sum(volumes) / len(volumes)
    avg_7d = sum(volumes[-7:]) / len(volumes[-7:])
    vol_trend = (avg_7d / avg_all - 1) * 100 if avg_all else 0.0

    return {
        "first_date": series[0][0],
        "last_date": series[-1][0],
        "sessions": len(series),
        "first_close": round(first, 2),
        "last_close": round(last, 2),
        "return_30d_pct": round(ret_30d, 2),
        "volatility_pct": round(vol, 2),
        "slope_pct_per_session": round(slope_pct, 3),
        "trend": trend,
        "avg_volume_all": round(avg_all),
        "avg_volume_7d": round(avg_7d),
        "volume_trend_pct": round(vol_trend, 1),
        # Sharpe-like: return tren moi don vi rui ro
        "risk_adj": round(ret_30d / vol, 2) if vol else 0.0,
        "normalized": [round(c / first * 100, 2) for c in closes],
        "dates": [d for d, _, _ in series],
    }


def main():
    tickers = load_tickers(CONFIG_PATH)
    by_ticker = load_rows(CSV_PATH)

    latest_date = max(d for series in by_ticker.values() for d, _, _ in series)

    metrics, missing = {}, []
    for t in tickers:
        series = by_ticker.get(t, [])[-WINDOW:]
        if len(series) < 5:
            missing.append(t)
            continue
        m = compute(series)
        if m["last_date"] != latest_date:
            m["stale"] = True
        metrics[t] = m

    # Xep hang: 60% risk-adjusted return, 40% momentum (slope) -> z-score don gian
    def zscores(key):
        vals = [metrics[t][key] for t in metrics]
        mean = sum(vals) / len(vals)
        sd = stdev(vals) or 1.0
        return {t: (metrics[t][key] - mean) / sd for t in metrics}

    z_risk = zscores("risk_adj")
    z_slope = zscores("slope_pct_per_session")
    for t in metrics:
        metrics[t]["score"] = round(0.6 * z_risk[t] + 0.4 * z_slope[t], 3)

    ranked = sorted(metrics, key=lambda t: metrics[t]["score"], reverse=True)
    for rank, t in enumerate(ranked, 1):
        metrics[t]["rank"] = rank
        if rank <= 3:
            metrics[t]["bucket"] = "consider"
        elif rank <= len(ranked) - 3:
            metrics[t]["bucket"] = "watch"
        else:
            metrics[t]["bucket"] = "avoid"

    out = {
        "generated_on": date.today().isoformat(),
        "data_latest_date": latest_date,
        "window_sessions": WINDOW,
        "tickers_missing": missing,
        "ranking": ranked,
        "metrics": metrics,
    }
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=2)
    print(json.dumps({t: {k: metrics[t][k] for k in
                          ("rank", "bucket", "return_30d_pct", "volatility_pct",
                           "trend", "volume_trend_pct", "risk_adj", "score",
                           "sessions")} for t in ranked},
                     ensure_ascii=False, indent=1))
    print("latest:", latest_date, "missing:", missing)


if __name__ == "__main__":
    main()
