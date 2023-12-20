import logging
import os
import re

import ffmpeg
import numpy as np
import opencc
import srt


def load_audio(file: str, sr: int = 16000) -> np.ndarray:
    try:
        out, _ = (
            ffmpeg.input(file, threads=0)
            .output("-", format="s16le", acodec="pcm_s16le", ac=1, ar=sr)
            .run(cmd=["ffmpeg", "-nostdin"], capture_stdout=True, capture_stderr=True)
        )
    except ffmpeg.Error as e:
        raise RuntimeError(f"Failed to load audio: {e.stderr.decode()}") from e

    return np.frombuffer(out, np.int16).flatten().astype(np.float32) / 32768.0


def is_video(filename):
    _, ext = os.path.splitext(filename)
    return ext in [".mp4", ".mov", ".mkv", ".avi", ".flv", ".f4v", ".webm"]


def is_audio(filename):
    _, ext = os.path.splitext(filename)
    return ext in [".ogg", ".wav", ".mp3", ".flac", ".m4a"]


def change_ext(filename, new_ext):
    # Change the extension of filename to new_ext
    base, _ = os.path.splitext(filename)
    if not new_ext.startswith("."):
        new_ext = "." + new_ext
    return base + new_ext


def add_cut(filename):
    # Add cut mark to the filename
    base, ext = os.path.splitext(filename)
    if base.endswith("_cut"):
        base = base[:-4] + "_" + base[-4:]
    else:
        base += "_cut"
    return base + ext


# a very simple markdown parser
class MD:
    def __init__(self, filename, encoding):
        self.lines = []
        self.EDIT_DONE_MAKR = "<-- Mark if you are done editing."
        self.encoding = encoding
        self.filename = filename
        if filename:
            self.load_file()

    def load_file(self):
        if os.path.exists(self.filename):
            with open(self.filename, encoding=self.encoding) as f:
                self.lines = f.readlines()

    def clear(self):
        self.lines = []

    def write(self):
        with open(self.filename, "wb") as f:
            f.write("\n".join(self.lines).encode(self.encoding, "replace"))

    def tasks(self):
        # get all tasks with their status
        ret = []
        for l in self.lines:
            mark, task = self._parse_task_status(l)
            if mark is not None:
                ret.append((mark, task))
        return ret

    def done_editing(self):
        for m, t in self.tasks():
            if m and self.EDIT_DONE_MAKR in t:
                return True
        return False

    def add(self, line):
        self.lines.append(line)

    def add_task(self, mark, contents):
        self.add(f'- [{"x" if mark else " "}] {contents.strip()}')

    def add_done_editing(self, mark):
        self.add_task(mark, self.EDIT_DONE_MAKR)

    def add_video(self, video_fn):
        ext = os.path.splitext(video_fn)[1][1:]
        self.add(
            f'\n<video controls="true" allowfullscreen="true"> <source src="{video_fn}" type="video/{ext}"> </video>\n'
        )

    def _parse_task_status(self, line):
        # return (is_marked, rest) or (None, line) if not a task
        m = re.match(r"- +\[([ xX])\] +(.*)", line)
        if not m:
            return None, line
        return m.groups()[0].lower() == "x", m.groups()[1]


def check_exists(output, force):
    if os.path.exists(output):
        if force:
            logging.info(f"{output} exists. Will overwrite it")
        else:
            logging.info(
                f"{output} exists, skipping... Use the --force flag to overwrite"
            )
            return True
    return False


def expand_segments(segments, expand_head, expand_tail, total_length):
    # Pad head and tail for each time segment
    results = []
    for i in range(len(segments)):
        t = segments[i]
        start = max(t["start"] - expand_head, segments[i - 1]["end"] if i > 0 else 0)
        end = min(
            t["end"] + expand_tail,
            segments[i + 1]["start"] if i < len(segments) - 1 else total_length,
        )
        results.append({"start": start, "end": end})
    return results


def remove_short_segments(segments, threshold):
    # Remove segments whose length < threshold
    return [s for s in segments if s["end"] - s["start"] > threshold]


def merge_adjacent_segments(segments, threshold):
    # Merge two adjacent segments if their distance < threshold
    results = []
    i = 0
    while i < len(segments):
        s = segments[i]
        for j in range(i + 1, len(segments)):
            if segments[j]["start"] < s["end"] + threshold:
                s["end"] = segments[j]["end"]
                i = j
            else:
                break
        i += 1
        results.append(s)
    return results


def compact_rst(sub_fn, encoding):
    cc = opencc.OpenCC("t2s")

    base, ext = os.path.splitext(sub_fn)
    COMPACT = "_compact"
    if ext != ".srt":
        logging.fatal("only .srt file is supported")

    if base.endswith(COMPACT):
        # to original rst
        with open(sub_fn, encoding=encoding) as f:
            lines = f.readlines()
        subs = []
        for l in lines:
            items = l.split(" ")
            if len(items) < 4:
                continue
            subs.append(
                srt.Subtitle(
                    index=0,
                    start=srt.srt_timestamp_to_timedelta(items[0]),
                    end=srt.srt_timestamp_to_timedelta(items[2]),
                    content=" ".join(items[3:]).strip(),
                )
            )
        with open(base[: -len(COMPACT)] + ext, "wb") as f:
            f.write(srt.compose(subs).encode(encoding, "replace"))
    else:
        # to a compact version
        with open(sub_fn, encoding=encoding) as f:
            subs = srt.parse(f.read())
        with open(base + COMPACT + ext, "wb") as f:
            for s in subs:
                f.write(
                    f"{srt.timedelta_to_srt_timestamp(s.start)} --> {srt.timedelta_to_srt_timestamp(s.end)} "
                    f"{cc.convert(s.content.strip())}\n".encode(encoding, "replace")
                )


def trans_srt_to_md(encoding, force, srt_fn, video_fn=None):
    base, ext = os.path.splitext(srt_fn)
    if ext != ".srt":
        logging.fatal("only .srt file is supported")
    md_fn = base + ext.split(".")[0] + ".md"

    check_exists(md_fn, force)

    with open(srt_fn, encoding=encoding) as f:
        subs = srt.parse(f.read())

    md = MD(md_fn, encoding)
    md.clear()
    md.add_done_editing(False)
    if video_fn:
        if not is_video(video_fn):
            logging.fatal(f"{video_fn} may not be a video")
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
