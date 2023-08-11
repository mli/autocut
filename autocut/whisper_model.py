from abc import ABC, abstractmethod
from typing import Literal, Union, List

import numpy as np
from pydub import AudioSegment
from tqdm import tqdm

from .type import SPEECH_TIMESTAMP, LANG


class AbstractWhisperModel(ABC):
    def __init__(self, mode):
        self.mode = mode
        self.whisper_model = None

    @abstractmethod
    def load(self, *args, **kwargs):
        pass

    @abstractmethod
    def transcribe(self, *args, **kwargs):
        pass


class WhisperModel(AbstractWhisperModel):
    def __init__(self):
        super().__init__("whisper")
        self.device = None

    def load(
        self,
        model_name: Literal[
            "tiny", "base", "small", "medium", "large", "large-v2"
        ] = "small",
        device: Union[Literal["cpu", "cuda"], None] = None,
    ):
        self.device = device

        import whisper

        self.whisper_model = whisper.load_model(model_name, device)

    def _process(self, audio, seg, lang, prompt):
        r = self.whisper_model.transcribe(
            audio[int(seg["start"]) : int(seg["end"])],
            task="transcribe",
            language=lang,
            initial_prompt=prompt,
        )
        r["origin_timestamp"] = seg
        return r

    def transcribe(
        self,
        raw_audio: AudioSegment,
        audio: np.ndarray,
        speech_timestamps: List[SPEECH_TIMESTAMP],
        lang: LANG,
        prompt: str,
    ):
        res = []
        if self.device == "cpu" and len(speech_timestamps) > 1:
            from multiprocessing import Pool

            pbar = tqdm(total=len(speech_timestamps))

            pool = Pool(processes=4)
            sub_res = []
            # TODO, a better way is merging these segments into a single one, so whisper can get more context
            for seg in speech_timestamps:
                sub_res.append(
                    pool.apply_async(
                        self._process,
                        (
                            self.whisper_model,
                            audio,
                            seg,
                            lang,
                            prompt,
                        ),
                        callback=lambda x: pbar.update(),
                    )
                )
            pool.close()
            pool.join()
            pbar.close()
            res = [i.get() for i in sub_res]
        else:
            for seg in (
                speech_timestamps
                if len(speech_timestamps) == 1
                else tqdm(speech_timestamps)
            ):
                r = self.whisper_model.transcribe(
                    audio[int(seg["start"]) : int(seg["end"])],
                    task="transcribe",
                    language=lang,
                    initial_prompt=prompt,
                    verbose=False if len(speech_timestamps) == 1 else None,
                )
                r["origin_timestamp"] = seg
                res.append(r)
        return res


class OpenAIModel(AbstractWhisperModel):
    def __init__(self):
        super().__init__("openai_whisper-1")
        import os

        if (
            os.environ.get("OPENAI_API_KEY") is None
            or os.environ.get("OPENAI_API_KEY_PATH") is None
        ):
            raise Exception("OPENAI_API_KEY is not set")

    def load(self, model_name: Literal["whisper-1"] = "whisper-1"):
        import openai
        from functools import partial

        self.whisper_model = partial(openai.Audio.transcribe, model=model_name)

    def transcribe(
        self,
        raw_audio: AudioSegment,
        audio: np.ndarray,
        speech_timestamps: List[SPEECH_TIMESTAMP],
        lang: LANG,
        prompt: str,
    ):
        pass
