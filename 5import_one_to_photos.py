#!/usr/bin/env python3
import shutil
import subprocess
import sys
from pathlib import Path

from config import IMPORTED_DIR, MODIFIED_DIR


OUTPUT_DIR = MODIFIED_DIR
IMPORTED_DIR = IMPORTED_DIR


def import_file(path: Path) -> subprocess.CompletedProcess:
    script = [
        "osascript",
        "-e",
        f'tell application "Photos" to import POSIX file "{path}" skip check duplicates yes',
    ]
    return subprocess.run(script, capture_output=True, text=True)


def main() -> int:
    IMPORTED_DIR.mkdir(parents=True, exist_ok=True)

    candidates = sorted(p for p in OUTPUT_DIR.glob("*.mov") if p.is_file())
    if not candidates:
        print("No .mov files left in modified/")
        return 0

    path = candidates[0]
    print(f"Importing: {path.name}")
    result = import_file(path)

    if result.returncode != 0:
        sys.stderr.write(result.stderr)
        raise RuntimeError(f"Photos import failed for {path.name}")

    if result.stdout.strip():
        print(result.stdout.strip())

    target = IMPORTED_DIR / path.name
    shutil.move(str(path), str(target))
    print(f"Moved to imported/: {target.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
