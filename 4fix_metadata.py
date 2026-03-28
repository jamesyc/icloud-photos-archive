#!/opt/homebrew/bin/python3

import argparse
import shutil
import subprocess
import sys

from pathlib import Path

from config import EXIFTOOL, MODIFIED_DIR, ORIGINALS_DIR, PERL, TRANSCODED_DIR


def find_original(base_stem: str) -> Path | None:
    candidates = sorted(ORIGINALS_DIR.glob(f"{base_stem}.*"))
    return candidates[0] if candidates else None


def build_exiftool_cmd(original: Path, target: Path) -> list[str]:
    return [
        PERL,
        str(EXIFTOOL),
        "-overwrite_original",
        "-api",
        "QuickTimeUTC=1",
        "-TagsFromFile",
        str(original),
        "-QuickTime:CreateDate<QuickTime:CreateDate",
        "-QuickTime:ModifyDate<QuickTime:ModifyDate",
        "-Keys:CreationDate<Keys:CreationDate",
        "-Keys:GPSCoordinates<Keys:GPSCoordinates",
        "-Keys:LocationAccuracyHorizontal<Keys:LocationAccuracyHorizontal",
        "-Keys:Make<Keys:Make",
        "-Keys:Model<Keys:Model",
        "-Keys:Software<Keys:Software",
        "-ItemList:GPSCoordinates<Keys:GPSCoordinates",
        "-UserData:GPSCoordinates<Keys:GPSCoordinates",
        "-UserData:Make<Keys:Make",
        "-UserData:Model<Keys:Model",
        str(target),
    ]


def process_one(transcoded: Path, overwrite: bool) -> int:
    if not transcoded.name.endswith(".hevc.mov"):
        print(f"skip non-hevc file: {transcoded.name}")
        return 0

    base_stem = transcoded.name[: -len(".hevc.mov")]
    original = find_original(base_stem)
    if not original:
        print(f"missing original for {transcoded.name}", file=sys.stderr)
        return 1

    MODIFIED_DIR.mkdir(parents=True, exist_ok=True)
    output = MODIFIED_DIR / f"{base_stem}.mov"
    if output.exists() and not overwrite:
        print(f"skip existing: {output.name}")
        return 0

    shutil.copy2(transcoded, output)
    cmd = build_exiftool_cmd(original, output)
    completed = subprocess.run(cmd, capture_output=True, text=True)
    if completed.stdout.strip():
        print(completed.stdout.strip())
    if completed.stderr.strip():
        print(completed.stderr.strip(), file=sys.stderr)
    if completed.returncode != 0:
        print(f"failed: {transcoded.name}", file=sys.stderr)
        return completed.returncode

    print(f"fixed: {transcoded.name} <- {original.name}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Fix QuickTime metadata on transcoded HEVC MOV files.")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()

    if not EXIFTOOL.exists():
        print(
            f"missing exiftool: {EXIFTOOL}. "
            "Set PHOTOS_COMPRESS_EXIFTOOL or install exiftool in /opt/homebrew/bin.",
            file=sys.stderr,
        )
        return 1

    files = sorted(TRANSCODED_DIR.glob("*.hevc.mov"))
    if args.limit is not None:
        files = files[: args.limit]

    rc = 0
    for transcoded in files:
        result = process_one(transcoded, overwrite=args.overwrite)
        if result != 0:
            rc = result
            break

    return rc


if __name__ == "__main__":
    raise SystemExit(main())
