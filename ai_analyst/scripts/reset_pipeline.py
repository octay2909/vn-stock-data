#!/usr/bin/env python3
"""
Workspace Reset Utility for AIDA ai_analyst.
Safely purges historical pipeline run outputs while preserving configurations and agent memories.
"""
import os
import sys
import shutil
import datetime
import argparse
import zipfile
from pathlib import Path

# Base directory is the project root (ai_analyst/)
BASE_DIR = Path(__file__).resolve().parent.parent

def setup_arg_parser():
    parser = argparse.ArgumentParser(description="Reset ai_analyst workspace to a clean/lightweight state.")
    parser.add_argument(
        "--backup",
        action="store_true",
        default=True,
        help="Compress and archive historical runs to data/archive/ before deleting (default: True)"
    )
    parser.add_argument(
        "--no-backup",
        action="store_false",
        dest="backup",
        help="Delete historical runs immediately WITHOUT backup (warning: destructive)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what files and folders would be deleted without actually deleting them"
    )
    return parser

def main():
    parser = setup_arg_parser()
    args = parser.parse_args()

    pipeline_dir = BASE_DIR / "data" / "pipeline"
    reports_dir = BASE_DIR / "data" / "reports"
    archive_dir = BASE_DIR / "data" / "archive"

    print("=" * 60)
    print("           AIDA WORKSPACE RESET UTILITY           ")
    print("=" * 60)
    print(f"Base Directory: {BASE_DIR}")
    print(f"Dry Run Mode:   {args.dry_run}")
    print(f"Backup Enabled: {args.backup}")
    print("-" * 60)

    # 1. Identify directories to delete
    targets = []
    
    # Under data/pipeline/
    if pipeline_dir.exists():
        for p in pipeline_dir.iterdir():
            if p.is_dir():
                targets.append(p)
                
    # Under data/reports/
    if reports_dir.exists():
        for r in reports_dir.iterdir():
            if r.is_dir():
                # reports structure has subdirectories like 'descriptive', etc.
                # let's clean any subdirectory inside data/reports
                targets.append(r)

    if not targets:
        print("[info] Workspace is already completely clean. No historical runs found.")
        sys.exit(0)

    print(f"Found {len(targets)} historical run directories to clean:")
    for t in targets:
        rel_path = t.relative_to(BASE_DIR)
        print(f" - {rel_path}")

    # 2. Backup Phase
    if args.backup and not args.dry_run:
        archive_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_path = archive_dir / f"workspace_archive_{timestamp}.zip"
        
        print(f"\n[backup] Archiving targets to: {zip_path.relative_to(BASE_DIR)} ...")
        try:
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for t in targets:
                    for root, _, files in os.walk(t):
                        for file in files:
                            file_path = Path(root) / file
                            # Store in zip using relative path from BASE_DIR to keep structure
                            arcname = file_path.relative_to(BASE_DIR)
                            zipf.write(file_path, arcname)
            print("[backup] Archive created successfully.")
        except Exception as e:
            print(f"[error] Failed to create backup archive: {e}", file=sys.stderr)
            print("[error] Aborting reset to prevent accidental data loss.", file=sys.stderr)
            sys.exit(1)

    # 3. Clean Phase
    print(f"\n[clean] Purging {len(targets)} folders ...")
    success_count = 0
    fail_count = 0
    
    for t in targets:
        rel_path = t.relative_to(BASE_DIR)
        if args.dry_run:
            print(f" - [dry-run] Would delete: {rel_path}")
            success_count += 1
        else:
            try:
                shutil.rmtree(t)
                print(f" - Deleted: {rel_path}")
                success_count += 1
            except Exception as e:
                print(f" - [error] Failed to delete {rel_path}: {e}", file=sys.stderr)
                fail_count += 1

    print("-" * 60)
    print(f"Reset finished. Success: {success_count}, Failed: {fail_count}")
    print("[protected] Long-term agent memory (.claude/agent-memory/) remains safe.")
    print("[protected] Configurations (config/) and schemas remain safe.")
    print("=" * 60)

if __name__ == "__main__":
    main()
