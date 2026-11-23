"""Read and apply video display rotation (iPhone portrait clips)."""

import json
import logging
import os
import shutil
import subprocess


def _binary(name):
    path = shutil.which(name)
    if path is None:
        raise RuntimeError(f"{name} not found on PATH")
    return path


def _stream_rotation(stream):
    for side in stream.get("side_data_list") or []:
        value = side.get("rotation")
        if value is not None:
            return int(round(float(value)))
    tags = stream.get("tags") or {}
    for key in ("rotate", "rotation"):
        if key in tags:
            return int(round(float(tags[key])))
    return 0


def display_rotation(filename):
    cmd = [
        _binary("ffprobe"),
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_streams",
        filename,
    ]
    try:
        out = subprocess.run(cmd, check=True, capture_output=True).stdout
    except (OSError, subprocess.CalledProcessError) as e:
        logging.warning(f"cannot probe {filename}: {e}")
        return 0
    for stream in json.loads(out.decode("utf-8", "replace")).get("streams", []):
        if stream.get("codec_type") == "video":
            return _stream_rotation(stream)
    return 0


def needs_rotation(filename):
    return display_rotation(filename) % 180 != 0


def normalize(filename, suffix="_rotated"):
    base, _ = os.path.splitext(filename)
    out = base + suffix + ".mp4"
    cmd = [
        _binary("ffmpeg"),
        "-y",
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
        out,
    ]
    subprocess.run(cmd, check=True)
    return out
