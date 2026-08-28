"""
run_pipeline.py — Bộ điều phối Pipeline phân tích dữ liệu hợp nhất (Unified Pipeline Orchestrator)

Bộ điều phối này cho phép khởi chạy toàn bộ quy trình tính toán dữ liệu thô (End-to-End Analytics) 
chỉ với một lệnh duy nhất:
  - Phase 2: Descriptive Compute (Tính toán mô tả, Simpson's Paradox, KPIs)
  - Phase 3: Predictive Forecasting (Dự báo doanh thu tự động, huấn luyện & chọn mô hình tối ưu)
  - Phase 4: HTML Report Compilation (Tổng hợp biểu đồ D3.js tương tác và kết xuất báo cáo động)

Tính năng nổi bật:
  1. Hỗ trợ đa nền tảng (Windows, macOS, Linux) chạy đồng nhất không phụ thuộc Shell Script.
  2. Tự động cấu hình sys.path toàn cục để loại bỏ hoàn toàn lỗi ModuleNotFoundError (PYTHONPATH).
  3. Đo lường thời gian chạy chi tiết của từng Phase để báo cáo hiệu suất C-suite.
"""

import os
import sys
import time
import argparse
from pathlib import Path
import subprocess

# ---------------------------------------------------------------------------
# Cấu hình PYTHONPATH động toàn cục (Giải quyết triệt để Xung đột 1)
# ---------------------------------------------------------------------------
BASE = Path(__file__).parent.parent
sys.path.insert(0, str(BASE.parent))
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(BASE / "ai_analyst"))

def print_banner():
    print("=" * 70)
    print("     [LAUNCHER] AI ANALYST UNIFIED PIPELINE RUNNER - VERSION 2.0   ")
    print("=" * 70)

def print_footer(success: bool, elapsed: float):
    print("=" * 70)
    if success:
        print(f"     [SUCCESS] PIPELINE COMPLETED SUCCESSFULLY IN {elapsed:.2f} SECONDS!")
    else:
        print("     [FAILURE] PIPELINE FAILED! CHECK LOGS ABOVE FOR DETAILS.")
    print("=" * 70)

def run_stage(name: str, cmd: list[str]) -> bool:
    print(f"\n[STAGE] Starting: {name}...")
    print(f"[CMD]   {' '.join(cmd)}")
    start = time.time()
    
    # Kế thừa môi trường hiện tại và tiêm PYTHONPATH tuyệt đối cho Subprocess
    # Đảm bảo có cả thư mục mẹ của ai_analyst để import tuyệt đối 'ai_analyst' hoạt động
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join([
        str(BASE.parent),
        str(BASE),
        str(BASE / "ai_analyst"),
        env.get("PYTHONPATH", "")
    ])
    
    result = subprocess.run(
        cmd,
        capture_output=False,
        text=True,
        env=env
    )
    
    elapsed = time.time() - start
    if result.returncode == 0:
        print(f"[OK]    {name} completed in {elapsed:.2f} seconds.")
        return True
    else:
        print(f"[ERROR] {name} failed with exit code: {result.returncode}")
        return False

def main():
    print_banner()
    
    parser = argparse.ArgumentParser(description="AI Analyst Unified Pipeline Orchestrator")
    parser.add_argument("--stem", required=True, help="Tên tiền tố của dataset (ví dụ: retail_daily_sales_2023_2026)")
    parser.add_argument("--output", default=None, help="Đường dẫn đầu ra tùy chọn cho file HTML report")
    args = parser.parse_args()
    
    python_exe = sys.executable
    scripts_dir = BASE / "scripts"
    
    # ---------------------------------------------------------------------------
    # Định nghĩa các Lệnh chạy từng Phase
    # ---------------------------------------------------------------------------
    stages = [
        (
            "Phase 2: Descriptive Computation",
            [python_exe, str(scripts_dir / "descriptive_compute.py"), "--stem", args.stem]
        ),
        (
            "Phase 3: Predictive Time-Series Forecasting",
            [python_exe, str(scripts_dir / "forecast_revenue.py"), "--stem", args.stem]
        ),
        (
            "Phase 4: HTML Interactive Report Compilation",
            [python_exe, str(scripts_dir / "render_html.py"), "--stem", args.stem] + (["--output", args.output] if args.output else [])
        )
    ]
    
    total_start = time.time()
    pipeline_success = True
    
    for name, cmd in stages:
        success = run_stage(name, cmd)
        if not success:
            pipeline_success = False
            break
            
    total_elapsed = time.time() - total_start
    print_footer(pipeline_success, total_elapsed)
    
    if not pipeline_success:
        sys.exit(1)

if __name__ == "__main__":
    main()
