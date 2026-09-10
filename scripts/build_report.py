#!/usr/bin/env python3
"""Render report HTML 1 trang tu stock_metrics.json (stdlib only)."""
import json, os
from datetime import date

ROOT = "/home/user/vn-stock-data"
M = json.load(open(os.path.join(ROOT, "data", "pipeline", "stock_metrics.json")))
metrics, ranked = M["metrics"], M["ranking"]
today = M["generated_on"]
OUT = os.path.join(ROOT, "data", "reports", f"stock_report_{today}.html")

C = {"blue": "#2554E7", "green": "#10B981", "amber": "#F59E0B", "red": "#EF4444",
     "navy": "#0F1729", "muted": "#64748B", "border": "#E2E8F0", "surface": "#F8FAFC"}
SERIES = ["#2554E7", "#9333EA", "#10B981", "#F97316", "#EF4444",
          "#0EA5E9", "#F59E0B", "#14B8A6", "#EC4899", "#64748B"]

NARRATIVE = json.load(open(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "narrative.json"), encoding="utf-8"))

# ── chart: Close normalized ve 100 ─────────────────────────────
W, H = 1080, 300
PL, PR, PT, PB = 44, 92, 14, 26
dates = metrics[ranked[0]]["dates"]
norm = {t: [c / metrics[t]["closes"][0] * 100 for c in metrics[t]["closes"]] for t in ranked}
lo = min(min(v) for v in norm.values())
hi = max(max(v) for v in norm.values())
lo, hi = lo - 2, hi + 2
n = len(dates)


def X(i): return PL + i * (W - PL - PR) / (n - 1)
def Y(v): return PT + (hi - v) * (H - PT - PB) / (hi - lo)


