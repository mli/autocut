import copy
import glob
import logging
import os
import re
import time

from . import cut, transcribe, utils


class Daemon:
    def __init__(self, args):
        self.args = args
        self.sleep = 1

    def run(self):
        assert len(self.args.inputs) == 1, 'Must provide a single folder'
        while True:
            self._iter()
            time.sleep(self.sleep)
            self.sleep = min(60, self.sleep+1)

    def _is_video(self, filename):
        _, ext = os.path.splitext(filename)
        return ext in ['.mp4', '.mov', '.mkv', '.flv']

    def _iter(self):
        folder = self.args.inputs[0]
        files = sorted(list(glob.glob(os.path.join(folder, '*'))))
        videos = [f for f in files if self._is_video(f)]
        args = copy.deepcopy(self.args)
        for f in videos:
            srt_fn = utils.change_ext(f, 'srt')
            md_fn = utils.change_ext(f, 'md')
            if srt_fn not in files or md_fn not in files:
                args.inputs = [f]
                try:
                    transcribe.Transcribe(args).run()
                    self.sleep = 1
                    break
                except RuntimeError as e:
                    logging.warn('Failed, may be due to the video is still on recording')
                    pass
            if md_fn in files:
                if utils.add_cut(md_fn) in files:
                    continue
                md = utils.MD(md_fn, self.args.encoding)
                if not md.done_editing():
                    continue
                args.inputs = [f, md_fn, srt_fn]
                cut.Cutter(args).run()
                self.sleep = 1
                break

        args.inputs = [os.path.join(folder, 'autocut.md')]
        merger = cut.Merger(args)
        merger.write_md(videos)
        merger.run()