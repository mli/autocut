import json
import os
import shutil
import subprocess
import unittest

from autocut import rotation
from config import TEST_MEDIA_PATH

PLAIN_MEDIA = os.path.join(TEST_MEDIA_PATH, "test001.mp4")


def _probe_size(path):
    out = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height",
            "-of",
            "json",
            path,
        ],
        check=True,
        capture_output=True,
    ).stdout
    stream = json.loads(out)["streams"][0]
    return stream["width"], stream["height"]


def _rotate_metadata(src, dst, degrees="-90"):
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-display_rotation",
            degrees,
            "-i",
            src,
            "-c",
            "copy",
            dst,
        ],
        check=True,
        capture_output=True,
    )


@unittest.skipUnless(
    shutil.which("ffmpeg") and shutil.which("ffprobe"), "rotation tests need ffmpeg"
)
class TestRotation(unittest.TestCase):
    def setUp(self):
        self.tmp = []

    def tearDown(self):
        for path in self.tmp:
            if os.path.exists(path):
                os.remove(path)

    def _rotated_copy(self):
        dst = os.path.join(TEST_MEDIA_PATH, "_rotated_test.mp4")
        self.tmp.append(dst)
        _rotate_metadata(PLAIN_MEDIA, dst)
        return dst

    def test_plain_video_has_no_rotation(self):
        self.assertFalse(rotation.needs_rotation(PLAIN_MEDIA))
        self.assertEqual(rotation.display_rotation(PLAIN_MEDIA), 0)

    def test_display_matrix_is_detected(self):
        rotated = self._rotated_copy()
        self.assertEqual(rotation.display_rotation(rotated), -90)
        self.assertTrue(rotation.needs_rotation(rotated))

    def test_normalize_swaps_to_portrait(self):
        rotated = self._rotated_copy()
        width, height = _probe_size(rotated)
        normalized = rotation.normalize(rotated, suffix="_normalized_test")
        self.tmp.append(normalized)
        new_width, new_height = _probe_size(normalized)
        self.assertEqual((new_width, new_height), (height, width))
