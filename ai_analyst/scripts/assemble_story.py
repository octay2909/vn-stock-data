#!/usr/bin/env python3
"""
CLI wrapper for the Hybrid Story Assembly engine.
Merges structured LLM slide copy drafts and raw data arrays dynamically.
"""
import sys
import io
import argparse
from pathlib import Path

# Fix encoding issues on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Include project base in Python path for absolute imports
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR.parent))

from helpers.story_assembler import StoryAssembler
from helpers.utils.logger import get_logger, new_run_id

def main():
    parser = argparse.ArgumentParser(description="Programmatically assemble final story_arc.json and report_context.json.")
    parser.add_argument("--stem", required=True, help="Dataset stem name (e.g. retail_daily_sales_2023_2026)")
    parser.add_argument("--run-id", default=None, help="Pipeline execution trace ID")
    args = parser.parse_args()

    run_id = args.run_id or new_run_id()
    log = get_logger(__name__, run_id=run_id, stem=args.stem)

    log.info("story_assembly_started", stem=args.stem)
    print("=" * 60)
    print(f"       AIDA HYBRID STORY ASSEMBLY ENGINE (Phase 4a)       ")
    print("=" * 60)
    
    assembler = StoryAssembler(args.stem, BASE_DIR)
    
    if not assembler.load_inputs():
        log.error("story_assembly_load_failed", reason="Could not load upstream descriptive or diagnostic output files.")
        print("[error] Could not load upstream descriptive or diagnostic output files.")
        sys.exit(1)

    if not assembler.assemble():
        log.error("story_assembly_execution_failed", reason="Failed to construct slide storyboard data injection.")
        print("[error] Failed to construct slide storyboard data injection.")
        sys.exit(1)

    log.info("story_assembly_completed_successfully")
    print("=" * 60)
    print("[success] Hybrid Story Assembly completed successfully.")
    print("=" * 60)

if __name__ == "__main__":
    main()
