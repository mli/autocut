import datetime
import logging
import os
import time

import opencc
import srt
import torch
import whisper

from . import utils


class Transcribe:
    def __init__(self, args):
        self.args = args
        self.sampling_rate = 16000
        self.whisper_model = None
        self.vad_model = None
        self.detect_speech = None

    def run(self):
        for input in self.args.inputs:
            logging.info(f"Transcribing {input}")
            name, _ = os.path.splitext(input)
            if utils.check_exists(name + ".md", self.args.force):
                continue

            audio = whisper.load_audio(input, sr=self.sampling_rate)
            speech_timestamps = self._detect_voice_activity(audio)
            transcribe_results = self._transcribe(audio, speech_timestamps)

            output = name + ".srt"
            self._save_srt(output, transcribe_results)
            logging.info(f"Transcribed {input} to {output}")
            self._save_md(name + ".md", output, input)
            logging.info(f'Saved texts to {name + ".md"} to mark sentences')

    def _detect_voice_activity(self, audio):
        """Detect segments that have voice activities"""
        if not self.args.vad:
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

        # Merge very closed segments
        # speeches = _merge_adjacent_segments(speeches, 0.5 * self.sampling_rate)

        # Remove too short segments
        speeches = utils.remove_short_segments(speeches, 10.0 * self.sampling_rate)

        # Expand to avoid to tight cut. You can tune the pad length
        speeches = utils.expand_segments(
            speeches, 0.2 * self.sampling_rate, 0.0 * self.sampling_rate, audio.shape[0]
        )

        logging.info(f"Done voice activity detection in {time.time() - tic:.1f} sec")
        return speeches

    def _transcribe(self, audio, speech_timestamps):
        tic = time.time()
        if self.whisper_model is None:
            self.whisper_model = whisper.load_model(
                self.args.whisper_model, self.args.device
            )

        res = []
        # TODO, a better way is merging these segments into a single one, so whisper can get more context
        for seg in speech_timestamps:
            r = self.whisper_model.transcribe(
                audio[int(seg["start"]) : int(seg["end"])],
                task="transcribe",
                language=self.args.lang,
                initial_prompt=self.args.prompt,
            )
            r["origin_timestamp"] = seg
            res.append(r)
        logging.info(f"Done transcription in {time.time() - tic:.1f} sec")
        return res

    def _save_srt(self, output, transcribe_results):
        subs = []
        # whisper sometimes generate traditional chinese, explicitly convert
        cc = opencc.OpenCC("t2s")

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
                start = s["start"] + origin["start"] / self.sampling_rate
                end = min(
                    s["end"] + origin["start"] / self.sampling_rate,
                    origin["end"] / self.sampling_rate,
                )
                if start > end:
                    continue
                # mark any empty segment that is not very short
                if start > prev_end + 1.0:
                    _add_sub(prev_end, start, "< No Speech >")
                _add_sub(start, end, s["text"])
                prev_end = end

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
