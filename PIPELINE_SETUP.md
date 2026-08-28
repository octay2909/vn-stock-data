# VN Stock Pipeline — Hướng dẫn Setup

## Tổng quan pipeline

```
18:00  GitHub Actions (daily_fetch.yml)
       → fetch_stock.py kéo data → commit stock_data.csv
       → Check: data có fresh không?

19:00  Claude Routine
       → Check: data có mới không? (so với last_analyzed.txt)
       → Chạy phân tích + tạo report HTML
       → Push report lên repo

20:00  GitHub Actions (daily_email.yml)
       → Check: có report HTML hôm nay không?
       → Nếu có → gửi email tóm tắt
       → Nếu không → bỏ qua (agent chưa chạy xong hoặc lỗi)
```

> Mỗi bước tự validate đầu vào trước khi chạy. Bước sau không chạy nếu bước trước chưa có output.

---

## Cấu trúc repo

```
vn-stock-data/                    ← GitHub repo root
├── .github/
│   └── workflows/
│       ├── daily_fetch.yml       ← 18:00: kéo data
│       └── daily_email.yml       ← 20:00: gửi email
├── ai_analyst/                   ← agent phân tích
├── data/
│   └── stock_data.csv            ← tự động tạo sau lần chạy đầu
├── logs/
│   ├── fetch.log                 ← log mỗi lần fetch
│   └── last_analyzed.txt         ← ngày agent chạy lần cuối
├── reports/
│   └── stock_report_YYYY-MM-DD.html  ← report hàng ngày
├── CLAUDE.md                     ← instructions cho Claude Routine
├── config.yaml                   ← cấu hình tickers, nguồn data
├── fetch_stock.py                ← script kéo data
├── send_summary.py               ← script gửi email
└── requirements.txt
```

> Muốn thêm/bớt mã hoặc đổi cấu hình → **chỉ sửa `config.yaml`**.

---

## Bước 1 — Tạo repo trên GitHub

1. Vào https://github.com → click **"New"**
2. Điền **Repository name**: `vn-stock-data`, **Visibility**: `Public`
3. Click **"Create repository"**

---

## Bước 2 — Upload files lên repo

**Dùng Git (nhanh nhất):**

```bash
cd "path/to/github_actions"
git init
git remote add origin https://github.com/your-username/vn-stock-data.git
git add .
git commit -m "initial setup"
git push -u origin main
```

**Upload thủ công:** Tạo `.github/workflows/daily_fetch.yml` bằng cách vào **"Add file"** → **"Create new file"**, gõ tên file có dấu `/` để tạo thư mục. Các file còn lại upload qua **"Upload files"**.

---

## Bước 3 — Cấp quyền write cho GitHub Actions

Vào repo → **Settings** → **Actions** → **General** → **Workflow permissions** → chọn **"Read and write permissions"** → **Save**.

---

## Bước 4 — Test fetch data lần đầu

1. Vào tab **Actions** → click **"VN Stock Daily Fetch"** → **"Run workflow"**
2. Chờ ~2 phút → kiểm tra tab **Code** có `data/stock_data.csv` chưa

Lần đầu fetch **90 ngày gần nhất** (~900 dòng).

---

## Bước 5 — Cấp quyền push cho Claude Routine (PAT)

Claude Routine cần PAT để tự push report lên repo.

Và cần được allow ở url này: https://github.com/apps/claude/installations/select_target

### 5a — Tạo PAT

1. Vào https://github.com/settings/tokens?type=beta → **"Generate new token"**
2. Điền:
   - **Token name**: `vn-stock-routine`
   - **Expiration**: 90 ngày
   - **Repository access**: Only select repositories → `vn-stock-data`
   - **Permissions** → **Contents**: `Read and write`
3. **Generate token** → copy ngay (chỉ hiện 1 lần)

### 5b — Nhúng PAT vào Routine Instructions

Thêm vào đầu Instructions của Claude Routine:

```
Trước khi push, chạy lệnh:
git remote set-url origin https://<YOUR_PAT>@github.com/your-username/vn-stock-data.git
```

> ⚠️ Không share routine này với ai. Khi PAT hết hạn → tạo token mới → update Instructions.

---

## Bước 6 — Setup Claude Routine (phân tích)

Tạo Claude Routine với:

| Setting | Giá trị |
|---|---|
| **Trigger** | Weekdays, 19:00 |
| **Connector** | repo `vn-stock-data` |
| **Model** | Haiku (tiết kiệm token) |

