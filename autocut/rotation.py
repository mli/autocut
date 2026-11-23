"""Read and apply video display rotation (iPhone portrait clips)."""

import json
import logging
import math
import subprocess


def _stream_rotation(stream):
    rotations = [side.get("rotation") for side in stream.get("side_data_list") or []]
    tags = stream.get("tags") or {}
    rotations.extend((tags.get("rotate"), tags.get("rotation")))
    for value in rotations:
        try:
            angle = float(value)
        except (TypeError, ValueError, OverflowError):
            continue
        if math.isfinite(angle):
            return round(angle)
    return 0


def display_rotation(filename):
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_streams",
        filename,
    ]
    try:
        out = subprocess.run(cmd, check=True, capture_output=True).stdout
        probe = json.loads(out.decode("utf-8", "replace"))
    except (OSError, subprocess.CalledProcessError, json.JSONDecodeError) as e:
        logging.warning(f"cannot probe {filename}: {e}")
        return 0
    for stream in probe.get("streams", []):
        if stream.get("codec_type") == "video":
            return _stream_rotation(stream)
    return 0


def needs_rotation(filename):
    return display_rotation(filename) % 180 != 0


def normalize(filename, output_path):
    cmd = [
        "ffmpeg",
        "-n",
        "-loglevel",
        "error",
        "-i",
        filename,
        "-c:v",
        "libx264",
        "-crf",
        "18",
        "-preset",
        "veryfast",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        output_path,
    ]
    subprocess.run(cmd, check=True)
