"""
fetch_stock.py — GitHub Actions version
----------------------------------------
Kéo data OHLCV của 10 mã chứng khoán VN, lưu vào CSV.

Logic:
- Lần đầu: fetch 30 ngày gần nhất
- Lần sau: chỉ fetch ngày còn thiếu, append vào file

Output: data/stock_data.csv
Cột: Date, Ticker, Open, High, Low, Close, Volume
"""

import csv
import logging
import sys
from datetime import date, timedelta
from pathlib import Path

import yaml

# ─── ĐỌC CONFIG ──────────────────────────────────────────────────────────────

_config = yaml.safe_load(Path("config.yaml").read_text(encoding="utf-8"))
TICKERS = _config["tickers"]
LOOKBACK_DAYS = _config["fetch"]["lookback_days"]
SOURCE = _config["fetch"]["source"]
OUTPUT_FILE = Path("data/stock_data.csv")
LOG_FILE = Path("logs/fetch.log")
HEADER = ["Date", "Ticker", "Open", "High", "Low", "Close", "Volume"]

# ─── LOGGING ─────────────────────────────────────────────────────────────────

LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),                              # GitHub Actions log
        logging.FileHandler(LOG_FILE, encoding="utf-8"),                # file log trong repo
    ],
)
log = logging.getLogger(__name__)

# ─── HELPERS ─────────────────────────────────────────────────────────────────

def get_latest_date_in_csv() -> str | None:
    if not OUTPUT_FILE.exists():
        return None
    latest = None
    with open(OUTPUT_FILE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            val = row.get("Date", "")[:10]
            if val and (latest is None or val > latest):
                latest = val
    return latest


# ─── MAIN ─────────────────────────────────────────────────────────────────────

def fetch_and_append():
    try:
        from vnstock import Vnstock
    except Exception as e:
        log.error(f"Lỗi import vnstock: {type(e).__name__}: {e}")
        sys.exit(1)

    today = date.today()
    yesterday = today - timedelta(days=1)

    # ── Xác định khoảng ngày cần fetch ───────────────────────────────────────
    latest_str = get_latest_date_in_csv()

    if latest_str is None:
        fetch_start = today - timedelta(days=LOOKBACK_DAYS)
        log.info(f"Chưa có data → fetch {LOOKBACK_DAYS} ngày: {fetch_start} → {yesterday}")
    else:
        fetch_start = date.fromisoformat(latest_str) + timedelta(days=1)
        if fetch_start > yesterday:
            log.info(f"Data đã up-to-date (latest: {latest_str}). Không có gì để fetch.")
            sys.exit(0)
        log.info(f"Fetch từ {fetch_start} → {yesterday}")

    start_str = fetch_start.strftime("%Y-%m-%d")
    end_str = yesterday.strftime("%Y-%m-%d")

    # ── Tạo thư mục data nếu chưa có ─────────────────────────────────────────
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    file_exists = OUTPUT_FILE.exists()

    # ── Fetch và append ───────────────────────────────────────────────────────
    success_count = 0
    total_rows = 0

    with open(OUTPUT_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(HEADER)

        for ticker in TICKERS:
            try:
                stock = Vnstock().stock(symbol=ticker, source=SOURCE)
                df = stock.quote.history(start=start_str, end=end_str, interval="1D")

                if df is None or df.empty:
                    log.warning(f"{ticker}: Không có data ({start_str} → {end_str})")
                    continue

                df["time"] = df["time"].astype(str).str[:10]
                df_filtered = df[
                    (df["time"] >= start_str) & (df["time"] <= end_str)
                ]

                if df_filtered.empty:
                    log.warning(f"{ticker}: Không có data trong khoảng này")
                    continue

                for _, row in df_filtered.iterrows():
                    writer.writerow([
                        row.get("time", ""),
                        ticker,
                        row.get("open", ""),
                        row.get("high", ""),
                        row.get("low", ""),
                        row.get("close", ""),
                        row.get("volume", ""),
                    ])
                    total_rows += 1

                log.info(f"{ticker}: ✓ {len(df_filtered)} dòng")
                success_count += 1

            except Exception as e:
                log.error(f"{ticker}: Lỗi — {e}")

    log.info(f"=== Xong: {success_count}/{len(TICKERS)} tickers | {total_rows} dòng mới ===")


if __name__ == "__main__":
    fetch_and_append()
