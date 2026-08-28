# VN Stock Daily Analyst

## Mục tiêu

Mỗi ngày sau khi `stock_data.csv` được cập nhật, chạy phân tích và tạo **1 report 1 trang dạng HTML** với khuyến nghị đầu tư cổ phiếu nào trong 10 mã theo dõi.

---

## Data

- **File input**: `data/stock_data.csv`
- **Cột**: `Date, Ticker, Open, High, Low, Close, Volume`
- **Config**: đọc `config.yaml` để lấy danh sách tickers và các tham số — KHÔNG hardcode
- **Lịch sử**: 30 ngày gần nhất, append hàng ngày

---

## Nhiệm vụ khi được gọi

### Bước 0 — Kiểm tra data trước khi chạy

**0a — Kiểm tra data có tồn tại không:**
- Nếu `data/stock_data.csv` không tồn tại → báo lỗi và dừng.

**0b — Kiểm tra data có fresh không:**
- Đọc ngày mới nhất trong `data/stock_data.csv` (cột `Date`)
- Nếu ngày mới nhất cách hôm nay quá 3 ngày → báo "Data cũ ({ngày}), có thể fetch bị lỗi. Dừng." và thoát.

**0c — Kiểm tra đã phân tích chưa:**
- Đọc ngày trong `logs/last_analyzed.txt` (nếu file tồn tại)
- Nếu `last_analyzed` == ngày mới nhất trong CSV → báo "Đã phân tích data này rồi. Dừng." và thoát.
- Nếu khác hoặc chưa có file → tiếp tục.

### Bước 1 — Đọc và tính toán

Đọc `data/stock_data.csv` — dùng **toàn bộ data có sẵn**, không giới hạn số ngày.

Tính các chỉ số sau cho từng ticker:

- **Return (toàn kỳ)**: % thay đổi Close từ ngày đầu tiên đến ngày mới nhất trong file
- **Return 30D**: % thay đổi Close 30 ngày gần nhất (nếu có đủ data)
- **Volatility**: độ lệch chuẩn của daily return (%)
- **Trend**: slope của Close (tăng / giảm / sideway)
- **Volume trend**: volume trung bình 7 ngày cuối so với toàn kỳ

Lưu kết quả vào `data/pipeline/stock_metrics.json`.

### Bước 2 — Xếp hạng và khuyến nghị

Dựa trên metrics, xếp hạng 10 mã theo tiêu chí:
- Return cao
- Volatility thấp (risk-adjusted)
- Trend đang tăng

Phân loại thành 3 nhóm:
- ✅ **Nên xem xét** (top 3)
- ⚠️ **Theo dõi thêm** (mid)
- ❌ **Tránh / chờ** (bottom)

### Bước 3 — Tạo HTML report 1 trang

Dùng **html-report skill** và **story-builder agent** để tạo report tại:
`data/reports/stock_report_{YYYY-MM-DD}.html`

**Report cần có:**
- Tiêu đề: "VN Stock Daily Briefing — {ngày hôm nay}"
- Bảng tóm tắt 10 mã: Return 30D | Volatility | Trend | Khuyến nghị
- 1 chart: performance comparison (Close normalized về 100 tại ngày đầu)
- Section "Top picks hôm nay" — 3 mã với lý do ngắn gọn (2-3 câu mỗi mã)
- Giữ ngắn gọn: **1 trang, không scroll dài**

---

## Agents liên quan

Hệ thống agent nằm tại: `./ai_analyst`

Sử dụng các agent sau từ folder đó:
- **descriptive-analyst** — tính metrics, trend
- **story-builder** — viết narrative khuyến nghị
- **visualizer** — tạo chart performance
- **html-report skill** — render HTML output

Đọc `./ai_analyst/CLAUDE.md` để hiểu conventions trước khi dùng.

---

## Output

```
github_actions/
└── data/
    ├── stock_data.csv          ← input (do GitHub Actions fetch)
    ├── pipeline/
    │   └── stock_metrics.json  ← intermediate
    └── reports/
        └── stock_report_YYYY-MM-DD.html  ← output cuối
```

---

## Lưu ý

- Không cần phân tích predictive (forecast). Chỉ cần descriptive + recommendation.
- Report phải đọc được trong 2 phút — ưu tiên bảng và bullet points, không viết dài.
- Nếu một mã thiếu data (thị trường nghỉ, lỗi fetch), bỏ qua và note trong report.
- Sau khi tạo report xong, ghi ngày mới nhất của data vào `logs/last_analyzed.txt`.

## Token efficiency — BẮT BUỘC tuân theo

- **Không chạy full pipeline ai_analyst** — chỉ dùng đúng 3 agent: `descriptive-analyst`, `story-builder`, `html-report`. Bỏ qua tất cả agent khác.
- **Không đọc reference docs** của skill trừ khi thực sự cần — ưu tiên dùng kiến thức sẵn có.
- **Không giải thích từng bước** trong quá trình chạy — chỉ báo khi xong hoặc khi có lỗi.
