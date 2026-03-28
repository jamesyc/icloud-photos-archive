#!/usr/bin/env python3

import argparse
import csv
import subprocess
import sys
from pathlib import Path

from config import BASE_DIR, BIG_VIDEOS_CSV


STATE_PATH = BASE_DIR / "delete-progress.txt"


def load_rows(csv_path: Path):
    if not csv_path.exists():
        raise SystemExit(f"missing CSV: {csv_path}")
    return list(csv.DictReader(csv_path.open()))


def load_index() -> int:
    if not STATE_PATH.exists():
        return 0
    try:
        return int(STATE_PATH.read_text().strip())
    except Exception:
        return 0


def save_index(idx: int) -> None:
    STATE_PATH.write_text(str(idx))


def run_osascript(lines: list[str]) -> subprocess.CompletedProcess:
    cmd = ["osascript"]
    for line in lines:
        cmd.extend(["-e", line])
    return subprocess.run(cmd, capture_output=True, text=True, check=True)


def focus_in_photos(search_text: str) -> str:
    script = [
        'set the clipboard to ""',
        'tell application "Photos" to activate',
        'delay 0.5',
        'tell application "System Events"',
        'keystroke "f" using command down',
        'delay 0.3',
        'keystroke "a" using command down',
        'delay 0.1',
        'key code 51',
        'delay 0.2',
        f'set the clipboard to "{search_text}"',
        'keystroke "v" using command down',
        'delay 1.0',
        'key code 125',
        'delay 0.2',
        'key code 36',
        'end tell',
        'return "ok"',
    ]
    return run_osascript(script).stdout.strip()


def main() -> int:
    parser = argparse.ArgumentParser(description="Open the next original in Photos and wait for manual delete.")
    parser.add_argument("--csv", type=Path, default=BIG_VIDEOS_CSV, help="CSV of originals to delete")
    parser.add_argument("--reset", action="store_true", help="Reset delete progress to the first row")
    parser.add_argument("--advance", action="store_true", help="Advance to the next row after you manually delete")
    args = parser.parse_args()

    rows = load_rows(args.csv.resolve())
    idx = load_index()

    if args.reset:
        save_index(0)
        idx = 0

    if idx >= len(rows):
        print("done")
        return 0

    row = rows[idx]
    try:
        resolved = focus_in_photos(row["original_filename"])
    except subprocess.CalledProcessError as exc:
        if exc.stderr:
            print(exc.stderr.strip(), file=sys.stderr)
        raise

    print(f"index,{idx + 1}/{len(rows)}")
    print(f"uuid,{row.get('uuid', '')}")
    print(f"resolved_id,{resolved}")
    print(f"original_filename,{row['original_filename']}")
    print(f"library_filename,{row.get('library_filename', '')}")
    print(f"original_file_size,{row.get('original_file_size', '')}")
    print(f"duration_seconds,{row.get('duration_seconds', '')}")
    print(f"created_local,{row.get('created_local', '')}")
    print("action,manually delete this item in Photos, then rerun with --advance")

    if args.advance:
        save_index(idx + 1)
        print(f"advanced_to,{idx + 2}")
    else:
        print(f"next_index_if_advanced,{idx + 2}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
