#!/usr/bin/env python3
"""Render report HTML 1 trang tu data/pipeline/stock_metrics.json.

Chart la inline SVG (khong phu thuoc CDN/JS) theo huong storytelling-with-data:
cac ma nen ve mau xam, 3 ma top picks ve mau nhan + direct label.
"""
import json
import os
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
METRICS_PATH = os.path.join(ROOT, "data", "pipeline", "stock_metrics.json")
REPORT_DIR = os.path.join(ROOT, "reports")

BUCKET_LABEL = {
    "consider": ("✅ Nên xem xét", "b-ok"),
    "watch": ("⚠️ Theo dõi thêm", "b-watch"),
    "avoid": ("❌ Tránh / chờ", "b-avoid"),
}
TREND_LABEL = {"tang": "▲ Tăng", "giam": "▼ Giảm", "sideway": "→ Sideway"}
ACCENT = ["#1a5fb4", "#2c8c5a", "#b5651d"]

# Luan diem cho tung top pick — viet tay, cap nhat khi ranking doi.
NOTES = {
    "FPT": "Dẫn đầu về hiệu suất điều chỉnh rủi ro: +{r}% trong 30 phiên với biến động chỉ {v}%/phiên. "
           "Đường giá đi lên đều, không có phiên gãy mạnh, và thanh khoản 7 phiên cuối vẫn ngang mức bình quân kỳ "
           "— đà tăng đến từ tích lũy chứ không phải một cú bơm ngắn hạn.",
    "MBB": "Biến động thấp nhất nhóm ngân hàng ({v}%/phiên) nhưng vẫn đạt +{r}%. "
           "Xu hướng tăng ổn định, phù hợp cho vị thế nắm giữ. "
           "Điểm cần lưu ý: khối lượng 7 phiên cuối giảm {vt}% so với bình quân — đà mua đang chậm lại, nên vào từng phần.",
    "TCB": "Tăng {r}% kèm khối lượng 7 phiên cuối cao hơn bình quân {vt}% — dòng tiền đang thực sự vào. "
           "Đổi lại, biến động {v}%/phiên thuộc nhóm cao hơn trung bình, nên biên độ dao động trong ngày sẽ rộng. "
           "Ưu tiên canh nhịp chỉnh thay vì mua đuổi.",
}


def fmt_pct(x, digits=2):
    return f"{x:+.{digits}f}%"


def build_chart(data, ranking, width=920, height=300):
    metrics = data["metrics"]
    pad_l, pad_r, pad_t, pad_b = 46, 62, 14, 26
    n = max(len(metrics[t]["normalized"]) for t in ranking)
    all_vals = [v for t in ranking for v in metrics[t]["normalized"]]
    lo = min(min(all_vals), 100) - 2
    hi = max(all_vals) + 2

    def x(i):
        return pad_l + (width - pad_l - pad_r) * (i / (n - 1))

    def y(v):
        return pad_t + (height - pad_t - pad_b) * (1 - (v - lo) / (hi - lo))

    parts = [f'<svg viewBox="0 0 {width} {height}" role="img" '
             f'aria-label="Diễn biến giá chuẩn hoá 30 phiên, gốc 100">']

    # Gridlines + truc y
    step = 5
    g = int(lo / step) * step
    while g <= hi:
        if g >= lo:
            cls = "grid base" if g == 100 else "grid"
            parts.append(f'<line class="{cls}" x1="{pad_l}" y1="{y(g):.1f}" x2="{width - pad_r}" y2="{y(g):.1f}"/>')
            parts.append(f'<text class="ax" x="{pad_l - 8}" y="{y(g) + 4:.1f}" text-anchor="end">{g}</text>')
        g += step

    top3 = ranking[:3]
    # Ve nhom nen truoc, top picks sau de nam tren cung
    for t in [x for x in ranking if x not in top3] + top3:
        vals = metrics[t]["normalized"]
        d = " ".join(f"{'M' if i == 0 else 'L'}{x(i):.1f},{y(v):.1f}" for i, v in enumerate(vals))
        if t in top3:
            c = ACCENT[top3.index(t)]
            parts.append(f'<path d="{d}" fill="none" stroke="{c}" stroke-width="2.4"/>')
            parts.append(f'<circle cx="{x(len(vals) - 1):.1f}" cy="{y(vals[-1]):.1f}" r="3.4" fill="{c}"/>')
            parts.append(f'<text class="lbl" x="{x(len(vals) - 1) + 8:.1f}" y="{y(vals[-1]) + 4:.1f}" '
                         f'fill="{c}">{t}</text>')
        else:
            parts.append(f'<path d="{d}" fill="none" stroke="#c9ced6" stroke-width="1.3"/>')

    dates = metrics[ranking[0]]["dates"]
    parts.append(f'<text class="ax" x="{pad_l}" y="{height - 6}">{dates[0]}</text>')
    parts.append(f'<text class="ax" x="{width - pad_r}" y="{height - 6}" text-anchor="end">{dates[-1]}</text>')
    parts.append("</svg>")
    return "\n".join(parts)


