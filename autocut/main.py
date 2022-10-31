import argparse
import datetime
import sys

# import torch
# import whisper
import srt
from moviepy import editor

def _expand_segments(segments, expand_head, expand_tail, total_length):
    # Pad head and tail for each time segment
    results = []
    for i in range(len(segments)):
        t = segments[i]
        start = max(t['start'] - expand_head,
            segments[i-1]['end'] if i > 0 else 0)
        end = min(t['end'] + expand_tail,
            segments[i+1]['start'] if i < len(segments)-1 else total_length)
        results.append({'start':start, 'end':end})
    return results

def _remove_short_segments(segments, threshold): 
    # Remove segments whose length < threshold
    return [s for s in segments if s['end'] - s['start'] > threshold]

def _merge_adjacent_segments(segments, threshold):
    # Merge two adjacent segments if their distance < threshold
    results = []
    i = 0
    while i < len(segments):
        s = segments[i]
        for j in range(i+1, len(segments)):
            if segments[j]['start'] < s['end'] + threshold:
                s['end'] = segments[j]['end']
                i = j
            else:
                break
        i += 1
        results.append(s) 
    return results

class Transcribe:
    def __init__(self, args):
        self.args = args
        self.sampling_rate = 16000
        self.whisper_model = None
        self.vad_model = None
        self.detect_speech = None

    def run(self):
        import whisper

        for input in self.args.inputs:
            print(f'Transcribing {input}')
            audio = whisper.load_audio(input, sr=self.sampling_rate)
            speech_timestamps = self._detect_voice_activity(audio)
            transcribe_results = self._transcibe(audio, speech_timestamps)
            output = '.'.join(input.split('.')[:-1])+'.srt'
            self._save_srt(output, transcribe_results)
            print(f'Transcribed {input} to {output}')
            

    def _detect_voice_activity(self, audio):
        """Detect segments that have voice activities"""
        if self.vad_model is None or self.detect_speech is None:
            import torch

            self.vad_model, utils = torch.hub.load(
                repo_or_dir='snakers4/silero-vad',
                model='silero_vad',
                trust_repo=True)
            
            self.detect_speech = utils[0]
        
        speeches = self.detect_speech(audio, self.vad_model, 
            sampling_rate=self.sampling_rate)
        
        # Merge very closed segments
        # speeches = _merge_adjacent_segments(speeches, 0.5 * self.sampling_rate)

        # Remove too shart segments 
        # speeches = _remove_short_segments(speeches, 1.0 * self.sampling_rate)

        # Expand to avoid to tight cut. You can tune the pad length

        speeches =  _expand_segments(speeches, 0.2*self.sampling_rate, 
            0.0*self.sampling_rate, audio.shape[0])
        
        return speeches

    def _transcibe(self, audio, speech_timestamps):
        if self.whisper_model is None:
            import whisper             
            self.whisper_model = whisper.load_model(self.args.whisper_model)        

        res = []
        for seg in speech_timestamps:    
            r = self.whisper_model.transcribe(
                    audio[int(seg['start']):int(seg['end'])],
                    task='transcribe', language='zh', initial_prompt=self.args.prompt)
            r['origin_timestamp'] = seg
            res.append(r)
        return res

    def _save_srt(self, output, transcribe_results):
        subs = []
        def _add_sub(start, end, text):
            subs.append(srt.Subtitle(index=0, 
                start=datetime.timedelta(seconds=start),
                end=datetime.timedelta(seconds=end), 
                content=text.strip()))

        prev_end = 0
        for r in transcribe_results:
            origin = r['origin_timestamp']
            for s in r['segments']:                
                start = s['start'] + origin['start'] / self.sampling_rate
                end = min(s['end'] + origin['start'] / self.sampling_rate, origin['end'] / self.sampling_rate)
                # mark any empty segment that is not very short
                if start > prev_end + 1.0:
                    _add_sub(prev_end, start, '< No Speech >')                
                _add_sub(start, end, s["text"])
                prev_end = end
        
        with open(output, 'w') as f:
            f.write(srt.compose(subs))

class Cutter:
    def __init__(self, args):
        self.args = args
        
    def run(self):
        assert len(self.args.inputs) == 2, 'must just provide two files, a video file and a srt file'
        video_fn, srt_fn = self.args.inputs
        if video_fn.endswith('.srt'):
            video_fn, srt_fn = srt_fn, video_fn 
        print(f'Cut {video_fn} based on {srt_fn}')
        segments = []
        with open(srt_fn) as f:
            subs = srt.parse(f.read())
        for x in subs:
            segments.append({'start':x.start.total_seconds(), 'end':x.end.total_seconds()})

        video = editor.VideoFileClip(video_fn)
        
        # Add a fade between two clips. Not quite necesary. keep code here for reference
        # fade = 0
        # segments = _expand_segments(segments, fade, 0, video.duration)
        # clips = [video.subclip(
        #         s['start'], s['end']).crossfadein(fade) for s in segments]
        # final_clip = editor.concatenate_videoclips(clips, padding = -fade)

        clips = [video.subclip(s['start'], s['end']).fx(editor.afx.audio_normalize) for s in segments]
        final_clip = editor.concatenate_videoclips(clips)
        print(f'Reduced duration from {video.duration:.1f} to {final_clip.duration:.1f}')
        output_fn = '.'.join(video_fn.split('.')[:-1]) + '_cut.mp4'
        # an alterantive to birate is use crf, e.g. ffmpeg_params=['-crf', '18']
        final_clip.write_videofile(output_fn, audio_codec='aac', logger=None, bitrate=self.args.bitrate)
        print(f'Saved video to {output_fn}')

def main():
    parser = argparse.ArgumentParser(description='Edit videos based on transcribed subtitles',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:

# Transcribe a video into subtitles
autocut -t my_video.mp4
# Delete uncessary sentences in my_video.srt, then
# generate a new video with only these sentences kept
autocut -c my_video.mp4 my_video.srt

Note that you can transcribe multiple vidoes at the same time to 
slightly make it faster:

autocut -t my_video_*.mp4

''')

    parser.add_argument('inputs', type=str, nargs='+',
                        help='Inputs filenames')
    parser.add_argument('-t', '--transcribe', help='Transcribe videos/audio into subtitles', 
        action=argparse.BooleanOptionalAction)
    parser.add_argument('-c', '--cut', help='Cut a video based on subtitles', 
        action=argparse.BooleanOptionalAction)
    parser.add_argument('--prompt', type=str, default='大家好，', 
        help='initial prompt feed into whisper')
    parser.add_argument('--whisper-model', type=str, default='large',
        choices=['tiny', 'base', 'small', 'medium', 'large'],
        help='The whisper model used to transcribe.')
    parser.add_argument('--bitrate', type=str, default='1m',        
        help='The bitrate to export the cutted video, such as 10m, 1m, or 500k')
    
    args = parser.parse_args()

    if args.transcribe:
        trans = Transcribe(args)
        trans.run()        
    else:
        cutter = Cutter(args)
        cutter.run()

    
if __name__ == "__main__":
    main()
