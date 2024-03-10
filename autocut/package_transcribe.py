import logging
import time
from typing import List, Any, Union, Literal

import numpy as np
import torch

from . import utils, whisper_model
from .type import WhisperMode, SPEECH_ARRAY_INDEX, WhisperModel, LANG


class Transcribe:
    def __init__(
        self,
        whisper_mode: Union[
            WhisperMode.WHISPER.value, WhisperMode.FASTER.value
        ] = WhisperMode.WHISPER.value,
        whisper_model_size: WhisperModel.get_values() = "small",
        vad: bool = True,
        device: Union[Literal["cpu", "cuda"], None] = None,
    ):
        self.whisper_mode = whisper_mode
        self.whisper_model_size = whisper_model_size
        self.vad = vad
        self.device = device
        self.sampling_rate = 16000
        self.whisper_model = None
        self.vad_model = None
        self.detect_speech = None

        tic = time.time()
        if self.whisper_model is None:
            if self.whisper_mode == WhisperMode.WHISPER.value:
                self.whisper_model = whisper_model.WhisperModel(self.sampling_rate)
                self.whisper_model.load(self.whisper_model_size, self.device)
            elif self.whisper_mode == WhisperMode.FASTER.value:
                self.whisper_model = whisper_model.FasterWhisperModel(
                    self.sampling_rate
                )
                self.whisper_model.load(self.whisper_model_size, self.device)
        logging.info(f"Done Init model in {time.time() - tic:.1f} sec")

    def run(self, audio: np.ndarray, lang: LANG, prompt: str = ""):
        speech_array_indices = self._detect_voice_activity(audio)
        transcribe_results = self._transcribe(audio, speech_array_indices, lang, prompt)
        return transcribe_results

    def format_results_to_srt(self, transcribe_results: List[Any]):
        return self.whisper_model.gen_srt(transcribe_results)

    def _detect_voice_activity(self, audio) -> List[SPEECH_ARRAY_INDEX]:
        """Detect segments that have voice activities"""
        if self.vad is False:
            return [{"start": 0, "end": len(audio)}]

        tic = time.time()
        if self.vad_model is None or self.detect_speech is None:
            # torch load limit https://github.com/pytorch/vision/issues/4156
            torch.hub._validate_not_a_forked_repo = lambda a, b, c: True
            self.vad_model, funcs = torch.hub.load(
                repo_or_dir="snakers4/silero-vad", model="silero_vad", trust_repo=True
            )

            self.detect_speech = funcs[0]

        speeches = self.detect_speech(
            audio, self.vad_model, sampling_rate=self.sampling_rate
        )

        # Remove too short segments
        speeches = utils.remove_short_segments(speeches, 1.0 * self.sampling_rate)

        # Expand to avoid to tight cut. You can tune the pad length
        speeches = utils.expand_segments(
            speeches, 0.2 * self.sampling_rate, 0.0 * self.sampling_rate, audio.shape[0]
        )

        # Merge very closed segments
        speeches = utils.merge_adjacent_segments(speeches, 0.5 * self.sampling_rate)

        logging.info(f"Done voice activity detection in {time.time() - tic:.1f} sec")
        return speeches if len(speeches) > 1 else [{"start": 0, "end": len(audio)}]

    def _transcribe(
        self,
        audio: np.ndarray,
        speech_array_indices: List[SPEECH_ARRAY_INDEX],
        lang: LANG,
        prompt: str = "",
    ) -> List[Any]:
        tic = time.time()
        res = self.whisper_model.transcribe(audio, speech_array_indices, lang, prompt)
        logging.info(f"Done transcription in {time.time() - tic:.1f} sec")
        return res
