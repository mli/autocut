import logging
import os
import re

import srt
from moviepy import editor

from . import utils


# Merge videos
class Merger:
    def __init__(self, args):
        self.args = args

    def write_md(self, videos):
        md = utils.MD(self.args.inputs[0], self.args.encoding)
        num_tasks = len(md.tasks())
        # Not overwrite if already marked as down or no new videos
        if md.done_editing() or num_tasks == len(videos) + 1:
            return

        md.clear()
        md.add_done_edditing(False)
        md.add('\nSelect the files that will be used to generate `autocut_final.mp4`\n')
        base = lambda fn: os.path.basename(fn)
        for f in videos:
            md_fn = utils.change_ext(f, 'md')
            video_md = utils.MD(md_fn, self.args.encoding)
            # select a few workds to scribe the video
            desc = ''
            if len(video_md.tasks()) > 1:
                for _, t in video_md.tasks()[1:]:
                    m = re.findall(r'\] (.*)', t)
                    if m and not 'no speech' in m[0].lower():
                        desc += m[0] + ' '
                    if len(desc) > 50: break
            md.add_task(False, f'[{base(f)}]({base(md_fn)}) {"[Editted]" if video_md.done_editing() else ""} {desc}')
        md.write()

    def run(self):
        md_fn = self.args.inputs[0]
        md = utils.MD(md_fn, self.args.encoding)
        if not md.done_editing():
            return

        videos = []
        for m, t in md.tasks():
            if not m: continue
            m = re.findall(r'\[(.*)\]', t)
            if not m: continue
            fn = os.path.join(os.path.dirname(md_fn), m[0])
            logging.info(f'Loading {fn}')
            videos.append(editor.VideoFileClip(fn))

        dur = sum([v.duration for v in videos])
        logging.info(f'Merging into a video with {dur / 60:.1f} min length')

        merged = editor.concatenate_videoclips(videos)
        fn = os.path.splitext(md_fn)[0] + '_merged.mp4'
        merged.write_videofile(fn, audio_codec='aac', bitrate=self.args.bitrate)  # logger=None,
        logging.info(f'Saved merged video to {fn}')


# Cut videos
class Cutter:
    def __init__(self, args):
        self.args = args

    def run(self):
        fns = {'srt': None, 'video': None, 'md': None}
        for fn in self.args.inputs:
            ext = os.path.splitext(fn)[1][1:]
            fns[ext if ext in fns else 'video'] = fn

        assert fns['video'], 'must provide a video filename'
        assert fns['srt'], 'must provide a srt filename'

        output_fn = utils.change_ext(utils.add_cut(fns['video']), 'mp4')
        base, ext = os.path.splitext(fns['srt'])
        srt_output_fn = base + ext.split(".")[0] + "_cut" + ".srt"
        if utils.check_exists(output_fn, self.args.force):
            return
        if utils.check_exists(srt_output_fn, self.args.force):
            return

        with open(fns['srt'], encoding=self.args.encoding) as f:
            subs = list(srt.parse(f.read()))

        if fns['md']:
            md = utils.MD(fns['md'], self.args.encoding)
            if not md.done_editing():
                return
            index = []
            new_content = {}
            for mark, sent in md.tasks():
                if not mark:
                    continue
                m = re.match(r'\[(\d+)', sent.strip())
                if m:
                    tag = int(m.groups()[0])
                    md_content = sent.split()
                    md_content.pop(0)
                    index.append(tag)
                    new_content[tag] = ''.join(md_content)
            subs = [s for s in subs if s.index in index]
            if self.args.overwrite_srt:
                for s in subs:
                    s.content = new_content[s.index]
            logging.info(f'Cut {fns["video"]} based on {fns["srt"]} and {fns["md"]}')
        else:
            logging.info(f'Cut {fns["video"]} based on {fns["srt"]}')

        segments = []
        # Avoid disordered subtitles
        subs.sort(key=lambda x: x.start)
        for x in subs:
            segments.append({'start': x.start.total_seconds(), 'end': x.end.total_seconds()})

        video = editor.VideoFileClip(fns['video'])

        # Add a fade between two clips. Not quite necesary. keep code here for reference
        # fade = 0
        # segments = _expand_segments(segments, fade, 0, video.duration)
        # clips = [video.subclip(
        #         s['start'], s['end']).crossfadein(fade) for s in segments]
        # final_clip = editor.concatenate_videoclips(clips, padding = -fade)

        clips = [video.subclip(s['start'], s['end']) for s in segments]
        final_clip = editor.concatenate_videoclips(clips)
        logging.info(f'Reduced duration from {video.duration:.1f} to {final_clip.duration:.1f}')

        aud = final_clip.audio.set_fps(44100)
        final_clip = final_clip.without_audio().set_audio(aud)
        final_clip = final_clip.fx(editor.afx.audio_normalize)

        # an alterantive to birate is use crf, e.g. ffmpeg_params=['-crf', '18']
        final_clip.write_videofile(output_fn, audio_codec='aac', bitrate=self.args.bitrate)
        logging.info(f'Saved video to {output_fn}')

        # format srt and generate new srt
        utils.refactor_srt(subs, srt_output_fn, self.args.encoding)
        logging.info(f'Saved refactored srt to {srt_output_fn}')
