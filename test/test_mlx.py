import sys
import unittest
from unittest.mock import Mock, patch

import numpy as np

from autocut import Transcribe
from autocut.whisper_model import MLXWhisperModel


class TestMLXWhisperModel(unittest.TestCase):
    def test_model_repositories(self):
        self.assertEqual(
            MLXWhisperModel.model_repositories["large-v3-turbo"],
            "mlx-community/whisper-large-v3-turbo",
        )
        self.assertEqual(
            MLXWhisperModel.model_repositories["large-v3"],
            "mlx-community/whisper-large-v3-mlx",
        )

    def test_rejects_explicit_devices_before_importing_mlx(self):
        with patch.dict(sys.modules, {"mlx_whisper": None}):
            for device in ("cpu", "cuda"):
                with self.subTest(device=device), self.assertRaisesRegex(
                    ValueError, rf"explicit device \('{device}'\).*Omit --device"
                ):
                    MLXWhisperModel().load(device=device)

    def test_transcribe_file_delegates_to_mlx(self):
        model = MLXWhisperModel()
        model.whisper_model = Mock()
        model.model_repository = "mlx-community/whisper-small-mlx"
        model.whisper_model.transcribe.return_value = {"segments": []}

        result = model.transcribe_file("test.mp4", "zh", "technical terms")

        self.assertEqual(result, {"segments": []})
        model.whisper_model.transcribe.assert_called_once_with(
            "test.mp4",
            path_or_hf_repo="mlx-community/whisper-small-mlx",
            language="zh",
            initial_prompt="technical terms",
            verbose=False,
        )

    def test_gen_srt_preserves_timestamps_and_adds_silence(self):
        model = MLXWhisperModel()
        result = model.gen_srt(
            [
                {
                    "segments": [
                        {"start": 1.0, "end": 2.0, "text": "你好"},
                        {"start": 4.0, "end": 5.0, "text": "世界"},
                    ]
                }
            ]
        )

        self.assertEqual(len(result), 3)
        self.assertEqual(result[0].content, "你好")
        self.assertEqual(result[1].content, "< No Speech >")
        self.assertEqual(result[2].content, "世界")
        self.assertEqual(result[0].start.total_seconds(), 1.0)
        self.assertEqual(result[2].end.total_seconds(), 5.0)

    def test_public_transcribe_returns_list_and_formats_srt(self):
        backend = Mock()
        backend.transcribe.return_value = {
            "segments": [{"start": 0.0, "end": 0.5, "text": "你好"}],
        }
        audio = np.zeros(8000, dtype=np.float32)

        with patch.dict(sys.modules, {"mlx_whisper": backend}):
            transcriber = Transcribe(whisper_mode="mlx")
            result = transcriber.run(audio, "zh")

        self.assertEqual(
            result,
            [
                {
                    "origin_timestamp": {"start": 0, "end": len(audio)},
                    "segments": backend.transcribe.return_value["segments"],
                }
            ],
        )
        backend.transcribe.assert_called_once()
        self.assertNotIn("device", backend.transcribe.call_args.kwargs)
        subtitles = transcriber.format_results_to_srt(result)
        self.assertEqual(len(subtitles), 1)
        self.assertEqual(subtitles[0].content, "你好")
        self.assertEqual(subtitles[0].end.total_seconds(), 0.5)


if __name__ == "__main__":
    unittest.main()
