import datetime
import logging
import os
from abc import ABC, abstractmethod
from typing import Literal, Union, List, Any

import numpy as np
import opencc
import srt
from pydub import AudioSegment
from tqdm import tqdm

from .type import SPEECH_ARRAY_INDEX, LANG

# whisper sometimes generate traditional chinese, explicitly convert
cc = opencc.OpenCC("t2s")


class AbstractWhisperModel(ABC):
    def __init__(self, mode, sample_rate=16000):
        self.mode = mode
        self.whisper_model = None
        self.sample_rate = sample_rate

    @abstractmethod
    def load(self, *args, **kwargs):
        pass

    @abstractmethod
    def transcribe(self, *args, **kwargs):
        pass

    @abstractmethod
    def gen_srt(self, transcribe_results: List[Any]) -> List[srt.Subtitle]:
        pass


class WhisperModel(AbstractWhisperModel):
    def __init__(self, sample_rate=16000):
        super().__init__("whisper", sample_rate)
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
        audio: np.ndarray,
        speech_array_indices: List[SPEECH_ARRAY_INDEX],
        lang: LANG,
        prompt: str,
    ):
        res = []
        if self.device == "cpu" and len(speech_array_indices) > 1:
            from multiprocessing import Pool

            pbar = tqdm(total=len(speech_array_indices))

            pool = Pool(processes=4)
            sub_res = []
            # TODO, a better way is merging these segments into a single one, so whisper can get more context
            for seg in speech_array_indices:
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
                speech_array_indices
                if len(speech_array_indices) == 1
                else tqdm(speech_array_indices)
            ):
                r = self.whisper_model.transcribe(
                    audio[int(seg["start"]) : int(seg["end"])],
                    task="transcribe",
                    language=lang,
                    initial_prompt=prompt,
                    verbose=False if len(speech_array_indices) == 1 else None,
                )
                r["origin_timestamp"] = seg
                res.append(r)
        return res

    def gen_srt(self, transcribe_results):
        subs = []

        def _add_sub(start, end, text):
            subs.append(
                srt.Subtitle(
                    index=0,
                    start=datetime.timedelta(seconds=start),
                    end=datetime.timedelta(seconds=end),
                    content=cc.convert(text.strip()),
                )
            )

        prev_end = 0
        for r in transcribe_results:
            origin = r["origin_timestamp"]
            for s in r["segments"]:
                start = s["start"] + origin["start"] / self.sample_rate
                end = min(
                    s["end"] + origin["start"] / self.sample_rate,
                    origin["end"] / self.sample_rate,
                )
                if start > end:
                    continue
                # mark any empty segment that is not very short
                if start > prev_end + 1.0:
                    _add_sub(prev_end, start, "< No Speech >")
                _add_sub(start, end, s["text"])
                prev_end = end

        return subs


class OpenAIModel(AbstractWhisperModel):
    max_single_audio_bytes = 25 * 2**20  # 25MB
    split_audio_bytes = 23 * 2**20  # 23MB, 2MB for safety(header, etc.)
    res = []

    def __init__(self, sample_rate=16000):
        super().__init__("openai_whisper-1", sample_rate)

        import os

        if (
            os.environ.get("OPENAI_API_KEY") is None
            and os.environ.get("OPENAI_API_KEY_PATH") is None
        ):
            raise Exception("OPENAI_API_KEY is not set")

    def load(self, model_name: Literal["whisper-1"] = "whisper-1"):
        import openai
        from functools import partial

        self.whisper_model = partial(openai.Audio.transcribe, model=model_name)

    def transcribe(
        self,
        input: srt,
        audio: np.ndarray,
        speech_array_indices: List[SPEECH_ARRAY_INDEX],
        lang: LANG,
        prompt: str,
    ) -> List[srt.Subtitle]:
        res = []
        name, _ = os.path.splitext(input)
        raw_audio = AudioSegment.from_file(input)
        ms_bytes = len(raw_audio[:1].raw_data)

        # since TPM and	RPM, no multiprocessor
        i = 0
        for index in (
            speech_array_indices
            if len(speech_array_indices) == 1
            else tqdm(speech_array_indices)
        ):
            start = int(index["start"]) / self.sample_rate * 1000
            end = int(index["end"]) / self.sample_rate * 1000
            audio_seg = raw_audio[start:end]
            if len(audio_seg.raw_data) < self.split_audio_bytes:
                temp_file = f"{name}_temp_{i}.wav"
                audio_seg.export(temp_file, format="wav")
                self._transcribe(temp_file, prompt, lang)
                os.remove(temp_file)
            else:
                logging.info(
                    f"Long audio with a size({len(audio_seg.raw_data)} bytes) greater than 25M({25 * 2**20} bytes) "
                    "will be segmented"
                    "due to Openai's API restrictions on files smaller than 25M"
                )
                split_num = len(audio_seg.raw_data) // self.split_audio_bytes + 1
                for j in range(split_num):
                    temp_file = f"{name}_{i}_temp_{j}.wav"
                    split_audio = audio_seg[
                        j
                        * self.split_audio_bytes
                        // ms_bytes : (j + 1)
                        * self.split_audio_bytes
                        // ms_bytes
                    ]
                    split_audio.export(temp_file, format="wav")
                    self._transcribe(temp_file, prompt, lang)
                    os.remove(temp_file)
            i += 1
        self.res, res = res, self.res
        return res

    def _transcribe(self, file, prompt, lang):
        def format_srt(
            subtitles_str: str, existing_subtitles_num: int, last_subtitle: srt.Subtitle
        ):
            subtitles = list(srt.parse(subtitles_str))
            for subtitle in subtitles:
                subtitle.index += existing_subtitles_num
                subtitle.start += last_subtitle.end
                subtitle.end += last_subtitle.end

            return subtitles

        subtitles = self.whisper_model(
            file=open(file, "rb"), prompt=prompt, language=lang, response_format="srt"
        )
        existing_subtitles_num = len(self.res)
        last_subtitle = (
            self.res[-1]
            if len(self.res) > 0
            else srt.Subtitle(-1, datetime.timedelta(), datetime.timedelta(), "")
        )
        self.res.extend(
            [
                subtitle
                for subtitle in format_srt(
                    subtitles, existing_subtitles_num, last_subtitle
                )
            ]
        )

    def gen_srt(self, transcribe_results: List[srt.Subtitle]):
        if len(transcribe_results) == 0:
            return []
        if len(transcribe_results) == 1:
            return transcribe_results
        subs = [transcribe_results[0]]
        for subtitle in transcribe_results[1:]:
            if subtitle.start - subs[-1].end > datetime.timedelta(seconds=1):
                subs.append(
                    srt.Subtitle(
                        index=0,
                        start=subs[-1].end,
                        end=subtitle.start,
                        content="< No Speech >",
                    )
                )
            subs.append(subtitle)
        return subs
