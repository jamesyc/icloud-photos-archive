#!/usr/bin/env python3
import argparse
import json
import shlex
import subprocess
import sys
from pathlib import Path

from config import FFMPEG, FFPROBE


FORMAT_TAG_KEYS = [
    "creation_time",
    "com.apple.quicktime.creationdate",
    "com.apple.quicktime.location.ISO6709",
    "com.apple.quicktime.location.accuracy.horizontal",
    "com.apple.quicktime.make",
    "com.apple.quicktime.model",
    "com.apple.quicktime.software",
]


def run_json(cmd: list[str]) -> dict:
    out = subprocess.check_output(cmd, text=True)
    return json.loads(out)


def ffprobe_metadata(path: Path) -> dict:
    return run_json(
        [
            FFPROBE,
            "-v",
            "error",
            "-show_entries",
            (
                "format=filename,size,duration:format_tags:"
                "stream=index,codec_type,width,height:stream_tags=handler_name,creation_time:"
                "stream_side_data=rotation"
            ),
            "-of",
            "json",
            str(path),
        ]
    )


def display_dimensions(video_stream: dict) -> tuple[int, int]:
    width = int(video_stream["width"])
    height = int(video_stream["height"])
    rotation = 0
    for item in video_stream.get("side_data_list", []):
        if "rotation" in item:
            rotation = int(item["rotation"])
            break
    if rotation % 180 != 0:
        width, height = height, width
    return width, height


def target_scale(video_stream: dict, long_edge: int) -> str:
    disp_w, disp_h = display_dimensions(video_stream)
    if disp_h >= disp_w:
        target_w = min(long_edge, disp_w)
        return f"{target_w}:-2"
    target_h = min(long_edge, disp_h)
    return f"-2:{target_h}"


def build_command(
    input_path: Path,
    output_path: Path,
    fps: int,
    long_edge: int,
    crf: int,
    preset: str,
) -> list[str]:
    meta = ffprobe_metadata(input_path)
    format_tags = meta.get("format", {}).get("tags", {})
    streams = meta.get("streams", [])
    has_data_streams = any(s.get("codec_type") == "data" for s in streams)

    video_stream = next(s for s in streams if s.get("codec_type") == "video")
    scale = target_scale(video_stream, long_edge)

    cmd = [
        FFMPEG,
        "-y",
        "-i",
        str(input_path),
        "-map",
        "0",
        "-map_metadata",
        "0",
        "-map_metadata:s:v",
        "0:s:v",
        "-map_metadata:s:a",
        "0:s:a",
        "-map_chapters",
        "0",
        "-vf",
        f"fps={fps},scale={scale}",
        "-c:v",
        "libx265",
        "-tag:v",
        "hvc1",
        "-preset",
        preset,
        "-crf",
        str(crf),
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "copy",
        "-movflags",
        "use_metadata_tags+faststart",
    ]

    if has_data_streams:
        cmd.extend(["-map_metadata:s:d", "0:s:d"])
        cmd.extend(["-c:d", "copy"])

    for key in FORMAT_TAG_KEYS:
        value = format_tags.get(key)
        if value:
            cmd.extend(["-metadata", f"{key}={value}"])

    for stream in streams:
        idx = stream["index"]
        codec_type = stream.get("codec_type")
        tags = stream.get("tags", {})
        if codec_type == "video":
            stream_spec = f"s:v:{sum(1 for s in streams[:idx+1] if s.get('codec_type') == 'video') - 1}"
        elif codec_type == "audio":
            stream_spec = f"s:a:{sum(1 for s in streams[:idx+1] if s.get('codec_type') == 'audio') - 1}"
        elif codec_type == "data":
            stream_spec = f"s:d:{sum(1 for s in streams[:idx+1] if s.get('codec_type') == 'data') - 1}"
        else:
            continue

        for key in ("creation_time", "handler_name"):
            value = tags.get(key)
            if value:
                cmd.extend([f"-metadata:{stream_spec}", f"{key}={value}"])

    cmd.append(str(output_path))
    return cmd


def main() -> int:
    parser = argparse.ArgumentParser(description="Transcode a Photos-exported video to HEVC MOV.")
    parser.add_argument("input", type=Path, help="Input video path")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Output path. Defaults to sibling .hevc.mov file.",
    )
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--long-edge", type=int, default=1080)
    parser.add_argument("--crf", type=int, default=20)
    parser.add_argument("--preset", default="medium")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--print-only", action="store_true")
    args = parser.parse_args()

    input_path = args.input.resolve()
    if not input_path.exists():
        print(f"Input file does not exist: {input_path}", file=sys.stderr)
        return 1

    output_arg = Path(str(args.output).strip()) if args.output else input_path.with_suffix(".hevc.mov")
    output_path = output_arg.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists() and not args.overwrite:
        print(f"Output already exists, skipping: {output_path}")
        return 0

    cmd = build_command(
        input_path=input_path,
        output_path=output_path,
        fps=args.fps,
        long_edge=args.long_edge,
        crf=args.crf,
        preset=args.preset,
    )

    if args.print_only:
        print(shlex.join(cmd))
        return 0

    print("Running:")
    print(shlex.join(cmd))
    completed = subprocess.run(cmd)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
