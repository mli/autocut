import copy
import glob
import logging
import os
import time

from . import cut, transcribe, utils


class Daemon:
    def __init__(self, args):
        self.args = args
        self.sleep = 1

    def run(self):
        assert len(self.args.inputs) == 1, "Must provide a single folder"
        while True:
            self._iter()
            time.sleep(self.sleep)
            self.sleep = min(60, self.sleep + 1)

    def _iter(self):
        folder = self.args.inputs[0]
        files = sorted(list(glob.glob(os.path.join(folder, "*"))))
        media_files = [f for f in files if utils.is_video(f) or utils.is_audio(f)]
        args = copy.deepcopy(self.args)
        for f in media_files:
            srt_fn = utils.change_ext(f, "srt")
            md_fn = utils.change_ext(f, "md")
            is_video_file = utils.is_video(f)
            if srt_fn not in files or md_fn not in files:
                args.inputs = [f]
                try:
                    transcribe.Transcribe(args).run()
                    self.sleep = 1
                    break
                except RuntimeError as e:
                    logging.warn(
                        "Failed, may be due to the video is still on recording"
                    )
                    pass
            if md_fn in files:
                if utils.add_cut(md_fn) in files:
                    continue
                md = utils.MD(md_fn, self.args.encoding)
                ext = "mp4" if is_video_file else "mp3"
                if not md.done_editing() or os.path.exists(
                    utils.change_ext(utils.add_cut(f), ext)
                ):
                    continue
                args.inputs = [f, md_fn, srt_fn]
                cut.Cutter(args).run()
                self.sleep = 1

        args.inputs = [os.path.join(folder, "autocut.md")]
        merger = cut.Merger(args)
        merger.write_md(media_files)
        merger.run()