def build_rows(data):
    rows = []
    for t in data["ranking"]:
        m = data["metrics"][t]
        label, cls = BUCKET_LABEL[m["bucket"]]
        ret_cls = "up" if m["return_30d_pct"] >= 0 else "down"
        vt_cls = "up" if m["volume_trend_pct"] >= 0 else "down"
        stale = ' <span class="flag" title="Thiếu phiên mới nhất">*</span>' if m.get("stale") else ""
        rows.append(f"""      <tr>
        <td class="rk">{m['rank']}</td>
        <td class="tk">{t}{stale}</td>
        <td class="num {ret_cls}">{fmt_pct(m['return_30d_pct'])}</td>
        <td class="num">{m['volatility_pct']:.2f}%</td>
        <td class="num">{m['risk_adj']:.2f}</td>
        <td>{TREND_LABEL[m['trend']]}</td>
        <td class="num {vt_cls}">{fmt_pct(m['volume_trend_pct'], 1)}</td>
        <td><span class="badge {cls}">{label}</span></td>
      </tr>""")
    return "\n".join(rows)


def build_picks(data):
    cards = []
    for i, t in enumerate(data["ranking"][:3]):
        m = data["metrics"][t]
        note = NOTES.get(t, "Xếp hạng cao nhờ hiệu suất điều chỉnh rủi ro và xu hướng giá đang lên.")
        note = note.format(r=f"{m['return_30d_pct']:.1f}", v=f"{m['volatility_pct']:.2f}",
                           vt=f"{abs(m['volume_trend_pct']):.0f}")
        cards.append(f"""    <article class="pick" style="--c:{ACCENT[i]}">
      <h3><span class="pin">#{i + 1}</span> {t}</h3>
      <p class="stats">{fmt_pct(m['return_30d_pct'])} · biến động {m['volatility_pct']:.2f}%/phiên · risk-adj {m['risk_adj']:.2f}</p>
      <p>{note}</p>
    </article>""")
    return "\n".join(cards)