**Instructions — copy nguyên đoạn sau vào ô Instructions:**

```
Trước khi push, chạy lệnh sau để dùng PAT:
git remote set-url origin https://<YOUR_PAT>@github.com/your-username/vn-stock-data.git

---

Đọc CLAUDE.md trong repo để hiểu pipeline, sau đó thực hiện theo thứ tự:

Bước 0 — Kiểm tra trước khi chạy:
- Nếu data/stock_data.csv không tồn tại → dừng, báo lỗi
- Nếu ngày mới nhất trong CSV cách hôm nay quá 3 ngày → dừng, báo "data cũ, fetch có thể bị lỗi"
- Nếu logs/last_analyzed.txt tồn tại và ngày trong đó == ngày mới nhất trong CSV → dừng, báo "đã phân tích rồi"

Bước 1 — Tính metrics cho từng ticker (chỉ đọc 30 ngày gần nhất từ CSV):
- Return 30D, Volatility, Trend, Volume trend

Bước 2 — Xếp hạng và phân loại:
- Top 3: nên xem xét
- Mid: theo dõi thêm
- Bottom: tránh / chờ

Bước 3 — Tạo HTML report 1 trang tại reports/stock_report_{YYYY-MM-DD}.html

Bước 4 — Push report lên repo

Bước 5 — Ghi ngày mới nhất của data vào logs/last_analyzed.txt

Lưu ý token efficiency:
- Không đọc toàn bộ CSV, chỉ lấy 30 ngày gần nhất
- Không chạy full pipeline ai_analyst, chỉ dùng: descriptive-analyst, story-builder, html-report
- Không giải thích từng bước, chỉ báo khi xong hoặc lỗi
```

> Thay `<YOUR_PAT>` và `your-username` bằng thông tin thực của bạn.

**Validation trong Routine (tự động):**
- Kiểm tra `stock_data.csv` tồn tại
- Kiểm tra data không quá 3 ngày cũ
- Kiểm tra chưa phân tích data này rồi (so với `last_analyzed.txt`)

---

## Bước 7 — Setup gửi email (tùy chọn)

Email gửi lúc 20:00 sau khi Routine phân tích xong. Script tự check có report hôm nay chưa trước khi gửi — nếu Routine chưa chạy xong thì bỏ qua.

### 7a — Tạo Gmail App Password

Vào https://myaccount.google.com/apppasswords → tạo password tên `vn-stock-github` → copy 16 ký tự.

> Nếu không thấy mục này: account dùng Passkey hoặc Google Workspace — Google chặn tính năng này, không có workaround.

### 7b — Thêm GitHub Secrets

Vào repo → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**:

| Secret name | Value |
|---|---|
| `GMAIL_USER` | your-email@gmail.com |
| `GMAIL_APP_PASSWORD` | 16 ký tự vừa tạo |
| `EMAIL_TO` | email nhận (có thể giống GMAIL_USER) |

Workflow `daily_email.yml` đã cấu hình sẵn, không cần thêm gì.

---

## Tùy chỉnh

| Muốn thay đổi | Sửa ở đâu |
|---|---|
| Thêm/bớt mã cổ phiếu | `config.yaml` → `tickers` |
| Số ngày fetch lần đầu | `config.yaml` → `fetch.lookback_days` |
| Nguồn data | `config.yaml` → `fetch.source` |
| Số mã top picks trong email | `config.yaml` → `report.top_picks` |
| Giờ fetch | `daily_fetch.yml` → `cron` |
| Giờ gửi email | `daily_email.yml` → `cron` |

---

## Troubleshooting

### Lỗi 403 khi Routine push
Toggle "Allow unrestricted git push" không hoạt động ổn định — dùng PAT theo Bước 5.

### PAT hết hạn
Vào https://github.com/settings/tokens?type=beta → tạo token mới → update Instructions của Routine.

### Routine báo "Data cũ" hoặc "Đã phân tích rồi"
Bình thường — cuối tuần, ngày lễ, hoặc đã chạy trong ngày.

### Email không gửi dù Routine đã chạy
Kiểm tra: report có trong thư mục `reports/` trên GitHub không? Nếu không → Routine bị lỗi lúc push. Xem log trong tab Actions.

### Actions không chạy tự động
Repo private free có 2000 phút/tháng. Pipeline này dùng ~4 phút/ngày → ~80 phút/tháng, trong giới hạn.
