import logging
import os
import time
from typing import List, Any

import numpy as np
import srt
import torch

from . import utils, whisper_model
from .type import WhisperMode, SPEECH_ARRAY_INDEX


class Transcribe:
    def __init__(self, args):
        self.args = args
        self.sampling_rate = 16000
        self.whisper_model = None
        self.vad_model = None
        self.detect_speech = None

        tic = time.time()
        if self.whisper_model is None:
            if self.args.whisper_mode == WhisperMode.WHISPER.value:
                self.whisper_model = whisper_model.WhisperModel(self.sampling_rate)
                self.whisper_model.load(self.args.whisper_model, self.args.device)
            elif self.args.whisper_mode == WhisperMode.OPENAI.value:
                self.whisper_model = whisper_model.OpenAIModel(
                    self.args.openai_rpm, self.sampling_rate
                )
                self.whisper_model.load()
            elif self.args.whisper_mode == WhisperMode.FASTER.value:
                self.whisper_model = whisper_model.FasterWhisperModel(
                    self.sampling_rate
                )
                self.whisper_model.load(self.args.whisper_model, self.args.device)
        logging.info(f"Done Init model in {time.time() - tic:.1f} sec")

    def run(self):
        for input in self.args.inputs:
            logging.info(f"Transcribing {input}")
            name, _ = os.path.splitext(input)
            if utils.check_exists(name + ".md", self.args.force):
                continue

            audio = utils.load_audio(input, sr=self.sampling_rate)
            speech_array_indices = self._detect_voice_activity(audio)
            transcribe_results = self._transcribe(input, audio, speech_array_indices)

            output = name + ".srt"
            self._save_srt(output, transcribe_results)
            logging.info(f"Transcribed {input} to {output}")
            self._save_md(name + ".md", output, input)
            logging.info(f'Saved texts to {name + ".md"} to mark sentences')

    def _detect_voice_activity(self, audio) -> List[SPEECH_ARRAY_INDEX]:
        """Detect segments that have voice activities"""
        if self.args.vad == "0":
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
        input: str,
        audio: np.ndarray,
        speech_array_indices: List[SPEECH_ARRAY_INDEX],
    ) -> List[Any]:
        tic = time.time()
        res = (
            self.whisper_model.transcribe(
                audio, speech_array_indices, self.args.lang, self.args.prompt
            )
            if self.args.whisper_mode == WhisperMode.WHISPER.value
            or self.args.whisper_mode == WhisperMode.FASTER.value
            else self.whisper_model.transcribe(
                input, audio, speech_array_indices, self.args.lang, self.args.prompt
            )
        )

        logging.info(f"Done transcription in {time.time() - tic:.1f} sec")
        return res

    def _save_srt(self, output, transcribe_results):
        subs = self.whisper_model.gen_srt(transcribe_results)
        with open(output, "wb") as f:
            f.write(srt.compose(subs).encode(self.args.encoding, "replace"))

    def _save_md(self, md_fn, srt_fn, video_fn):
        with open(srt_fn, encoding=self.args.encoding) as f:
            subs = srt.parse(f.read())

        md = utils.MD(md_fn, self.args.encoding)
        md.clear()
        md.add_done_editing(False)
        md.add_video(os.path.basename(video_fn))
        md.add(
            f"\nTexts generated from [{os.path.basename(srt_fn)}]({os.path.basename(srt_fn)})."
            "Mark the sentences to keep for autocut.\n"
            "The format is [subtitle_index,duration_in_second] subtitle context.\n\n"
        )

        for s in subs:
            sec = s.start.seconds
            pre = f"[{s.index},{sec // 60:02d}:{sec % 60:02d}]"
            md.add_task(False, f"{pre:11} {s.content.strip()}")
        md.write()