def main():
    with open(METRICS_PATH, encoding="utf-8") as fh:
        data = json.load(fh)

    today = date.today().isoformat()
    missing = data["tickers_missing"]
    stale = [t for t, m in data["metrics"].items() if m.get("stale")]
    notes = []
    if missing:
        notes.append(f"Không đủ dữ liệu để chấm điểm: {', '.join(missing)} — đã loại khỏi bảng xếp hạng.")
    if stale:
        notes.append(f"Thiếu phiên {data['data_latest_date']}: {', '.join(stale)} (đánh dấu *).")
    if not notes:
        notes.append("Đủ dữ liệu 30 phiên cho cả 10 mã, không có phiên lỗi.")

    top = data["ranking"][0]
    lead = (f"{top} dẫn đầu bảng xếp hạng 30 phiên với {fmt_pct(data['metrics'][top]['return_30d_pct'])} "
            f"và biến động {data['metrics'][top]['volatility_pct']:.2f}%/phiên.")

    html = f"""<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>VN Stock Daily Briefing — {today}</title>
<style>
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; padding: 26px 30px 30px; background: #f6f7f9; color: #1a1d21;
         font: 14px/1.5 "Inter", -apple-system, "Segoe UI", Roboto, sans-serif; }}
  main {{ max-width: 1000px; margin: 0 auto; background: #fff; padding: 26px 30px 24px;
          border: 1px solid #e3e6ea; border-radius: 10px; }}
  header {{ border-bottom: 2px solid #1a1d21; padding-bottom: 12px; margin-bottom: 16px; }}
  h1 {{ font-size: 21px; margin: 0 0 4px; letter-spacing: -.2px; }}
  .sub {{ color: #6b7280; font-size: 12.5px; margin: 0; }}
  .lead {{ font-size: 14.5px; margin: 0 0 16px; padding: 9px 12px; background: #eef3fb;
           border-left: 3px solid #1a5fb4; border-radius: 0 4px 4px 0; }}
  h2 {{ font-size: 12px; text-transform: uppercase; letter-spacing: .8px; color: #6b7280;
        margin: 20px 0 8px; font-weight: 600; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  th {{ text-align: left; font-size: 11px; text-transform: uppercase; letter-spacing: .4px;
        color: #6b7280; border-bottom: 1px solid #d5d9df; padding: 6px 8px; font-weight: 600; }}
  td {{ padding: 6px 8px; border-bottom: 1px solid #eef0f3; }}
  th.num, td.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
  .rk {{ color: #9aa1ab; width: 26px; }}
  .tk {{ font-weight: 700; }}
  .up {{ color: #17703f; }}
  .down {{ color: #b3261e; }}
  .flag {{ color: #b3261e; font-weight: 700; }}
  .badge {{ display: inline-block; padding: 2px 8px; border-radius: 20px; font-size: 11.5px; white-space: nowrap; }}
  .b-ok {{ background: #e4f3ea; color: #17703f; }}
  .b-watch {{ background: #fdf2dd; color: #8a5a00; }}
  .b-avoid {{ background: #fbe6e4; color: #a52018; }}
  .chart {{ margin-top: 6px; }}
  svg {{ width: 100%; height: auto; }}
  .grid {{ stroke: #edeff2; stroke-width: 1; }}
  .grid.base {{ stroke: #b9bfc8; stroke-dasharray: 3 3; }}
  .ax {{ font-size: 10.5px; fill: #8a919b; }}
  .lbl {{ font-size: 12px; font-weight: 700; }}
  .picks {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }}
  .pick {{ border: 1px solid #e3e6ea; border-top: 3px solid var(--c); border-radius: 6px; padding: 11px 13px; }}
  .pick h3 {{ margin: 0 0 3px; font-size: 15px; }}
  .pin {{ color: var(--c); }}
  .pick .stats {{ margin: 0 0 6px; font-size: 11.5px; color: #6b7280; font-variant-numeric: tabular-nums; }}
  .pick p {{ margin: 0; font-size: 12.5px; line-height: 1.45; }}
  footer {{ margin-top: 18px; padding-top: 10px; border-top: 1px solid #eef0f3;
            font-size: 11.5px; color: #8a919b; }}
  footer li {{ margin: 2px 0; }}
  footer ul {{ margin: 4px 0 0; padding-left: 16px; }}
  @media (max-width: 760px) {{ .picks {{ grid-template-columns: 1fr; }} }}
</style>
</head>
<body>
<main>
  <header>
    <h1>VN Stock Daily Briefing — {today}</h1>
    <p class="sub">Dữ liệu đến phiên {data['data_latest_date']} · cửa sổ {data['window_sessions']} phiên gần nhất · {len(data['ranking'])} mã theo dõi</p>
  </header>

  <p class="lead">{lead} Xếp hạng ưu tiên lợi nhuận điều chỉnh rủi ro (60%) và độ dốc xu hướng (40%).</p>

  <h2>Bảng xếp hạng 30 phiên</h2>
  <table>
    <thead>
      <tr>
        <th class="rk">#</th><th>Mã</th><th class="num">Return 30D</th><th class="num">Biến động</th>
        <th class="num">Risk-adj</th><th>Xu hướng</th><th class="num">KL 7P vs kỳ</th><th>Khuyến nghị</th>
      </tr>
    </thead>
    <tbody>
{build_rows(data)}
    </tbody>
  </table>

  <h2>Diễn biến giá chuẩn hoá (phiên đầu = 100)</h2>
  <div class="chart">
{build_chart(data, data['ranking'])}
  </div>

  <h2>Top picks hôm nay</h2>
  <div class="picks">
{build_picks(data)}
  </div>

  <footer>
    <strong>Ghi chú.</strong>
    <ul>
      <li>{'</li><li>'.join(notes)}</li>
      <li>Risk-adj = Return 30D chia cho độ lệch chuẩn daily return. Biến động tính theo %/phiên.</li>
      <li>Phân tích mô tả trên dữ liệu giá lịch sử, không phải dự báo hay khuyến nghị đầu tư.</li>
    </ul>
  </footer>
</main>
</body>
</html>
"""
    os.makedirs(REPORT_DIR, exist_ok=True)
    out = os.path.join(REPORT_DIR, f"stock_report_{today}.html")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(html)
    print(out)


if __name__ == "__main__":
    main()
