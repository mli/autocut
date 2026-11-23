import json
import shutil
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from autocut import rotation
from autocut.cut import Cutter, editor
from config import TEST_MEDIA_PATH, TestArgs

PLAIN_MEDIA = Path(TEST_MEDIA_PATH) / "test001.mp4"
# Synthetic 64x48 clip with audio and a -90 degree display matrix.
ROTATED_MEDIA = Path(TEST_MEDIA_PATH) / "display-matrix.mp4"
needs_ffmpeg = pytest.mark.skipif(
    not (shutil.which("ffmpeg") and shutil.which("ffprobe")),
    reason="rotation integration tests need ffmpeg and ffprobe",
)


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


def _make_cutter(tmp_path, sample):
    source = tmp_path / "trip.mov"
    subtitles = tmp_path / "trip.srt"
    shutil.copyfile(sample, source)
    subtitles.write_text("1\n00:00:00,000 --> 00:00:00,500\nSample\n", encoding="utf-8")
    args = TestArgs()
    args.inputs = [str(source), str(subtitles)]
    return Cutter(args)


def test_normal_cut_without_ffprobe(tmp_path, caplog):
    cutter = _make_cutter(tmp_path, PLAIN_MEDIA)
    with patch.object(
        rotation.subprocess, "run", side_effect=FileNotFoundError("ffprobe")
    ):
        cutter.run()
    assert (tmp_path / "trip_cut.mp4").is_file()
    assert f"cannot probe {tmp_path / 'trip.mov'}: ffprobe" in caplog.text


@pytest.mark.parametrize(
    ("side_data", "tags", "expected"),
    [
        ([{"rotation": -90}], {"rotate": "90"}, -90),
        ([{"rotation": "bad"}, {"rotation": "0"}], {"rotate": "90"}, 0),
        ([{"rotation": "-inf"}], {"rotate": "NaN", "rotation": "90"}, 90),
        ([], {"rotate": "bad", "rotation": "Infinity"}, 0),
    ],
)
def test_probe_uses_first_finite_rotation(side_data, tags, expected):
    stream = {"codec_type": "video", "side_data_list": side_data, "tags": tags}
    probe = subprocess.CompletedProcess(
        args=[], returncode=0, stdout=json.dumps({"streams": [stream]}).encode()
    )
    with patch.object(rotation.subprocess, "run", return_value=probe):
        assert rotation.display_rotation("trip.mov") == expected


@needs_ffmpeg
def test_plain_video_has_no_rotation():
    assert not rotation.needs_rotation(PLAIN_MEDIA)
    assert rotation.display_rotation(PLAIN_MEDIA) == 0


@needs_ffmpeg
def test_display_matrix_is_detected():
    assert rotation.display_rotation(ROTATED_MEDIA) == -90
    assert rotation.needs_rotation(ROTATED_MEDIA)


@needs_ffmpeg
def test_normalize_swaps_to_portrait(tmp_path):
    width, height = _probe_size(ROTATED_MEDIA)
    normalized = tmp_path / "normalized.mp4"
    rotation.normalize(ROTATED_MEDIA, normalized)
    assert _probe_size(normalized) == (height, width)
    assert rotation.display_rotation(normalized) == 0


@pytest.fixture
def portrait_cutter(tmp_path):
    return _make_cutter(tmp_path, ROTATED_MEDIA)


@needs_ffmpeg
def test_portrait_cut_preserves_existing_video(portrait_cutter, tmp_path):
    existing_video = tmp_path / "trip_rotated.mp4"
    shutil.copyfile(PLAIN_MEDIA, existing_video)

    portrait_cutter.run()

    assert existing_video.read_bytes() == PLAIN_MEDIA.read_bytes()
    assert _probe_size(tmp_path / "trip_cut.mp4") == (48, 64)


@needs_ffmpeg
def test_portrait_cut_cleans_temp_dir_on_open_failure(portrait_cutter, tmp_path):
    opened_paths = []

    def fail_open(filename):
        path = Path(filename)
        assert path.is_file()
        opened_paths.append(path)
        raise OSError("cannot open clip")

    with patch.object(editor, "VideoFileClip", side_effect=fail_open):
        with pytest.raises(OSError, match="cannot open clip"):
            portrait_cutter.run()

    (rotated_path,) = opened_paths
    assert rotated_path.parent != tmp_path
    assert not rotated_path.parent.exists()


@needs_ffmpeg
def test_portrait_cut_closes_reader_and_removes_temp_on_write_failure(portrait_cutter):
    opened_clips = []
    open_clip = editor.VideoFileClip

    def track_open(filename):
        clip = open_clip(filename)
        opened_clips.append(clip)
        return clip

    with patch.object(editor, "VideoFileClip", side_effect=track_open):
        with patch.object(
            editor.VideoClip,
            "write_videofile",
            side_effect=OSError("cannot write clip"),
        ):
            with pytest.raises(OSError, match="cannot write clip"):
                portrait_cutter.run()

    (source_clip,) = opened_clips
    assert source_clip.reader is None
    assert source_clip.audio is None
    assert not Path(source_clip.filename).parent.exists()
