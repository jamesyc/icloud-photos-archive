#!/usr/bin/env python3

import argparse
import csv
import sqlite3
import sys
from pathlib import Path

from config import BIG_VIDEOS_CSV, PHOTOS_DB


QUERY = """
SELECT
  a.ZUUID AS uuid,
  a.ZFILENAME AS library_filename,
  aa.ZORIGINALFILENAME AS original_filename,
  aa.ZORIGINALFILESIZE AS original_file_size,
  printf('%.3f', a.ZDURATION) AS duration_seconds,
  a.ZWIDTH AS stored_width,
  a.ZHEIGHT AS stored_height,
  datetime(a.ZDATECREATED + 978307200, 'unixepoch', 'localtime') AS created_local
FROM ZASSET a
JOIN ZADDITIONALASSETATTRIBUTES aa ON aa.Z_PK = a.ZADDITIONALATTRIBUTES
WHERE a.ZKIND = 1
  AND COALESCE(a.ZTRASHEDSTATE, 0) = 0
  AND aa.ZORIGINALFILESIZE >= ?
ORDER BY aa.ZORIGINALFILESIZE DESC
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="List large Photos videos into a CSV.")
    parser.add_argument("--min-mb", type=int, default=300, help="Minimum original size in MiB")
    parser.add_argument("--db", type=Path, default=PHOTOS_DB, help="Path to Photos.sqlite")
    parser.add_argument("--out", type=Path, default=BIG_VIDEOS_CSV, help="Output CSV path")
    args = parser.parse_args()

    db_path = args.db.expanduser().resolve()
    out_path = args.out.expanduser().resolve()
    if not db_path.exists():
        print(f"Photos DB not found: {db_path}", file=sys.stderr)
        return 1

    min_bytes = args.min_mb * 1024 * 1024
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    rows = conn.execute(QUERY, (min_bytes,)).fetchall()
    conn.close()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys() if rows else [
            "uuid",
            "library_filename",
            "original_filename",
            "original_file_size",
            "duration_seconds",
            "stored_width",
            "stored_height",
            "created_local",
        ])
        writer.writeheader()
        for row in rows:
            writer.writerow(dict(row))

    total_bytes = sum(int(row["original_file_size"]) for row in rows)
    print(f"wrote {len(rows)} rows to {out_path}")
    print(f"total_bytes={total_bytes}")
    print(f"total_gib={total_bytes / (1024 ** 3):.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