parts = []
for gv in range(int(lo // 5 * 5), int(hi) + 6, 5):
    if not (lo <= gv <= hi):
        continue
    parts.append(f'<line x1="{PL}" y1="{Y(gv):.1f}" x2="{W-PR}" y2="{Y(gv):.1f}" '
                 f'stroke="{C["border"]}" stroke-width="1"/>')
    parts.append(f'<text x="{PL-8}" y="{Y(gv)+4:.1f}" text-anchor="end" class="ax">{gv}</text>')
for i in (0, n // 2, n - 1):
    anchor = "start" if i == 0 else ("end" if i == n - 1 else "middle")
    parts.append(f'<text x="{X(i):.1f}" y="{H-8}" text-anchor="{anchor}" class="ax">{dates[i][5:]}</text>')
for k, t in enumerate(ranked):
    d = " ".join(f"{'M' if i == 0 else 'L'}{X(i):.1f},{Y(v):.1f}" for i, v in enumerate(norm[t]))
    top = metrics[t]["bucket"] == "buy"
    parts.append(f'<path d="{d}" fill="none" stroke="{SERIES[k]}" '
                 f'stroke-width="{2.4 if top else 1.2}" opacity="{1 if top else 0.45}"/>')

# nhan cuoi duong: day xuong de khong chong nhau (toi thieu 12px)
GAP = 12
lab = sorted(((Y(norm[t][-1]), t, k) for k, t in enumerate(ranked)), key=lambda x: x[0])
placed = []
for y, t, k in lab:
    if placed and y - placed[-1][0] < GAP:
        y = placed[-1][0] + GAP
    placed.append((y, t, k))
shift = placed[-1][0] - (H - PB)  # neu tran day, keo ca cum len
if shift > 0:
    placed = [(y - shift, t, k) for y, t, k in placed]
for y, t, k in placed:
    top = metrics[t]["bucket"] == "buy"
    ay = Y(norm[t][-1])
    if abs(y - ay) > 2:
        parts.append(f'<line x1="{W-PR}" y1="{ay:.1f}" x2="{W-PR+4}" y2="{y-4:.1f}" '
                     f'stroke="{SERIES[k]}" stroke-width="0.8" opacity="0.4"/>')
    parts.append(f'<text x="{W-PR+6}" y="{y:.1f}" class="lb" fill="{SERIES[k]}" '
                 f'opacity="{1 if top else 0.7}">{t} {norm[t][-1]:.0f}</text>')
chart = (f'<svg viewBox="0 0 {W} {H}" role="img" '
         f'aria-label="Hiệu suất giá đóng cửa chuẩn hoá về 100">{"".join(parts)}</svg>')

# ── bang ──────────────────────────────────────────────────────
BADGE = {"buy": ("badge-buy", "✅ Nên xem xét"),
         "watch": ("badge-watch", "⚠️ Theo dõi thêm"),
         "avoid": ("badge-avoid", "❌ Tránh / chờ")}
TR = {"Tăng": ("t-up", "▲ Tăng"), "Giảm": ("t-down", "▼ Giảm"), "Sideway": ("t-flat", "► Sideway")}
rows = []
for t in ranked:
    m = metrics[t]
    bc, bt = BADGE[m["bucket"]]
    tc, tt = TR[m["trend"]]
    vt = m["volume_trend_pct"]
    rows.append(
        f'<tr><td class="rk">{m["rank"]}</td><td class="tk">{t}</td>'
        f'<td class="num pos">+{m["return_30d_pct"]:.2f}%</td>'
        f'<td class="num">{m["volatility_pct"]:.2f}%</td>'
        f'<td class="num">{m["risk_adj"]:.2f}</td>'
        f'<td class="{tc}">{tt}</td>'
        f'<td class="num {"pos" if vt >= 0 else "neg"}">{vt:+.1f}%</td>'
        f'<td><span class="badge {bc}">{bt}</span></td></tr>')

picks = []
for t in ranked[:3]:
    m = metrics[t]
    picks.append(
        f'<div class="pick"><div class="pick-h"><span class="pick-tk">{t}</span>'
        f'<span class="pick-ret">+{m["return_30d_pct"]:.1f}% / 30D</span></div>'
        f'<div class="pick-sub">Vol {m["volatility_pct"]:.2f}% · R/R {m["risk_adj"]:.2f} · '
        f'KL 7D {m["volume_trend_pct"]:+.0f}%</div>'
        f'<p>{NARRATIVE[t]}</p></div>')

miss = M["tickers_missing"]
note = (f'Thiếu data: {", ".join(miss)} — đã loại khỏi xếp hạng.' if miss
        else 'Đủ data cho cả 10 mã trong cửa sổ quan sát.')
w = metrics[ranked[0]]
avg_ret = sum(metrics[t]["return_30d_pct"] for t in ranked) / len(ranked)
n_up = sum(1 for t in ranked if metrics[t]["trend"] == "Tăng")

html = f"""<!DOCTYPE html>
<html lang="vi"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>VN Stock Daily Briefing — {today}</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font:400 13px/1.5 'IBM Plex Sans',system-ui,-apple-system,sans-serif;
color:#1A202C;background:#F7F6F2;padding:20px}}
.page{{max-width:1180px;margin:0 auto;background:#fff;border:1px solid {C['border']};
border-radius:16px;padding:24px 28px;box-shadow:0 4px 6px rgba(0,0,0,.06)}}
h1{{font:700 25px/1.2 'Outfit',system-ui,sans-serif;color:{C['navy']};letter-spacing:-.4px}}
.sub{{color:{C['muted']};font-size:12px;margin-top:4px}}
header{{display:flex;justify-content:space-between;align-items:flex-end;gap:16px;
border-bottom:2px solid {C['navy']};padding-bottom:12px;margin-bottom:16px;flex-wrap:wrap}}
.kpis{{display:flex;gap:22px}}
.kpi-v{{font:700 20px 'Outfit',sans-serif;color:{C['navy']}}}
.kpi-l{{font-size:10px;text-transform:uppercase;letter-spacing:.5px;color:{C['muted']}}}
h2{{font:600 15px 'Outfit',sans-serif;color:{C['navy']};margin:18px 0 8px;
display:flex;align-items:center;gap:8px}}
h2::before{{content:"";width:3px;height:14px;background:{C['blue']};border-radius:2px}}
table{{width:100%;border-collapse:collapse;font-size:12.5px}}
th{{text-align:left;font:600 10px 'IBM Plex Sans',sans-serif;text-transform:uppercase;
letter-spacing:.5px;color:{C['muted']};padding:6px 8px;border-bottom:1px solid {C['border']}}}
td{{padding:6px 8px;border-bottom:1px solid #F1F5F9}}
tbody tr:hover{{background:{C['surface']}}}
.num{{text-align:right;font-family:'IBM Plex Mono',Menlo,monospace}}
th.num{{text-align:right}}
.rk{{color:{C['muted']};width:24px}}.tk{{font-weight:700;color:{C['navy']}}}
.pos{{color:{C['green']}}}.neg{{color:{C['red']}}}
.t-up{{color:{C['green']};font-weight:600}}.t-down{{color:{C['red']};font-weight:600}}
.t-flat{{color:{C['muted']};font-weight:600}}
.badge{{display:inline-block;padding:2px 8px;border-radius:20px;font-size:11px;font-weight:600;white-space:nowrap}}
.badge-buy{{background:rgba(16,185,129,.12);color:{C['green']}}}
.badge-watch{{background:rgba(245,158,11,.12);color:{C['amber']}}}
.badge-avoid{{background:rgba(239,68,68,.1);color:{C['red']}}}
.chart{{background:#FCFCFA;border:1px solid {C['border']};border-radius:12px;padding:6px 4px}}
.chart svg{{width:100%;height:auto;display:block}}
.ax{{font:400 9.5px 'IBM Plex Mono',monospace;fill:{C['muted']}}}
.lb{{font:600 10px 'IBM Plex Sans',sans-serif}}
.picks{{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}}
.pick{{border:1px solid {C['border']};border-left:3px solid {C['green']};
border-radius:10px;padding:10px 12px;background:{C['surface']}}}
.pick-h{{display:flex;justify-content:space-between;align-items:baseline}}
.pick-tk{{font:700 16px 'Outfit',sans-serif;color:{C['navy']}}}
.pick-ret{{font:600 12px 'IBM Plex Mono',monospace;color:{C['green']}}}
.pick-sub{{font:400 10.5px 'IBM Plex Mono',monospace;color:{C['muted']};margin:2px 0 6px}}
.pick p{{font-size:12px;line-height:1.45;color:#334155}}
footer{{margin-top:16px;padding-top:10px;border-top:1px solid {C['border']};
font-size:10.5px;color:{C['muted']};display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap}}
@media(max-width:820px){{.picks{{grid-template-columns:1fr}}body{{padding:10px}}
.page{{padding:16px}}header{{align-items:flex-start}}}}
</style></head><body><div class="page">
<header>
  <div><h1>VN Stock Daily Briefing — {today}</h1>
  <div class="sub">Cửa sổ {w['sessions']} phiên · {w['from']} → {w['to']} · Data mới nhất: {M['data_latest_date']}</div></div>
  <div class="kpis">
    <div><div class="kpi-v">{len(ranked)}</div><div class="kpi-l">Mã theo dõi</div></div>
    <div><div class="kpi-v pos">+{avg_ret:.1f}%</div><div class="kpi-l">Return TB 30D</div></div>
    <div><div class="kpi-v">{n_up}/{len(ranked)}</div><div class="kpi-l">Xu hướng tăng</div></div>
  </div>
</header>

<h2>Bảng tổng hợp 10 mã</h2>
<table><thead><tr><th></th><th>Mã</th><th class="num">Return 30D</th>
<th class="num">Volatility</th><th class="num">Return/Risk</th><th>Trend</th>
<th class="num">KL 7D vs TB</th><th>Khuyến nghị</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table>

<h2>Hiệu suất so sánh (Close chuẩn hoá = 100 tại {w['from']})</h2>
<div class="chart">{chart}</div>

<h2>Top picks hôm nay</h2>
<div class="picks">{''.join(picks)}</div>

<footer><span>{note}</span>
<span>Xếp hạng = 45% Return 30D + 30% (nghịch) Volatility + 25% Slope xu hướng, z-score chuẩn hoá.
Báo cáo mô tả, không phải khuyến nghị đầu tư.</span></footer>
</div></body></html>"""

os.makedirs(os.path.dirname(OUT), exist_ok=True)
open(OUT, "w", encoding="utf-8").write(html)
print("wrote", OUT, len(html), "bytes")
