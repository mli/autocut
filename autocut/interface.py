from subprocess import Popen, PIPE
import logging
import ffmpeg
import streamlit as st
import numpy as np

from autocut.transcribe import Transcribe


class Interface:
    def __init__(self):
        self.args = MyArgs()
        self.transcribe = None
        self.uploaded_video = None
        self.sampling_rate = None
        self.lang = None
        self.whisper_model = None
        self.prompt = None
        self.device = None
        self.vad = None

    def run(self):
        self.create_page()
        if self.uploaded_video is not None:
            st.write(self.sampling_rate, self.lang, self.prompt, self.whisper_model, self.device, self.vad)
            self.args.update(self.sampling_rate, self.lang, self.prompt, self.whisper_model, self.device, self.vad)
            # To read file as bytes:
            bytes_data = self.uploaded_video.getvalue()
            # audio = self._load_audio(bytes_data)
            # st.write(audio.size)
            self.transcribe = TranscribeByBytes(self.args)
            if self.transcribe.load_audio(bytes_data, self.uploaded_video.name):
                if st.button('开始转换'):
                    st.info(f'Transcribing {self.uploaded_video.name}', icon="ℹ")
                    self.transcribe.run()

    def create_page(self):
        st.write('# AutoCut: 通过字幕来剪切视频')
        st.write('AutoCut对你的视频自动生成字幕。然后你选择需要保留的句子，AutoCut将对你视频中对应的片段裁切并保存。'
                 '你无需使用视频编辑软件，只需要编辑文本文件即可完成剪切。')
        self.sampling_rate = st.slider('设置采样率', 10000, 44100, 16000)
        self.whisper_model = st.selectbox('设置模型大小', ('small', 'tiny', 'base', 'medium', 'large'))
        self.lang = st.radio('设置模型语言', ('zh', 'en'), horizontal=True)
        self.prompt = st.text_input('设置模型Prompt（可为空）', '')
        self.device = st.selectbox('选择运行设备', ('none', 'cpu', 'cuda'))
        st.write('> None代表自适应，cpu代表强制使用cpu，cuda达标强制使用gpu')
        self.vad = st.radio('是否使用VAD', ('no', 'yes'), horizontal=True)
        self.uploaded_video = st.file_uploader("选择一个视频文件", type=['mp4', 'mov', 'mkv', 'flv'])


class TranscribeByBytes(Transcribe):
    def __init__(self, args):
        super().__init__(args)
        self.audio = None
        self.video_name = None

    def load_audio(self, bytes_data: bytes, video_name='') -> bool:
        self.video_name = video_name
        try:
            # This launches a subprocess to decode audio while down-mixing and resampling as necessary.
            # Requires the ffmpeg CLI and `ffmpeg-python` package to be installed.
            cmd = ['ffmpeg', '-n', '-i', 'pipe:', '-acodec', 'pcm_s16le', '-f', 'wav', '-ac', '1', '-ar',
                   str(self.args.sampling_rate), 'pipe:']
            p = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE, bufsize=-1)
            out, _ = p.communicate(input=bytes_data)
            p.stdin.close()
        except ffmpeg.Error as e:
            raise RuntimeError(f"Failed to load audio: {e.stderr.decode()}") from e
        self.audio = np.frombuffer(out, np.int16).flatten().astype(np.float32) / 32768.0
        print(self.audio.size)
        return True

    def run(self):
        logging.info(f'Transcribing {input}')
        speech_timestamps = self._detect_voice_activity(self.audio)
        transcribe_results = self._transcibe(self.audio, speech_timestamps)
        st.write(transcribe_results)


class MyArgs:
    def __init__(self, sampling_rate=16000, lang='zh', prompt='', whisper_model='small', device=None, vad=False):
        self.sampling_rate = sampling_rate
        self.lang = lang
        self.prompt = prompt
        self.whisper_model = whisper_model
        self.device = device
        self.vad = vad

    def update(self, sampling_rate: int, lang: st, prompt: str, whisper_model: str, device: str, vad: str):
        self.sampling_rate = sampling_rate
        self.lang = lang
        self.prompt = prompt
        self.whisper_model = whisper_model
        self.device = device if device != 'none' else None
        self.vad = True if vad == 'yes' else False


if __name__ == '__main__':
    Interface().run()
