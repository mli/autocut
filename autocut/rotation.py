"""Display-rotation helpers for containers that carry a display matrix.

iPhone (and many Android) cameras store landscape pixels plus a rotation
matrix.  moviepy 1.x parses that matrix into ``clip.rotation`` but never
applies it, so a portrait recording is cut back as a landscape video with the
picture squashed.  ffmpeg applies the matrix by default, so the helpers here
use ffprobe/ffmpeg directly and stay free of heavy imports so they can be used
before the media stack is importable.
"""
import json
import logging
import os
import shutil
import subprocess


def _binary(name):
    path = shutil.which(name)
    if path is None:
        raise RuntimeError(f"cannot find {name} on PATH; install ffmpeg first")
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
    """Return the container display rotation in degrees, 0 when it has none."""
    cmd = [
        _binary("ffprobe"), "-v", "error", "-print_format", "json",
        "-show_streams", filename,
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
    """True when the display matrix asks for a 90/270 degree turn."""
    return display_rotation(filename) % 180 != 0


def normalize(filename, suffix="_rotated"):
    """Bake the display matrix into pixels and return the new file path.

    ffmpeg applies exactly the matrix a normal player would, which keeps the
    orientation correct without re-implementing the rotation sign convention.
    """
    base, _ = os.path.splitext(filename)
    out = base + suffix + ".mp4"
    cmd = [
        _binary("ffmpeg"), "-y", "-loglevel", "error", "-i", filename,
        "-c:v", "libx264", "-crf", "18", "-preset", "veryfast",
        "-c:a", "aac", "-b:a", "192k", out,
    ]
    subprocess.run(cmd, check=True)
    return out
