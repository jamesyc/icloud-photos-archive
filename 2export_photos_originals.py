#!/usr/bin/env python3
import argparse
import csv
import datetime as dt
import subprocess
import sys
import time

from pathlib import Path

from config import BIG_VIDEOS_CSV, ORIGINALS_DIR

def try_osascript(lines: list[str]) -> subprocess.CompletedProcess:
    script = []
    for line in lines:
        script.extend(["-e", line])
    return subprocess.run(["osascript", *script], capture_output=True, text=True)


def applescript_date_literal(created_local: str) -> str:
    stamp = dt.datetime.strptime(created_local, "%Y-%m-%d %H:%M:%S")
    month = stamp.strftime("%B")
    weekday = stamp.strftime("%A")
    hour_12 = stamp.strftime("%I").lstrip("0") or "12"
    am_pm = stamp.strftime("%p")
    return f'date "{weekday}, {month} {stamp.day}, {stamp.year} at {hour_12}:{stamp:%M:%S} {am_pm}"'


def filename_variants(original_filename: str, library_filename: str) -> list[str]:
    names = []
    for candidate in [original_filename, library_filename]:
        if candidate and candidate not in names:
            names.append(candidate)
        if candidate:
            lower = candidate.lower()
            upper = candidate.upper()
            stem = Path(candidate).stem
            for variant in [lower, upper, stem]:
                if variant and variant not in names:
                    names.append(variant)
    return names


def export_one(
    uuid: str,
    original_filename: str,
    library_filename: str,
    created_local: str,
    out_dir: Path,
) -> tuple[bool, str]:
    created_date = applescript_date_literal(created_local)
    resolvers = [
        f'(first media item whose id is "{uuid}/L0/001")',
        f'(first media item whose id starts with "{uuid}")',
    ]

    for name in filename_variants(original_filename, library_filename):
        resolvers.append(f'(first media item whose filename is "{name}")')
        resolvers.append(f'(first media item whose filename is "{name}" and date is {created_date})')

    for resolver in resolvers:
        lines = [
            f'set outDir to POSIX file "{out_dir}/"',
            'tell application "Photos"',
            f"set targetItem to {resolver}",
            "export {targetItem} to outDir with using originals",
            "end tell",
        ]
        result = try_osascript(lines)
        if result.returncode == 0:
            return True, resolver

    return False, ""


def main() -> int:
    parser = argparse.ArgumentParser(description="Export original videos from Photos using a CSV inventory.")
    parser.add_argument(
        "--csv",
        type=Path,
        default=BIG_VIDEOS_CSV,
        help="CSV generated from the Photos DB",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=ORIGINALS_DIR,
        help="Directory to export originals into",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Export at most this many rows; 0 means all rows",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=0.0,
        help="Seconds to sleep between exports",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Re-export even if the expected original filename already exists",
    )
    args = parser.parse_args()

    csv_path = args.csv.resolve()
    out_dir = args.out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    if not csv_path.exists():
        print(f"CSV not found: {csv_path}", file=sys.stderr)
        return 1

    exported = 0
    skipped = 0

    with csv_path.open(newline="") as f:
        rows = list(csv.DictReader(f))

    if args.limit > 0:
        rows = rows[: args.limit]

    for row in rows:
        uuid = row["uuid"]
        original_filename = row["original_filename"] or row["library_filename"]
        target = out_dir / original_filename

        if target.exists() and not args.overwrite:
            print(f"skip exists: {target.name}")
            skipped += 1
            continue

        print(f"export {uuid} -> {target.name}")
        ok, resolver = export_one(
            uuid,
            original_filename,
            row["library_filename"],
            row["created_local"],
            out_dir,
        )
        if not ok:
            print(f"skip unresolved: {uuid} ({original_filename})", file=sys.stderr)
            skipped += 1
            continue

        print(f"  resolved via {resolver}")

        exported += 1
        if args.sleep > 0:
            time.sleep(args.sleep)

    print(f"done: exported={exported} skipped={skipped} out_dir={out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
