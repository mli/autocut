import hashlib
import json
import time
import os.path
import shlex
import zipfile
from io import StringIO
from subprocess import Popen, PIPE
import logging
import ffmpeg
import srt
import streamlit as st
import numpy as np

from autocut.cut import Cutter
from autocut.transcribe import Transcribe
from autocut.utils import MD


md5 = hashlib.md5()


class Interface:
    def __init__(self):
        self.args = MyArgs()
        self.upload_video_tab1 = None
        self.upload_video_tab3 = None
        self.sampling_rate = None
        self.lang = None
        self.whisper_model = None
        self.prompt = None
        self.device = None
        self.vad = None
        self.transcribe_btn = None
        self.cut_btn = None
        self.upload_srt_tab2 = None
        self.upload_srt_tab3 = None
        self.upload_md = None
        self.srt_checkboxes = []
        self.srt_edit_confirm = None
        self.tab1, self.tab2, self.tab3 = None, None, None
        self.name = None
        self.md_contents = None
        self.srt_raw_contents = []
        self.srt_contents = None
        self.video_contents = None

    def run(self):
        self.create_page()
        if self.upload_video_tab1 is not None:
            # To read file as bytes:
            bytes_data = self.upload_video_tab1.getvalue()
            # 目前不知道如何直接处理bytes，就先保存了再直接复用transcribe
            self.name = self._save_file(bytes_data, self.upload_video_tab1.name)
            [base, ext] = self.name.split('.')
            if self.transcribe_btn:
                st.info(f'Transcribing {self.upload_video_tab1.name}', icon="ℹ")
                self.transcribe()
                time.sleep(0.5)
                if os.path.exists('./temp/' + base + '.md'):
                    st.info(f'Transcribing {self.upload_video_tab1.name} 处理完成', icon="ℹ")
                    self.zip_file(['./temp/' + base + '.md',
                                   './temp/' + base + '.srt'],
                                  './temp/' + base + '.zip')
                    with open('./temp/' + base + '.zip', "rb") as file:
                        self.tab1.download_button(
                            label="下载结果",
                            data=file,
                            file_name=base + '.zip',
                            mime='application/zip',
                        )
                else:
                    st.info(f'Transcribing {self.upload_video_tab1.name} 处理失败', icon="🚨")

        if self.upload_srt_tab2 is not None:
            [base, ext] = self.upload_srt_tab2.name.split('.')
            self.srt_contents = list(srt.parse(StringIO(self.upload_srt_tab2.getvalue().decode("utf-8"))))
            for i in range(len(self.srt_contents)):
                self.srt_checkboxes.append(self.tab2.checkbox('删除下方字幕', key=i))
                content = srt.compose([self.srt_contents[i]])[2:]
                self.tab2.subheader(content.replace(content.split()[3], ''))
                self.srt_raw_contents.append(
                    self.tab2.text_input('',
                                         srt.compose([self.srt_contents[i]])[2:].split()[3],
                                         label_visibility='collapsed')
                )
                self.tab2.progress(100)
            self.srt_edit_confirm = self.tab2.button('编辑完成')
            if self.srt_edit_confirm:
                new_srt = []
                for i in range(len(self.srt_contents)):
                    if not self.srt_checkboxes[i]:
                        new_srt.append(self.srt_contents[i])
                        new_srt[-1].content = self.srt_raw_contents[i]
                for i in range(len(new_srt)):
                    new_srt[i].index = i + 1
                self.tab2.download_button(
                    label="下载编辑后srt",
                    data=srt.compose(new_srt),
                    file_name=base + '_cut.srt',
                    mime='text/plain',
                )

        if self.cut_btn:
            if self.upload_video_tab3 is not None and self.upload_srt_tab3 is not None:
                video_name = self._save_file(self.upload_video_tab3.getvalue(), self.upload_video_tab3.name)
                srt_name = self._save_file(self.upload_srt_tab3.getvalue(), self.upload_srt_tab3.name)
                self.args.inputs = ['./temp/' + video_name, './temp/' + srt_name]
                if self.upload_md is not None:
                    md_name = self._save_file(self.upload_md.getvalue(), self.upload_md.name)
                    self.args.inputs.append('./temp/' + md_name)
                st.info(f'开始剪切 {self.upload_video_tab3.name}', icon="ℹ")
                self.cut()
                time.sleep(0.5)
                [base, ext] = video_name.split('.')
                if os.path.exists('./temp/' + base + '_cut.mp4'):
                    st.info(f'{self.upload_video_tab3.name} 剪切处理完成', icon="ℹ")
                    self._read_video('./temp/' + base + '_cut.mp4')
                    self.tab3.video(self.video_contents)
                    self.tab3.download_button(
                        label="下载剪切后视频",
                        data=self.video_contents,
                        file_name='./temp/' + base + '_cut.mp4',
                        mime='video/mp4',
                    )
                else:
                    st.info(f'{self.upload_video_tab3.name} 剪切出错了', icon="🚨")
            else:
                st.info('视频或srt字幕文件未上传', icon="🚨")

    def _save_file(self, bytes_data: bytes, name: str):
        if not os.path.exists('./temp'):
            os.makedirs('./temp')
        md5.update(name.encode(encoding='utf-8'))
        name = str(md5.hexdigest()) + str(time.time()).replace('.', '-') + '.' + name.split('.')[1]
        with open('./temp/' + name, "wb") as f:
            f.write(bytes_data)
        return name

    def transcribe(self):
        self.args.update(self.sampling_rate, self.lang, self.prompt, self.whisper_model, self.device, self.vad)
        self.args.inputs = ['./temp/' + self.name]
        Transcribe(self.args).run()

    def cut(self):
        Cutter(self.args).run()

    def create_page(self):
        st.header('AutoCut: 通过字幕来剪切视频')
        st.write('AutoCut对你的视频自动生成字幕。然后你选择需要保留的句子，AutoCut将对你视频中对应的片段裁切并保存。'
                 '你无需使用视频编辑软件，只需要编辑文本文件即可完成剪切。')
        self.tab1, self.tab2, self.tab3 = st.tabs(["识别视频", "编辑字幕", "剪切视频"])

        with self.tab1:
            self.sampling_rate = st.slider('设置采样率', 10000, 44100, 16000)
            self.whisper_model = st.selectbox('设置模型大小', ('small', 'tiny', 'base', 'medium', 'large'))
            self.lang = st.radio('设置模型语言', ('zh', 'en'), horizontal=True)
            self.prompt = st.text_input('设置模型Prompt（可为空）', '')
            self.device = st.selectbox('选择运行设备', ('none', 'cpu', 'cuda'))
            st.write('> None代表自适应，cpu代表强制使用cpu，cuda代表强制使用gpu')
            self.vad = st.radio('是否使用VAD', ('no', 'yes'), horizontal=True)
            self.upload_video_tab1 = st.file_uploader("选择一个视频文件", type=['mp4', 'mov', 'mkv', 'flv'], key='rec_video')
            self.transcribe_btn = st.button('开始转换')
        with self.tab2:
            self.upload_srt_tab2 = st.file_uploader("上传字幕文件", type=['srt'], key='raw_srt')

        with self.tab3:
            st.write('上传视频')
            self.upload_video_tab3 = st.file_uploader("选择一个视频文件", type=['mp4', 'mov', 'mkv', 'flv'], key='cut_video')
            st.write('上传md文件（非必选）')
            self.upload_md = st.file_uploader("上传md字幕文件", type=['md'], key='md')
            st.write('上传对应srt文件')
            self.upload_srt_tab3 = st.file_uploader("上传srt字幕文件", type=['srt'], key='srt')
            self.cut_btn = st.button('开始剪切')

    def _read_md_file(self, md_fn: str):
        md = MD(md_fn, 'utf-8')
        self.md_contents = md.lines

    def _read_srt_file(self, srt_fn: str):
        with open(srt_fn, encoding='utf-8') as f:
            self.srt_contents = list(srt.parse(f.read()))

    def _read_video(self, video_fn: str):
        with open(video_fn, 'rb') as f:
            self.video_contents = f.read()

    def zip_file(self, file_list: [], zip_file: str):
        with zipfile.ZipFile(zip_file, "w") as zf:
            for file in file_list:
                zf.write(file)


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
            out, _ = Popen(shlex.split('ffprobe -v error -i pipe: -select_streams v -print_format json -show_streams'),
                           stdin=PIPE, stdout=PIPE, bufsize=-1) \
                .communicate(input=bytes_data)
            video_info = json.loads(out)
            # 得到视频的分辨率
            width = (video_info['streams'][0])['width']
            height = (video_info['streams'][0])['height']
            print(video_info)
            print(width, height)

            out, _ = (
                ffmpeg.input('pipe:', threads=0, format='rawvideo', s='{}x{}'.format(width, height))
                .output('pipe:', format="s16le", acodec="pcm_s16le", ac=1, ar=self.args.sampling_rate)
                .run(input=bytes_data, capture_stdout=True, capture_stderr=True)
            )
            print(out)
            logging.info(StringIO(_.decode("utf-8")).read())
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
    def __init__(self, sampling_rate=16000, bitrate='10m', lang='zh', prompt='', whisper_model='small', device=None,
                 vad=False):
        self.inputs = []
        self.encoding = 'utf-8'
        self.sampling_rate = sampling_rate
        self.lang = lang
        self.prompt = prompt
        self.whisper_model = whisper_model
        self.device = device
        self.vad = vad
        self.force = True
        self.bitrate = bitrate

    def update(self, sampling_rate: int, lang: str, prompt: str, whisper_model: str, device: str, vad: str):
        self.sampling_rate = sampling_rate
        self.lang = lang
        self.prompt = prompt
        self.whisper_model = whisper_model
        self.device = device if device != 'none' else None
        self.vad = True if vad == 'yes' else False


if __name__ == '__main__':
    Interface().run()
