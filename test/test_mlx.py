import unittest
from unittest.mock import Mock

import numpy as np

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
            {
                "segments": [
                    {"start": 1.0, "end": 2.0, "text": "你好"},
                    {"start": 4.0, "end": 5.0, "text": "世界"},
                ]
            }
        )

        self.assertEqual(len(result), 3)
        self.assertEqual(result[0].content, "你好")
        self.assertEqual(result[1].content, "< No Speech >")
        self.assertEqual(result[2].content, "世界")
        self.assertEqual(result[0].start.total_seconds(), 1.0)
        self.assertEqual(result[2].end.total_seconds(), 5.0)

    def test_transcribe_accepts_in_memory_audio(self):
        model = MLXWhisperModel()
        model.transcribe_file = Mock(return_value={"segments": []})

        result = model.transcribe(np.array([0.0, 0.5], dtype=np.float32), [], "zh", "")

        self.assertEqual(result, {"segments": []})
        model.transcribe_file.assert_called_once()


if __name__ == "__main__":
    unittest.main()
