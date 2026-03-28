#!/usr/bin/env python3

import os
import shutil
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent

ORIGINALS_DIR = BASE_DIR / "originals"
TRANSCODED_DIR = BASE_DIR / "transcoded"
MODIFIED_DIR = BASE_DIR / "modified"
IMPORTED_DIR = BASE_DIR / "imported"
TOOLS_DIR = BASE_DIR / "tools"

BIG_VIDEOS_CSV = BASE_DIR / "big-videos.csv"


def _env_or_path(env_name: str, fallback: Path) -> Path:
    value = os.environ.get(env_name)
    return Path(value).expanduser() if value else fallback


def _find_executable(env_name: str, candidates: list[str]) -> str:
    if env_name in os.environ:
        return os.environ[env_name]
    for candidate in candidates:
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    raise FileNotFoundError(f"Could not find executable for {env_name}: {candidates}")


def _find_exiftool() -> Path:
    env_value = os.environ.get("PHOTOS_COMPRESS_EXIFTOOL")
    if env_value:
        return Path(env_value).expanduser()

    bundled = sorted(TOOLS_DIR.glob("Image-ExifTool-*/exiftool"))
    if bundled:
        return bundled[-1]

    for candidate in ["/opt/homebrew/bin/exiftool", "exiftool"]:
        resolved = shutil.which(candidate) if candidate == "exiftool" else candidate
        if resolved and Path(resolved).exists():
            return Path(resolved)

    return Path("/opt/homebrew/bin/exiftool")


PHOTOS_LIBRARY = _env_or_path(
    "PHOTOS_COMPRESS_LIBRARY",
    Path.home() / "Pictures" / "Photos Library.photoslibrary",
)
PHOTOS_DB = PHOTOS_LIBRARY / "database" / "Photos.sqlite"

FFMPEG = _find_executable("PHOTOS_COMPRESS_FFMPEG", ["/opt/homebrew/bin/ffmpeg", "ffmpeg"])
FFPROBE = _find_executable("PHOTOS_COMPRESS_FFPROBE", ["/opt/homebrew/bin/ffprobe", "ffprobe"])
PERL = _find_executable("PHOTOS_COMPRESS_PERL", ["/usr/bin/perl", "perl"])
EXIFTOOL = _find_exiftool()
